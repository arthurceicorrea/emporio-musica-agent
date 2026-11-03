"""SQLAlchemy 2.0 ORM models representing the Emporio da Musica relational schema."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

from src.config import settings


class Base(DeclarativeBase):
    """Declarative base class for all ORM entities."""


class Category(Base):
    """Musical instrument category entity."""

    __tablename__ = "categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    products: Mapped[list[Product]] = relationship(
        "Product", back_populates="category", cascade="all, delete-orphan"
    )


class Customer(Base):
    """Store customer entity."""

    __tablename__ = "customers"

    customer_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    email: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    orders: Mapped[list[Order]] = relationship(
        "Order", back_populates="customer", cascade="all, delete-orphan"
    )


class Product(Base):
    """Musical instrument catalog product entity."""

    __tablename__ = "products"

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    price_brl: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.category_id"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    specs_json: Mapped[str] = mapped_column("specs", Text, nullable=False, default="{}")
    created_at: Mapped[str] = mapped_column(String(30), nullable=True)

    category: Mapped[Category] = relationship("Category", back_populates="products")
    promotions: Mapped[list[Promotion]] = relationship(
        "Promotion", back_populates="product", cascade="all, delete-orphan"
    )
    order_items: Mapped[list[OrderItem]] = relationship(
        "OrderItem", back_populates="product"
    )

    @property
    def specs(self) -> dict[str, Any]:
        """Deserialize technical specifications JSON string into a Python dictionary."""
        try:
            data = json.loads(self.specs_json) if self.specs_json else {}
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    @property
    def is_available(self) -> bool:
        """Check whether the product is active and currently in stock."""
        return self.status == "active" and self.stock_quantity > 0


class Promotion(Base):
    """Promotional discount entity linked to a catalog product."""

    __tablename__ = "promotions"

    promotion_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.product_id"), nullable=False, index=True
    )
    discount_percent: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    product: Mapped[Product] = relationship("Product", back_populates="promotions")


class Order(Base):
    """Customer purchase order header entity."""

    __tablename__ = "orders"

    order_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.customer_id"), nullable=False, index=True
    )
    order_date: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    total_brl: Mapped[float] = mapped_column(Float, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(40), nullable=False)
    tracking_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    estimated_delivery: Mapped[str | None] = mapped_column(String(30), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer: Mapped[Customer] = relationship("Customer", back_populates="orders")
    items: Mapped[list[OrderItem]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    """Line item belonging to a customer order."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.order_id"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.product_id"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    order: Mapped[Order] = relationship("Order", back_populates="items")
    product: Mapped[Product] = relationship("Product", back_populates="order_items")


def get_engine(database_url: str | None = None) -> Engine:
    """Create and return a SQLAlchemy Engine instance."""
    url = database_url or settings.database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True)


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Return a configured SQLAlchemy sessionmaker."""
    target_engine = engine or get_engine()
    return sessionmaker(bind=target_engine, autoflush=False, autocommit=False, future=True)
