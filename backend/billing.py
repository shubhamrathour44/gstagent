import os
from datetime import datetime
from uuid import uuid4
from typing import Optional
from io import BytesIO

import psycopg2
from psycopg2.extras import RealDictCursor

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


router = APIRouter(prefix="/billing", tags=["Billing"])

DATABASE_URL = os.getenv("DATABASE_URL")


def get_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id VARCHAR(100) PRIMARY KEY,
        invoice_number VARCHAR(100) UNIQUE,
        client_name VARCHAR(255) NOT NULL,
        service_name VARCHAR(255) NOT NULL,
        amount NUMERIC DEFAULT 0,
        tax_amount NUMERIC DEFAULT 0,
        total_amount NUMERIC DEFAULT 0,
        status VARCHAR(50) DEFAULT 'unpaid',
        due_date DATE NULL,
        remarks TEXT NULL,
        payment_mode VARCHAR(100) NULL,
        payment_reference VARCHAR(255) NULL,
        paid_at TIMESTAMP NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """)

    conn.commit()
    cur.close()
    conn.close()


init_db()


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
    year = datetime.utcnow().year

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) AS count
        FROM invoices
        WHERE EXTRACT(YEAR FROM created_at) = %s
    """, (year,))
    count = cur.fetchone()["count"] + 1
    cur.close()
    conn.close()

    return f"INV-{year}-{count:04d}"


@router.get("/status")
async def billing_status():
    return {
        "status": "ok",
        "module": "billing_invoice_management",
        "storage": "postgresql",
        "features": [
            "invoice_creation",
            "invoice_search",
            "fee_collection_tracking",
            "mark_paid",
            "outstanding_tracking",
            "pdf_invoice_download"
        ]
    }


@router.post("/create")
async def create_invoice(payload: InvoiceCreate):
    invoice_id = str(uuid4())
    invoice_number = generate_invoice_number()
    total_amount = payload.amount + payload.tax_amount

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO invoices (
            id, invoice_number, client_name, service_name,
            amount, tax_amount, total_amount, status,
            due_date, remarks
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING *
    """, (
        invoice_id,
        invoice_number,
        payload.client_name,
        payload.service_name,
        payload.amount,
        payload.tax_amount,
        total_amount,
        payload.status,
        payload.due_date,
        payload.remarks
    ))

    invoice = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Invoice created", "invoice": invoice}


@router.get("/list")
async def list_invoices(
    from_date: Optional[str] = Query(default=None, alias="from"),
    to_date: Optional[str] = Query(default=None, alias="to")
):
    conn = get_db()
    cur = conn.cursor()

    if from_date and to_date:
        cur.execute("""
            SELECT *
            FROM invoices
            WHERE created_at::date BETWEEN %s AND %s
            ORDER BY created_at DESC
        """, (from_date, to_date))
    else:
        cur.execute("""
            SELECT *
            FROM invoices
            ORDER BY created_at DESC
        """)

    invoices = cur.fetchall()
    cur.close()
    conn.close()

    return {"invoices": invoices, "count": len(invoices)}


@router.get("/search")
async def search_invoices(q: str = ""):
    conn = get_db()
    cur = conn.cursor()

    search_term = f"%{q}%"

    cur.execute("""
        SELECT *
        FROM invoices
        WHERE
            invoice_number ILIKE %s
            OR client_name ILIKE %s
            OR service_name ILIKE %s
            OR status ILIKE %s
            OR payment_mode ILIKE %s
            OR payment_reference ILIKE %s
        ORDER BY created_at DESC
    """, (
        search_term,
        search_term,
        search_term,
        search_term,
        search_term,
        search_term
    ))

    invoices = cur.fetchall()
    cur.close()
    conn.close()

    return {
        "query": q,
        "count": len(invoices),
        "invoices": invoices
    }


@router.get("/dashboard")
async def billing_dashboard():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS total FROM invoices")
    total = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) AS paid FROM invoices WHERE status = 'paid'")
    paid = cur.fetchone()["paid"]

    cur.execute("SELECT COUNT(*) AS unpaid FROM invoices WHERE status = 'unpaid'")
    unpaid = cur.fetchone()["unpaid"]

    cur.execute("SELECT COUNT(*) AS overdue FROM invoices WHERE status = 'overdue'")
    overdue = cur.fetchone()["overdue"]

    cur.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS revenue
        FROM invoices
        WHERE status = 'paid'
    """)
    revenue = cur.fetchone()["revenue"]

    cur.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS outstanding
        FROM invoices
        WHERE status IN ('unpaid', 'overdue')
    """)
    outstanding = cur.fetchone()["outstanding"]

    cur.close()
    conn.close()

    return {
        "total_invoices": total,
        "paid_invoices": paid,
        "unpaid_invoices": unpaid,
        "overdue_invoices": overdue,
        "total_revenue": float(revenue),
        "outstanding_amount": float(outstanding),
    }


@router.get("/outstanding")
async def outstanding_invoices():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM invoices
        WHERE status IN ('unpaid', 'overdue')
        ORDER BY created_at DESC
    """)

    invoices = cur.fetchall()

    cur.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS outstanding_amount
        FROM invoices
        WHERE status IN ('unpaid', 'overdue')
    """)

    outstanding_amount = cur.fetchone()["outstanding_amount"]

    cur.close()
    conn.close()

    return {
        "outstanding_count": len(invoices),
        "outstanding_amount": float(outstanding_amount),
        "invoices": invoices
    }


@router.put("/mark-paid/{invoice_id}")
async def mark_invoice_paid(invoice_id: str, payload: PaymentUpdate):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE invoices
        SET status = 'paid',
            payment_mode = %s,
            payment_reference = %s,
            paid_at = NOW(),
            remarks = COALESCE(%s, remarks),
            updated_at = NOW()
        WHERE id = %s
        RETURNING *
    """, (
        payload.payment_mode,
        payload.payment_reference,
        payload.remarks,
        invoice_id
    ))

    invoice = cur.fetchone()

    if not invoice:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Invoice not found")

    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Invoice marked as paid", "invoice": invoice}


