"""
GST Payment Tracking Router

API endpoints for:
- Payment schedule generation
- Late payment interest calculation
- Payment recording
- Payment status tracking
- Financial reporting
"""

import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel
from decimal import Decimal

from auth import CurrentUser, get_current_user
from database import Base, get_db, new_id
from gst.payment_engine import (
    InterestCalculationEngine,
    PaymentScheduleEngine,
    PaymentTracker,
    PaymentStatus,
    PaymentMethod,
    PaymentRecord,
    PaymentSchedule
)

logger = logging.getLogger(__name__)

payment_router = APIRouter(prefix="/gst-payments", tags=["GST Payments"])


# ── DATABASE MODELS ────────────────────────────────────────────────────────────

class GSTPayment(Base):
    """GST payment record."""
    __tablename__ = "gst_payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    gstin: Mapped[str] = mapped_column(String(15), index=True, nullable=False)
    period: Mapped[str] = mapped_column(String(6), index=True, nullable=False)

    tax_payable: Mapped[float] = mapped_column(Float, nullable=False)
    amount_paid: Mapped[float] = mapped_column(Float, default=0.0)

    due_date: Mapped[str] = mapped_column(String(10), nullable=False)
    payment_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    challan_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    payment_status: Mapped[str] = mapped_column(String(20), default="not_due", index=True)
    interest_due: Mapped[float] = mapped_column(Float, default=0.0)
    total_due: Mapped[float] = mapped_column(Float, default=0.0)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── SCHEMAS ────────────────────────────────────────────────────────────────────

class PaymentRecordRequest(BaseModel):
    """Record a payment."""
    gstin: str
    period: str
    amount_paid: float
    payment_date: str  # YYYY-MM-DD
    payment_method: str  # bank_transfer, challan, etc.
    challan_number: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class PaymentScheduleResponse(BaseModel):
    """Payment schedule entry."""
    gstin: str
    period: str
    return_type: str
    tax_payable: float
    due_date: str
    days_until_due: int
    status: str
    amount_paid: float = 0.0
    payment_date: Optional[str] = None
    interest_due: float = 0.0
    total_due: float = 0.0


class PaymentStatusResponse(BaseModel):
    """Payment status."""
    tax_payable: float
    amount_paid: float
    balance: float
    due_date: str
    days_overdue: int
    interest_amount: float
    total_due: float
    status: str


# ── ENDPOINTS ──────────────────────────────────────────────────────────────────

