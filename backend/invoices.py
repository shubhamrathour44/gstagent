"""Invoice Register API for GSTAgent.

Drop this file at: backend/invoices.py
Then mount it in main_v2.py:
    from invoices import router as invoices_router
    app.include_router(invoices_router)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth import CurrentUser, get_current_user
from database import get_db

router = APIRouter(prefix="/invoices", tags=["Invoices"])


class InvoiceIn(BaseModel):
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    invoice_type: str = "purchase"
    vendor_name: Optional[str] = None
    vendor_gstin: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    taxable_value: float = 0
    cgst: float = 0
    sgst: float = 0
    igst: float = 0
    total_amount: float = 0
    language: Optional[str] = None
    confidence: Optional[str] = None
    source: str = "smart_invoice_upload"


async def ensure_invoice_table(db: AsyncSession) -> None:
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS invoices (
            id VARCHAR(64) PRIMARY KEY,
            firm_id VARCHAR(64),
            client_id VARCHAR(64),
            client_name VARCHAR(255),
            invoice_type VARCHAR(32),
            vendor_name VARCHAR(255),
            vendor_gstin VARCHAR(32),
            invoice_number VARCHAR(128),
            invoice_date VARCHAR(32),
            taxable_value FLOAT DEFAULT 0,
            cgst FLOAT DEFAULT 0,
            sgst FLOAT DEFAULT 0,
            igst FLOAT DEFAULT 0,
            total_amount FLOAT DEFAULT 0,
            language VARCHAR(64),
            confidence VARCHAR(64),
            source VARCHAR(128),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    await db.commit()


def _firm_id(user: Any) -> str:
    return str(getattr(user, "firm_id", None) or getattr(user, "id", None) or "demo_firm")


@router.post("/create")
@router.post("")
async def create_invoice(
    payload: InvoiceIn,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_invoice_table(db)
    if not payload.invoice_number:
        raise HTTPException(status_code=400, detail="Invoice number is required")
    invoice_id = str(uuid4())
    firm_id = _firm_id(current_user)
    await db.execute(text("""
        INSERT INTO invoices (
            id, firm_id, client_id, client_name, invoice_type, vendor_name, vendor_gstin,
            invoice_number, invoice_date, taxable_value, cgst, sgst, igst, total_amount,
            language, confidence, source, created_at, updated_at
        ) VALUES (
            :id, :firm_id, :client_id, :client_name, :invoice_type, :vendor_name, :vendor_gstin,
            :invoice_number, :invoice_date, :taxable_value, :cgst, :sgst, :igst, :total_amount,
            :language, :confidence, :source, :created_at, :updated_at
        )
    """), {
        "id": invoice_id,
        "firm_id": firm_id,
        "client_id": str(payload.client_id or ""),
        "client_name": payload.client_name or "",
        "invoice_type": payload.invoice_type or "purchase",
        "vendor_name": payload.vendor_name or "",
        "vendor_gstin": payload.vendor_gstin or "",
        "invoice_number": payload.invoice_number or "",
        "invoice_date": payload.invoice_date or "",
        "taxable_value": float(payload.taxable_value or 0),
        "cgst": float(payload.cgst or 0),
        "sgst": float(payload.sgst or 0),
        "igst": float(payload.igst or 0),
        "total_amount": float(payload.total_amount or 0),
        "language": payload.language or "",
        "confidence": payload.confidence or "",
        "source": payload.source or "smart_invoice_upload",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })
    await db.commit()
    return {"ok": True, "message": "Invoice saved", "invoice_id": invoice_id}


@router.get("/list")
@router.get("")
async def list_invoices(
    client_id: Optional[str] = None,
    invoice_type: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_invoice_table(db)
    firm_id = _firm_id(current_user)
    sql = "SELECT * FROM invoices WHERE firm_id = :firm_id"
    params: dict[str, Any] = {"firm_id": firm_id}
    if client_id:
        sql += " AND client_id = :client_id"
        params["client_id"] = str(client_id)
    if invoice_type:
        sql += " AND invoice_type = :invoice_type"
        params["invoice_type"] = invoice_type
    sql += " ORDER BY created_at DESC LIMIT 500"
    result = await db.execute(text(sql), params)
    rows = [dict(r._mapping) for r in result]
    return {"invoices": rows, "count": len(rows)}


@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_invoice_table(db)
    await db.execute(text("DELETE FROM invoices WHERE id = :id AND firm_id = :firm_id"), {"id": invoice_id, "firm_id": _firm_id(current_user)})
    await db.commit()
    return {"ok": True, "message": "Invoice deleted"}
