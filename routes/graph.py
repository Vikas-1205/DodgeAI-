"""
API routes for Graph operations.

Endpoints:
    GET /graph/node/{node_id}       — single node with metadata
    GET /graph/neighbors/{node_id}  — incoming + outgoing edges
    GET /graph/trace/{node_id}      — full downstream flow tree
"""

from fastapi import APIRouter, HTTPException, status

from graph import build_graph, get_neighbors, trace_flow

router = APIRouter(prefix="/graph", tags=["Graph"])


def _get_graph():
    """Build graph from current DB state."""
    return build_graph()


# ─── GET /graph/node/{node_id} ───────────────────────────────────────────────


@router.get("/node/{node_id}")
def get_node(node_id: str):
    """
    Retrieve a single node and its metadata.

    `node_id` format: ``EntityType:pk`` e.g. ``Order:1``, ``Customer:3``
    """
    G = _get_graph()

    if node_id not in G:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node '{node_id}' not found in graph",
        )

    node_data = dict(G.nodes[node_id])
    return {
        "id": node_id,
        **node_data,
    }


# ─── GET /graph/neighbors/{node_id} ─────────────────────────────────────────


@router.get("/neighbors/{node_id}")
def get_node_neighbors(node_id: str):
    """
    Retrieve all incoming and outgoing neighbors of a node.

    `node_id` format: ``EntityType:pk`` e.g. ``Delivery:1``
    """
    G = _get_graph()

    result = get_neighbors(G, node_id)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"],
        )

    return result


# ─── GET /graph/trace/{node_id} ──────────────────────────────────────────────


@router.get("/trace/{node_id}")
def trace_node_flow(node_id: str):
    """
    Trace the full downstream flow from a starting node (BFS).

    `node_id` format: ``EntityType:pk`` e.g. ``Order:1``

    Returns a nested tree of all reachable entities following
    the business flow: Order → Customer/Products/Deliveries → Invoices → Payments
    """
    G = _get_graph()

    result = trace_flow(G, node_id)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"],
        )

    return result
