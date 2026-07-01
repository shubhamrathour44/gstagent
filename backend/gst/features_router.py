"""
Extended Features Router

API endpoints for:
- GST return types (GSTR-1 through GSTR-9)
- Automated reminders
- Advanced analytics
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from gst.gstr_types_engine import GSTReturnTypesEngine, ReturnType
from gst.reminder_engine import ReminderEngine, ReminderScheduler, ReminderTiming, ReminderType
from gst.analytics_engine import AnalyticsEngine

features_router = APIRouter(prefix="/gst-features", tags=["GST Features"])


# ═══════════════════════════════════════════════════════════════════════════
# PART 1: GST RETURN TYPES ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@features_router.get("/return-types/list")
async def list_return_types():
    """Get all available GST return types"""
    return {
        "return_types": [
            {
                "code": rt.value,
                "name": rt.name,
                "description": GSTReturnTypesEngine.get_return_config(rt).description
            }
            for rt in ReturnType
        ]
    }


@features_router.get("/return-types/{return_type}")
async def get_return_type_info(return_type: str):
    """Get detailed info for a specific return type"""
    try:
        rt = ReturnType[return_type.upper().replace("-", "_")]
        return GSTReturnTypesEngine.get_return_summary(rt)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Return type {return_type} not found")


@features_router.get("/return-types/due-dates/{period}")
async def get_due_dates_for_period(period: str):
    """Get all due dates for a period (e.g., 042026)"""
    try:
        return GSTReturnTypesEngine.get_all_returns_for_period(period)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@features_router.get("/filing-calendar/{year}")
async def get_filing_calendar(year: int):
    """Get complete filing calendar for a financial year"""
    try:
        return {
            "fiscal_year": f"{year}-{year+1}",
            "calendar": GSTReturnTypesEngine.get_filing_calendar(year)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@features_router.get("/return-due-date/{return_type}/{period}")
async def get_return_due_date(return_type: str, period: str):
    """Get due date for a specific return and period"""
    try:
        rt = ReturnType[return_type.upper().replace("-", "_")]
        due_date = GSTReturnTypesEngine.get_due_date(rt, period)
        config = GSTReturnTypesEngine.get_return_config(rt)

        return {
            "return_type": return_type,
            "period": period,
            "due_date": due_date,
            "frequency": config.frequency.value,
            "applicable_to": config.applicable_to
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# PART 2: AUTOMATED REMINDERS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@features_router.get("/reminders/schedule/{due_date}")
async def get_reminder_schedule(due_date: str):
    """Get reminder schedule for a due date"""
    try:
        return {
            "due_date": due_date,
            "reminders": ReminderEngine.get_reminder_schedule(due_date)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@features_router.post("/reminders/generate-email")
async def generate_email_reminder(
    return_type: str = Query(...),
    period: str = Query(...),
    tax_amount: float = Query(...),
    due_date: str = Query(...),
    timing: str = Query("7_days_before")
):
    """Generate email reminder template"""
    try:
        reminder_timing = ReminderTiming(timing)
        subject, body, _ = ReminderEngine.generate_email(
            timing=reminder_timing,
            recipient_email="user@example.com",
            recipient_name="User",
            return_type=return_type,
            period=period,
            tax_amount=tax_amount,
            due_date=due_date
        )

        return {
            "type": "email",
            "timing": timing,
            "subject": subject,
            "body": body,
            "ready_to_send": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@features_router.post("/reminders/generate-sms")
async def generate_sms_reminder(
    return_type: str = Query(...),
    period: str = Query(...),
    tax_amount: float = Query(...),
    due_date: str = Query(...),
    timing: str = Query("7_days_before")
):
    """Generate SMS reminder template"""
    try:
        reminder_timing = ReminderTiming(timing)
        sms_text = ReminderEngine.generate_sms(
            timing=reminder_timing,
            return_type=return_type,
            period=period,
            tax_amount=tax_amount,
            due_date=due_date
        )

        return {
            "type": "sms",
            "timing": timing,
            "message": sms_text,
            "character_count": len(sms_text),
            "ready_to_send": True
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@features_router.post("/reminders/schedule-payment-reminders")
async def schedule_payment_reminders(
    return_type: str = Query(...),
    period: str = Query(...),
    tax_amount: float = Query(...),
    due_date: str = Query(...),
    email: Optional[str] = Query(None),
    phone: Optional[str] = Query(None)
):
    """Schedule all payment reminders"""
    try:
        reminder_methods = []
        if email:
            reminder_methods.append(ReminderType.EMAIL)
        if phone:
            reminder_methods.append(ReminderType.SMS)
        reminder_methods.append(ReminderType.IN_APP)

        scheduled = ReminderScheduler.schedule_payment_reminders(
            user_id="demo_user",
            return_type=return_type,
            period=period,
            tax_amount=tax_amount,
            due_date=due_date,
            recipient_email=email,
            phone_number=phone,
            reminder_methods=reminder_methods
        )

        return scheduled
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# PART 3: ADVANCED ANALYTICS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@features_router.post("/analytics/payment-trends")
async def analyze_payment_trends(months: int = Query(12)):
    """Analyze payment trends over time"""
    try:
        # Demo data - in production, fetch from database
        demo_payments = [
            {"tax_amount": 100000, "amount_paid": 100000, "days_late": 5, "interest_paid": 250},
            {"tax_amount": 105000, "amount_paid": 105000, "days_late": 10, "interest_paid": 525},
            {"tax_amount": 95000, "amount_paid": 95000, "days_late": 0, "interest_paid": 0},
            {"tax_amount": 110000, "amount_paid": 110000, "days_late": 15, "interest_paid": 825},
            {"tax_amount": 100000, "amount_paid": 100000, "days_late": 3, "interest_paid": 150},
            {"tax_amount": 102000, "amount_paid": 102000, "days_late": 7, "interest_paid": 357},
        ]

        return AnalyticsEngine.analyze_payment_trends(demo_payments, months)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@features_router.post("/analytics/cash-flow-forecast")
async def forecast_cash_flow(forecast_months: int = Query(6)):
    """Forecast future cash flow requirements"""
    try:
        # Demo data
        demo_payments = [
            {"tax_amount": 100000},
            {"tax_amount": 105000},
            {"tax_amount": 95000},
            {"tax_amount": 110000},
            {"tax_amount": 100000},
            {"tax_amount": 102000},
        ]

        return AnalyticsEngine.forecast_cash_flow(demo_payments, forecast_months)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@features_router.post("/analytics/tax-optimization")
async def get_tax_optimization():
    """Get tax optimization recommendations"""
    try:
        # Demo data
        demo_payments = [
            {"tax_amount": 100000, "days_late": 5, "interest_paid": 250},
            {"tax_amount": 105000, "days_late": 10, "interest_paid": 525},
            {"tax_amount": 95000, "days_late": 0, "interest_paid": 0},
            {"tax_amount": 110000, "days_late": 15, "interest_paid": 825},
            {"tax_amount": 100000, "days_late": 3, "interest_paid": 150},
        ]

        return AnalyticsEngine.get_tax_optimization_recommendations(demo_payments)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@features_router.post("/analytics/compliance-metrics")
async def get_compliance_metrics():
    """Get GST compliance analytics"""
    try:
        # Demo data
        demo_payments = [
            {"days_late": 5},
            {"days_late": 10},
            {"days_late": 0},
            {"days_late": 15},
            {"days_late": -2},  # Early
            {"days_late": 3},
        ]

        return AnalyticsEngine.get_compliance_analytics(demo_payments)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@features_router.get("/analytics/industry-benchmark")
async def get_industry_benchmark(
    tax_amount: float = Query(...),
    business_type: str = Query("B2B"),
    state: str = Query("National")
):
    """Compare with industry benchmarks"""
    try:
        return AnalyticsEngine.get_industry_benchmark(tax_amount, business_type, state)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@features_router.post("/analytics/dashboard-summary")
async def get_dashboard_summary():
    """Get complete dashboard summary"""
    try:
        # Demo data
        demo_payments = [
            {"tax_amount": 100000, "days_late": 5, "interest_paid": 250},
            {"tax_amount": 105000, "days_late": 10, "interest_paid": 525},
            {"tax_amount": 95000, "days_late": 0, "interest_paid": 0},
            {"tax_amount": 110000, "days_late": 15, "interest_paid": 825},
            {"tax_amount": 100000, "days_late": 3, "interest_paid": 150},
            {"tax_amount": 102000, "days_late": 7, "interest_paid": 357},
        ]

        return AnalyticsEngine.get_dashboard_summary(demo_payments)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# COMBINED ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@features_router.get("/features-status")
async def features_status():
    """Get status of all new features"""
    return {
        "status": "All features enabled",
        "gst_return_types": {
            "status": "ACTIVE",
            "supports": "GSTR-1, 2, 3, 3B, 4, 5, 6, 7, 8, 9",
            "endpoints": 4
        },
        "automated_reminders": {
            "status": "ACTIVE",
            "methods": ["email", "sms", "push", "in_app"],
            "endpoints": 3
        },
        "advanced_analytics": {
            "status": "ACTIVE",
            "metrics": ["trends", "forecasts", "optimization", "compliance", "benchmarking"],
            "endpoints": 6
        },
        "total_new_endpoints": 13
    }
