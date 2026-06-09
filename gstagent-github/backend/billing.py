"""
GSTAgent — Razorpay Billing
Handles: plan orders, payment verification, webhooks, subscription status

Setup:
    1. Create account at razorpay.com
    2. Get Key ID and Key Secret from Dashboard → Settings → API Keys
    3. Set environment variables:
       RAZORPAY_KEY_ID=rzp_live_xxxxx
       RAZORPAY_KEY_SECRET=xxxxx
    4. Add webhook in Razorpay Dashboard:
       URL: https://api.gstagent.in/billing/webhook
       Events: payment.captured, subscription.activated, subscription.cancelled

Requirements:
    pip install razorpay
"""

import os
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional

# ─── PLANS ────────────────────────────────────────────────────────────────────

PLANS = {
    "starter": {
        "name": "Starter",
        "price_monthly": 2999,        # ₹2,999/month
        "price_yearly": 29990,        # ₹29,990/year (₹2,499/mo)
        "max_gstins": 5,
        "max_reconciliations": 20,    # per month
        "features": [
            "Up to 5 GSTINs",
            "20 reconciliations/month",
            "AI mismatch explanations",
            "Vendor email drafts",
            "Excel export",
            "Email support",
        ],
        "razorpay_plan_id_monthly": os.getenv("RAZORPAY_PLAN_STARTER_MONTHLY", ""),
        "razorpay_plan_id_yearly":  os.getenv("RAZORPAY_PLAN_STARTER_YEARLY", ""),
    },
    "growth": {
        "name": "Growth",
        "price_monthly": 7999,        # ₹7,999/month
        "price_yearly": 79990,        # ₹79,990/year
        "max_gstins": 25,
        "max_reconciliations": 100,
        "features": [
            "Up to 25 GSTINs",
            "100 reconciliations/month",
            "All Starter features",
            "Notice reply drafting",
            "Tally connector",
            "Zoho Books integration",
            "Filing QA checks",
            "Priority support",
        ],
        "razorpay_plan_id_monthly": os.getenv("RAZORPAY_PLAN_GROWTH_MONTHLY", ""),
        "razorpay_plan_id_yearly":  os.getenv("RAZORPAY_PLAN_GROWTH_YEARLY", ""),
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 19999,       # ₹19,999/month
        "price_yearly": 199990,
        "max_gstins": -1,             # Unlimited
        "max_reconciliations": -1,
        "features": [
            "Unlimited GSTINs",
            "Unlimited reconciliations",
            "All Growth features",
            "GSP integration",
            "Multi-user workspace",
            "Audit logs",
            "Dedicated onboarding",
            "SLA support",
            "Custom integrations",
        ],
        "razorpay_plan_id_monthly": os.getenv("RAZORPAY_PLAN_ENTERPRISE_MONTHLY", ""),
        "razorpay_plan_id_yearly":  os.getenv("RAZORPAY_PLAN_ENTERPRISE_YEARLY", ""),
    },
}

# ─── RAZORPAY CLIENT ──────────────────────────────────────────────────────────

def get_razorpay_client():
    """Get Razorpay client. Import lazily so app starts without it."""
    try:
        import razorpay
        return razorpay.Client(auth=(
            os.getenv("RAZORPAY_KEY_ID", ""),
            os.getenv("RAZORPAY_KEY_SECRET", "")
        ))
    except ImportError:
        raise HTTPException(503, "Razorpay not installed. Run: pip install razorpay")

# ─── SCHEMAS ──────────────────────────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    plan_id: str          # starter | growth | enterprise
    billing: str = "monthly"   # monthly | yearly

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    plan_id: str
    billing: str

class SubscriptionRequest(BaseModel):
    plan_id: str
    billing: str = "monthly"

# ─── ROUTER ───────────────────────────────────────────────────────────────────

billing_router = APIRouter(prefix="/billing", tags=["Billing"])


@billing_router.get("/plans")
async def list_plans():
    """Return all plans with pricing. Used by pricing page."""
    return {
        "plans": [
            {
                "id": plan_id,
                "name": plan["name"],
                "price_monthly": plan["price_monthly"],
                "price_yearly": plan["price_yearly"],
                "max_gstins": plan["max_gstins"],
                "max_reconciliations": plan["max_reconciliations"],
                "features": plan["features"],
                "popular": plan_id == "growth",
            }
            for plan_id, plan in PLANS.items()
        ],
        "currency": "INR",
        "note": "Prices include 18% GST. Annual billing saves 17%."
    }


