"""API routes for Customer management."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from schemas import CustomerCreate, CustomerUpdate, CustomerResponse
from services import customer_service

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    return customer_service.create_customer(db, data)


@router.get("/", response_model=list[CustomerResponse])
def get_all_customers(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    return customer_service.get_all_customers(db, skip=skip, limit=limit)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    return customer_service.get_customer(db, customer_id)


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(customer_id: int, data: CustomerUpdate, db: Session = Depends(get_db)):
    return customer_service.update_customer(db, customer_id, data)


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    return customer_service.delete_customer(db, customer_id)
