from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import String, DateTime, Text, Float, Integer, JSON, select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from auth import CurrentUser, get_current_user
from database import Base, get_db, new_id


router = APIRouter(prefix="/reconciliation", tags=["AI GST Reconciliation"])


class GSTReconciliation(Base):
    __tablename__ = "ai_gst_reconciliations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True)
    client_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    client_name: Mapped[str] = mapped_column(String(255))

    period: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    purchase_register_file: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gstr2b_file: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    total_pr_invoices: Mapped[int] = mapped_column(Integer, default=0)
    total_2b_invoices: Mapped[int] = mapped_column(Integer, default=0)
    matched_count: Mapped[int] = mapped_column(Integer, default=0)
    mismatch_count: Mapped[int] = mapped_column(Integer, default=0)
    missing_in_2b_count: Mapped[int] = mapped_column(Integer, default=0)
    missing_in_pr_count: Mapped[int] = mapped_column(Integer, default=0)

    total_itc_pr: Mapped[float] = mapped_column(Float, default=0.0)
    total_itc_2b: Mapped[float] = mapped_column(Float, default=0.0)
    itc_difference: Mapped[float] = mapped_column(Float, default=0.0)

    status: Mapped[str] = mapped_column(String(50), default="completed")
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)

    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GSTMismatch(Base):
    __tablename__ = "ai_gst_mismatches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True)
    reconciliation_id: Mapped[str] = mapped_column(String(36), index=True)

    supplier_gstin: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    supplier_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    invoice_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    mismatch_type: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(50), default="medium")

    pr_taxable: Mapped[float] = mapped_column(Float, default=0.0)
    pr_itc: Mapped[float] = mapped_column(Float, default=0.0)
    gstr2b_taxable: Mapped[float] = mapped_column(Float, default=0.0)
    gstr2b_itc: Mapped[float] = mapped_column(Float, default=0.0)
    difference: Mapped[float] = mapped_column(Float, default=0.0)

    ai_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vendor_email_draft: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class InvoiceItem(BaseModel):
    supplier_gstin: Optional[str] = None
    supplier_name: Optional[str] = None
    invoice_number: str
    invoice_date: Optional[str] = None
    taxable_value: float = 0.0
    cgst: float = 0.0
    sgst: float = 0.0
    igst: float = 0.0


class ReconcileRequest(BaseModel):
    client_id: Optional[str] = None
    client_name: str
    period: Optional[str] = None
    purchase_register_file: Optional[str] = None
    gstr2b_file: Optional[str] = None
    purchase_register: List[InvoiceItem]
    gstr2b: List[InvoiceItem]


def norm_invoice(value: str) -> str:
    return str(value or "").replace("/", "").replace("-", "").replace(" ", "").upper().strip()


def total_itc(item: InvoiceItem) -> float:
    return round(float(item.cgst or 0) + float(item.sgst or 0) + float(item.igst or 0), 2)


def make_key(item: InvoiceItem) -> str:
    return f"{str(item.supplier_gstin or '').upper().strip()}::{norm_invoice(item.invoice_number)}"


def reconciliation_to_dict(r: GSTReconciliation) -> dict:
    return {
        "id": r.id,
        "client_id": r.client_id,
        "client_name": r.client_name,
        "period": r.period,
        "purchase_register_file": r.purchase_register_file,
        "gstr2b_file": r.gstr2b_file,
        "total_pr_invoices": r.total_pr_invoices,
        "total_2b_invoices": r.total_2b_invoices,
        "matched_count": r.matched_count,
        "mismatch_count": r.mismatch_count,
        "missing_in_2b_count": r.missing_in_2b_count,
        "missing_in_pr_count": r.missing_in_pr_count,
        "total_itc_pr": r.total_itc_pr,
        "total_itc_2b": r.total_itc_2b,
        "itc_difference": r.itc_difference,
        "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "result_json": r.result_json,
    }


