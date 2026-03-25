"""Service layer for OrderItem operations."""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models import OrderItem
from schemas import OrderItemCreate


def get_order_item(db: Session, item_id: str) -> OrderItem:
    item = db.query(OrderItem).filter(OrderItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order item not found")
    return item


def get_all_order_items(db: Session, skip: int = 0, limit: int = 1000) -> list[OrderItem]:
    return db.query(OrderItem).offset(skip).limit(limit).all()
