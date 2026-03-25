"""
Natural Language to SQL — converts user queries into safe SQL using an LLM.

Supports two providers (auto-detected from environment variables):
    1. Groq   — set GROQ_API_KEY
    2. Gemini — set GEMINI_API_KEY

Usage:
    from nl_to_sql import generate_sql

    result = generate_sql("Show all customers from Bangalore")
    # result["sql"]   → "SELECT * FROM customers ..."
    # result["error"] → None or error message
"""

from __future__ import annotations

import os
import re
import json
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


# ─── Allowed tables & schema context ─────────────────────────────────────────


ALLOWED_TABLES = {
    "customers",
    "addresses",
    "products",
    "orders",
    "order_items",
    "deliveries",
    "invoices",
    "payments",
}

SCHEMA_DDL = """
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(50),
    created_at DATETIME,
    updated_at DATETIME
);

CREATE TABLE addresses (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    address_type VARCHAR(20),       -- 'shipping' or 'billing'
    street VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100) NOT NULL DEFAULT 'India',
    is_default INTEGER DEFAULT 0,
    created_at DATETIME,
    updated_at DATETIME
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sku VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    unit_price FLOAT NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    created_at DATETIME,
    updated_at DATETIME
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    shipping_address_id INTEGER REFERENCES addresses(id),
    billing_address_id INTEGER REFERENCES addresses(id),
    order_date DATETIME,
    status VARCHAR(50),             -- pending, confirmed, shipped, delivered, cancelled
    total_amount FLOAT,
    notes TEXT,
    created_at DATETIME,
    updated_at DATETIME
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price FLOAT NOT NULL,
    total_price FLOAT NOT NULL,
    created_at DATETIME,
    UNIQUE(order_id, product_id)
);

CREATE TABLE deliveries (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    status VARCHAR(50),             -- pending, shipped, in_transit, delivered, failed
    shipped_date DATETIME,
    delivered_date DATETIME,
    tracking_number VARCHAR(255) UNIQUE,
    carrier VARCHAR(100),
    notes TEXT,
    created_at DATETIME,
    updated_at DATETIME
);

CREATE TABLE invoices (
    id INTEGER PRIMARY KEY,
    delivery_id INTEGER NOT NULL REFERENCES deliveries(id),
    invoice_number VARCHAR(100) NOT NULL UNIQUE,
    invoice_date DATETIME,
    due_date DATE,
    total_amount FLOAT NOT NULL,
    status VARCHAR(50),             -- unpaid, paid, overdue, cancelled
    notes TEXT,
    created_at DATETIME,
    updated_at DATETIME
);

CREATE TABLE payments (
    id INTEGER PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id),
    payment_date DATETIME,
    amount FLOAT NOT NULL,
    method VARCHAR(50) NOT NULL,    -- credit_card, bank_transfer, cash, upi, wallet
    transaction_ref VARCHAR(255) UNIQUE,
    status VARCHAR(50),             -- completed, pending, failed, refunded
    notes TEXT,
    created_at DATETIME
);
""".strip()


# ─── Prompt template ─────────────────────────────────────────────────────────


SYSTEM_PROMPT = f"""You are a SQL query generator for a business data management system using SQLite.

DATABASE SCHEMA:
{SCHEMA_DDL}

STRICT RULES — you MUST follow every single one:
1. Output ONLY a valid SQLite SELECT query. No explanations, no markdown, no commentary.
2. You may ONLY reference these tables: {', '.join(sorted(ALLOWED_TABLES))}.
3. Use ONLY columns that exist in the schema above. NEVER invent or hallucinate columns, tables, or data.
4. Use proper JOINs when the query spans multiple tables.
5. Use table aliases for readability (e.g. c for customers, o for orders).
6. Always use LIMIT when the user asks for "top N" or a ranking.
7. If the user's question is NOT related to the business data in these tables, respond with EXACTLY:
   THIS_IS_IRRELEVANT
   This applies to ALL of the following categories — ALWAYS reject them:
   - General knowledge (geography, history, science, trivia)
   - Coding or programming questions
   - Jokes, stories, poems, creative writing
   - Math problems unrelated to the dataset
   - Weather, time, personal assistant tasks
   - Opinions, recommendations, personal questions
   - ANY topic not directly answerable from the tables above
8. Never use DELETE, DROP, UPDATE, INSERT, ALTER, CREATE, or any DDL/DML. Only SELECT.
9. Never use subqueries when a JOIN suffices.
10. If ambiguous, prefer the simplest correct interpretation.
11. NEVER generate SQL that references columns or tables not in the schema. If unsure, respond THIS_IS_IRRELEVANT.

EXAMPLES:
User: "Show all customers"
Output: SELECT * FROM customers;

User: "Top 3 products by price"
Output: SELECT * FROM products ORDER BY unit_price DESC LIMIT 3;

User: "Total revenue per customer"
Output: SELECT c.id, c.name, SUM(o.total_amount) AS total_revenue FROM customers c JOIN orders o ON o.customer_id = c.id GROUP BY c.id, c.name ORDER BY total_revenue DESC;

User: "What is the weather today?"
Output: THIS_IS_IRRELEVANT

User: "Tell me a joke"
Output: THIS_IS_IRRELEVANT

User: "Write a Python function"
Output: THIS_IS_IRRELEVANT

User: "Who is the president of India?"
Output: THIS_IS_IRRELEVANT

User: "What is 2 + 2?"
Output: THIS_IS_IRRELEVANT
"""

