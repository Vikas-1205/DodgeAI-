"""
Safe SQL Executor — runs dynamically generated SELECT queries via SQLAlchemy.

Safety:
    - Only SELECT statements are allowed
    - Parameterised execution through SQLAlchemy text()
    - Graceful handling of invalid SQL, empty results, and DB errors

Usage:
    from query_executor import execute_sql

    result = execute_sql("SELECT * FROM customers LIMIT 5;")
    # result["success"]  → True
    # result["columns"]  → ["id", "name", ...]
    # result["rows"]     → [{"id": 1, "name": "Acme"}, ...]
    # result["row_count"]→ 5
"""

from __future__ import annotations

import re
import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from database import SessionLocal

logger = logging.getLogger(__name__)


# ─── Allowed tables (same whitelist as nl_to_sql) ────────────────────────────

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

# Keywords that must never appear in executable SQL
BLOCKED_KEYWORDS = [
    "DELETE", "DROP", "UPDATE", "INSERT", "ALTER",
    "CREATE", "TRUNCATE", "REPLACE", "ATTACH", "DETACH",
    "PRAGMA", "GRANT", "REVOKE", "VACUUM",
]


# ─── Validation ──────────────────────────────────────────────────────────────


def _validate_query(sql: str) -> Optional[str]:
    """
    Validate a SQL string before execution.

    Returns an error message if the query is rejected, or None if safe.
    """
    if not sql or not sql.strip():
        return "Query is empty."

    cleaned = sql.strip().rstrip(";").strip()
    upper = cleaned.upper()

    # Must start with SELECT
    if not upper.lstrip("( ").startswith("SELECT"):
        return "Only SELECT queries are allowed."

    # Block dangerous keywords (whole-word match to avoid false positives)
    for kw in BLOCKED_KEYWORDS:
        if re.search(rf"\b{kw}\b", upper):
            return f"Blocked: query contains forbidden keyword '{kw}'."

    # Verify all referenced tables are in the whitelist
    table_refs = re.findall(r"(?:FROM|JOIN)\s+(\w+)", sql, re.IGNORECASE)
    for table in table_refs:
        if table.lower() not in ALLOWED_TABLES:
            return f"Blocked: query references unknown table '{table}'."

    return None


# ─── Executor ─────────────────────────────────────────────────────────────────


def execute_sql(sql: str, db: Optional[Session] = None) -> dict:
    """
    Execute a validated SELECT query and return results as JSON-friendly dicts.

    Parameters
    ----------
    sql : str
        A SQL SELECT statement to execute.
    db : Session, optional
        An existing SQLAlchemy session. If None, a new session is created
        and closed automatically.

    Returns
    -------
    dict
        On success::

            {
                "success": True,
                "columns": ["id", "name", ...],
                "rows": [{"id": 1, "name": "Acme"}, ...],
                "row_count": 5,
                "error": None
            }

        On failure::

            {
                "success": False,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": "...description..."
            }
    """
    empty_result = {
        "success": False,
        "columns": [],
        "rows": [],
        "row_count": 0,
        "error": None,
    }

    # ── Pre-execution validation ──────────────────────────────────────
    validation_error = _validate_query(sql)
    if validation_error:
        return {**empty_result, "error": validation_error}

    # ── Execute ───────────────────────────────────────────────────────
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        result = db.execute(text(sql))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]

        if not rows:
            return {
                "success": True,
                "columns": columns,
                "rows": [],
                "row_count": 0,
                "error": None,
            }

        return {
            "success": True,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "error": None,
        }

    except (OperationalError, ProgrammingError) as e:
        logger.warning("SQL syntax/operational error: %s", e)
        db.rollback()
        return {**empty_result, "error": f"SQL error: {_extract_message(e)}"}

    except SQLAlchemyError as e:
        logger.error("Database error: %s", e)
        db.rollback()
        return {**empty_result, "error": f"Database error: {_extract_message(e)}"}

    except Exception as e:
        logger.error("Unexpected error executing SQL: %s", e)
        db.rollback()
        return {**empty_result, "error": f"Unexpected error: {str(e)}"}

    finally:
        if own_session:
            db.close()


def _extract_message(exc: Exception) -> str:
    """Extract a clean, user-friendly error message from a SQLAlchemy exception."""
    msg = str(exc.orig) if hasattr(exc, "orig") and exc.orig else str(exc)
    # Truncate very long messages
    return msg[:300] if len(msg) > 300 else msg


# ─── CLI demo ────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    from database import engine, Base
    import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    test_queries = [
        ("Valid SELECT", "SELECT * FROM customers LIMIT 3;"),
        ("Empty result", "SELECT * FROM customers WHERE id = 99999;"),
        ("Invalid SQL", "SELEC * FORM customers;"),
        ("Blocked DELETE", "DELETE FROM customers WHERE id = 1;"),
        ("Unknown table", "SELECT * FROM users;"),
        ("Empty string", ""),
    ]

    for label, sql in test_queries:
        print(f"\n{'─'*50}")
        print(f"  Test: {label}")
        print(f"  SQL:  {sql}")
        result = execute_sql(sql)
        if result["success"]:
            print(f"  ✅ {result['row_count']} rows, columns: {result['columns']}")
            for row in result["rows"][:2]:
                print(f"     {row}")
        else:
            print(f"  ⚠  {result['error']}")
