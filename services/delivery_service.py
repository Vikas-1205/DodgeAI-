"""Service layer for Delivery operations."""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models import Delivery
from schemas import DeliveryCreate, DeliveryUpdate


def create_delivery(db: Session, data: DeliveryCreate) -> Delivery:
    delivery = Delivery(**data.model_dump())
    db.add(delivery)
    db.commit()
    db.refresh(delivery)
    return delivery


def get_delivery(db: Session, delivery_id: int) -> Delivery:
    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    return delivery


def get_all_deliveries(db: Session, skip: int = 0, limit: int = 1000) -> list[Delivery]:
    return db.query(Delivery).offset(skip).limit(limit).all()


def update_delivery(db: Session, delivery_id: int, data: DeliveryUpdate) -> Delivery:
    delivery = get_delivery(db, delivery_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(delivery, key, value)
    db.commit()
    db.refresh(delivery)
    return delivery


def delete_delivery(db: Session, delivery_id: int) -> dict:
    delivery = get_delivery(db, delivery_id)
    db.delete(delivery)
    db.commit()
    return {"detail": "Delivery deleted successfully"}
