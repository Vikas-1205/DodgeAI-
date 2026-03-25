"""API routes for OrderItem management."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas import OrderItemResponse
from services import order_item_service

router = APIRouter(prefix="/order_items", tags=["Order Items"])


@router.get("/", response_model=list[OrderItemResponse])
def get_all_order_items(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    return order_item_service.get_all_order_items(db, skip=skip, limit=limit)


@router.get("/{item_id}", response_model=OrderItemResponse)
def get_order_item(item_id: str, db: Session = Depends(get_db)):
    return order_item_service.get_order_item(db, item_id)
