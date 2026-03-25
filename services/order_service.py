"""Service layer for Order operations."""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models import Order, OrderItem
from schemas import OrderCreate, OrderUpdate


def create_order(db: Session, data: OrderCreate) -> Order:
    order_data = data.model_dump(exclude={"items"})
    order = Order(**order_data)
    db.add(order)
    db.flush()

    if data.items:
        for item_data in data.items:
            item = OrderItem(**item_data.model_dump(), order_id=order.id)
            db.add(item)
        # Recalculate total
        order.total_amount = sum(item.total_price for item in data.items)

    db.commit()
    db.refresh(order)
    return order


def get_order(db: Session, order_id: int) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


def get_all_orders(db: Session, skip: int = 0, limit: int = 1000) -> list[Order]:
    return db.query(Order).offset(skip).limit(limit).all()


def update_order(db: Session, order_id: int, data: OrderUpdate) -> Order:
    order = get_order(db, order_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(order, key, value)
    db.commit()
    db.refresh(order)
    return order


def delete_order(db: Session, order_id: int) -> dict:
    order = get_order(db, order_id)
    db.delete(order)
    db.commit()
    return {"detail": "Order deleted successfully"}
