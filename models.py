"""
SQLAlchemy ORM models for the business data system.

Entities:
- Customer        — business customer
- Address         — postal addresses linked to customers
- Product         — catalog items
- Order           — customer purchase orders (links to shipping/billing addresses)
- OrderItem       — line items within an order
- Delivery        — shipment tracking for an order
- Invoice         — billing document linked to a delivery
- Payment         — payment against an invoice

Relationship chain:
  Customer → Orders → OrderItems ← Products
                    → Deliveries → Invoices → Payments
  Customer → Addresses (used by Orders as shipping/billing)
"""

from datetime import datetime, date

from sqlalchemy import (
    Column, Integer, String, Float, Numeric, Text, Date, DateTime,
    ForeignKey, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


# ─── Address ─────────────────────────────────────────────────────────────────


class Address(Base):
    __tablename__ = "addresses"

    id = Column(String(100), primary_key=True)
    customer_id = Column(String(100), ForeignKey("customers.id"), nullable=False, index=True)
    address_type = Column(String(20), default="shipping")  # shipping, billing
    street = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=False, default="India")
    is_default = Column(Integer, default=0)  # 0 = False, 1 = True (SQLite friendly)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="addresses")

    def __repr__(self):
        return f"<Address(id={self.id}, city='{self.city}', type='{self.address_type}')>"


# ─── Customer ────────────────────────────────────────────────────────────────


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    addresses = relationship("Address", back_populates="customer", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer(id={self.id}, name='{self.name}', email='{self.email}')>"


# ─── Product ─────────────────────────────────────────────────────────────────


class Product(Base):
    __tablename__ = "products"

    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    unit_price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    order_items = relationship("OrderItem", back_populates="product")

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', sku='{self.sku}')>"


# ─── Order ───────────────────────────────────────────────────────────────────


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(100), primary_key=True)
    customer_id = Column(String(100), ForeignKey("customers.id"), nullable=False, index=True)
    shipping_address_id = Column(String(100), ForeignKey("addresses.id"), nullable=True, index=True)
    billing_address_id = Column(String(100), ForeignKey("addresses.id"), nullable=True, index=True)
    order_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="pending")  # pending, confirmed, shipped, delivered, cancelled
    total_amount = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    shipping_address = relationship("Address", foreign_keys=[shipping_address_id])
    billing_address = relationship("Address", foreign_keys=[billing_address_id])
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    deliveries = relationship("Delivery", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order(id={self.id}, customer_id={self.customer_id}, status='{self.status}')>"


# ─── OrderItem ───────────────────────────────────────────────────────────────


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String(100), primary_key=True)
    order_id = Column(String(100), ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(String(100), ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    __table_args__ = (
        UniqueConstraint("order_id", "product_id", name="uq_order_product"),
    )

    def __repr__(self):
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, product_id={self.product_id})>"


# ─── Delivery ────────────────────────────────────────────────────────────────


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(String(100), primary_key=True)
    order_id = Column(String(100), ForeignKey("orders.id"), nullable=False, index=True)
    status = Column(String(50), default="pending")  # pending, shipped, in_transit, delivered, failed
    shipped_date = Column(DateTime, nullable=True)
    delivered_date = Column(DateTime, nullable=True)
    tracking_number = Column(String(255), nullable=True, unique=True)
    carrier = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="deliveries")
    invoices = relationship("Invoice", back_populates="delivery", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Delivery(id={self.id}, order_id={self.order_id}, status='{self.status}')>"


# ─── Invoice ─────────────────────────────────────────────────────────────────


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(100), primary_key=True)
    delivery_id = Column(String(100), ForeignKey("deliveries.id"), nullable=False, index=True)
    invoice_number = Column(String(100), unique=True, nullable=False, index=True)
    invoice_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(Date, nullable=True)
    total_amount = Column(Float, nullable=False)
    status = Column(String(50), default="unpaid")  # unpaid, paid, overdue, cancelled
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    delivery = relationship("Delivery", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Invoice(id={self.id}, invoice_number='{self.invoice_number}', status='{self.status}')>"


# ─── Payment ─────────────────────────────────────────────────────────────────


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(100), primary_key=True)
    invoice_id = Column(String(100), ForeignKey("invoices.id"), nullable=False, index=True)
    payment_date = Column(DateTime, default=datetime.utcnow)
    amount = Column(Float, nullable=False)
    method = Column(String(50), nullable=False)  # credit_card, bank_transfer, cash, upi, wallet
    transaction_ref = Column(String(255), nullable=True, unique=True)
    status = Column(String(50), default="completed")  # completed, pending, failed, refunded
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoice = relationship("Invoice", back_populates="payments")

    def __repr__(self):
        return f"<Payment(id={self.id}, invoice_id={self.invoice_id}, amount={self.amount})>"
