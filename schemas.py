"""
Pydantic schemas for request validation and response serialization.

Each entity has:
- Base: shared fields
- Create: fields required for creation
- Update: optional fields for partial updates
- Response: fields returned in API responses (with ORM mode)
"""

from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field


# ─── Address ─────────────────────────────────────────────────────────────────


class AddressBase(BaseModel):
    customer_id: str
    address_type: Optional[str] = Field(default="shipping", max_length=20)
    street: str = Field(..., min_length=1, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: str = Field(default="India", max_length=100)
    is_default: Optional[int] = Field(default=0, ge=0, le=1)


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    address_type: Optional[str] = Field(None, max_length=20)
    street: Optional[str] = Field(None, min_length=1, max_length=255)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    is_default: Optional[int] = Field(None, ge=0, le=1)


class AddressResponse(AddressBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


# ─── Customer ────────────────────────────────────────────────────────────────


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., max_length=255)
    phone: Optional[str] = Field(None, max_length=50)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)


class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    addresses: List[AddressResponse] = []


# ─── Product ─────────────────────────────────────────────────────────────────


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sku: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    unit_price: float = Field(..., ge=0)
    stock_quantity: int = Field(default=0, ge=0)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    unit_price: Optional[float] = Field(None, ge=0)
    stock_quantity: Optional[int] = Field(None, ge=0)


class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


# ─── Order Item ──────────────────────────────────────────────────────────────


class OrderItemBase(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=0)
    unit_price: float = Field(..., ge=0)
    total_price: float = Field(..., ge=0)


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_id: str
    created_at: datetime


# ─── Order ───────────────────────────────────────────────────────────────────


class OrderBase(BaseModel):
    customer_id: str
    shipping_address_id: Optional[str] = None
    billing_address_id: Optional[str] = None
    status: Optional[str] = Field(default="pending", max_length=50)
    total_amount: Optional[float] = Field(default=0.0, ge=0)
    notes: Optional[str] = None


class OrderCreate(OrderBase):
    items: Optional[List[OrderItemCreate]] = None


class OrderUpdate(BaseModel):
    shipping_address_id: Optional[str] = None
    billing_address_id: Optional[str] = None
    status: Optional[str] = Field(None, max_length=50)
    total_amount: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None


class OrderResponse(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_date: datetime
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse] = []


# ─── Delivery ────────────────────────────────────────────────────────────────


class DeliveryBase(BaseModel):
    order_id: str
    status: Optional[str] = Field(default="pending", max_length=50)
    tracking_number: Optional[str] = Field(None, max_length=255)
    carrier: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class DeliveryCreate(DeliveryBase):
    pass


class DeliveryUpdate(BaseModel):
    status: Optional[str] = Field(None, max_length=50)
    shipped_date: Optional[datetime] = None
    delivered_date: Optional[datetime] = None
    tracking_number: Optional[str] = Field(None, max_length=255)
    carrier: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class DeliveryResponse(DeliveryBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    shipped_date: Optional[datetime] = None
    delivered_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ─── Invoice ─────────────────────────────────────────────────────────────────


class InvoiceBase(BaseModel):
    delivery_id: str
    invoice_number: str = Field(..., min_length=1, max_length=100)
    total_amount: float = Field(..., ge=0)
    due_date: Optional[date] = None
    status: Optional[str] = Field(default="unpaid", max_length=50)
    notes: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    due_date: Optional[date] = None
    total_amount: Optional[float] = Field(None, ge=0)
    status: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class InvoiceResponse(InvoiceBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    invoice_date: datetime
    created_at: datetime
    updated_at: datetime


# ─── Payment ─────────────────────────────────────────────────────────────────


class PaymentBase(BaseModel):
    invoice_id: str
    amount: float = Field(..., ge=0)
    method: str = Field(..., max_length=50)
    transaction_ref: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(default="completed", max_length=50)
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    amount: Optional[float] = Field(None, ge=0)
    method: Optional[str] = Field(None, max_length=50)
    transaction_ref: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class PaymentResponse(PaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    payment_date: datetime
    created_at: datetime
