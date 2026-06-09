from datetime import datetime
from uuid import uuid4
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import CurrentUser, get_current_user

router = APIRouter(prefix="/billing", tags=["Billing"])

BILLING_STORE = {}


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
async def billing_status(current_user: CurrentUser = Depends(get_current_user)):
    return {
        "status": "ok",
        "module": "billing_invoice_management",
        "firm_id": current_user.firm_id
    }


@router.post("/create")
async def create_invoice(payload: InvoiceCreate, current_user: CurrentUser = Depends(get_current_user)):
    invoice_id = str(uuid4())
    total_amount = payload.amount + payload.tax_amount

    invoice = {
        "id": invoice_id,
        "firm_id": current_user.firm_id,
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
async def list_invoices(current_user: CurrentUser = Depends(get_current_user)):
    invoices = [
        item for item in BILLING_STORE.values()
        if item["firm_id"] == current_user.firm_id
    ]
    return {"invoices": invoices, "count": len(invoices)}


@router.get("/dashboard")
async def billing_dashboard(current_user: CurrentUser = Depends(get_current_user)):
    invoices = [
        item for item in BILLING_STORE.values()
        if item["firm_id"] == current_user.firm_id
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
async def update_invoice(invoice_id: str, payload: InvoiceUpdate, current_user: CurrentUser = Depends(get_current_user)):
    invoice = BILLING_STORE.get(invoice_id)

    if not invoice or invoice["firm_id"] != current_user.firm_id:
        raise HTTPException(status_code=404, detail="Invoice not found")

    updates = payload.dict(exclude_unset=True)
    invoice.update(updates)

    amount = invoice.get("amount", 0) or 0
    tax_amount = invoice.get("tax_amount", 0) or 0
    invoice["total_amount"] = amount + tax_amount
    invoice["updated_at"] = datetime.utcnow().isoformat()

    return {"message": "Invoice updated", "invoice": invoice}


@router.delete("/delete/{invoice_id}")
async def delete_invoice(invoice_id: str, current_user: CurrentUser = Depends(get_current_user)):
    invoice = BILLING_STORE.get(invoice_id)

    if not invoice or invoice["firm_id"] != current_user.firm_id:
        raise HTTPException(status_code=404, detail="Invoice not found")

    del BILLING_STORE[invoice_id]
    return {"message": "Invoice deleted", "id": invoice_id}