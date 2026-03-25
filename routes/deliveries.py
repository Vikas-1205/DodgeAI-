"""API routes for Delivery management."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from schemas import DeliveryCreate, DeliveryUpdate, DeliveryResponse
from services import delivery_service

router = APIRouter(prefix="/deliveries", tags=["Deliveries"])


@router.post("/", response_model=DeliveryResponse, status_code=status.HTTP_201_CREATED)
def create_delivery(data: DeliveryCreate, db: Session = Depends(get_db)):
    return delivery_service.create_delivery(db, data)


@router.get("/", response_model=list[DeliveryResponse])
def get_all_deliveries(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    return delivery_service.get_all_deliveries(db, skip=skip, limit=limit)


@router.get("/{delivery_id}", response_model=DeliveryResponse)
def get_delivery(delivery_id: int, db: Session = Depends(get_db)):
    return delivery_service.get_delivery(db, delivery_id)


@router.put("/{delivery_id}", response_model=DeliveryResponse)
def update_delivery(delivery_id: int, data: DeliveryUpdate, db: Session = Depends(get_db)):
    return delivery_service.update_delivery(db, delivery_id, data)


@router.delete("/{delivery_id}")
def delete_delivery(delivery_id: int, db: Session = Depends(get_db)):
    return delivery_service.delete_delivery(db, delivery_id)
