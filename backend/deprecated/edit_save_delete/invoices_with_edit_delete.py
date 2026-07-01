"""
Invoice Register API for GSTAgent demo.

Fix included:
- Does NOT query firm_id because the existing Railway Postgres invoices table
  was created without a firm_id column.
- Uses client_id as string/UUID.
- Auto-creates invoices table if it does not exist.
- Works with Smart Invoice Upload and Invoice Register frontend.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user, CurrentUser
from database import get_db


router = APIRouter(prefix="/invoices", tags=["Invoices"])


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY,
    client_id TEXT,
    client_name TEXT,
    invoice_type TEXT,
    vendor_name TEXT,
    vendor_gstin TEXT,
    invoice_number TEXT,
    invoice_date TEXT,
    taxable_value DOUBLE PRECISION DEFAULT 0,
    cgst DOUBLE PRECISION DEFAULT 0,
    sgst DOUBLE PRECISION DEFAULT 0,
    igst DOUBLE PRECISION DEFAULT 0,
    total_amount DOUBLE PRECISION DEFAULT 0,
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class InvoiceCreate(BaseModel):
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    invoice_type: str = "purchase"
    vendor_name: Optional[str] = ""
    vendor_gstin: Optional[str] = ""
    invoice_number: Optional[str] = ""
    invoice_date: Optional[str] = ""
    taxable_value: float = 0
    cgst: float = 0
    sgst: float = 0
    igst: float = 0
    total_amount: float = 0
    raw_data: Optional[dict[str, Any]] = None


class InvoiceUpdate(BaseModel):
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    invoice_type: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_gstin: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    taxable_value: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    total_amount: Optional[float] = None
    raw_data: Optional[dict[str, Any]] = None

async def ensure_invoice_table(db: AsyncSession) -> None:
    await db.execute(text(CREATE_TABLE_SQL))
    # Add missing columns safely for older tables.
    for col_sql in [
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS client_id TEXT",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS client_name TEXT",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS invoice_type TEXT",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS vendor_name TEXT",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS vendor_gstin TEXT",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS invoice_number TEXT",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS invoice_date TEXT",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS taxable_value DOUBLE PRECISION DEFAULT 0",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS cgst DOUBLE PRECISION DEFAULT 0",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS sgst DOUBLE PRECISION DEFAULT 0",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS igst DOUBLE PRECISION DEFAULT 0",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS total_amount DOUBLE PRECISION DEFAULT 0",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS raw_data JSONB",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    ]:
        await db.execute(text(col_sql))
    await db.commit()


def row_to_dict(row: Any) -> dict:
    data = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    if data.get("created_at") is not None:
        data["created_at"] = str(data["created_at"])
    return data


@router.post("")
@router.post("/")
@router.post("/create")
async def create_invoice(
    payload: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await ensure_invoice_table(db)
    invoice_id = f"inv_{int(datetime.utcnow().timestamp() * 1000)}"

    await db.execute(
        text(
            """
            INSERT INTO invoices (
                id, client_id, client_name, invoice_type,
                vendor_name, vendor_gstin, invoice_number, invoice_date,
                taxable_value, cgst, sgst, igst, total_amount, raw_data, created_at
            )
            VALUES (
                :id, :client_id, :client_name, :invoice_type,
                :vendor_name, :vendor_gstin, :invoice_number, :invoice_date,
                :taxable_value, :cgst, :sgst, :igst, :total_amount,
                CAST(:raw_data AS JSONB), CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "id": invoice_id,
            "client_id": payload.client_id or "",
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
            "raw_data": __import__("json").dumps(payload.raw_data or {}),
        },
    )
    await db.commit()

    return {"ok": True, "invoice_id": invoice_id, "message": "Invoice saved successfully"}


@router.get("")
@router.get("/")
@router.get("/list")
async def list_invoices(
    client_id: Optional[str] = Query(default=None),
    invoice_type: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await ensure_invoice_table(db)

    sql = "SELECT * FROM invoices WHERE 1=1"
    params: dict[str, Any] = {}

    if client_id:
        sql += " AND client_id = :client_id"
        params["client_id"] = client_id

    if invoice_type:
        sql += " AND invoice_type = :invoice_type"
        params["invoice_type"] = invoice_type

    sql += " ORDER BY created_at DESC LIMIT 500"

    result = await db.execute(text(sql), params)
    invoices = [row_to_dict(row) for row in result.fetchall()]
    return {"ok": True, "invoices": invoices, "count": len(invoices)}


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await ensure_invoice_table(db)
    result = await db.execute(text("SELECT * FROM invoices WHERE id = :id"), {"id": invoice_id})
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"ok": True, "invoice": row_to_dict(row)}


@router.put("/{invoice_id}")
async def update_invoice(
    invoice_id: str,
    payload: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await ensure_invoice_table(db)
    existing = await db.execute(text("SELECT id FROM invoices WHERE id = :id"), {"id": invoice_id})
    if not existing.fetchone():
        raise HTTPException(status_code=404, detail="Invoice not found")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return {"ok": True, "message": "No changes supplied"}

    allowed = {
        "client_id", "client_name", "invoice_type", "vendor_name", "vendor_gstin",
        "invoice_number", "invoice_date", "taxable_value", "cgst", "sgst",
        "igst", "total_amount", "raw_data"
    }
    updates = []
    params: dict[str, Any] = {"id": invoice_id}
    import json
    for key, value in data.items():
        if key not in allowed:
            continue
        if key == "raw_data":
            updates.append(f"{key} = CAST(:{key} AS JSONB)")
            params[key] = json.dumps(value or {})
        else:
            updates.append(f"{key} = :{key}")
            params[key] = value

    if not updates:
        return {"ok": True, "message": "No valid changes supplied"}

    # updated_at may not exist on old tables, so add it safely.
    await db.execute(text("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP"))
    updates.append("updated_at = CURRENT_TIMESTAMP")

    await db.execute(text("UPDATE invoices SET " + ", ".join(updates) + " WHERE id = :id"), params)
    await db.commit()
    return {"ok": True, "invoice_id": invoice_id, "message": "Invoice updated"}


@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await ensure_invoice_table(db)
    await db.execute(text("DELETE FROM invoices WHERE id = :id"), {"id": invoice_id})
    await db.commit()
    return {"ok": True, "message": "Invoice deleted"}
