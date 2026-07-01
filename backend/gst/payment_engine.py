"""
GST Payment & Interest Tracking Engine

Calculates:
- GST payment schedules
- Late payment interest (18% p.a.)
- Penalties and surcharges
- Payment status tracking
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List
from enum import Enum
from datetime import datetime, timedelta
from decimal import Decimal
import math


class PaymentStatus(str, Enum):
    """Payment status."""
    NOT_DUE = "not_due"        # Due date in future
    DUE = "due"                # Due but not paid
    PAID = "paid"              # Paid on time
    LATE = "late"              # Paid after due date
    PENDING = "pending"        # Payment in transit
    OVERDUE = "overdue"        # Not paid, past due date


class PaymentMethod(str, Enum):
    """Method of payment."""
    BANK_TRANSFER = "bank_transfer"
    CHALLAN = "challan"
    NEFT = "neft"
    RTGS = "rtgs"
    CHEQUE = "cheque"
    CREDIT_CARD = "credit_card"


@dataclass
class InterestCalculation:
    """Interest calculation details."""
    principal: float  # Tax amount
    rate_per_month: float  # 18% p.a. = 1.5% per month
    days_late: int
    months_late: float
    interest_amount: float
    total_due: float

    def to_dict(self):
        return asdict(self)


@dataclass
class PaymentSchedule:
    """GST payment schedule entry."""
    gstin: str
    period: str  # MMYYYY
    return_type: str  # GSTR-1, GSTR-3B
    tax_payable: float
    due_date: str  # YYYY-MM-DD
    days_until_due: int
    status: PaymentStatus
    amount_paid: float = 0.0
    payment_date: Optional[str] = None
    payment_method: Optional[str] = None
    challan_number: Optional[str] = None
    interest_due: float = 0.0
    total_due: float = 0.0
    late_days: int = 0
    notes: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class PaymentRecord:
    """Individual payment record."""
    payment_id: str
    gstin: str
    period: str
    amount: float
    payment_date: str  # YYYY-MM-DD
    payment_method: PaymentMethod
    challan_number: Optional[str]
    reference_number: str
    status: str  # confirmed, pending, failed
    created_at: str
    created_by: Optional[str]

    def to_dict(self):
        return asdict(self)


class InterestCalculationEngine:
    """Calculate GST late payment interest."""

    # 18% per annum = 1.5% per month = 0.05% per day
    ANNUAL_RATE = 0.18
    MONTHLY_RATE = self.ANNUAL_RATE / 12
    DAILY_RATE = self.ANNUAL_RATE / 365

    @staticmethod
    def calculate_interest(
        principal: float,
        due_date: str,
        payment_date: Optional[str] = None,
        today: Optional[str] = None
    ) -> InterestCalculation:
        """
        Calculate interest on late payment.

        Args:
            principal: Tax amount to be paid
            due_date: Payment due date (YYYY-MM-DD)
            payment_date: When payment was made (YYYY-MM-DD)
            today: Current date (YYYY-MM-DD) for calculation

        Returns:
            InterestCalculation with details
        """
        from datetime import datetime as dt

        current_date = dt.fromisoformat(today) if today else dt.now()
        due = dt.fromisoformat(due_date)

        # Determine calculation date
        if payment_date:
            calc_date = dt.fromisoformat(payment_date)
        else:
            calc_date = current_date

        # If paid on time or before due date, no interest
        if calc_date <= due:
            return InterestCalculation(
                principal=principal,
                rate_per_month=InterestCalculationEngine.MONTHLY_RATE * 100,
                days_late=0,
                months_late=0,
                interest_amount=0.0,
                total_due=principal
            )

        # Calculate days late
        days_late = (calc_date - due).days
        months_late = days_late / 30  # Approximate

        # Interest calculation: 18% p.a. = 0.05% per day
        # Or 1.5% per month
        interest = principal * (InterestCalculationEngine.DAILY_RATE * days_late)

        return InterestCalculation(
            principal=principal,
            rate_per_month=InterestCalculationEngine.MONTHLY_RATE * 100,
            days_late=days_late,
            months_late=round(months_late, 2),
            interest_amount=round(interest, 2),
            total_due=round(principal + interest, 2)
        )

    @staticmethod
    def calculate_interest_on_date(
        principal: float,
        due_date: str,
        target_date: str
    ) -> float:
        """Calculate interest amount for a specific date."""
        from datetime import datetime as dt

        due = dt.fromisoformat(due_date)
        target = dt.fromisoformat(target_date)

        if target <= due:
            return 0.0

        days_late = (target - due).days
        interest = principal * (InterestCalculationEngine.DAILY_RATE * days_late)

        return round(interest, 2)


class PaymentScheduleEngine:
    """Generate GST payment schedules."""

    @staticmethod
    def generate_schedule(
        gstin: str,
        gstr1_tax_payable: float,
        gstr3b_tax_payable: float,
        period: str  # MMYYYY
    ) -> List[PaymentSchedule]:
        """
        Generate payment schedule for GST returns.

        GST Due Dates:
        - GSTR-1: 11th of next month (self-invoice reporting)
        - GSTR-3B: 20th of next month (tax payment)

        Args:
            gstin: 15-digit GSTIN
            gstr1_tax_payable: Tax from GSTR-1 (usually 0, informational)
            gstr3b_tax_payable: Actual tax to be paid
            period: MMYYYY format

        Returns:
            List of payment schedules
        """
        from datetime import datetime as dt

        # Parse period
        month = int(period[:2])
        year = int(period[2:])

        # Calculate due dates
        # For April 2026 (042026), due is May 11/20
        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1

        gstr1_due = PaymentScheduleEngine._format_date(next_year, next_month, 11)
        gstr3b_due = PaymentScheduleEngine._format_date(next_year, next_month, 20)

        schedules = []

        # GSTR-1 entry (informational, no payment usually)
        today = dt.now()
        gstr1_schedule = PaymentSchedule(
            gstin=gstin,
            period=period,
            return_type="GSTR-1",
            tax_payable=gstr1_tax_payable,
            due_date=gstr1_due,
            days_until_due=max(0, (dt.fromisoformat(gstr1_due) - today).days),
            status=PaymentScheduleEngine._determine_status(gstr1_due, None),
            notes="GSTR-1 due date (filing, not payment)"
        )
        schedules.append(gstr1_schedule)

        # GSTR-3B entry (actual payment)
        gstr3b_schedule = PaymentSchedule(
            gstin=gstin,
            period=period,
            return_type="GSTR-3B",
            tax_payable=gstr3b_tax_payable,
            due_date=gstr3b_due,
            days_until_due=max(0, (dt.fromisoformat(gstr3b_due) - today).days),
            status=PaymentScheduleEngine._determine_status(gstr3b_due, None),
            total_due=gstr3b_tax_payable,
            notes="GSTR-3B tax payment due"
        )
        schedules.append(gstr3b_schedule)

        return schedules

    @staticmethod
    def _format_date(year: int, month: int, day: int) -> str:
        """Format date as YYYY-MM-DD."""
        return f"{year:04d}-{month:02d}-{day:02d}"

    @staticmethod
    def _determine_status(due_date: str, payment_date: Optional[str]) -> PaymentStatus:
        """Determine payment status."""
        from datetime import datetime as dt

        today = dt.now().date()
        due = dt.fromisoformat(due_date).date()

        if payment_date:
            paid = dt.fromisoformat(payment_date).date()
            if paid <= due:
                return PaymentStatus.PAID
            else:
                return PaymentStatus.LATE

        if today < due:
            return PaymentStatus.NOT_DUE
        elif today >= due:
            return PaymentStatus.OVERDUE

        return PaymentStatus.DUE


class PaymentTracker:
    """Track GST payments and calculate totals."""

    @staticmethod
    def get_payment_summary(
        payments: List[PaymentRecord],
        period: str
    ) -> dict:
        """
        Get payment summary for a period.

        Returns:
            Summary with totals, status, and metrics
        """
        if not payments:
            return {
                "period": period,
                "total_payments": 0,
                "total_amount": 0.0,
                "status": "unpaid",
                "payments": []
            }

        total_amount = sum(p.amount for p in payments)
        confirmed = [p for p in payments if p.status == "confirmed"]
        pending = [p for p in payments if p.status == "pending"]

        status = "paid" if confirmed else "pending" if pending else "failed"

        return {
            "period": period,
            "total_payments": len(confirmed),
            "total_amount": total_amount,
            "confirmed_amount": sum(p.amount for p in confirmed),
            "pending_amount": sum(p.amount for p in pending),
            "status": status,
            "payment_methods": list(set(p.payment_method for p in payments)),
            "payments": [p.to_dict() for p in confirmed]
        }

    @staticmethod
    def get_payment_status(
        tax_payable: float,
        due_date: str,
        amount_paid: float = 0.0,
        payment_date: Optional[str] = None
    ) -> dict:
        """
        Get detailed payment status.

        Returns:
            Status with balance and interest (if late)
        """
        from datetime import datetime as dt

        # Calculate interest if late
        interest_calc = InterestCalculationEngine.calculate_interest(
            principal=tax_payable - amount_paid,
            due_date=due_date,
            payment_date=payment_date
        )

        balance = tax_payable - amount_paid
        today = dt.now().date()
        due = dt.fromisoformat(due_date).date()

        return {
            "tax_payable": tax_payable,
            "amount_paid": amount_paid,
            "balance": balance,
            "due_date": due_date,
            "days_overdue": max(0, (today - due).days),
            "interest": {
                "amount": interest_calc.interest_amount,
                "rate": "18% p.a.",
                "calculation_period": f"{interest_calc.days_late} days"
            },
            "total_due": interest_calc.total_due,
            "status": PaymentScheduleEngine._determine_status(due_date, payment_date)
        }

    @staticmethod
    def get_fiscal_year_summary(
        payments_by_month: dict,  # {period: [payments]}
        fiscal_year: str  # 2025-26
    ) -> dict:
        """
        Get annual payment summary.

        Args:
            payments_by_month: Dictionary of period -> payments list
            fiscal_year: FY format (2025-26)

        Returns:
            Annual summary with totals and trends
        """
        all_payments = []
        for period_payments in payments_by_month.values():
            all_payments.extend(period_payments)

        total_amount = sum(p.amount for p in all_payments)
        total_payments = len([p for p in all_payments if p.status == "confirmed"])

        return {
            "fiscal_year": fiscal_year,
            "total_periods": len(payments_by_month),
            "total_payments": total_payments,
            "total_amount": total_amount,
            "average_per_month": total_amount / max(1, len(payments_by_month)),
            "payment_methods": list(set(p.payment_method for p in all_payments)),
            "periods_summary": {
                period: PaymentTracker.get_payment_summary([p for p in all_payments if p.period == period], period)
                for period in payments_by_month.keys()
            }
        }
