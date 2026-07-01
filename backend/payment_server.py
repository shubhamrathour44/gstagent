"""
Standalone Payment Tracking Server

Runs only the GST Payment Tracking module for testing/demo.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("payment-tracking-server")

app = FastAPI(
    title="GSTAgent Payment Tracking API",
    description="GST Payment Tracking with Interest Calculation",
    version="1.0.0"
)

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "https://gstagent.co.in",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check
@app.get("/")
async def root():
    return {
        "message": "GSTAgent Payment Tracking API",
        "status": "healthy",
        "version": "1.0.0",
        "module": "payment-tracking"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "payment-tracking",
        "database": "sqlite"
    }

# Import feature routers
from gst.features_router import features_router
from gst.itr_router import itr_router
from gst.gstr3b_router import gstr3b_router
from gst.itr_forms_router import itr_forms_router

# Include routers
app.include_router(features_router)
app.include_router(itr_router)
app.include_router(gstr3b_router)
app.include_router(itr_forms_router)

# Demo Endpoints (No auth required for demo)
@app.get("/demo/interest-calculator")
async def demo_interest_calculator(
    tax_amount: float = 100000,
    due_date: str = "2026-05-20",
    payment_date: str = "2026-06-05"
):
    """Calculate interest for demo purposes."""
    from gst.payment_engine import InterestCalculationEngine

    result = InterestCalculationEngine.calculate_interest(
        principal=tax_amount,
        due_date=due_date,
        payment_date=payment_date
    )

    return {
        "tax_amount": tax_amount,
        "due_date": due_date,
        "payment_date": payment_date,
        "interest_rate": "18% p.a.",
        "days_late": result.days_late,
        "interest_amount": result.interest_amount,
        "total_due": result.total_due
    }

@app.get("/demo/payment-schedule")
async def demo_payment_schedule(
    gstin: str = "27ABCDE1234F1Z5",
    period: str = "042026"
):
    """Get payment schedule for demo."""
    from gst.payment_engine import PaymentScheduleEngine

    schedules = PaymentScheduleEngine.generate_schedule(
        gstin=gstin,
        gstr1_tax_payable=0,
        gstr3b_tax_payable=100000,
        period=period
    )

    return {
        "gstin": gstin,
        "period": period,
        "schedule": [
            {
                "return_type": s.return_type,
                "due_date": s.due_date,
                "tax_payable": s.tax_payable,
                "status": s.status.value
            }
            for s in schedules
        ]
    }

@app.get("/demo/payment-status")
async def demo_payment_status(
    tax_payable: float = 100000,
    amount_paid: float = 100000,
    due_date: str = "2026-05-20",
    payment_date: str = "2026-06-05"
):
    """Get payment status for demo."""
    from gst.payment_engine import PaymentTracker

    status = PaymentTracker.get_payment_status(
        tax_payable=tax_payable,
        due_date=due_date,
        amount_paid=amount_paid,
        payment_date=payment_date
    )

    return status

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("GST PAYMENT TRACKING SERVER")
    print("="*70)
    print("\nServer starting on http://0.0.0.0:8000")
    print("\nDemo Endpoints:")
    print("  [1] Interest Calculator:")
    print("      GET /demo/interest-calculator")
    print("  [2] Payment Schedule:")
    print("      GET /demo/payment-schedule")
    print("  [3] Payment Status:")
    print("      GET /demo/payment-status")
    print("\nTest URLs:")
    print("  http://localhost:8000/health")
    print("  http://localhost:8000/demo/interest-calculator")
    print("  http://localhost:8000/demo/payment-schedule")
    print("\n" + "="*70 + "\n")

    uvicorn.run(
        "payment_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
