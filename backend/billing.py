from datetime import datetime
from uuid import uuid4
from typing import Optional
from io import BytesIO

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


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


class PaymentUpdate(BaseModel):
    payment_mode: str = "cash"
    payment_reference: Optional[str] = None
    remarks: Optional[str] = None


def generate_invoice_number():
    count = len(BILLING_STORE) + 1
    year = datetime.utcnow().year
    return f"INV-{year}-{count:04d}"


@router.get("/status")
async def billing_status():
    return {
        "status": "ok",
        "module": "billing_invoice_management",
        "features": [
            "invoice_creation",
            "fee_collection_tracking",
            "mark_paid",
            "outstanding_tracking",
            "pdf_invoice_download"
        ]
    }


@router.post("/create")
async def create_invoice(payload: InvoiceCreate):
    invoice_id = str(uuid4())
    total_amount = payload.amount + payload.tax_amount

    invoice = {
        "id": invoice_id,
        "invoice_number": generate_invoice_number(),
        "firm_id": DEFAULT_FIRM_ID,
        "client_name": payload.client_name,
        "service_name": payload.service_name,
        "amount": payload.amount,
        "tax_amount": payload.tax_amount,
        "total_amount": total_amount,
        "status": payload.status,
        "due_date": payload.due_date,
        "remarks": payload.remarks,
        "payment_mode": None,
        "payment_reference": None,
        "paid_at": None,
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


@router.get("/outstanding")
async def outstanding_invoices():
    invoices = [
        item for item in BILLING_STORE.values()
        if item["firm_id"] == DEFAULT_FIRM_ID and item["status"] in ["unpaid", "overdue"]
    ]

    return {
        "outstanding_count": len(invoices),
        "outstanding_amount": sum(i["total_amount"] for i in invoices),
        "invoices": invoices
    }


@router.put("/mark-paid/{invoice_id}")
async def mark_invoice_paid(invoice_id: str, payload: PaymentUpdate):
    invoice = BILLING_STORE.get(invoice_id)

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice["status"] = "paid"
    invoice["payment_mode"] = payload.payment_mode
    invoice["payment_reference"] = payload.payment_reference
    invoice["paid_at"] = datetime.utcnow().isoformat()

    if payload.remarks:
        invoice["remarks"] = payload.remarks

    invoice["updated_at"] = datetime.utcnow().isoformat()

    return {
        "message": "Invoice marked as paid",
        "invoice": invoice
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


@router.get("/pdf/{invoice_id}")
async def download_invoice_pdf(invoice_id: str):
    invoice = BILLING_STORE.get(invoice_id)

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(50, height - 60, "GSTAgent Invoice")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, height - 85, "CA Practice Management Platform")

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, height - 130, f"Invoice No: {invoice.get('invoice_number')}")
    pdf.drawString(50, height - 150, f"Date: {invoice.get('created_at', '')[:10]}")
    pdf.drawString(50, height - 170, f"Status: {invoice.get('status', '').upper()}")

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, height - 220, "Bill To:")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, height - 245, invoice.get("client_name", "-"))

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, height - 300, "Service")
    pdf.drawString(300, height - 300, "Amount")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, height - 325, invoice.get("service_name", "-"))
    pdf.drawString(300, height - 325, f"Rs. {invoice.get('amount', 0)}")

    pdf.drawString(50, height - 350, "Tax")
    pdf.drawString(300, height - 350, f"Rs. {invoice.get('tax_amount', 0)}")

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, height - 390, "Total")
    pdf.drawString(300, height - 390, f"Rs. {invoice.get('total_amount', 0)}")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, height - 450, f"Due Date: {invoice.get('due_date') or '-'}")
    pdf.drawString(50, height - 470, f"Payment Mode: {invoice.get('payment_mode') or '-'}")
    pdf.drawString(50, height - 490, f"Payment Reference: {invoice.get('payment_reference') or '-'}")

    pdf.drawString(50, height - 540, "Remarks:")
    pdf.drawString(50, height - 560, invoice.get("remarks") or "-")

    pdf.setFont("Helvetica", 9)
    pdf.drawString(50, 50, "Generated by GSTAgent")

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    filename = f"{invoice.get('invoice_number', 'invoice')}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )