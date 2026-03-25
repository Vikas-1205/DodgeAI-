"""
Data Loader — Load CSV / JSON datasets into the database.

Usage:
    python load_data.py                          # loads all files from data/ folder
    python load_data.py data/customers.csv       # load a specific file
    python load_data.py file1.csv file2.json     # load multiple specific files

The loader automatically detects the target table from the filename
(e.g. "customers.csv" → customers table) and handles duplicates safely.

Supported tables:
    customers, addresses, products, orders, order_items,
    deliveries, invoices, payments
"""

import csv
import json
import sys
import os
from pathlib import Path
from datetime import datetime, date

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import SessionLocal, engine, Base
from models import (
    Customer, Address, Product, Order, OrderItem,
    Delivery, Invoice, Payment,
)


# ─── Table name → Model mapping ──────────────────────────────────────────────

MODEL_MAP: dict[str, type] = {
    "customers": Customer,
    "addresses": Address,
    "products": Product,
    "orders": Order,
    "order_items": OrderItem,
    "deliveries": Delivery,
    "invoices": Invoice,
    "payments": Payment,
}

# Load order respects foreign-key dependencies
LOAD_ORDER = [
    "customers",
    "addresses",
    "products",
    "orders",
    "order_items",
    "deliveries",
    "invoices",
    "payments",
]

# Fields that should be parsed as dates/datetimes
DATETIME_FIELDS = {
    "created_at", "updated_at", "order_date", "shipped_date",
    "delivered_date", "invoice_date", "payment_date",
}
DATE_FIELDS = {"due_date"}

# Fields that should be parsed as integers
INT_FIELDS = {
    "quantity", "stock_quantity", "is_default",
}

# Fields that should be parsed as floats
FLOAT_FIELDS = {"unit_price", "total_price", "total_amount", "amount"}


# ─── Helpers ──────────────────────────────────────────────────────────────────


def parse_value(key: str, value: str):
    """Convert a string value to the appropriate Python type based on field name."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None

    if isinstance(value, str):
        value = value.strip()

    if key in DATETIME_FIELDS:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except (ValueError, TypeError):
                continue
        return None

    if key in DATE_FIELDS:
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value, fmt).date()
            except (ValueError, TypeError):
                continue
        return None

    if key in INT_FIELDS:
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    if key in FLOAT_FIELDS:
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    return value


def read_csv(filepath: str) -> list[dict]:
    """Read a CSV file and return a list of row dicts."""
    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k.strip(): v for k, v in row.items()})
    return rows


def read_json(filepath: str) -> list[dict]:
    """Read a JSON file (array of objects) and return a list of dicts."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        # support {"customers": [...]} style files
        for key, val in data.items():
            if isinstance(val, list):
                return val
        return [data]
    return data


def read_file(filepath: str) -> list[dict]:
    """Dispatch to CSV or JSON reader based on file extension."""
    ext = Path(filepath).suffix.lower()
    if ext == ".csv":
        return read_csv(filepath)
    elif ext == ".json":
        return read_json(filepath)
    else:
        raise ValueError(f"Unsupported file format: {ext} (use .csv or .json)")


def table_name_from_file(filepath: str) -> str:
    """
    Derive the target table name from the filename.
    Examples:
        customers.csv       → customers
        order_items.json    → order_items
        01_products.csv     → products   (strips numeric prefixes)
    """
    stem = Path(filepath).stem.lower()
    # Strip leading digits and underscores (e.g. "01_customers" → "customers")
    parts = stem.split("_")
    while parts and parts[0].isdigit():
        parts.pop(0)
    name = "_".join(parts) if parts else stem

    if name not in MODEL_MAP:
        raise ValueError(
            f"Cannot map filename '{Path(filepath).name}' to a table. "
            f"Expected one of: {', '.join(MODEL_MAP.keys())}"
        )
    return name


# ─── Core Loader ──────────────────────────────────────────────────────────────


