"""Service layer for Payment operations."""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models import Payment
from schemas import PaymentCreate, PaymentUpdate


def create_payment(db: Session, data: PaymentCreate) -> Payment:
    payment = Payment(**data.model_dump())
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def get_payment(db: Session, payment_id: int) -> Payment:
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


def get_all_payments(db: Session, skip: int = 0, limit: int = 1000) -> list[Payment]:
    return db.query(Payment).offset(skip).limit(limit).all()


def update_payment(db: Session, payment_id: int, data: PaymentUpdate) -> Payment:
    payment = get_payment(db, payment_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(payment, key, value)
    db.commit()
    db.refresh(payment)
    return payment


def delete_payment(db: Session, payment_id: int) -> dict:
    payment = get_payment(db, payment_id)
    db.delete(payment)
    db.commit()
    return {"detail": "Payment deleted successfully"}