@billing_router.post("/create-order")
async def create_order(request: CreateOrderRequest):
    """
    Create a Razorpay order for a one-time payment.
    Frontend uses this order_id to open the Razorpay checkout.
    """
    if request.plan_id not in PLANS:
        raise HTTPException(400, f"Unknown plan: {request.plan_id}")

    plan = PLANS[request.plan_id]
    amount = plan["price_monthly"] if request.billing == "monthly" else plan["price_yearly"]
    amount_paise = amount * 100  # Razorpay uses paise

    rzp = get_razorpay_client()

    try:
        order = rzp.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"gstagent_{request.plan_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "notes": {
                "plan_id": request.plan_id,
                "billing": request.billing,
                "product": "GSTAgent"
            }
        })
        return {
            "order_id": order["id"],
            "amount": amount_paise,
            "currency": "INR",
            "plan_id": request.plan_id,
            "plan_name": plan["name"],
            "billing": request.billing,
            "razorpay_key": os.getenv("RAZORPAY_KEY_ID", ""),
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to create order: {str(e)}")


@billing_router.post("/verify-payment")
async def verify_payment(request: VerifyPaymentRequest):
    """
    Verify Razorpay payment signature after checkout.
    CRITICAL: Always verify signature before activating subscription.
    """
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")

    # Verify signature
    expected = hmac.new(
        key_secret.encode(),
        f"{request.razorpay_order_id}|{request.razorpay_payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, request.razorpay_signature):
        raise HTTPException(400, "Payment verification failed. Invalid signature.")

    # Activate subscription in DB
    # In production:
    # await FirmRepo.activate_plan(db, firm_id, plan_id, billing, payment_id)
    expiry = datetime.now() + (timedelta(days=365) if request.billing == "yearly" else timedelta(days=30))

    return {
        "status": "activated",
        "plan_id": request.plan_id,
        "payment_id": request.razorpay_payment_id,
        "valid_until": expiry.isoformat(),
        "message": f"Plan activated successfully. Valid until {expiry.strftime('%d %b %Y')}."
    }


@billing_router.post("/webhook")
async def razorpay_webhook(request: Request):
    """
    Razorpay webhook endpoint.
    Set this URL in Razorpay Dashboard → Settings → Webhooks.
    """
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    # Verify webhook signature
    expected = hmac.new(webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(400, "Invalid webhook signature")

    event = json.loads(body)
    event_type = event.get("event")

    if event_type == "payment.captured":
        payment = event["payload"]["payment"]["entity"]
        # Handle successful payment
        # await FirmRepo.activate_plan(db, ...)
        print(f"Payment captured: {payment['id']} — ₹{payment['amount'] // 100}")

    elif event_type == "subscription.activated":
        sub = event["payload"]["subscription"]["entity"]
        print(f"Subscription activated: {sub['id']}")

    elif event_type == "subscription.cancelled":
        sub = event["payload"]["subscription"]["entity"]
        # Downgrade to free tier at period end
        print(f"Subscription cancelled: {sub['id']}")

    elif event_type == "payment.failed":
        payment = event["payload"]["payment"]["entity"]
        # Notify user of failed payment
        print(f"Payment failed: {payment['id']}")

    return {"status": "ok"}


@billing_router.get("/status")
async def billing_status():
    """
    Get current firm's billing status.
    In production: fetch from DB using current_user.firm_id
    """
    # Mock response — replace with DB lookup
    return {
        "plan": "growth",
        "plan_name": "Growth",
        "status": "active",
        "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
        "gstins_used": 4,
        "gstins_limit": 25,
        "reconciliations_used": 12,
        "reconciliations_limit": 100,
        "next_billing_date": (datetime.now() + timedelta(days=30)).strftime("%d %b %Y"),
        "amount_next": 7999,
    }


@billing_router.post("/create-subscription")
async def create_subscription(request: SubscriptionRequest):
    """
    Create a recurring Razorpay subscription (auto-renewal).
    Use this instead of create-order for monthly auto-pay.
    """
    if request.plan_id not in PLANS:
        raise HTTPException(400, f"Unknown plan: {request.plan_id}")

    plan = PLANS[request.plan_id]
    plan_key = "razorpay_plan_id_monthly" if request.billing == "monthly" else "razorpay_plan_id_yearly"
    razorpay_plan_id = plan.get(plan_key)

    if not razorpay_plan_id:
        raise HTTPException(400, "Subscription plan not configured. Contact support.")

    rzp = get_razorpay_client()

    try:
        subscription = rzp.subscription.create({
            "plan_id": razorpay_plan_id,
            "customer_notify": 1,
            "total_count": 12 if request.billing == "monthly" else 1,
            "quantity": 1,
            "notes": {"product": "GSTAgent", "plan": request.plan_id}
        })
        return {
            "subscription_id": subscription["id"],
            "plan_id": request.plan_id,
            "razorpay_key": os.getenv("RAZORPAY_KEY_ID", ""),
        }
    except Exception as e:
        raise HTTPException(500, f"Subscription creation failed: {str(e)}")