def load_table(
    db: Session,
    table_name: str,
    rows: list[dict],
) -> dict:
    """
    Insert rows into the specified table.

    Returns a summary dict: {inserted, skipped, errors}.
    Handles duplicates by catching IntegrityError per row.
    """
    model_cls = MODEL_MAP[table_name]

    # Get valid column names for this model
    valid_columns = {c.name for c in model_cls.__table__.columns}

    inserted = 0
    skipped = 0
    errors = []

    for i, raw_row in enumerate(rows, start=1):
        # Filter to valid columns and parse types
        row = {}
        for key, value in raw_row.items():
            col = key.strip().lower()
            if col in valid_columns:
                row[col] = parse_value(col, value)

        if not row:
            continue

        try:
            obj = model_cls(**row)
            db.add(obj)
            db.flush()
            inserted += 1
        except IntegrityError as e:
            db.rollback()
            skipped += 1
        except Exception as e:
            db.rollback()
            errors.append(f"Row {i}: {e}")

    db.commit()
    return {"inserted": inserted, "skipped": skipped, "errors": errors}


def load_file(db: Session, filepath: str) -> tuple[str, dict]:
    """
    Load a single CSV/JSON file into the appropriate table.

    Returns (table_name, summary_dict).
    """
    table_name = table_name_from_file(filepath)
    rows = read_file(filepath)
    summary = load_table(db, table_name, rows)
    return table_name, summary


def load_directory(db: Session, directory: str = "data") -> dict[str, dict]:
    """
    Load all CSV/JSON files from a directory, in FK-dependency order.

    Returns {table_name: summary_dict} for each file loaded.
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")

    # Discover files
    files = sorted(
        [f for f in dir_path.iterdir() if f.suffix.lower() in (".csv", ".json")],
        key=lambda f: f.name,
    )

    # Map each file to its table
    file_table_map: dict[str, str] = {}
    for f in files:
        try:
            tname = table_name_from_file(str(f))
            file_table_map[str(f)] = tname
        except ValueError as e:
            print(f"  ⚠  Skipping {f.name}: {e}")

    # Sort files by LOAD_ORDER for FK safety
    def sort_key(filepath: str) -> int:
        tname = file_table_map.get(filepath, "")
        return LOAD_ORDER.index(tname) if tname in LOAD_ORDER else 999

    sorted_files = sorted(file_table_map.keys(), key=sort_key)

    results: dict[str, dict] = {}
    for filepath in sorted_files:
        tname = file_table_map[filepath]
        print(f"  📂 Loading {Path(filepath).name} → {tname}...")
        rows = read_file(filepath)
        summary = load_table(db, tname, rows)
        results[tname] = summary

    return results


# ─── Summary Printer ─────────────────────────────────────────────────────────


def print_summary(results: dict[str, dict]):
    """Print a formatted summary of the load operation."""
    print("\n" + "=" * 55)
    print("  DATA LOAD SUMMARY")
    print("=" * 55)
    print(f"  {'Table':<20} {'Inserted':>9} {'Skipped':>9} {'Errors':>8}")
    print("-" * 55)

    total_inserted = 0
    total_skipped = 0
    total_errors = 0

    for table, info in results.items():
        ins = info["inserted"]
        skp = info["skipped"]
        err = len(info["errors"])
        total_inserted += ins
        total_skipped += skp
        total_errors += err
        print(f"  {table:<20} {ins:>9} {skp:>9} {err:>8}")

    print("-" * 55)
    print(f"  {'TOTAL':<20} {total_inserted:>9} {total_skipped:>9} {total_errors:>8}")
    print("=" * 55)

    # Print any error details
    for table, info in results.items():
        if info["errors"]:
            print(f"\n  ⚠  Errors in '{table}':")
            for e in info["errors"][:10]:
                print(f"     → {e}")
            if len(info["errors"]) > 10:
                print(f"     ... and {len(info['errors']) - 10} more")

    # Print current record counts from DB
    db = SessionLocal()
    try:
        print("\n  📊 Current DB record counts:")
        for tname in LOAD_ORDER:
            model = MODEL_MAP[tname]
            count = db.query(model).count()
            print(f"     {tname:<20} {count:>6} records")
    finally:
        db.close()

    print()


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    """CLI entry point."""
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        args = sys.argv[1:]

        if not args:
            # Default: load from data/ directory
            print("\n📦 Loading all files from data/ directory...\n")
            results = load_directory(db, "data")
        else:
            # Load specific files
            results: dict[str, dict] = {}
            for filepath in args:
                if not os.path.isfile(filepath):
                    print(f"  ⚠  File not found: {filepath}")
                    continue
                print(f"\n📦 Loading {filepath}...")
                tname, summary = load_file(db, filepath)
                results[tname] = summary

        print_summary(results)

    finally:
        db.close()


if __name__ == "__main__":
    main()
