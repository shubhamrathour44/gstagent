"""
Saved Invoice Reconciliation API for GSTAgent demo.

Fix included:
- Does NOT depend on firm_id column.
- Reads saved purchase invoices from invoices table using client_id.
- Matches saved invoices against pasted/uploaded GSTR-2B JSON rows.
"""

from __future__ import annotations

from typing import Optional, Any
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user, CurrentUser
from database import get_db

try:
    from invoices import ensure_invoice_table
except Exception:
    ensure_invoice_table = None


router = APIRouter(prefix="/reconcile-saved", tags=["Saved Invoice Reconciliation"])


CREATE_RECON_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS saved_reconciliations (
    id TEXT PRIMARY KEY,
    client_id TEXT,
    client_name TEXT,
    period TEXT,
    matched_count INTEGER DEFAULT 0,
    mismatch_count INTEGER DEFAULT 0,
    missing_count INTEGER DEFAULT 0,
    amount_mismatch_count INTEGER DEFAULT 0,
    gstin_mismatch_count INTEGER DEFAULT 0,
    itc_difference DOUBLE PRECISION DEFAULT 0,
    results JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class ReconcileSavedRequest(BaseModel):
    client_id: str
    client_name: Optional[str] = ""
    period: str
    gstr2b: list[dict[str, Any]] = []


async def ensure_tables(db: AsyncSession) -> None:
    if ensure_invoice_table:
        await ensure_invoice_table(db)
    await db.execute(text(CREATE_RECON_TABLE_SQL))
    await db.commit()


def norm(v: Any) -> str:
    return str(v or "").strip().upper().replace(" ", "").replace("-", "").replace("/", "")


def get_val(row: dict, keys: list[str], default: Any = "") -> Any:
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    lower = {str(k).lower(): v for k, v in row.items()}
    for k in keys:
        lk = k.lower()
        if lk in lower and lower[lk] not in (None, ""):
            return lower[lk]
    return default


def to_float(v: Any) -> float:
    try:
        return float(str(v or 0).replace(",", "").replace("₹", "").strip())
    except Exception:
        return 0.0


def invoice_key(row: dict) -> str:
    gstin = norm(get_val(row, ["vendor_gstin", "supplier_gstin", "gstin", "ctin"]))
    inv = norm(get_val(row, ["invoice_number", "inum", "invoice_no", "inv_no"]))
    return f"{gstin}|{inv}"


def row_to_dict(row: Any) -> dict:
    data = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    if data.get("created_at") is not None:
        data["created_at"] = str(data["created_at"])
    return data


@router.post("/run")
async def run_reconciliation(
    payload: ReconcileSavedRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await ensure_tables(db)

    inv_result = await db.execute(
        text(
            """
            SELECT * FROM invoices
            WHERE client_id = :client_id
            AND COALESCE(invoice_type, 'purchase') = 'purchase'
            ORDER BY created_at DESC
            LIMIT 1000
            """
        ),
        {"client_id": payload.client_id},
    )
    purchase_invoices = [row_to_dict(r) for r in inv_result.fetchall()]

    two_b = payload.gstr2b or []
    two_b_by_key = {invoice_key(x): x for x in two_b if invoice_key(x) != "|"}

    results = []
    matched = 0
    missing = 0
    amount_mismatch = 0
    gstin_mismatch = 0
    itc_risk = 0.0

    for inv in purchase_invoices:
        key = invoice_key(inv)
        total = to_float(get_val(inv, ["total_amount", "total", "invoice_value", "val"]))
        tax = to_float(inv.get("cgst")) + to_float(inv.get("sgst")) + to_float(inv.get("igst"))

        match = two_b_by_key.get(key)

        if match:
            b_total = to_float(get_val(match, ["total_amount", "total", "invoice_value", "val"]))
            b_tax = to_float(get_val(match, ["tax_amount", "tax", "igst", "cgst", "sgst"], 0))
            diff = abs(total - b_total)

            if diff > 5:
                amount_mismatch += 1
                itc_risk += tax
                results.append({
                    "status": "AMOUNT_MISMATCH",
                    "severity": "HIGH" if diff > 1000 else "MEDIUM",
                    "invoice_number": inv.get("invoice_number"),
                    "vendor_gstin": inv.get("vendor_gstin"),
                    "vendor_name": inv.get("vendor_name"),
                    "book_total": total,
                    "gstr2b_total": b_total,
                    "difference": diff,
                    "itc_risk": tax,
                    "reason": "Invoice matched by GSTIN and invoice number, but amount differs from GSTR-2B."
                })
            else:
                matched += 1
                results.append({
                    "status": "MATCHED",
                    "severity": "LOW",
                    "invoice_number": inv.get("invoice_number"),
                    "vendor_gstin": inv.get("vendor_gstin"),
                    "vendor_name": inv.get("vendor_name"),
                    "book_total": total,
                    "gstr2b_total": b_total,
                    "difference": diff,
                    "itc_risk": 0,
                    "reason": "Invoice matched with GSTR-2B."
                })
        else:
            # Try same invoice number but different GSTIN
            inv_no = norm(inv.get("invoice_number"))
            possible = None
            for row in two_b:
                if norm(get_val(row, ["invoice_number", "inum", "invoice_no", "inv_no"])) == inv_no:
                    possible = row
                    break

            if possible:
                gstin_mismatch += 1
                itc_risk += tax
                results.append({
                    "status": "GSTIN_MISMATCH",
                    "severity": "HIGH",
                    "invoice_number": inv.get("invoice_number"),
                    "vendor_gstin": inv.get("vendor_gstin"),
                    "gstr2b_gstin": get_val(possible, ["vendor_gstin", "supplier_gstin", "gstin", "ctin"]),
                    "vendor_name": inv.get("vendor_name"),
                    "book_total": total,
                    "gstr2b_total": to_float(get_val(possible, ["total_amount", "total", "invoice_value", "val"])),
                    "difference": 0,
                    "itc_risk": tax,
                    "reason": "Invoice number found in GSTR-2B, but supplier GSTIN differs."
                })
            else:
                missing += 1
                itc_risk += tax
                results.append({
                    "status": "MISSING_IN_2B",
                    "severity": "HIGH",
                    "invoice_number": inv.get("invoice_number"),
                    "vendor_gstin": inv.get("vendor_gstin"),
                    "vendor_name": inv.get("vendor_name"),
                    "book_total": total,
                    "gstr2b_total": 0,
                    "difference": total,
                    "itc_risk": tax,
                    "reason": "Invoice exists in saved purchase invoices but is not found in GSTR-2B. Possible vendor filing issue."
                })

    mismatch_count = missing + amount_mismatch + gstin_mismatch
    recon_id = f"rec_{__import__('time').time_ns()}"

    await db.execute(
        text(
            """
            INSERT INTO saved_reconciliations (
                id, client_id, client_name, period,
                matched_count, mismatch_count, missing_count,
                amount_mismatch_count, gstin_mismatch_count,
                itc_difference, results, created_at
            )
            VALUES (
                :id, :client_id, :client_name, :period,
                :matched_count, :mismatch_count, :missing_count,
                :amount_mismatch_count, :gstin_mismatch_count,
                :itc_difference, CAST(:results AS JSONB), CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "id": recon_id,
            "client_id": payload.client_id,
            "client_name": payload.client_name or "",
            "period": payload.period,
            "matched_count": matched,
            "mismatch_count": mismatch_count,
            "missing_count": missing,
            "amount_mismatch_count": amount_mismatch,
            "gstin_mismatch_count": gstin_mismatch,
            "itc_difference": itc_risk,
            "results": __import__("json").dumps(results),
        },
    )
    await db.commit()

    return {
        "ok": True,
        "reconciliation_id": recon_id,
        "summary": {
            "matched": matched,
            "mismatches": mismatch_count,
            "missing_in_2b": missing,
            "amount_mismatch": amount_mismatch,
            "gstin_mismatch": gstin_mismatch,
            "itc_risk": itc_risk,
            "total_purchase_invoices": len(purchase_invoices),
            "total_gstr2b_rows": len(two_b),
        },
        "results": results,
    }


@router.get("/list")
async def list_reconciliations(
    client_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await ensure_tables(db)

    sql = "SELECT * FROM saved_reconciliations WHERE 1=1"
    params: dict[str, Any] = {}
    if client_id:
        sql += " AND client_id = :client_id"
        params["client_id"] = client_id
    sql += " ORDER BY created_at DESC LIMIT 100"

    result = await db.execute(text(sql), params)
    rows = [row_to_dict(r) for r in result.fetchall()]
    return {"ok": True, "reconciliations": rows, "count": len(rows)}
