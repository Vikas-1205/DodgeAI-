"""
Intent Detector — classifies user queries into intent types.

Intents:
    TRACE  — user wants to trace the flow of a specific entity
             e.g. "trace order 1", "show full flow of invoice 3"
    QUERY  — standard data question routed to NL-to-SQL pipeline

Usage:
    from intent_detector import detect_intent

    intent = detect_intent("trace order 1")
    # intent["type"]        → "trace"
    # intent["entity_type"] → "Order"
    # intent["entity_id"]   → 1
"""

from __future__ import annotations

import re
from typing import Optional


# ─── Entity type mapping ─────────────────────────────────────────────────────
# Maps user-facing keywords to graph node type prefixes.

ENTITY_ALIASES: dict[str, str] = {
    "order": "Order",
    "orders": "Order",
    "delivery": "Delivery",
    "deliveries": "Delivery",
    "shipment": "Delivery",
    "invoice": "Invoice",
    "invoices": "Invoice",
    "bill": "Invoice",
    "payment": "Payment",
    "payments": "Payment",
    "customer": "Customer",
    "customers": "Customer",
    "product": "Product",
    "products": "Product",
}

# Regex entity group for matching
_ENTITY_PATTERN = "|".join(sorted(ENTITY_ALIASES.keys(), key=len, reverse=True))


# ─── Trace patterns ──────────────────────────────────────────────────────────
# Each pattern captures (entity_keyword, id).

TRACE_PATTERNS = [
    # "trace order 1", "trace invoice 123"
    re.compile(
        rf"\btrace\s+(?:the\s+)?({_ENTITY_PATTERN})\s+#?(\d+)\b",
        re.IGNORECASE,
    ),
    # "trace order number 1", "trace invoice no 123"
    re.compile(
        rf"\btrace\s+(?:the\s+)?({_ENTITY_PATTERN})\s+(?:number|no|num|id|#)\s*#?(\d+)\b",
        re.IGNORECASE,
    ),
    # "show full flow of order 1", "show flow of delivery 5"
    re.compile(
        rf"\bshow\s+(?:the\s+)?(?:full\s+)?flow\s+(?:of|for)\s+(?:the\s+)?({_ENTITY_PATTERN})\s+#?(\d+)\b",
        re.IGNORECASE,
    ),
    # "track order 1", "track delivery 5"
    re.compile(
        rf"\btrack\s+(?:the\s+)?({_ENTITY_PATTERN})\s+#?(\d+)\b",
        re.IGNORECASE,
    ),
    # "flow of order 1", "flow for invoice 2"
    re.compile(
        rf"\bflow\s+(?:of|for)\s+(?:the\s+)?({_ENTITY_PATTERN})\s+#?(\d+)\b",
        re.IGNORECASE,
    ),
    # "order 1 flow", "invoice 3 trace"
    re.compile(
        rf"\b({_ENTITY_PATTERN})\s+#?(\d+)\s+(?:flow|trace|tracking|chain)\b",
        re.IGNORECASE,
    ),
    # "what happened to order 1", "what happened with delivery 3"
    re.compile(
        rf"\bwhat\s+happen(?:ed|s)?\s+(?:to|with)\s+(?:the\s+)?({_ENTITY_PATTERN})\s+#?(\d+)\b",
        re.IGNORECASE,
    ),
    # "status of order 1", "status for delivery 5" (trace-like)
    re.compile(
        rf"\b(?:full\s+)?status\s+(?:of|for)\s+(?:the\s+)?({_ENTITY_PATTERN})\s+#?(\d+)\b",
        re.IGNORECASE,
    ),
]


# ─── Broad trace keyword check ───────────────────────────────────────────────
# If none of the structured patterns match, do a loose check for trace-like
# keywords paired with an entity+ID anywhere in the query.

_TRACE_KEYWORDS = re.compile(
    r"\b(trace|track|flow|chain|journey|lifecycle|full\s+status)\b",
    re.IGNORECASE,
)

_LOOSE_ENTITY_ID = re.compile(
    rf"\b({_ENTITY_PATTERN})\s+#?(\d+)\b",
    re.IGNORECASE,
)


# ─── Public API ───────────────────────────────────────────────────────────────


def detect_intent(query: str) -> dict:
    """
    Classify a user query into an intent.

    Parameters
    ----------
    query : str
        The raw user query.

    Returns
    -------
    dict
        Always contains ``"type"`` (``"trace"`` or ``"query"``).

        For trace intents::

            {
                "type": "trace",
                "entity_type": "Order",     # graph node type
                "entity_id": 1,             # primary key
                "node_id": "Order:1",       # ready-to-use graph node ID
            }

        For regular queries::

            {"type": "query"}
    """
    text = query.strip()

    # Try structured patterns first
    for pattern in TRACE_PATTERNS:
        match = pattern.search(text)
        if match:
            return _build_trace_intent(match.group(1), match.group(2))

    # Fallback: trace keyword + entity:id anywhere in the query
    if _TRACE_KEYWORDS.search(text):
        entity_match = _LOOSE_ENTITY_ID.search(text)
        if entity_match:
            return _build_trace_intent(entity_match.group(1), entity_match.group(2))

    return {"type": "query"}


def _build_trace_intent(entity_keyword: str, raw_id: str) -> dict:
    """Build a trace intent dict from matched groups."""
    entity_type = ENTITY_ALIASES.get(entity_keyword.lower(), entity_keyword.title())
    entity_id = raw_id.strip()
    return {
        "type": "trace",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "node_id": f"{entity_type}:{entity_id}",
    }


# ─── CLI test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_queries = [
        "trace order 740506",
        "Trace the invoice 90504248",
        "show full flow of order 740556",
        "show flow for delivery 80738076",
        "track order 740506",
        "flow of invoice 90504259",
        "order 740506 flow",
        "what happened to order 740506",
        "invoice 90504248 trace",
        "full status of delivery 80738076",
        "trace order number 740506",
        "trace order #740506",
        "Can you trace the journey of order 740506?",
        "show all customers",
        "how many orders are pending?",
        "total revenue by customer",
        "what is the weather?",
    ]

    print("Intent Detection Tests")
    print("=" * 60)
    for q in test_queries:
        result = detect_intent(q)
        tag = "TRACE" if result["type"] == "trace" else "QUERY"
        extra = f" → {result.get('node_id', '')}" if tag == "TRACE" else ""
        print(f"  [{tag:5s}] {q}{extra}")
