from datetime import datetime
from uuid import uuid4
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/billing", tags=["Billing"])

BILLING_STORE = {}
DEFAULT_FIRM_ID = "default_firm"


class InvoiceCreate(BaseModel):
    client_name: str
    service_name: str
    amount: float
    tax_amount: float = 0
    status: str = "unpaid"
    due_date: Optional[str] = None
    remarks: Optional[str] = None


class InvoiceUpdate(BaseModel):
    client_name: Optional[str] = None
    service_name: Optional[str] = None
    amount: Optional[float] = None
    tax_amount: Optional[float] = None
    status: Optional[str] = None
    due_date: Optional[str] = None
    remarks: Optional[str] = None


@router.get("/status")
async def billing_status():
    return {
        "status": "ok",
        "module": "billing_invoice_management"
    }


@router.post("/create")
async def create_invoice(payload: InvoiceCreate):
    invoice_id = str(uuid4())
    total_amount = payload.amount + payload.tax_amount

    invoice = {
        "id": invoice_id,
        "firm_id": DEFAULT_FIRM_ID,
        "client_name": payload.client_name,
        "service_name": payload.service_name,
        "amount": payload.amount,
        "tax_amount": payload.tax_amount,
        "total_amount": total_amount,
        "status": payload.status,
        "due_date": payload.due_date,
        "remarks": payload.remarks,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    BILLING_STORE[invoice_id] = invoice
    return {"message": "Invoice created", "invoice": invoice}


@router.get("/list")
async def list_invoices():
    invoices = [
        item for item in BILLING_STORE.values()
        if item["firm_id"] == DEFAULT_FIRM_ID
    ]
    return {"invoices": invoices, "count": len(invoices)}


@router.get("/dashboard")
async def billing_dashboard():
    invoices = [
        item for item in BILLING_STORE.values()
        if item["firm_id"] == DEFAULT_FIRM_ID
    ]

    return {
        "total_invoices": len(invoices),
        "paid_invoices": sum(1 for i in invoices if i["status"] == "paid"),
        "unpaid_invoices": sum(1 for i in invoices if i["status"] == "unpaid"),
        "overdue_invoices": sum(1 for i in invoices if i["status"] == "overdue"),
        "total_revenue": sum(i["total_amount"] for i in invoices if i["status"] == "paid"),
        "outstanding_amount": sum(i["total_amount"] for i in invoices if i["status"] in ["unpaid", "overdue"]),
    }


@router.put("/update/{invoice_id}")
async def update_invoice(invoice_id: str, payload: InvoiceUpdate):
    invoice = BILLING_STORE.get(invoice_id)

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    updates = payload.dict(exclude_unset=True)
    invoice.update(updates)

    amount = invoice.get("amount", 0) or 0
    tax_amount = invoice.get("tax_amount", 0) or 0
    invoice["total_amount"] = amount + tax_amount
    invoice["updated_at"] = datetime.utcnow().isoformat()

    return {"message": "Invoice updated", "invoice": invoice}


@router.delete("/delete/{invoice_id}")
async def delete_invoice(invoice_id: str):
    invoice = BILLING_STORE.get(invoice_id)

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    del BILLING_STORE[invoice_id]
    return {"message": "Invoice deleted", "id": invoice_id}