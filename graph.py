"""
Graph Construction Module — converts database entities into a NetworkX directed graph.

Node types:  Customer, Product, Order, OrderItem, Delivery, Invoice, Payment
Edge types:  PLACED_BY, CONTAINS, FULFILLED_BY, BILLED_BY, PAID_BY

Usage:
    from graph import build_graph, get_neighbors, trace_flow

    G = build_graph()          # build from current DB state
    get_neighbors(G, "Order:1")
    trace_flow(G, "Order:1")
"""

from __future__ import annotations

from typing import Optional

import networkx as nx
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Customer, Product, Order, OrderItem, Delivery, Invoice, Payment


# ─── Node ID convention ──────────────────────────────────────────────────────
# Every node is keyed as  "<EntityType>:<pk>"
# e.g. "Customer:1", "Order:3", "Payment:7"


def _node_id(entity_type: str, pk: int) -> str:
    return f"{entity_type}:{pk}"


# ─── Metadata extractors ─────────────────────────────────────────────────────
# Each returns a flat dict of serialisable attributes to store on the node.


def _customer_meta(c: Customer) -> dict:
    return {
        "type": "Customer",
        "name": c.name,
        "email": c.email,
        "phone": c.phone or "",
    }


def _product_meta(p: Product) -> dict:
    return {
        "type": "Product",
        "name": p.name,
        "sku": p.sku,
        "unit_price": p.unit_price,
        "stock_quantity": p.stock_quantity,
    }


def _order_meta(o: Order) -> dict:
    return {
        "type": "Order",
        "order_date": str(o.order_date) if o.order_date else "",
        "status": o.status,
        "total_amount": o.total_amount,
        "customer_id": o.customer_id,
    }


def _order_item_meta(oi: OrderItem) -> dict:
    return {
        "type": "OrderItem",
        "order_id": oi.order_id,
        "product_id": oi.product_id,
        "quantity": oi.quantity,
        "unit_price": oi.unit_price,
        "total_price": oi.total_price,
    }


def _delivery_meta(d: Delivery) -> dict:
    return {
        "type": "Delivery",
        "order_id": d.order_id,
        "status": d.status,
        "tracking_number": d.tracking_number or "",
        "carrier": d.carrier or "",
        "shipped_date": str(d.shipped_date) if d.shipped_date else "",
        "delivered_date": str(d.delivered_date) if d.delivered_date else "",
    }


def _invoice_meta(i: Invoice) -> dict:
    return {
        "type": "Invoice",
        "delivery_id": i.delivery_id,
        "invoice_number": i.invoice_number,
        "total_amount": i.total_amount,
        "status": i.status,
        "invoice_date": str(i.invoice_date) if i.invoice_date else "",
        "due_date": str(i.due_date) if i.due_date else "",
    }


def _payment_meta(p: Payment) -> dict:
    return {
        "type": "Payment",
        "invoice_id": p.invoice_id,
        "amount": p.amount,
        "method": p.method,
        "status": p.status,
        "transaction_ref": p.transaction_ref or "",
        "payment_date": str(p.payment_date) if p.payment_date else "",
    }


# ─── build_graph ──────────────────────────────────────────────────────────────


