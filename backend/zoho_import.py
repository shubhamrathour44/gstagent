
from __future__ import annotations

import io
import re
import uuid
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth import CurrentUser, get_current_user
from database import get_db

router = APIRouter(prefix="/zoho-import", tags=["Zoho Books Import"])

def _clean_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")

def _find(row: dict, names: list[str], default: Any = "") -> Any:
    for name in names:
        if name in row and pd.notna(row[name]):
            return row[name]
    return default

def _num(value: Any) -> float:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    s = str(value).replace(",", "").replace("₹", "").strip()
    if s == "" or s.lower() in {"nan", "none"}:
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0

def _date(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    try:
        return pd.to_datetime(value).date().isoformat()
    except Exception:
        return str(value).strip()

async def _ensure_invoice_table(db: AsyncSession) -> None:
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            client_id TEXT,
            invoice_type TEXT,
            vendor_name TEXT,
            vendor_gstin TEXT,
            invoice_number TEXT,
            invoice_date TEXT,
            taxable_value NUMERIC DEFAULT 0,
            cgst NUMERIC DEFAULT 0,
            sgst NUMERIC DEFAULT 0,
            igst NUMERIC DEFAULT 0,
            total_amount NUMERIC DEFAULT 0,
            source TEXT DEFAULT 'tally',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    for col, typ in [
        ("client_id", "TEXT"), ("invoice_type", "TEXT"), ("vendor_name", "TEXT"),
        ("vendor_gstin", "TEXT"), ("invoice_number", "TEXT"), ("invoice_date", "TEXT"),
        ("taxable_value", "NUMERIC DEFAULT 0"), ("cgst", "NUMERIC DEFAULT 0"),
        ("sgst", "NUMERIC DEFAULT 0"), ("igst", "NUMERIC DEFAULT 0"),
        ("total_amount", "NUMERIC DEFAULT 0"), ("source", "TEXT DEFAULT 'tally'"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ]:
        await db.execute(text(f"ALTER TABLE invoices ADD COLUMN IF NOT EXISTS {col} {typ}"))
    await db.commit()

async def _read_table(file: UploadFile) -> pd.DataFrame:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    name = (file.filename or "").lower()
    if name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(raw))
    else:
        df = pd.read_excel(io.BytesIO(raw))
    df.columns = [_clean_key(c) for c in df.columns]
    return df.fillna("")

def _normalize(row: dict, client_id: str, invoice_type: str) -> dict:
    vendor_name = _find(row, ["party_name", "particulars", "supplier_name", "vendor_name", "customer_name", "ledger_name", "name", "buyer_name"])
    vendor_gstin = str(_find(row, ["gstin", "supplier_gstin", "party_gstin", "vendor_gstin", "customer_gstin", "gstin_uin", "registration_number"])).upper().strip()
    invoice_number = str(_find(row, ["invoice_number", "invoice_no", "voucher_no", "voucher_number", "bill_no", "reference_no", "ref_no", "document_number"], f"ZOHO-{uuid.uuid4().hex[:8].upper()}")).strip()
    invoice_date = _date(_find(row, ["invoice_date", "date", "voucher_date", "bill_date", "document_date"]))
    taxable = _num(_find(row, ["taxable_value", "taxable_amount", "assessable_value", "basic_value", "amount_before_tax", "net_amount"], 0))
    cgst = _num(_find(row, ["cgst", "central_tax", "cgst_amount"], 0))
    sgst = _num(_find(row, ["sgst", "state_tax", "sgst_amount"], 0))
    igst = _num(_find(row, ["igst", "integrated_tax", "igst_amount"], 0))
    total = _num(_find(row, ["total_amount", "invoice_value", "gross_total", "amount", "total"], 0))
    if total == 0:
        total = taxable + cgst + sgst + igst
    return {
        "id": str(uuid.uuid4()), "client_id": client_id, "invoice_type": invoice_type,
        "vendor_name": str(vendor_name).strip(), "vendor_gstin": vendor_gstin,
        "invoice_number": invoice_number, "invoice_date": invoice_date,
        "taxable_value": taxable, "cgst": cgst, "sgst": sgst, "igst": igst,
        "total_amount": total, "source": "zoho"
    }

@router.get("/status")
async def status(current_user: CurrentUser = Depends(get_current_user)):
    return {"status": "ready", "provider": "zoho"}

@router.post("/invoices")
async def import_invoices(
    client_id: str = Form(...),
    invoice_type: str = Form("purchase"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    invoice_type = invoice_type.lower().strip()
    if invoice_type not in {"purchase", "sales"}:
        raise HTTPException(status_code=400, detail="invoice_type must be purchase or sales")
    await _ensure_invoice_table(db)
    df = await _read_table(file)
    imported, skipped, samples = 0, 0, []
    for _, r in df.iterrows():
        inv = _normalize(r.to_dict(), client_id, invoice_type)
        if not inv["invoice_number"] and not inv["vendor_name"]:
            skipped += 1
            continue
        await db.execute(text("""
            INSERT INTO invoices (
                id, client_id, invoice_type, vendor_name, vendor_gstin, invoice_number,
                invoice_date, taxable_value, cgst, sgst, igst, total_amount, source, created_at, updated_at
            ) VALUES (
                :id, :client_id, :invoice_type, :vendor_name, :vendor_gstin, :invoice_number,
                :invoice_date, :taxable_value, :cgst, :sgst, :igst, :total_amount, :source, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
        """), inv)
        imported += 1
        if len(samples) < 5:
            samples.append(inv)
    await db.commit()
    return {"status": "success", "provider": "zoho", "imported": imported, "skipped": skipped, "samples": samples}

@router.post("/masters")
async def import_masters(file: UploadFile = File(...), current_user: CurrentUser = Depends(get_current_user)):
    df = await _read_table(file)
    return {"status": "success", "provider": "zoho", "masters_found": len(df), "columns": list(df.columns)}
