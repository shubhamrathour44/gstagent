"""Saved Invoice Reconciliation API for GSTAgent.

Drop this file at: backend/reconcile_saved.py
Mount in main_v2.py:
    from reconcile_saved import router as reconcile_saved_router
    app.include_router(reconcile_saved_router)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth import CurrentUser, get_current_user
from database import get_db

try:
    from invoices import ensure_invoice_table
except Exception:
    ensure_invoice_table = None

router = APIRouter(prefix="/reconcile-saved", tags=["Saved Invoice Reconciliation"])

class ReconcileRunIn(BaseModel):
    client_id: str
    client_name: Optional[str] = None
    period: str = ""
    gstr2b: list[dict[str, Any]] = []


def _firm_id(user: Any) -> str:
    return str(getattr(user, "firm_id", None) or getattr(user, "id", None) or "demo_firm")

async def ensure_tables(db: AsyncSession) -> None:
    if ensure_invoice_table:
        await ensure_invoice_table(db)
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS saved_reconciliations (
            id VARCHAR(64) PRIMARY KEY,
            firm_id VARCHAR(64),
            client_id VARCHAR(64),
            client_name VARCHAR(255),
            period VARCHAR(32),
            matched_count INTEGER DEFAULT 0,
            mismatch_count INTEGER DEFAULT 0,
            itc_at_risk FLOAT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    await db.commit()

def norm(x: dict[str, Any]) -> dict[str, Any]:
    gstin = str(x.get("vendor_gstin") or x.get("supplier_gstin") or x.get("gstin") or x.get("ctin") or "").upper().replace(" ", "")
    inv = str(x.get("invoice_number") or x.get("inum") or x.get("invoice_no") or x.get("inv_no") or x.get("number") or "").upper().replace(" ", "")
    def num(*keys):
        for k in keys:
            try:
                if x.get(k) not in (None, ""):
                    return float(x.get(k) or 0)
            except Exception:
                pass
        return 0.0
    total = num("total_amount", "val", "invoice_value", "amount")
    tax = num("tax_amount") or (num("cgst", "camt") + num("sgst", "samt") + num("igst", "iamt"))
    return {**x, "_gstin": gstin, "_inv": inv, "_total": total, "_tax": tax}

@router.post("/run")
async def run_reconciliation(payload: ReconcileRunIn, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await ensure_tables(db)
    firm_id = _firm_id(current_user)
    result = await db.execute(text("""
        SELECT * FROM invoices
        WHERE firm_id = :firm_id AND client_id = :client_id AND invoice_type = 'purchase'
        ORDER BY created_at DESC LIMIT 1000
    """), {"firm_id": firm_id, "client_id": str(payload.client_id)})
    invoices = [norm(dict(r._mapping)) for r in result]
    gstr2b = [norm(x) for x in payload.gstr2b]

    bmap = {x["_gstin"] + "|" + x["_inv"]: x for x in gstr2b}
    used: set[str] = set()
    rows: list[dict[str, Any]] = []
    itc = 0.0

    for inv in invoices:
        key = inv["_gstin"] + "|" + inv["_inv"]
        b = bmap.get(key)
        tax_value = float(inv.get("cgst") or 0) + float(inv.get("sgst") or 0) + float(inv.get("igst") or 0)
        if not b:
            itc += tax_value
            rows.append({"status":"Missing in 2B","invoice_number":inv.get("invoice_number"),"vendor_gstin":inv.get("vendor_gstin"),"book_amount":inv.get("total_amount") or inv.get("_total"),"two_b_amount":0,"explanation":"Invoice exists in saved purchase register but not in GSTR-2B. Possible vendor filing issue.","action":"Vendor follow-up"})
            continue
        used.add(key)
        diff = abs(float(inv.get("total_amount") or inv.get("_total") or 0) - float(b.get("_total") or 0))
        if diff > 2:
            itc += diff
            rows.append({"status":"Amount Mismatch","invoice_number":inv.get("invoice_number"),"vendor_gstin":inv.get("vendor_gstin"),"book_amount":inv.get("total_amount") or inv.get("_total"),"two_b_amount":b.get("_total"),"explanation":"Invoice found in both records but value differs.","action":"Verify bill and GSTR-2B value"})
        else:
            rows.append({"status":"Matched","invoice_number":inv.get("invoice_number"),"vendor_gstin":inv.get("vendor_gstin"),"book_amount":inv.get("total_amount") or inv.get("_total"),"two_b_amount":b.get("_total"),"explanation":"Invoice matched with GSTR-2B.","action":"No action"})

    invoice_keys = {i["_gstin"] + "|" + i["_inv"] for i in invoices}
    for b in gstr2b:
        key = b["_gstin"] + "|" + b["_inv"]
        if key not in used and key not in invoice_keys:
            rows.append({"status":"Extra in 2B","invoice_number":b.get("invoice_number") or b.get("inum"),"vendor_gstin":b.get("supplier_gstin") or b.get("vendor_gstin") or b.get("gstin"),"book_amount":0,"two_b_amount":b.get("_total"),"explanation":"Invoice appears in GSTR-2B but not in saved invoice register.","action":"Check missing purchase bill"})

    summary = {
        "matched": len([r for r in rows if r["status"] == "Matched"]),
        "missing_in_2b": len([r for r in rows if r["status"] == "Missing in 2B"]),
        "amount_mismatch": len([r for r in rows if r["status"] == "Amount Mismatch"]),
        "extra_in_2b": len([r for r in rows if r["status"] == "Extra in 2B"]),
        "itc_at_risk": round(itc, 2),
    }
    rec_id = str(uuid4())
    await db.execute(text("""
        INSERT INTO saved_reconciliations (id, firm_id, client_id, client_name, period, matched_count, mismatch_count, itc_at_risk, created_at)
        VALUES (:id,:firm_id,:client_id,:client_name,:period,:matched_count,:mismatch_count,:itc_at_risk,:created_at)
    """), {"id":rec_id,"firm_id":firm_id,"client_id":payload.client_id,"client_name":payload.client_name or "","period":payload.period,"matched_count":summary["matched"],"mismatch_count":len(rows)-summary["matched"],"itc_at_risk":summary["itc_at_risk"],"created_at":datetime.utcnow()})
    await db.commit()
    return {"ok": True, "reconciliation_id": rec_id, "summary": summary, "results": rows}

@router.get("/list")
async def list_reconciliations(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await ensure_tables(db)
    result = await db.execute(text("""
        SELECT * FROM saved_reconciliations WHERE firm_id = :firm_id ORDER BY created_at DESC LIMIT 100
    """), {"firm_id": _firm_id(current_user)})
    rows = [dict(r._mapping) for r in result]
    return {"reconciliations": rows, "count": len(rows)}