def build_graph(db: Optional[Session] = None) -> nx.DiGraph:
    """
    Query all entities from the database and construct a directed graph.

    Node IDs follow the pattern ``EntityType:pk`` (e.g. ``Order:1``).
    Each node carries a ``type`` attribute plus entity-specific metadata.
    Each edge carries a ``relationship`` attribute.

    Parameters
    ----------
    db : Session, optional
        An existing SQLAlchemy session.  If *None*, a new session is
        created (and closed) automatically.

    Returns
    -------
    nx.DiGraph
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        G = nx.DiGraph()

        # ── Nodes ────────────────────────────────────────────────────────

        customers = db.query(Customer).all()
        for c in customers:
            G.add_node(_node_id("Customer", c.id), **_customer_meta(c))

        products = db.query(Product).all()
        for p in products:
            G.add_node(_node_id("Product", p.id), **_product_meta(p))

        orders = db.query(Order).all()
        for o in orders:
            G.add_node(_node_id("Order", o.id), **_order_meta(o))

        order_items = db.query(OrderItem).all()
        for oi in order_items:
            G.add_node(_node_id("OrderItem", oi.id), **_order_item_meta(oi))

        deliveries = db.query(Delivery).all()
        for d in deliveries:
            G.add_node(_node_id("Delivery", d.id), **_delivery_meta(d))

        invoices = db.query(Invoice).all()
        for i in invoices:
            G.add_node(_node_id("Invoice", i.id), **_invoice_meta(i))

        payments = db.query(Payment).all()
        for p in payments:
            G.add_node(_node_id("Payment", p.id), **_payment_meta(p))

        # ── Edges ────────────────────────────────────────────────────────

        # Order → Customer  (PLACED_BY)
        for o in orders:
            G.add_edge(
                _node_id("Order", o.id),
                _node_id("Customer", o.customer_id),
                relationship="PLACED_BY",
            )

        # Order → Product  (CONTAINS) via OrderItems
        for oi in order_items:
            G.add_edge(
                _node_id("Order", oi.order_id),
                _node_id("Product", oi.product_id),
                relationship="CONTAINS",
                quantity=oi.quantity,
                unit_price=oi.unit_price,
                total_price=oi.total_price,
            )

        # Order → Delivery  (FULFILLED_BY)
        for d in deliveries:
            G.add_edge(
                _node_id("Order", d.order_id),
                _node_id("Delivery", d.id),
                relationship="FULFILLED_BY",
            )

        # Delivery → Invoice  (BILLED_BY)
        for i in invoices:
            G.add_edge(
                _node_id("Delivery", i.delivery_id),
                _node_id("Invoice", i.id),
                relationship="BILLED_BY",
            )

        # Invoice → Payment  (PAID_BY)
        for p in payments:
            G.add_edge(
                _node_id("Invoice", p.invoice_id),
                _node_id("Payment", p.id),
                relationship="PAID_BY",
            )

        return G

    finally:
        if own_session:
            db.close()


# ─── get_neighbors ────────────────────────────────────────────────────────────


def get_neighbors(G: nx.DiGraph, node_id: str) -> dict:
    """
    Return the outgoing and incoming neighbors of a node with edge metadata.

    Parameters
    ----------
    G : nx.DiGraph
        The graph returned by ``build_graph()``.
    node_id : str
        Node identifier, e.g. ``"Order:1"``.

    Returns
    -------
    dict
        ``{ "node": {...}, "outgoing": [...], "incoming": [...] }``
    """
    if node_id not in G:
        return {"error": f"Node '{node_id}' not found in graph"}

    node_data = dict(G.nodes[node_id])

    outgoing = []
    for _, target, edge_data in G.out_edges(node_id, data=True):
        outgoing.append({
            "target": target,
            "target_type": G.nodes[target].get("type", ""),
            **edge_data,
        })

    incoming = []
    for source, _, edge_data in G.in_edges(node_id, data=True):
        incoming.append({
            "source": source,
            "source_type": G.nodes[source].get("type", ""),
            **edge_data,
        })

    return {
        "node": {"id": node_id, **node_data},
        "outgoing": outgoing,
        "incoming": incoming,
    }


# ─── trace_flow ───────────────────────────────────────────────────────────────


def trace_flow(G: nx.DiGraph, start_node_id: str) -> dict:
    """
    Trace the full downstream flow from a starting node using BFS.

    This follows all outgoing edges recursively, building a tree of the
    entire business flow.  For example, starting from ``Order:1`` would
    yield the chain:

        Order → Customer, Products, Deliveries → Invoices → Payments

    Parameters
    ----------
    G : nx.DiGraph
        The graph returned by ``build_graph()``.
    start_node_id : str
        The starting node, e.g. ``"Order:1"``.

    Returns
    -------
    dict
        A nested structure::

            {
                "start": "Order:1",
                "nodes_visited": ["Order:1", ...],
                "edges_traversed": [{"from": ..., "to": ..., "relationship": ...}, ...],
                "flow": [
                    {"node": "Order:1", "type": "Order", "metadata": {...},
                     "children": [
                         {"node": "Delivery:1", "type": "Delivery", ...},
                         ...
                     ]},
                ]
            }
    """
    if start_node_id not in G:
        return {"error": f"Node '{start_node_id}' not found in graph"}

    visited_nodes: list[str] = []
    edges_traversed: list[dict] = []

    def _build_tree(node_id: str, seen: set) -> dict:
        seen.add(node_id)
        visited_nodes.append(node_id)

        node_data = dict(G.nodes[node_id])
        children = []

        for _, target, edge_data in G.out_edges(node_id, data=True):
            edges_traversed.append({
                "from": node_id,
                "to": target,
                "relationship": edge_data.get("relationship", ""),
            })
            if target not in seen:
                children.append(_build_tree(target, seen))

        return {
            "node": node_id,
            "type": node_data.get("type", ""),
            "metadata": node_data,
            "children": children,
        }

    flow_tree = _build_tree(start_node_id, set())

    return {
        "start": start_node_id,
        "nodes_visited": visited_nodes,
        "edges_traversed": edges_traversed,
        "flow": [flow_tree],
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────


def _print_graph_stats(G: nx.DiGraph):
    """Print a summary of the graph."""
    print("\n" + "=" * 55)
    print("  GRAPH SUMMARY")
    print("=" * 55)
    print(f"  Total nodes : {G.number_of_nodes()}")
    print(f"  Total edges : {G.number_of_edges()}")

    # Node counts by type
    type_counts: dict[str, int] = {}
    for _, data in G.nodes(data=True):
        t = data.get("type", "Unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    print("\n  Nodes by type:")
    for t in sorted(type_counts):
        print(f"    {t:<15} {type_counts[t]:>5}")

    # Edge counts by relationship
    rel_counts: dict[str, int] = {}
    for _, _, data in G.edges(data=True):
        r = data.get("relationship", "Unknown")
        rel_counts[r] = rel_counts.get(r, 0) + 1

    print("\n  Edges by relationship:")
    for r in sorted(rel_counts):
        print(f"    {r:<20} {rel_counts[r]:>5}")

    print("=" * 55)


def _print_trace(trace: dict):
    """Pretty-print a trace_flow result."""
    if "error" in trace:
        print(f"  ⚠  {trace['error']}")
        return

    print(f"\n  Trace from: {trace['start']}")
    print(f"  Nodes visited : {len(trace['nodes_visited'])}")
    print(f"  Edges traversed: {len(trace['edges_traversed'])}")

    def _print_tree(node: dict, indent: int = 2):
        prefix = " " * indent
        meta = node.get("metadata", {})
        label = meta.get("name", meta.get("invoice_number", meta.get("tracking_number", "")))
        extra = f" — {label}" if label else ""
        print(f"{prefix}• {node['node']} [{node['type']}]{extra}")
        for child in node.get("children", []):
            _print_tree(child, indent + 4)

    print()
    for root in trace["flow"]:
        _print_tree(root)


if __name__ == "__main__":
    from database import engine, Base
    import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    G = build_graph()
    _print_graph_stats(G)

    # Demo: trace from first order if it exists
    if "Order:1" in G:
        print("\n─── trace_flow('Order:1') ─────────────────────────────")
        _print_trace(trace_flow(G, "Order:1"))

    # Demo: get_neighbors for first delivery
    if "Delivery:1" in G:
        print("\n─── get_neighbors('Delivery:1') ───────────────────────")
        info = get_neighbors(G, "Delivery:1")
        print(f"  Node: {info['node']}")
        print(f"  Outgoing ({len(info['outgoing'])}):")
        for e in info["outgoing"]:
            print(f"    → {e['target']} [{e.get('relationship', '')}]")
        print(f"  Incoming ({len(info['incoming'])}):")
        for e in info["incoming"]:
            print(f"    ← {e['source']} [{e.get('relationship', '')}]")

    print()
