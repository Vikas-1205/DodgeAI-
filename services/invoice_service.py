"""Service layer for Invoice operations."""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models import Invoice
from schemas import InvoiceCreate, InvoiceUpdate


def create_invoice(db: Session, data: InvoiceCreate) -> Invoice:
    invoice = Invoice(**data.model_dump())
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def get_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


def get_all_invoices(db: Session, skip: int = 0, limit: int = 1000) -> list[Invoice]:
    return db.query(Invoice).offset(skip).limit(limit).all()


def update_invoice(db: Session, invoice_id: int, data: InvoiceUpdate) -> Invoice:
    invoice = get_invoice(db, invoice_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(invoice, key, value)
    db.commit()
    db.refresh(invoice)
    return invoice


def delete_invoice(db: Session, invoice_id: int) -> dict:
    invoice = get_invoice(db, invoice_id)
    db.delete(invoice)
    db.commit()
    return {"detail": "Invoice deleted successfully"}
