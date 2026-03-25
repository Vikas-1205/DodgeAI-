"""Service layer for Product operations."""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models import Product
from schemas import ProductCreate, ProductUpdate


def create_product(db: Session, data: ProductCreate) -> Product:
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def get_product(db: Session, product_id: int) -> Product:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


def get_all_products(db: Session, skip: int = 0, limit: int = 1000) -> list[Product]:
    return db.query(Product).offset(skip).limit(limit).all()


def update_product(db: Session, product_id: int, data: ProductUpdate) -> Product:
    product = get_product(db, product_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> dict:
    product = get_product(db, product_id)
    db.delete(product)
    db.commit()
    return {"detail": "Product deleted successfully"}
