"""API routes for Order management."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from schemas import OrderCreate, OrderUpdate, OrderResponse
from services import order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    return order_service.create_order(db, data)


@router.get("/", response_model=list[OrderResponse])
def get_all_orders(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    return order_service.get_all_orders(db, skip=skip, limit=limit)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    return order_service.get_order(db, order_id)


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, data: OrderUpdate, db: Session = Depends(get_db)):
    return order_service.update_order(db, order_id, data)


@router.delete("/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    return order_service.delete_order(db, order_id)
