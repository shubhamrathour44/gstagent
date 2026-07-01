"""
Sales Register Reconciliation Router

API endpoints for reconciling Sales Register vs GSTR-1.
Complements purchase reconciliation (PR vs GSTR-2B).
"""

import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from auth import CurrentUser, get_current_user
from database import get_db, Reconciliation, Mismatch
from sales_reconciliation_engine import SalesReconciliationEngine

logger = logging.getLogger(__name__)

sales_router = APIRouter(prefix="/reconciliation/sales", tags=["Sales Reconciliation"])

_engine = SalesReconciliationEngine()


# ── SCHEMAS ────────────────────────────────────────────────────────────────────

class SalesReconciliationRequest(BaseModel):
    """Request to reconcile sales data."""
    gstin: str
    period: str  # MMYYYY
    company_name: str
    sales_register: list  # List of invoice dicts
    gstr1_invoices: list  # List of GSTR-1 invoices


class ReconciliationSummaryResponse(BaseModel):
    """Summary of reconciliation results."""
    reconciliation_id: str
    gstin: str
    period: str
    type: str  # "sales"
    total_invoices_sr: int
    total_invoices_gstr1: int
    matched: int
    mismatched: int
    match_rate: float
    revenue_difference: float
    tax_difference: float
    high_severity_issues: int
    medium_severity_issues: int
    low_severity_issues: int


# ── ENDPOINTS ──────────────────────────────────────────────────────────────────

