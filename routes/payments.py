"""API routes for Payment management."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from schemas import PaymentCreate, PaymentUpdate, PaymentResponse
from services import payment_service

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(data: PaymentCreate, db: Session = Depends(get_db)):
    return payment_service.create_payment(db, data)


@router.get("/", response_model=list[PaymentResponse])
def get_all_payments(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    return payment_service.get_all_payments(db, skip=skip, limit=limit)


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    return payment_service.get_payment(db, payment_id)


@router.put("/{payment_id}", response_model=PaymentResponse)
def update_payment(payment_id: int, data: PaymentUpdate, db: Session = Depends(get_db)):
    return payment_service.update_payment(db, payment_id, data)


@router.delete("/{payment_id}")
def delete_payment(payment_id: int, db: Session = Depends(get_db)):
    return payment_service.delete_payment(db, payment_id)
