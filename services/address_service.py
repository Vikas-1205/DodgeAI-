"""Service layer for Address operations."""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models import Address
from schemas import AddressCreate, AddressUpdate


def create_address(db: Session, data: AddressCreate) -> Address:
    address = Address(**data.model_dump())
    db.add(address)
    db.commit()
    db.refresh(address)
    return address


def get_address(db: Session, address_id: int) -> Address:
    address = db.query(Address).filter(Address.id == address_id).first()
    if not address:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    return address


def get_all_addresses(db: Session, skip: int = 0, limit: int = 1000) -> list[Address]:
    return db.query(Address).offset(skip).limit(limit).all()


def get_addresses_by_customer(db: Session, customer_id: int) -> list[Address]:
    return db.query(Address).filter(Address.customer_id == customer_id).all()


def update_address(db: Session, address_id: int, data: AddressUpdate) -> Address:
    address = get_address(db, address_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(address, key, value)
    db.commit()
    db.refresh(address)
    return address


def delete_address(db: Session, address_id: int) -> dict:
    address = get_address(db, address_id)
    db.delete(address)
    db.commit()
    return {"detail": "Address deleted successfully"}
