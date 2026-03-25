"""
Answer Generator — converts SQL query results into natural language using an LLM.

Takes the user's original question and the raw SQL result rows, then produces
a clean, human-readable answer grounded strictly in the data.

Usage:
    from answer_generator import generate_answer

    answer = generate_answer(
        question="How many customers do we have?",
        sql="SELECT COUNT(*) AS total FROM customers;",
        result={"columns": ["total"], "rows": [{"total": 5}], "row_count": 1},
    )
    # answer["response"] → "There are 5 customers in the system."
"""

from __future__ import annotations

import os
import json
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


# ─── Prompt template ─────────────────────────────────────────────────────────


ANSWER_SYSTEM_PROMPT = """You are a data analyst assistant. Your job is to convert SQL query results into clear, natural language answers.

STRICT RULES:
1. Answer ONLY based on the data provided. Never make up information.
2. If the result is empty (0 rows), say so clearly: "No matching records were found."
3. Keep answers concise and professional — 1-3 sentences for simple results, a brief summary for larger result sets.
4. For numerical data, include the actual numbers from the results.
5. For tabular data with many rows, summarize the key findings rather than listing every row.
6. Do NOT mention SQL, queries, databases, tables, or columns in your response — speak as if you are directly answering a business question.
7. Do NOT add information that is not present in the results.
8. Use proper formatting: numbers, currency (₹ for amounts), dates in readable format.
9. If the data contains names, mention them specifically.
10. Do NOT wrap your response in quotes or markdown. Just provide the plain text answer.
"""


# ─── LLM provider calls ──────────────────────────────────────────────────────


def _get_provider() -> tuple[str, str]:
    """Auto-detect LLM provider from environment variables."""
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    if groq_key:
        return "groq", groq_key
    if gemini_key:
        return "gemini", gemini_key

    raise EnvironmentError(
        "No LLM API key found. Set either GROQ_API_KEY or GEMINI_API_KEY."
    )


def _call_groq(system_prompt: str, user_message: str, api_key: str) -> str:
    response = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.3,
            "max_tokens": 512,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def _call_gemini(system_prompt: str, user_message: str, api_key: str) -> str:
    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_prompt}\n\n{user_message}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 512,
            },
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def _call_llm(system_prompt: str, user_message: str) -> str:
    """Route to the appropriate LLM provider."""
    provider, api_key = _get_provider()
    if provider == "groq":
        return _call_groq(system_prompt, user_message, api_key)
    else:
        return _call_gemini(system_prompt, user_message, api_key)


# ─── Result formatting ───────────────────────────────────────────────────────


def _format_result_for_prompt(result: dict) -> str:
    """
    Format SQL result dict into a compact string for the LLM prompt.
    Limits rows to avoid exceeding token limits.
    """
    row_count = result.get("row_count", 0)
    columns = result.get("columns", [])
    rows = result.get("rows", [])

    if row_count == 0:
        return "The query returned 0 rows (no matching data)."

    # Cap at 50 rows to stay within token limits
    display_rows = rows[:50]
    truncated = row_count > 50

    lines = [
        f"Row count: {row_count}",
        f"Columns: {', '.join(columns)}",
        "",
        "Data:",
        json.dumps(display_rows, indent=2, default=str),
    ]

    if truncated:
        lines.append(f"\n... (showing first 50 of {row_count} total rows)")

    return "\n".join(lines)


# ─── Public API ───────────────────────────────────────────────────────────────


def generate_answer(
    question: str,
    sql: str,
    result: dict,
) -> dict:
    """
    Generate a natural language answer from a SQL query result.

    Parameters
    ----------
    question : str
        The user's original natural language question.
    sql : str
        The SQL query that was executed.
    result : dict
        The result from ``execute_sql()``, containing ``columns``, ``rows``,
        ``row_count``, ``success``, and ``error``.

    Returns
    -------
    dict
        ``{"response": "...", "error": None}`` on success.
        ``{"response": None, "error": "..."}`` on failure.
    """
    # Handle failed queries
    if not result.get("success", False):
        error_msg = result.get("error", "Unknown query error")
        return {
            "response": f"I couldn't retrieve the data: {error_msg}",
            "error": None,
        }

    # Handle empty results without calling LLM
    if result.get("row_count", 0) == 0:
        return {
            "response": "No matching records were found for your query.",
            "error": None,
        }

    # Build the user message
    formatted_data = _format_result_for_prompt(result)
    user_message = (
        f"User's question: {question}\n\n"
        f"SQL query used: {sql}\n\n"
        f"Query results:\n{formatted_data}\n\n"
        f"Provide a clear, natural language answer based strictly on this data."
    )

    try:
        raw_answer = _call_llm(ANSWER_SYSTEM_PROMPT, user_message)
        return {"response": raw_answer, "error": None}

    except EnvironmentError as e:
        return {"response": None, "error": str(e)}

    except httpx.HTTPStatusError as e:
        logger.error("LLM API error: %s", e)
        return {"response": None, "error": f"LLM API error: {e.response.status_code}"}

    except Exception as e:
        logger.error("Answer generation failed: %s", e)
        return {"response": None, "error": f"Answer generation failed: {str(e)}"}


# ─── CLI demo ────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    # Demo with mock data (no LLM call needed for empty result)
    print("─── Test: Empty result ───")
    ans = generate_answer(
        question="Show customers from Mars",
        sql="SELECT * FROM customers WHERE city = 'Mars';",
        result={"success": True, "columns": ["id", "name"], "rows": [], "row_count": 0},
    )
    print(f"  ✅ {ans['response']}")

    print("\n─── Test: Failed query ───")
    ans = generate_answer(
        question="Something broken",
        sql="INVALID SQL",
        result={"success": False, "error": "SQL syntax error", "columns": [], "rows": [], "row_count": 0},
    )
    print(f"  ✅ {ans['response']}")

    print("\n─── Test: With LLM (requires API key) ───")
    ans = generate_answer(
        question="How many customers do we have?",
        sql="SELECT COUNT(*) AS total FROM customers;",
        result={"success": True, "columns": ["total"], "rows": [{"total": 5}], "row_count": 1},
    )
    if ans["error"]:
        print(f"  ⚠  {ans['error']}")
    else:
        print(f"  ✅ {ans['response']}")
