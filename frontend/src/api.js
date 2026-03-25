const API_BASE = '/api/v1';

export async function fetchGraphData() {
    /* Build an adjacency structure from the graph endpoints.
       We fetch every node type by querying the DB-backed endpoints. */
    const tables = ['customers', 'products', 'orders', 'order_items', 'deliveries', 'invoices', 'payments'];
    const nodes = [];
    const links = [];

    const responses = await Promise.all(
        tables.map(t => fetch(`${API_BASE}/${t}`).then(r => r.ok ? r.json() : []))
    );

    const [customers, products, orders, orderItems, deliveries, invoices, payments] = responses;

    /* Nodes */
    customers.forEach(c => nodes.push({ id: `Customer:${c.id}`, type: 'Customer', label: c.name, ...c }));
    products.forEach(p => nodes.push({ id: `Product:${p.id}`, type: 'Product', label: p.name, ...p }));
    orders.forEach(o => nodes.push({ id: `Order:${o.id}`, type: 'Order', label: `Order #${o.id}`, ...o }));
    orderItems.forEach(oi => nodes.push({ id: `OrderItem:${oi.id}`, type: 'OrderItem', label: `Item #${oi.id}`, ...oi }));
    deliveries.forEach(d => nodes.push({ id: `Delivery:${d.id}`, type: 'Delivery', label: d.tracking_number || `Del #${d.id}`, ...d }));
    invoices.forEach(i => nodes.push({ id: `Invoice:${i.id}`, type: 'Invoice', label: i.invoice_number || `Inv #${i.id}`, ...i }));
    payments.forEach(p => nodes.push({ id: `Payment:${p.id}`, type: 'Payment', label: `Pay #${p.id}`, ...p }));

    /* Edges */
    orders.forEach(o => {
        links.push({ source: `Order:${o.id}`, target: `Customer:${o.customer_id}`, rel: 'PLACED_BY' });
    });
    orderItems.forEach(oi => {
        links.push({ source: `Order:${oi.order_id}`, target: `Product:${oi.product_id}`, rel: 'CONTAINS' });
    });
    deliveries.forEach(d => {
        links.push({ source: `Order:${d.order_id}`, target: `Delivery:${d.id}`, rel: 'FULFILLED_BY' });
    });
    invoices.forEach(i => {
        links.push({ source: `Delivery:${i.delivery_id}`, target: `Invoice:${i.id}`, rel: 'BILLED_BY' });
    });
    payments.forEach(p => {
        links.push({ source: `Invoice:${p.invoice_id}`, target: `Payment:${p.id}`, rel: 'PAID_BY' });
    });

    return { nodes, links };
}

export async function sendChatMessage(query) {
    const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}
