"""Service layer for Customer operations."""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models import Customer
from schemas import CustomerCreate, CustomerUpdate


def create_customer(db: Session, data: CustomerCreate) -> Customer:
    customer = Customer(**data.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def get_customer(db: Session, customer_id: int) -> Customer:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


def get_all_customers(db: Session, skip: int = 0, limit: int = 1000) -> list[Customer]:
    return db.query(Customer).offset(skip).limit(limit).all()


def update_customer(db: Session, customer_id: int, data: CustomerUpdate) -> Customer:
    customer = get_customer(db, customer_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer


def delete_customer(db: Session, customer_id: int) -> dict:
    customer = get_customer(db, customer_id)
    db.delete(customer)
    db.commit()
    return {"detail": "Customer deleted successfully"}
