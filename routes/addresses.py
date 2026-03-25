"""API routes for Address management."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from schemas import AddressCreate, AddressUpdate, AddressResponse
from services import address_service

router = APIRouter(prefix="/addresses", tags=["Addresses"])


@router.post("/", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
def create_address(data: AddressCreate, db: Session = Depends(get_db)):
    return address_service.create_address(db, data)


@router.get("/", response_model=list[AddressResponse])
def get_all_addresses(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    return address_service.get_all_addresses(db, skip=skip, limit=limit)


@router.get("/customer/{customer_id}", response_model=list[AddressResponse])
def get_addresses_by_customer(customer_id: int, db: Session = Depends(get_db)):
    return address_service.get_addresses_by_customer(db, customer_id)


@router.get("/{address_id}", response_model=AddressResponse)
def get_address(address_id: int, db: Session = Depends(get_db)):
    return address_service.get_address(db, address_id)


@router.put("/{address_id}", response_model=AddressResponse)
def update_address(address_id: int, data: AddressUpdate, db: Session = Depends(get_db)):
    return address_service.update_address(db, address_id, data)


@router.delete("/{address_id}")
def delete_address(address_id: int, db: Session = Depends(get_db)):
    return address_service.delete_address(db, address_id)
