"""
Generate SQL DDL (CREATE TABLE statements) from SQLAlchemy models.

Usage:
    python generate_sql.py          # prints to stdout
    python generate_sql.py > schema.sql   # saves to file
"""

from sqlalchemy import create_engine
from sqlalchemy.schema import CreateTable

from database import Base
import models  # noqa: F401  — triggers model registration on Base.metadata


def generate_ddl() -> str:
    """Return the full SQL DDL for all registered models."""
    engine = create_engine("sqlite:///./app.db")
    lines: list[str] = []
    for table in Base.metadata.sorted_tables:
        ddl = CreateTable(table).compile(engine)
        lines.append(str(ddl).strip() + ";\n")
    return "\n\n".join(lines)


if __name__ == "__main__":
    print(generate_ddl())