@router.put("/update/{invoice_id}")
async def update_invoice(invoice_id: str, payload: InvoiceUpdate):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM invoices WHERE id = %s", (invoice_id,))
    invoice = cur.fetchone()

    if not invoice:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Invoice not found")

    client_name = payload.client_name if payload.client_name is not None else invoice["client_name"]
    service_name = payload.service_name if payload.service_name is not None else invoice["service_name"]
    amount = payload.amount if payload.amount is not None else float(invoice["amount"])
    tax_amount = payload.tax_amount if payload.tax_amount is not None else float(invoice["tax_amount"])
    status = payload.status if payload.status is not None else invoice["status"]
    due_date = payload.due_date if payload.due_date is not None else invoice["due_date"]
    remarks = payload.remarks if payload.remarks is not None else invoice["remarks"]
    total_amount = amount + tax_amount

    cur.execute("""
        UPDATE invoices
        SET client_name = %s,
            service_name = %s,
            amount = %s,
            tax_amount = %s,
            total_amount = %s,
            status = %s,
            due_date = %s,
            remarks = %s,
            updated_at = NOW()
        WHERE id = %s
        RETURNING *
    """, (
        client_name,
        service_name,
        amount,
        tax_amount,
        total_amount,
        status,
        due_date,
        remarks,
        invoice_id
    ))

    updated_invoice = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Invoice updated", "invoice": updated_invoice}


@router.delete("/delete/{invoice_id}")
async def delete_invoice(invoice_id: str):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM invoices WHERE id = %s RETURNING id", (invoice_id,))
    deleted = cur.fetchone()

    if not deleted:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Invoice not found")

    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Invoice deleted", "id": invoice_id}


@router.get("/pdf/{invoice_id}")
async def download_invoice_pdf(invoice_id: str):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM invoices WHERE id = %s", (invoice_id,))
    invoice = cur.fetchone()

    cur.close()
    conn.close()

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
    pdf.drawString(50, height - 150, f"Date: {str(invoice.get('created_at'))[:10]}")
    pdf.drawString(50, height - 170, f"Status: {invoice.get('status', '').upper()}")

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, height - 220, "Bill To:")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, height - 245, invoice.get("client_name") or "-")

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, height - 300, "Service")
    pdf.drawString(300, height - 300, "Amount")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, height - 325, invoice.get("service_name") or "-")
    pdf.drawString(300, height - 325, f"Rs. {float(invoice.get('amount') or 0)}")

    pdf.drawString(50, height - 350, "Tax")
    pdf.drawString(300, height - 350, f"Rs. {float(invoice.get('tax_amount') or 0)}")

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, height - 390, "Total")
    pdf.drawString(300, height - 390, f"Rs. {float(invoice.get('total_amount') or 0)}")

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