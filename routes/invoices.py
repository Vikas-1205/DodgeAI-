"""API routes for Invoice management."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from schemas import InvoiceCreate, InvoiceUpdate, InvoiceResponse
from services import invoice_service

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(data: InvoiceCreate, db: Session = Depends(get_db)):
    return invoice_service.create_invoice(db, data)


@router.get("/", response_model=list[InvoiceResponse])
def get_all_invoices(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    return invoice_service.get_all_invoices(db, skip=skip, limit=limit)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    return invoice_service.get_invoice(db, invoice_id)


@router.put("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(invoice_id: int, data: InvoiceUpdate, db: Session = Depends(get_db)):
    return invoice_service.update_invoice(db, invoice_id, data)


@router.delete("/{invoice_id}")
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)):
    return invoice_service.delete_invoice(db, invoice_id)
