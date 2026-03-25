"""
Chat endpoint — orchestrates the full conversational pipeline.

POST /chat
    Body: {"query": "How many customers do we have?"}

Two flows:
    1. TRACE intent → graph traversal (trace_flow)
    2. QUERY intent → NL → SQL → execute → answer (LLM pipeline)

Response:
    {
        "query": "...",
        "intent": "query" | "trace",
        "sql": "..." | null,
        "result": [...],
        "answer": "..."
    }
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from guardrails import check_relevance
from intent_detector import detect_intent
from nl_to_sql import generate_sql
from query_executor import execute_sql
from answer_generator import generate_answer
from graph import build_graph, trace_flow


router = APIRouter(tags=["Chat"])


# ─── Request / Response schemas ──────────────────────────────────────────────


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Natural language question")


class ChatResponse(BaseModel):
    query: str
    intent: str = "query"
    sql: str | None = None
    result: list = []
    answer: str


# ─── Trace flow formatter ────────────────────────────────────────────────────


def _format_trace_answer(trace_result: dict) -> str:
    """Convert a trace_flow result into a step-by-step readable chain."""
    if "error" in trace_result:
        return trace_result["error"]

    edges = trace_result.get("edges_traversed", [])
    if not edges:
        return f"No outgoing connections found from {trace_result['start']}."

    flow_tree = trace_result.get("flow", [{}])[0]
    lines = [f"**Flow trace from {trace_result['start']}:**\n"]

    def _walk(node: dict, depth: int = 0):
        indent = "  " * depth
        node_id = node["node"]
        node_type = node.get("type", "")
        meta = node.get("metadata", {})

        # Pick a human-friendly label
        label = (
            meta.get("name")
            or meta.get("invoice_number")
            or meta.get("tracking_number")
            or meta.get("transaction_ref")
            or ""
        )
        status = meta.get("status", "")

        detail_parts = []
        if label:
            detail_parts.append(label)
        if status:
            detail_parts.append(f"status: {status}")

        # Add amounts where relevant
        amount = meta.get("total_amount") or meta.get("amount")
        if amount:
            detail_parts.append(f"₹{amount:,.2f}")

        detail = f" — {', '.join(detail_parts)}" if detail_parts else ""

        # Find the relationship edge leading to this node
        arrow = "→" if depth > 0 else "•"
        lines.append(f"{indent}{arrow} **{node_type}** (#{node_id.split(':')[1]}){detail}")

        for child in node.get("children", []):
            # Get relationship label
            rel = ""
            for edge in edges:
                if edge["from"] == node_id and edge["to"] == child["node"]:
                    rel = edge.get("relationship", "")
                    break
            if rel:
                lines.append(f"{indent}  ↓ _{rel}_")
            _walk(child, depth + 1)

    _walk(flow_tree)
    return "\n".join(lines)


def _trace_result_to_list(trace_result: dict) -> list:
    """Convert trace edges into a flat list of step dicts for the result field."""
    steps = []
    for edge in trace_result.get("edges_traversed", []):
        steps.append({
            "from": edge["from"],
            "to": edge["to"],
            "relationship": edge.get("relationship", ""),
        })
    return steps


# ─── POST /chat ──────────────────────────────────────────────────────────────


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Full conversational flow:
    1. Guardrail check (pre-LLM filter for irrelevant queries)
    2. Detect intent (trace vs query)
    3. Route to graph traversal OR NL→SQL→execute→answer
    4. Return structured response
    """
    user_query = request.query.strip()

    # ── Guardrail: reject irrelevant queries before any LLM call ──────
    rejection = check_relevance(user_query)
    if rejection:
        return ChatResponse(
            query=user_query,
            intent="query",
            sql=None,
            result=[],
            answer=rejection,
        )

    # ── Intent detection ──────────────────────────────────────────────
    intent = detect_intent(user_query)

    # ── TRACE flow ────────────────────────────────────────────────────
    if intent["type"] == "trace":
        node_id = intent["node_id"]

        try:
            G = build_graph()
        except Exception as e:
            return ChatResponse(
                query=user_query,
                intent="trace",
                answer=f"Failed to build graph: {str(e)}",
            )

        trace_result = trace_flow(G, node_id)

        if "error" in trace_result:
            return ChatResponse(
                query=user_query,
                intent="trace",
                result=[],
                answer=f"{trace_result['error']}. Please check the ID and try again.",
            )

        return ChatResponse(
            query=user_query,
            intent="trace",
            sql=None,
            result=_trace_result_to_list(trace_result),
            answer=_format_trace_answer(trace_result),
        )

    # ── QUERY flow (NL → SQL → execute → answer) ─────────────────────
    sql_result = generate_sql(user_query)

    if sql_result["error"]:
        return ChatResponse(
            query=user_query,
            intent="query",
            sql=None,
            result=[],
            answer=sql_result["error"],
        )

    sql = sql_result["sql"]

    exec_result = execute_sql(sql)

    if not exec_result["success"]:
        return ChatResponse(
            query=user_query,
            intent="query",
            sql=sql,
            result=[],
            answer=f"I generated a query but it failed to execute: {exec_result['error']}",
        )

    rows = exec_result["rows"]

    answer_result = generate_answer(
        question=user_query,
        sql=sql,
        result=exec_result,
    )

    answer = answer_result["response"] if answer_result["response"] else (
        answer_result["error"] or "Unable to generate an answer."
    )

    return ChatResponse(
        query=user_query,
        intent="query",
        sql=sql,
        result=rows,
        answer=answer,
    )