def mismatch_to_dict(m: GSTMismatch) -> dict:
    return {
        "id": m.id,
        "reconciliation_id": m.reconciliation_id,
        "supplier_gstin": m.supplier_gstin,
        "supplier_name": m.supplier_name,
        "invoice_number": m.invoice_number,
        "invoice_date": m.invoice_date,
        "mismatch_type": m.mismatch_type,
        "severity": m.severity,
        "pr_taxable": m.pr_taxable,
        "pr_itc": m.pr_itc,
        "gstr2b_taxable": m.gstr2b_taxable,
        "gstr2b_itc": m.gstr2b_itc,
        "difference": m.difference,
        "ai_explanation": m.ai_explanation,
        "vendor_email_draft": m.vendor_email_draft,
        "status": m.status,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def generate_ai_explanation(mismatch_type: str, supplier: str, invoice: str, difference: float) -> str:
    if mismatch_type == "missing_in_2b":
        return f"Invoice {invoice} from {supplier} is available in Purchase Register but not found in GSTR-2B. ITC should be kept on hold until the supplier uploads or amends the invoice."
    if mismatch_type == "missing_in_pr":
        return f"Invoice {invoice} from {supplier} is available in GSTR-2B but missing in Purchase Register. Verify whether this purchase entry was omitted in books."
    if mismatch_type == "itc_difference":
        return f"Invoice {invoice} from {supplier} has ITC difference of ₹{difference}. Verify taxable value, CGST, SGST, IGST, and amendments."
    return f"Invoice {invoice} from {supplier} requires manual verification."


def generate_vendor_email(supplier: str, invoice: str, mismatch_type: str) -> str:
    return f"""Dear {supplier or 'Vendor'},

We are reconciling our GST ITC records and found an issue related to invoice {invoice}.

Mismatch Type: {mismatch_type}

Please verify the invoice details in your GSTR-1 and make the necessary correction/upload if required.

Regards,
Accounts Team
"""


@router.get("/status")
async def status(current_user: CurrentUser = Depends(get_current_user)):
    return {
        "status": "ok",
        "module": "ai_gst_reconciliation_engine",
        "storage": "postgresql",
        "firm_id": current_user.firm_id,
        "features": [
            "purchase_register_vs_gstr2b",
            "auto_matching",
            "missing_in_2b",
            "missing_in_purchase_register",
            "itc_difference",
            "ai_explanation",
            "vendor_email_draft",
            "firm_isolation"
        ]
    }


@router.post("/run")
async def run_reconciliation(
    payload: ReconcileRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    pr_map = {make_key(i): i for i in payload.purchase_register}
    b2b_map = {make_key(i): i for i in payload.gstr2b}

    all_keys = set(pr_map.keys()) | set(b2b_map.keys())

    matched = []
    mismatch_objects = []

    total_pr_itc = round(sum(total_itc(i) for i in payload.purchase_register), 2)
    total_2b_itc = round(sum(total_itc(i) for i in payload.gstr2b), 2)

    for key in all_keys:
        pr = pr_map.get(key)
        b2b = b2b_map.get(key)

        if pr and b2b:
            pr_itc = total_itc(pr)
            b2b_itc = total_itc(b2b)
            diff = round(pr_itc - b2b_itc, 2)

            if abs(diff) <= 1:
                matched.append(key)
            else:
                supplier = pr.supplier_name or b2b.supplier_name or "-"
                invoice = pr.invoice_number or b2b.invoice_number
                mismatch_objects.append({
                    "supplier_gstin": pr.supplier_gstin or b2b.supplier_gstin,
                    "supplier_name": supplier,
                    "invoice_number": invoice,
                    "invoice_date": pr.invoice_date or b2b.invoice_date,
                    "mismatch_type": "itc_difference",
                    "severity": "high" if abs(diff) > 1000 else "medium",
                    "pr_taxable": pr.taxable_value,
                    "pr_itc": pr_itc,
                    "gstr2b_taxable": b2b.taxable_value,
                    "gstr2b_itc": b2b_itc,
                    "difference": diff,
                })

        elif pr and not b2b:
            pr_itc = total_itc(pr)
            mismatch_objects.append({
                "supplier_gstin": pr.supplier_gstin,
                "supplier_name": pr.supplier_name,
                "invoice_number": pr.invoice_number,
                "invoice_date": pr.invoice_date,
                "mismatch_type": "missing_in_2b",
                "severity": "high",
                "pr_taxable": pr.taxable_value,
                "pr_itc": pr_itc,
                "gstr2b_taxable": 0.0,
                "gstr2b_itc": 0.0,
                "difference": pr_itc,
            })

        elif b2b and not pr:
            b2b_itc = total_itc(b2b)
            mismatch_objects.append({
                "supplier_gstin": b2b.supplier_gstin,
                "supplier_name": b2b.supplier_name,
                "invoice_number": b2b.invoice_number,
                "invoice_date": b2b.invoice_date,
                "mismatch_type": "missing_in_pr",
                "severity": "medium",
                "pr_taxable": 0.0,
                "pr_itc": 0.0,
                "gstr2b_taxable": b2b.taxable_value,
                "gstr2b_itc": b2b_itc,
                "difference": -b2b_itc,
            })

    rec = GSTReconciliation(
        firm_id=current_user.firm_id,
        client_id=payload.client_id,
        client_name=payload.client_name,
        period=payload.period,
        purchase_register_file=payload.purchase_register_file,
        gstr2b_file=payload.gstr2b_file,
        total_pr_invoices=len(payload.purchase_register),
        total_2b_invoices=len(payload.gstr2b),
        matched_count=len(matched),
        mismatch_count=len(mismatch_objects),
        missing_in_2b_count=sum(1 for m in mismatch_objects if m["mismatch_type"] == "missing_in_2b"),
        missing_in_pr_count=sum(1 for m in mismatch_objects if m["mismatch_type"] == "missing_in_pr"),
        total_itc_pr=total_pr_itc,
        total_itc_2b=total_2b_itc,
        itc_difference=round(total_pr_itc - total_2b_itc, 2),
        result_json={"matched": matched, "mismatches": mismatch_objects},
        created_by=current_user.user_id,
    )

    db.add(rec)
    await db.commit()
    await db.refresh(rec)

    saved_mismatches = []

    for m in mismatch_objects:
        explanation = generate_ai_explanation(
            m["mismatch_type"],
            m.get("supplier_name") or "-",
            m.get("invoice_number") or "-",
            m.get("difference") or 0
        )

        email = generate_vendor_email(
            m.get("supplier_name") or "Vendor",
            m.get("invoice_number") or "-",
            m["mismatch_type"]
        )

        mm = GSTMismatch(
            firm_id=current_user.firm_id,
            reconciliation_id=rec.id,
            supplier_gstin=m.get("supplier_gstin"),
            supplier_name=m.get("supplier_name"),
            invoice_number=m.get("invoice_number"),
            invoice_date=m.get("invoice_date"),
            mismatch_type=m["mismatch_type"],
            severity=m["severity"],
            pr_taxable=m["pr_taxable"],
            pr_itc=m["pr_itc"],
            gstr2b_taxable=m["gstr2b_taxable"],
            gstr2b_itc=m["gstr2b_itc"],
            difference=m["difference"],
            ai_explanation=explanation,
            vendor_email_draft=email,
        )

        db.add(mm)
        saved_mismatches.append(mm)

    await db.commit()

    return {
        "message": "Reconciliation completed",
        "reconciliation": reconciliation_to_dict(rec),
        "mismatches": [mismatch_to_dict(m) for m in saved_mismatches]
    }


@router.get("/list")
async def list_reconciliations(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(GSTReconciliation)
        .where(GSTReconciliation.firm_id == current_user.firm_id)
        .order_by(desc(GSTReconciliation.created_at))
    )

    records = result.scalars().all()

    return {
        "count": len(records),
        "reconciliations": [reconciliation_to_dict(r) for r in records]
    }


@router.get("/mismatches/{reconciliation_id}")
async def get_mismatches(
    reconciliation_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(GSTMismatch)
        .where(
            and_(
                GSTMismatch.firm_id == current_user.firm_id,
                GSTMismatch.reconciliation_id == reconciliation_id
            )
        )
        .order_by(desc(GSTMismatch.created_at))
    )

    mismatches = result.scalars().all()

    return {
        "count": len(mismatches),
        "mismatches": [mismatch_to_dict(m) for m in mismatches]
    }


@router.get("/dashboard")
async def dashboard(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    firm_filter = GSTReconciliation.firm_id == current_user.firm_id

    total_runs = await db.scalar(
        select(func.count()).select_from(GSTReconciliation).where(firm_filter)
    ) or 0

    total_mismatches = await db.scalar(
        select(func.count()).select_from(GSTMismatch).where(GSTMismatch.firm_id == current_user.firm_id)
    ) or 0

    high_risk = await db.scalar(
        select(func.count())
        .select_from(GSTMismatch)
        .where(and_(GSTMismatch.firm_id == current_user.firm_id, GSTMismatch.severity == "high"))
    ) or 0

    total_itc_difference = await db.scalar(
        select(func.coalesce(func.sum(GSTReconciliation.itc_difference), 0))
        .where(firm_filter)
    ) or 0

    return {
        "total_runs": total_runs,
        "total_mismatches": total_mismatches,
        "high_risk_mismatches": high_risk,
        "total_itc_difference": round(float(total_itc_difference), 2)
    }


@router.put("/mismatch/resolve/{mismatch_id}")
async def resolve_mismatch(
    mismatch_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(GSTMismatch).where(
            and_(
                GSTMismatch.id == mismatch_id,
                GSTMismatch.firm_id == current_user.firm_id
            )
        )
    )

    mismatch = result.scalar_one_or_none()

    if not mismatch:
        raise HTTPException(status_code=404, detail="Mismatch not found")

    mismatch.status = "resolved"
    await db.commit()
    await db.refresh(mismatch)

    return {
        "message": "Mismatch resolved",
        "mismatch": mismatch_to_dict(mismatch)
    }