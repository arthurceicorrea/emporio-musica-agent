"""ETL pipeline for ingesting and sanitizing Emporio da Musica CSV datasets into SQLite."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.config import settings
from src.database.models import (
    Base,
    Category,
    Customer,
    Order,
    OrderItem,
    Product,
    Promotion,
    get_engine,
    get_session_factory,
)

logger = logging.getLogger(__name__)


def _resolve_csv_path(data_dir: Path, table_name: str) -> Path:
    """Locate a CSV file supporting both prefixed challenge names and short table names."""
    candidates = [
        data_dir / f"desafio_tecnico_ai_eng - {table_name}.csv",
        data_dir / f"{table_name}.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"CSV dataset for '{table_name}' not found in {data_dir}. "
        f"Checked: {[str(c.name) for c in candidates]}"
    )


def _clean_nullable_str(value: Any) -> str | None:
    """Normalize pandas NaN or blank strings into None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text if text else None


def _normalize_specs_json(raw_specs: Any) -> str:
    """Validate and normalize product technical specifications JSON string."""
    cleaned = _clean_nullable_str(raw_specs)
    if not cleaned:
        return "{}"
    try:
        parsed = json.loads(cleaned)
        return json.dumps(parsed, ensure_ascii=False)
    except json.JSONDecodeError:
        logger.warning("Malformed specs JSON encountered: %s", cleaned)
        return "{}"


def ingest_all_csvs(session: Session, data_dir: Path | None = None) -> dict[str, int]:
    """Load all six store CSV files into the relational database within a transaction."""
    source_dir = data_dir or settings.data_dir
    row_counts: dict[str, int] = {}

    # Clear existing records in reverse dependency order for idempotent re-seeding
    session.query(OrderItem).delete()
    session.query(Order).delete()
    session.query(Promotion).delete()
    session.query(Product).delete()
    session.query(Customer).delete()
    session.query(Category).delete()
    session.flush()

    # 1. Categories
    cat_df = pd.read_csv(_resolve_csv_path(source_dir, "categories"), encoding="utf-8")
    categories = [
        Category(
            category_id=int(row["category_id"]),
            name=str(row["name"]).strip(),
            description=_clean_nullable_str(row.get("description")),
        )
        for _, row in cat_df.iterrows()
    ]
    session.add_all(categories)
    row_counts["categories"] = len(categories)

    # 2. Customers
    cust_df = pd.read_csv(_resolve_csv_path(source_dir, "customers"), encoding="utf-8")
    customers = [
        Customer(
            customer_id=int(row["customer_id"]),
            name=str(row["name"]).strip(),
            phone=str(row["phone"]).strip(),
            email=str(row["email"]).strip().lower(),
            city=str(row["city"]).strip(),
        )
        for _, row in cust_df.iterrows()
    ]
    session.add_all(customers)
    row_counts["customers"] = len(customers)

    # 3. Products
    prod_df = pd.read_csv(_resolve_csv_path(source_dir, "products"), encoding="utf-8")
    products = [
        Product(
            product_id=int(row["product_id"]),
            price_brl=float(row["price_brl"]),
            name=str(row["name"]).strip(),
            category_id=int(row["category_id"]),
            description=str(row["description"]).strip(),
            stock_quantity=int(row["stock_quantity"]),
            status=str(row["status"]).strip().lower(),
            specs_json=_normalize_specs_json(row.get("specs")),
            created_at=_clean_nullable_str(row.get("created_at")),
        )
        for _, row in prod_df.iterrows()
    ]
    session.add_all(products)
    row_counts["products"] = len(products)

    # 4. Promotions
    promo_df = pd.read_csv(_resolve_csv_path(source_dir, "promotions"), encoding="utf-8")
    promotions = [
        Promotion(
            promotion_id=int(row["promotion_id"]),
            product_id=int(row["product_id"]),
            discount_percent=float(row["discount_percent"]),
            description=str(row["description"]).strip(),
            is_active=bool(int(row["is_active"])),
        )
        for _, row in promo_df.iterrows()
    ]
    session.add_all(promotions)
    row_counts["promotions"] = len(promotions)

    # 5. Orders
    orders_df = pd.read_csv(_resolve_csv_path(source_dir, "orders"), encoding="utf-8")
    orders = [
        Order(
            order_id=int(row["order_id"]),
            customer_id=int(row["customer_id"]),
            order_date=str(row["order_date"]).strip(),
            status=str(row["status"]).strip().lower(),
            total_brl=float(row["total_brl"]),
            payment_method=str(row["payment_method"]).strip().lower(),
            tracking_code=_clean_nullable_str(row.get("tracking_code")),
            estimated_delivery=_clean_nullable_str(row.get("estimated_delivery")),
            notes=_clean_nullable_str(row.get("notes")),
        )
        for _, row in orders_df.iterrows()
    ]
    session.add_all(orders)
    row_counts["orders"] = len(orders)

    # 6. Order Items
    items_df = pd.read_csv(_resolve_csv_path(source_dir, "order_items"), encoding="utf-8")
    order_items = [
        OrderItem(
            order_id=int(row["order_id"]),
            product_id=int(row["product_id"]),
            quantity=int(row["quantity"]),
        )
        for _, row in items_df.iterrows()
    ]
    session.add_all(order_items)
    row_counts["order_items"] = len(order_items)

    session.commit()
    return row_counts


def init_and_seed_database(
    engine: Engine | None = None,
    data_dir: Path | None = None,
    force_reseed: bool = False,
) -> dict[str, int]:
    """Create database tables and populate them from CSV files if empty or forced."""
    target_engine = engine or get_engine()
    Base.metadata.create_all(bind=target_engine)
    session_factory = get_session_factory(target_engine)

    with session_factory() as session:
        existing_products = session.query(Product).count()
        if existing_products > 0 and not force_reseed:
            return {
                "categories": session.query(Category).count(),
                "customers": session.query(Customer).count(),
                "products": existing_products,
                "promotions": session.query(Promotion).count(),
                "orders": session.query(Order).count(),
                "order_items": session.query(OrderItem).count(),
            }
        return ingest_all_csvs(session=session, data_dir=data_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    counts = init_and_seed_database(force_reseed=True)
    logger.info("Database successfully initialized and seeded: %s", counts)