@sales_router.post("/reconcile")
async def reconcile_sales(
    request: SalesReconciliationRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Reconcile Sales Register vs GSTR-1.

    Detects:
    - Invoices in SR but not in GSTR-1
    - Invoices in GSTR-1 but not in SR
    - Tax/amount mismatches
    - Supply type differences

    Returns detailed mismatch report with recommended actions.
    """
    try:
        # Run reconciliation
        result = _engine.reconcile(
            gstin=request.gstin,
            period=request.period,
            sales_register=request.sales_register,
            gstr1_invoices=request.gstr1_invoices
        )

        # Store in database
        reconciliation = Reconciliation(
            firm_id=current_user.firm_id,
            client_id=None,  # Can be linked later
            gstin=request.gstin,
            company_name=request.company_name,
            period=request.period,
            source="gstr1",
            result_json=result.to_dict(),
            pr_count=result.total_sr_invoices,
            b2b_count=result.total_gstr1_invoices,
            matched_count=result.matched_invoices,
            mismatch_count=result.mismatched_invoices,
            match_rate=result.summary_stats.get("match_rate", 0),
            itc_difference=result.tax_difference,
            high_count=result.high_severity_count,
            medium_count=result.medium_severity_count,
            low_count=result.low_severity_count,
            created_by=current_user.id,
        )
        db.add(reconciliation)
        await db.flush()

        # Store mismatches
        for mismatch in result.mismatches:
            mismatch_obj = Mismatch(
                firm_id=current_user.firm_id,
                reconciliation_id=reconciliation.id,
                mismatch_id=mismatch.mismatch_id,
                mismatch_type=mismatch.mismatch_type.value,
                severity=mismatch.severity.value,
                supplier_name=mismatch.customer_name,
                supplier_gstin=mismatch.customer_gstin,
                invoice_number=mismatch.invoice_number,
                invoice_date=mismatch.invoice_date,
                tax_impact=mismatch.tax_impact,
                recommended_action=mismatch.recommended_action.value,
                raw_json=mismatch.to_dict(),
            )
            db.add(mismatch_obj)

        await db.commit()
        await db.refresh(reconciliation)

        logger.info(f"Sales reconciliation completed: {request.gstin} {request.period}")

        return {
            "success": True,
            "reconciliation_id": reconciliation.id,
            "gstin": request.gstin,
            "period": request.period,
            "message": "Sales reconciliation completed",
            "summary": {
                "total_sr_invoices": result.total_sr_invoices,
                "total_gstr1_invoices": result.total_gstr1_invoices,
                "matched": result.matched_invoices,
                "mismatched": result.mismatched_invoices,
                "match_rate": result.summary_stats.get("match_rate", 0),
                "missing_in_gstr1": result.missing_in_gstr1,
                "missing_in_sr": result.missing_in_sr,
                "revenue_difference": result.revenue_difference,
                "tax_difference": result.tax_difference,
                "high_severity": result.high_severity_count,
                "medium_severity": result.medium_severity_count,
                "low_severity": result.low_severity_count,
            },
            "next_step": "Review mismatches and take recommended actions"
        }

    except Exception as e:
        logger.error(f"Sales reconciliation error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Reconciliation failed: {str(e)}")


@sales_router.get("/results/{reconciliation_id}")
async def get_reconciliation_results(
    reconciliation_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed reconciliation results."""
    result = await db.execute(
        select(Reconciliation).where(
            and_(
                Reconciliation.id == reconciliation_id,
                Reconciliation.firm_id == current_user.firm_id
            )
        )
    )
    reconciliation = result.scalar_one_or_none()

    if not reconciliation:
        raise HTTPException(status_code=404, detail="Reconciliation not found")

    return {
        "reconciliation_id": reconciliation.id,
        "gstin": reconciliation.gstin,
        "period": reconciliation.period,
        "company_name": reconciliation.company_name,
        "reconciled_at": reconciliation.created_at.isoformat(),
        "summary": {
            "total_sr": reconciliation.pr_count,
            "total_gstr1": reconciliation.b2b_count,
            "matched": reconciliation.matched_count,
            "mismatched": reconciliation.mismatch_count,
            "match_rate": reconciliation.match_rate,
            "revenue_difference": reconciliation.itc_difference,
            "high_severity": reconciliation.high_count,
            "medium_severity": reconciliation.medium_count,
            "low_severity": reconciliation.low_count,
        },
        "full_result": reconciliation.result_json
    }


@sales_router.get("/mismatches/{reconciliation_id}")
async def get_mismatches(
    reconciliation_id: str,
    severity: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get mismatches from a reconciliation."""
    query = select(Mismatch).where(
        and_(
            Mismatch.reconciliation_id == reconciliation_id,
            Mismatch.firm_id == current_user.firm_id
        )
    )

    if severity:
        query = query.where(Mismatch.severity == severity)

    result = await db.execute(query.order_by(desc(Mismatch.tax_impact)))
    mismatches = result.scalars().all()

    return {
        "reconciliation_id": reconciliation_id,
        "total_mismatches": len(mismatches),
        "mismatches": [
            {
                "mismatch_id": m.mismatch_id,
                "type": m.mismatch_type,
                "severity": m.severity,
                "customer": m.supplier_name,
                "gstin": m.supplier_gstin,
                "invoice_no": m.invoice_number,
                "invoice_date": m.invoice_date,
                "tax_impact": m.tax_impact,
                "recommended_action": m.recommended_action,
                "status": m.status,
            }
            for m in mismatches
        ]
    }


@sales_router.get("/statistics")
async def get_sales_reconciliation_stats(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get sales reconciliation statistics."""
    # Total reconciliations
    total_result = await db.execute(
        select(func.count(Reconciliation.id)).where(
            and_(
                Reconciliation.firm_id == current_user.firm_id,
                Reconciliation.source == "gstr1"
            )
        )
    )
    total_recon = total_result.scalar() or 0

    # Mismatches by severity
    severity_result = await db.execute(
        select(Mismatch.severity, func.count(Mismatch.id)).where(
            and_(
                Mismatch.firm_id == current_user.firm_id,
                Mismatch.status == "open"
            )
        ).group_by(Mismatch.severity)
    )
    severity_stats = {row[0]: row[1] for row in severity_result.fetchall()}

    # Total tax impact of open mismatches
    impact_result = await db.execute(
        select(func.sum(Mismatch.tax_impact)).where(
            and_(
                Mismatch.firm_id == current_user.firm_id,
                Mismatch.status == "open"
            )
        )
    )
    total_impact = impact_result.scalar() or 0

    return {
        "total_reconciliations": total_recon,
        "open_mismatches": {
            "high": severity_stats.get("high", 0),
            "medium": severity_stats.get("medium", 0),
            "low": severity_stats.get("low", 0),
        },
        "total_tax_impact": total_impact,
        "next_step": "Review high and medium severity mismatches"
    }


@sales_router.post("/mismatches/{mismatch_id}/resolve")
async def resolve_mismatch(
    mismatch_id: str,
    resolution_notes: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark mismatch as resolved."""
    result = await db.execute(
        select(Mismatch).where(
            and_(
                Mismatch.mismatch_id == mismatch_id,
                Mismatch.firm_id == current_user.firm_id
            )
        )
    )
    mismatch = result.scalar_one_or_none()

    if not mismatch:
        raise HTTPException(status_code=404, detail="Mismatch not found")

    mismatch.status = "resolved"
    mismatch.resolution_notes = resolution_notes
    mismatch.resolved_by = current_user.id
    mismatch.resolved_at = datetime.utcnow()

    await db.commit()

    return {
        "success": True,
        "mismatch_id": mismatch_id,
        "status": "resolved",
        "message": "Mismatch marked as resolved"
    }


@sales_router.get("/periodic-summary")
async def periodic_summary(
    period: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get sales reconciliation summary for a period.

    Shows all GSTs with their reconciliation status.
    """
    query = select(Reconciliation).where(
        and_(
            Reconciliation.firm_id == current_user.firm_id,
            Reconciliation.source == "gstr1"
        )
    )

    if period:
        query = query.where(Reconciliation.period == period)

    result = await db.execute(
        query.order_by(desc(Reconciliation.created_at))
    )
    reconciliations = result.scalars().all()

    return {
        "period": period,
        "total_reconciliations": len(reconciliations),
        "summary": [
            {
                "gstin": r.gstin,
                "period": r.period,
                "company": r.company_name,
                "match_rate": r.match_rate,
                "mismatches": r.mismatch_count,
                "high_severity": r.high_count,
                "tax_impact": r.itc_difference,
                "reconciled_at": r.created_at.isoformat(),
            }
            for r in reconciliations
        ]
    }


@sales_router.get("/status")
async def sales_reconciliation_status(current_user: CurrentUser = Depends(get_current_user)):
    """Get sales reconciliation module status."""
    return {
        "status": "ok",
        "module": "sales_reconciliation",
        "capabilities": [
            "reconcile_sr_vs_gstr1",
            "mismatch_detection",
            "severity_classification",
            "financial_impact_calculation",
            "customer_wise_summary",
            "resolution_tracking",
            "periodic_reporting"
        ],
        "features": {
            "mismatch_types": [
                "invoice_not_in_gstr1",
                "invoice_not_in_sr",
                "taxable_value_mismatch",
                "tax_amount_mismatch",
                "supply_type_mismatch"
            ],
            "severity_levels": ["high", "medium", "low"],
            "impact_metrics": ["revenue_difference", "tax_impact", "match_rate"]
        },
        "note": "Complements purchase reconciliation (PR vs GSTR-2B) for complete GST validation"
    }
