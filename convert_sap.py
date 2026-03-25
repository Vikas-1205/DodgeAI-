import json
import csv
import glob
from collections import defaultdict

def iter_jsonl(pattern):
    for filepath in glob.glob(pattern):
        with open(filepath, 'r') as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)

def main():
    print("Parsing Customers...")
    customers = []
    # Just need billing/shipping address mapping
    addresses = []
    seen_customers = set()

    for row in iter_jsonl("data_sap/sap-o2c-data/business_partners/*.jsonl"):
        cid = row.get("businessPartner")
        if cid and cid not in seen_customers:
            seen_customers.add(cid)
            name = row.get("businessPartnerFullName", "")
            customers.append({
                "id": cid,
                "name": name if name else "Unknown",
                "email": f"{cid}@example.com",
                "phone": ""
            })
            # Add default addresses
            addresses.append({
                "id": f"A_B_{cid}",
                "customer_id": cid,
                "address_type": "billing",
                "street": "123 Main",
                "city": "SAP City",
                "country": "Germany"
            })
            addresses.append({
                "id": f"A_S_{cid}",
                "customer_id": cid,
                "address_type": "shipping",
                "street": "123 Main",
                "city": "SAP City",
                "country": "Germany"
            })

    print(f"Loaded {len(customers)} customers.")

    print("Parsing Products...")
    products = []
    seen_products = set()
    for row in iter_jsonl("data_sap/sap-o2c-data/products/*.jsonl"):
        pid = row.get("product")
        if pid and pid not in seen_products:
            seen_products.add(pid)
            products.append({
                "id": pid,
                "name": f"Product {row.get('productOldId', pid)}",
                "sku": pid,
                "unit_price": 100.0,  # default
                "stock_quantity": 1000
            })
    print(f"Loaded {len(products)} products.")

    print("Parsing Orders...")
    orders = []
    for row in iter_jsonl("data_sap/sap-o2c-data/sales_order_headers/*.jsonl"):
        oid = row.get("salesOrder")
        cid = row.get("soldToParty")
        
        # Ensure customer exists or use dummy
        if cid not in seen_customers:
            seen_customers.add(cid)
            customers.append({"id": cid, "name": f"Customer {cid}", "email": "", "phone": ""})
            addresses.extend([{
                "id": f"A_B_{cid}", "customer_id": cid, "address_type": "billing", "street": "", "city": "", "country": ""
            }, {
                "id": f"A_S_{cid}", "customer_id": cid, "address_type": "shipping", "street": "", "city": "", "country": ""
            }])

        orders.append({
            "id": oid,
            "customer_id": cid,
            "shipping_address_id": f"A_S_{cid}",
            "billing_address_id": f"A_B_{cid}",
            "order_date": row.get("creationDate"),
            "status": row.get("overallDeliveryStatus", "completed"),
            "total_amount": row.get("totalNetAmount", 0)
        })

    print(f"Loaded {len(orders)} orders.")

    print("Parsing Order Items...")
    order_items = []
    for row in iter_jsonl("data_sap/sap-o2c-data/sales_order_items/*.jsonl"):
        oid = row.get("salesOrder")
        pid = row.get("material")
        qty = row.get("requestedQuantity", 1)
        net = row.get("netAmount", 0)

        if pid not in seen_products:
            seen_products.add(pid)
            products.append({"id": pid, "name": f"Product {pid}", "sku": pid, "unit_price": 0, "stock_quantity": 0})

        order_items.append({
            "id": f"{oid}_{row.get('salesOrderItem')}",
            "order_id": oid,
            "product_id": pid,
            "quantity": qty,
            "unit_price": round(float(net) / max(float(qty), 1), 2),
            "total_price": net
        })

    print("Parsing Deliveries...")
    # Map delivery -> order
    deliv_to_order = {}
    for row in iter_jsonl("data_sap/sap-o2c-data/outbound_delivery_items/*.jsonl"):
        did = row.get("deliveryDocument")
        oid = row.get("referenceSdDocument") # Usually sales order
        if did and oid:
            deliv_to_order[did] = oid
    
    deliveries = []
    for did, oid in deliv_to_order.items():
        deliveries.append({
            "id": did,
            "order_id": oid,
            "status": "delivered",
            "shipped_date": "2025-01-01T00:00:00.000Z",
            "delivered_date": "2025-01-02T00:00:00.000Z",
            "tracking_number": f"TRK-{did}",
            "carrier": "SAP Logistics"
        })
    print(f"Loaded {len(deliveries)} deliveries.")

    print("Parsing Invoices...")
    inv_to_deliv = {}
    for row in iter_jsonl("data_sap/sap-o2c-data/billing_document_items/*.jsonl"):
        iid = row.get("billingDocument")
        ref = row.get("referenceSdDocument")
        # if reference is an 80 million series it usually is a delivery
        if iid and ref:
            inv_to_deliv[iid] = ref

    invoices = []
    for row in iter_jsonl("data_sap/sap-o2c-data/billing_document_headers/*.jsonl"):
        iid = row.get("billingDocument")
        did = inv_to_deliv.get(iid)
        
        # If no delivery linked, link to a dummy delivery or skip?
        # A billing doc MUST link to a delivery in our strict schema, unless we relax it.
        # Let's create dummy deliveries for invoices that lack one but link back to the order.
        if not did:
            continue # skipping detached invoices for clean graph

        invoices.append({
            "id": iid,
            "delivery_id": did,
            "invoice_number": f"INV-{iid}",
            "invoice_date": row.get("creationDate"),
            "due_date": row.get("billingDocumentDate"),
            "total_amount": row.get("totalNetAmount", 0),
            "status": "paid"
        })
    print(f"Loaded {len(invoices)} invoices.")

    print("Parsing Payments...")
    payments = []
    for row in iter_jsonl("data_sap/sap-o2c-data/journal_entry_items_accounts_receivable/*.jsonl"):
        pid = row.get("accountingDocument")
        iid = row.get("referenceDocument") # Points to billing document
        amt = row.get("amountInCompanyCodeCurrency", 0)
        
        # only want payments against an invoice we know
        # Usually positive amounts are receivables, negative are payments, let's just take all non-zero
        if iid and abs(float(amt)) > 0:
            payments.append({
                "id": f"{pid}_{row.get('accountingDocumentItem')}",
                "invoice_id": iid,
                "payment_date": row.get("postingDate"),
                "amount": abs(float(amt)),
                "method": "bank_transfer",
                "transaction_ref": f"TXN-{pid}-{row.get('accountingDocumentItem')}",
                "status": "completed"
            })
    print(f"Loaded {len(payments)} payments.")

    def write_csv(filename, data):
        if not data: return
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        print(f"Wrote {filename}")

    # Write out
    import os
    os.makedirs("data", exist_ok=True)
    write_csv("data/customers.csv", list(customers))
    write_csv("data/addresses.csv", addresses)
    write_csv("data/products.csv", list(products))
    write_csv("data/orders.csv", orders)
    write_csv("data/order_items.csv", order_items)
    write_csv("data/deliveries.csv", deliveries)
    write_csv("data/invoices.csv", invoices)
    write_csv("data/payments.csv", payments)

if __name__ == '__main__':
    main()