IRRELEVANT_MARKER = "THIS_IS_IRRELEVANT"
IRRELEVANT_RESPONSE = (
    "This system is designed to answer questions related to the "
    "provided dataset only."
)


# ─── LLM provider abstraction ────────────────────────────────────────────────


def _call_groq(user_query: str, api_key: str) -> str:
    """Call Groq chat completions API."""
    response = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_query},
            ],
            "temperature": 0.0,
            "max_tokens": 512,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def _call_gemini(user_query: str, api_key: str) -> str:
    """Call Google Gemini (generativelanguage) API."""
    # Using 1.5-flash for better stability in production
    model = "gemini-1.5-flash"
    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [
                {
                    "parts": [
                        {"text": f"{SYSTEM_PROMPT}\n\nUser query: {user_query}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 512,
            },
        },
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def _get_provider() -> tuple[str, str]:
    """
    Auto-detect which LLM provider to use based on environment variables.
    Returns (provider_name, api_key).
    """
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    if groq_key:
        return "groq", groq_key
    if gemini_key:
        return "gemini", gemini_key

    raise EnvironmentError(
        "No LLM API key found. Set either GROQ_API_KEY or GEMINI_API_KEY "
        "as an environment variable."
    )


# ─── Post-processing & guardrails ────────────────────────────────────────────


def _clean_sql(raw: str) -> str:
    """
    Strip markdown fences, trailing semicolons issues, and whitespace
    from the LLM output.
    """
    text = raw.strip()

    # Remove ```sql ... ``` wrappers
    text = re.sub(r"^```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    # Remove leading/trailing whitespace & newlines
    text = text.strip()

    # Ensure it ends with a semicolon
    if text and not text.endswith(";"):
        text += ";"

    return text


def _validate_sql(sql: str) -> Optional[str]:
    """
    Validate the generated SQL against guardrails.
    Returns an error message if invalid, or None if OK.
    """
    upper = sql.upper().strip()

    # Block any DDL / DML
    dangerous_keywords = ["DELETE", "DROP", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE"]
    for kw in dangerous_keywords:
        # Match as whole word to avoid false positives (e.g. "created_at")
        if re.search(rf"\b{kw}\b", upper):
            return f"Blocked: generated SQL contains forbidden keyword '{kw}'."

    # Must be a SELECT
    if not upper.lstrip("( ").startswith("SELECT"):
        return "Blocked: generated SQL is not a SELECT statement."

    # Check tables referenced are in ALLOWED_TABLES
    # Simple heuristic: find all identifiers after FROM and JOIN
    table_refs = re.findall(
        r"(?:FROM|JOIN)\s+(\w+)", sql, re.IGNORECASE
    )
    for table in table_refs:
        if table.lower() not in ALLOWED_TABLES:
            return f"Blocked: query references unknown table '{table}'."

    return None


# ─── Public API ───────────────────────────────────────────────────────────────


def generate_sql(query: str) -> dict:
    """
    Convert a natural language query into a validated SQL SELECT statement.

    Parameters
    ----------
    query : str
        The user's natural language question.

    Returns
    -------
    dict
        On success:  ``{"sql": "SELECT ...", "error": None}``
        On rejection: ``{"sql": None, "error": "This system only supports ..."}``
        On failure:   ``{"sql": None, "error": "...description..."}``
    """
    if not query or not query.strip():
        return {"sql": None, "error": "Query cannot be empty."}

    try:
        provider, api_key = _get_provider()
    except EnvironmentError as e:
        return {"sql": None, "error": str(e)}

    try:
        if provider == "groq":
            raw = _call_groq(query, api_key)
        else:
            raw = _call_gemini(query, api_key)
    except httpx.HTTPStatusError as e:
        error_body = e.response.text
        logger.error("LLM API error (status %s): %s", e.response.status_code, error_body)
        return {"sql": None, "error": f"LLM API error: {e.response.status_code}. Detail: {error_body[:100]}"}
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return {"sql": None, "error": f"LLM call failed: {str(e)}"}

    # Check for irrelevant query
    if IRRELEVANT_MARKER in raw.upper().replace(" ", "_").replace("-", "_"):
        return {"sql": None, "error": IRRELEVANT_RESPONSE}

    sql = _clean_sql(raw)

    # Validate guardrails
    validation_error = _validate_sql(sql)
    if validation_error:
        return {"sql": None, "error": validation_error}

    return {"sql": sql, "error": None}


# ─── CLI demo ────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import sys

    queries = sys.argv[1:] or [
        "Show all customers",
        "Top 3 most expensive products",
        "Total revenue by customer",
        "What is the weather today?",
        "Orders that have been delivered",
    ]

    for q in queries:
        print(f"\n📝 Query: {q}")
        result = generate_sql(q)
        if result["error"]:
            print(f"   ⚠  {result['error']}")
        else:
            print(f"   ✅ {result['sql']}")