@payment_router.get("/schedule")
async def get_payment_schedule(
    gstin: str,
    period: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get payment schedule for GST returns.

    Returns due dates for GSTR-1 and GSTR-3B filing.
    """
    try:
        # If period specified, get that month's schedule
        if period:
            result = await db.execute(
                select(GSTPayment).where(
                    and_(
                        GSTPayment.firm_id == current_user.firm_id,
                        GSTPayment.gstin == gstin.upper(),
                        GSTPayment.period == period
                    )
                ).order_by(GSTPayment.due_date)
            )
            payments = result.scalars().all()

            return {
                "gstin": gstin,
                "period": period,
                "schedule": [
                    {
                        "return_type": "GSTR-3B",  # Assuming GSTR-3B
                        "tax_payable": p.tax_payable,
                        "due_date": p.due_date,
                        "status": p.payment_status,
                        "amount_paid": p.amount_paid,
                        "interest_due": p.interest_due,
                        "total_due": p.total_due
                    }
                    for p in payments
                ]
            }
        else:
            # Get upcoming due dates (next 3 months)
            result = await db.execute(
                select(GSTPayment).where(
                    and_(
                        GSTPayment.firm_id == current_user.firm_id,
                        GSTPayment.gstin == gstin.upper()
                    )
                ).order_by(GSTPayment.due_date).limit(3)
            )
            payments = result.scalars().all()

            return {
                "gstin": gstin,
                "upcoming_schedule": [
                    {
                        "period": p.period,
                        "due_date": p.due_date,
                        "tax_payable": p.tax_payable,
                        "status": p.payment_status
                    }
                    for p in payments
                ]
            }

    except Exception as e:
        logger.error(f"Schedule retrieval error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@payment_router.post("/record")
async def record_payment(
    request: PaymentRecordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Record a GST payment.

    Tracks payment date, method, and calculates interest if late.
    """
    try:
        # Get payment record
        result = await db.execute(
            select(GSTPayment).where(
                and_(
                    GSTPayment.firm_id == current_user.firm_id,
                    GSTPayment.gstin == request.gstin.upper(),
                    GSTPayment.period == request.period
                )
            )
        )
        payment = result.scalar_one_or_none()

        if not payment:
            # Create new payment record
            payment = GSTPayment(
                firm_id=current_user.firm_id,
                gstin=request.gstin.upper(),
                period=request.period,
                tax_payable=0.0,  # Will be set from GSTR-3B
                amount_paid=request.amount_paid,
                due_date=datetime.now().strftime("%Y-%m-%d"),
                payment_date=request.payment_date,
                payment_method=request.payment_method,
                challan_number=request.challan_number,
                reference_number=request.reference_number,
                notes=request.notes,
                recorded_by=current_user.id
            )
            db.add(payment)
        else:
            # Update existing record
            payment.amount_paid = request.amount_paid
            payment.payment_date = request.payment_date
            payment.payment_method = request.payment_method
            payment.challan_number = request.challan_number
            payment.reference_number = request.reference_number
            payment.notes = request.notes
            payment.updated_at = datetime.utcnow()

        # Calculate interest if late
        interest_calc = InterestCalculationEngine.calculate_interest(
            principal=max(0, payment.tax_payable - payment.amount_paid),
            due_date=payment.due_date,
            payment_date=request.payment_date
        )

        payment.interest_due = interest_calc.interest_amount
        payment.total_due = interest_calc.total_due
        payment.payment_status = PaymentScheduleEngine._determine_status(
            payment.due_date,
            request.payment_date
        )

        await db.commit()
        await db.refresh(payment)

        logger.info(f"Payment recorded: {request.gstin} {request.period}")

        return {
            "success": True,
            "message": "Payment recorded successfully",
            "payment": {
                "gstin": payment.gstin,
                "period": payment.period,
                "amount_paid": payment.amount_paid,
                "payment_date": payment.payment_date,
                "payment_method": payment.payment_method,
                "status": payment.payment_status,
                "interest_due": payment.interest_due,
                "total_due": payment.total_due
            }
        }

    except Exception as e:
        logger.error(f"Payment recording error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@payment_router.get("/status/{gstin}/{period}")
async def get_payment_status(
    gstin: str,
    period: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get payment status for a period."""
    result = await db.execute(
        select(GSTPayment).where(
            and_(
                GSTPayment.firm_id == current_user.firm_id,
                GSTPayment.gstin == gstin.upper(),
                GSTPayment.period == period
            )
        )
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    # Recalculate interest if not paid yet
    if not payment.payment_date:
        interest_calc = InterestCalculationEngine.calculate_interest(
            principal=payment.tax_payable - payment.amount_paid,
            due_date=payment.due_date
        )
        payment.interest_due = interest_calc.interest_amount
        payment.total_due = interest_calc.total_due

    return PaymentStatusResponse(
        tax_payable=payment.tax_payable,
        amount_paid=payment.amount_paid,
        balance=payment.tax_payable - payment.amount_paid,
        due_date=payment.due_date,
        days_overdue=max(0, (datetime.now().date() - datetime.fromisoformat(payment.due_date).date()).days),
        interest_amount=payment.interest_due,
        total_due=payment.total_due,
        status=payment.payment_status
    )


@payment_router.get("/summary/{gstin}")
async def get_payment_summary(
    gstin: str,
    fiscal_year: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get payment summary for GSTIN.

    Shows all payments, totals, and status.
    """
    query = select(GSTPayment).where(
        and_(
            GSTPayment.firm_id == current_user.firm_id,
            GSTPayment.gstin == gstin.upper()
        )
    )

    result = await db.execute(query.order_by(desc(GSTPayment.period)))
    payments = result.scalars().all()

    if not payments:
        return {
            "gstin": gstin,
            "total_due": 0.0,
            "total_paid": 0.0,
            "balance": 0.0,
            "payments": []
        }

    total_tax = sum(p.tax_payable for p in payments)
    total_paid = sum(p.amount_paid for p in payments)
    total_interest = sum(p.interest_due for p in payments)
    total_due = sum(p.total_due for p in payments)

    # Recalculate interests for unpaid amounts
    for p in payments:
        if not p.payment_date:
            interest = InterestCalculationEngine.calculate_interest(
                principal=p.tax_payable - p.amount_paid,
                due_date=p.due_date
            )
            p.interest_due = interest.interest_amount
            p.total_due = interest.total_due

    return {
        "gstin": gstin,
        "fiscal_year": fiscal_year,
        "total_payments": len([p for p in payments if p.payment_date]),
        "total_tax_due": total_tax,
        "total_paid": total_paid,
        "balance": total_tax - total_paid,
        "total_interest": sum(p.interest_due for p in payments),
        "total_amount_due": total_tax - total_paid + sum(p.interest_due for p in payments),
        "payments": [
            {
                "period": p.period,
                "tax_payable": p.tax_payable,
                "amount_paid": p.amount_paid,
                "payment_date": p.payment_date,
                "status": p.payment_status,
                "interest": p.interest_due,
                "total_due": p.total_due
            }
            for p in sorted(payments, key=lambda x: x.period, reverse=True)
        ]
    }


@payment_router.get("/interest-calculator")
async def calculate_interest(
    tax_amount: float = Query(...),
    due_date: str = Query(...),  # YYYY-MM-DD
    payment_date: Optional[str] = Query(None),  # YYYY-MM-DD
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Calculate interest for late payment.

    18% per annum = 1.5% per month = 0.05% per day
    """
    try:
        interest_calc = InterestCalculationEngine.calculate_interest(
            principal=tax_amount,
            due_date=due_date,
            payment_date=payment_date
        )

        return {
            "tax_amount": tax_amount,
            "due_date": due_date,
            "payment_date": payment_date or "Not paid",
            "interest_rate": "18% p.a.",
            "days_late": interest_calc.days_late,
            "interest_amount": interest_calc.interest_amount,
            "total_payable": interest_calc.total_due
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@payment_router.get("/upcoming-due")
async def get_upcoming_due_payments(
    days_forward: int = Query(30),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get payments due in next N days.

    Helps with payment planning and cash flow management.
    """
    from datetime import datetime as dt, timedelta

    future_date = (dt.now() + timedelta(days=days_forward)).date()

    result = await db.execute(
        select(GSTPayment).where(
            and_(
                GSTPayment.firm_id == current_user.firm_id,
                GSTPayment.payment_status.in_(["not_due", "due", "overdue"]),
                GSTPayment.due_date <= future_date.isoformat()
            )
        ).order_by(GSTPayment.due_date)
    )
    payments = result.scalars().all()

    return {
        "firm_id": current_user.firm_id,
        "days_forward": days_forward,
        "total_due": sum(p.total_due for p in payments),
        "payments": [
            {
                "gstin": p.gstin,
                "period": p.period,
                "due_date": p.due_date,
                "tax_payable": p.tax_payable,
                "amount_paid": p.amount_paid,
                "balance": p.tax_payable - p.amount_paid,
                "interest": p.interest_due,
                "total_due": p.total_due,
                "status": p.payment_status,
                "days_until_due": max(0, (dt.fromisoformat(p.due_date).date() - dt.now().date()).days)
            }
            for p in payments
        ]
    }


@payment_router.get("/status-check")
async def payment_module_status(current_user: CurrentUser = Depends(get_current_user)):
    """Get payment tracking module status."""
    return {
        "status": "ok",
        "module": "gst_payments",
        "capabilities": [
            "payment_scheduling",
            "interest_calculation",
            "payment_recording",
            "status_tracking",
            "financial_reporting",
            "cash_flow_planning"
        ],
        "features": {
            "interest_rate": "18% per annum",
            "calculation_frequency": "Daily",
            "payment_methods": [
                "bank_transfer",
                "challan",
                "neft",
                "rtgs",
                "cheque",
                "credit_card"
            ],
            "reporting": [
                "period_summary",
                "annual_summary",
                "upcoming_due",
                "overdue_tracking"
            ]
        },
        "note": "Completes GST financial tracking with payment scheduling and interest calculation"
    }
