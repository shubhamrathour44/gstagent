"""GSTAgent API v2.1 — backend foundation fixed.

Fixes included:
- PostgreSQL/SQLite persistence through database.py
- Real register/login from auth.py
- Firm-scoped clients, reconciliations and mismatches
- Billing router mounted
- Reconciliation upload/raw flows save to DB
- Excel/AI endpoints read from DB instead of in-memory store
"""

from __future__ import annotations

import io
import json
import os
from datetime import datetime
from typing import Optional

import pandas as pd
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ai_agent import (
    draft_notice_reply,
    draft_vendor_email,
    explain_mismatch as ai_explain_mismatch,
    filing_qa_check,
    generate_reconciliation_summary,
)
from auth import CurrentUser, auth_router, get_current_user
from database import (
    AuditRepo,
    ClientRepo,
    MismatchRepo,
    ReconciliationRepo,
    create_tables,
    get_db,
)
from excel_export import generate_to_bytes
from integrations import TallyConfig, TallyConnector, tally_router, zoho_router
from gsp.router import gsp_router
from tax.router import tax_router
from reconciliation_engine import GSTReconciliationEngine

try:
    from billing import billing_router
except Exception:  # Razorpay is optional during local dev
    billing_router = None


app = FastAPI(
    title="GSTAgent API",
    description="AI-powered GST, tax and compliance platform foundation for Indian CA firms",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

allowed_origins = os.getenv(
    "CORS_ORIGINS",
    "https://gstagent.co.in,https://www.gstagent.co.in,https://gstagent.vercel.app,http://localhost:3000,http://localhost:5173,http://localhost:8000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(tally_router)
app.include_router(zoho_router)
app.include_router(gsp_router)
app.include_router(tax_router)
if billing_router is not None:
    app.include_router(billing_router)

engine = GSTReconciliationEngine()


@app.on_event("startup")
async def startup() -> None:
    await create_tables()


class ReconcileRequest(BaseModel):
    gstin: str
    period: str
    company_name: str
    purchase_register: list[dict]
    gstr_2b: list[dict]
    client_id: Optional[str] = None
    source: str = "file_upload"


class VendorEmailRequest(BaseModel):
    reconciliation_id: str
    mismatch_id: str
    sender_company: str
    sender_gstin: str


class NoticeReplyRequest(BaseModel):
    notice_number: str
    notice_date: str
    notice_type: str
    notice_content: str
    taxpayer_gstin: str
    taxpayer_name: str
    supporting_facts: str


class FilingQARequest(BaseModel):
    reconciliation_id: str
    return_type: str
    draft_return_summary: dict


class SendEmailRequest(BaseModel):
    to_email: str
    to_name: str
    subject: str
    body: str
    reconciliation_id: str
    mismatch_id: str


class ClientCreateRequest(BaseModel):
    name: str
    gstin: str
    city: Optional[str] = None
    business_type: Optional[str] = None
    contact_email: Optional[str] = None
    tally_company: Optional[str] = None
    zoho_org_id: Optional[str] = None


class ResolveMismatchRequest(BaseModel):
    status: str = "resolved"
    notes: str = ""


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "2.1.0",
        "domain": "gstagent.co.in",
        "database": "enabled",
        "timestamp": datetime.utcnow().isoformat(),
        "features": ["auth", "database", "reconciliation", "ai", "tally", "zoho", "gsp_connector", "excel_export", "billing", "income_tax_assistant"],
    }


def client_to_dict(client) -> dict:
    return {
        "id": client.id,
        "firm_id": client.firm_id,
        "name": client.name,
        "gstin": client.gstin,
        "city": client.city,
        "business_type": client.business_type,
        "contact_email": client.contact_email,
        "tally_company": client.tally_company,
        "zoho_org_id": client.zoho_org_id,
        "is_active": client.is_active,
        "created_at": client.created_at.isoformat() if client.created_at else None,
    }


def rec_to_dict(rec) -> dict:
    return {
        "id": rec.id,
        "firm_id": rec.firm_id,
        "client_id": rec.client_id,
        "gstin": rec.gstin,
        "company_name": rec.company_name,
        "period": rec.period,
        "source": rec.source,
        "pr_count": rec.pr_count,
        "b2b_count": rec.b2b_count,
        "matched_count": rec.matched_count,
        "mismatch_count": rec.mismatch_count,
        "match_rate": rec.match_rate,
        "itc_difference": rec.itc_difference,
        "high_count": rec.high_count,
        "medium_count": rec.medium_count,
        "low_count": rec.low_count,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }


async def get_or_create_client(db: AsyncSession, current_user: CurrentUser, *, gstin: str, company_name: str, client_id: str | None = None):
    if client_id:
        client = await ClientRepo.get(db, client_id, current_user.firm_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found for this firm")
        return client

    client = await ClientRepo.get_by_gstin(db, gstin, current_user.firm_id)
    if client:
        return client

    return await ClientRepo.create(db, current_user.firm_id, {
        "name": company_name,
        "gstin": gstin.upper().strip(),
    })


@app.get("/clients")
async def list_clients(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    clients = await ClientRepo.list_for_firm(db, current_user.firm_id)
    return {"clients": [client_to_dict(c) for c in clients], "firm_id": current_user.firm_id}


@app.post("/clients")
async def create_client(request: ClientCreateRequest, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    existing = await ClientRepo.get_by_gstin(db, request.gstin, current_user.firm_id)
    if existing:
        raise HTTPException(status_code=409, detail="This GSTIN already exists in your firm")
    client = await ClientRepo.create(db, current_user.firm_id, {
        "name": request.name.strip(),
        "gstin": request.gstin.upper().strip(),
        "city": request.city,
        "business_type": request.business_type,
        "contact_email": request.contact_email,
        "tally_company": request.tally_company,
        "zoho_org_id": request.zoho_org_id,
    })
    await AuditRepo.log(db, current_user.firm_id, current_user.user_id, "client.created", "client", client.id, {"gstin": client.gstin})
    return {"client": client_to_dict(client)}


@app.post("/reconcile")
async def reconcile(request: ReconcileRequest, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    client = await get_or_create_client(db, current_user, gstin=request.gstin, company_name=request.company_name, client_id=request.client_id)
    result = engine.reconcile(request.gstin, request.period, request.purchase_register, request.gstr_2b)
    result_dict = result.to_dict()
    rec = await ReconciliationRepo.create(
        db,
        firm_id=current_user.firm_id,
        client_id=client.id,
        company_name=request.company_name,
        source=request.source,
        result_json=result_dict,
        created_by=current_user.user_id,
    )
    await AuditRepo.log(db, current_user.firm_id, current_user.user_id, "reconciliation.created", "reconciliation", rec.id, {"gstin": request.gstin, "period": request.period})
    return {"reconciliation_id": rec.id, "client": client_to_dict(client), "result": result_dict}


@app.post("/reconcile/upload")
async def reconcile_upload(
    gstin: str,
    period: str,
    company_name: str,
    client_id: Optional[str] = None,
    purchase_register_file: UploadFile = File(...),
    gstr_2b_file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        pr_bytes = await purchase_register_file.read()
        pr_df = pd.read_excel(io.BytesIO(pr_bytes))
        pr_df.columns = [str(c).lower().strip().replace(" ", "_") for c in pr_df.columns]
        purchase_register = pr_df.to_dict(orient="records")

        b2b_bytes = await gstr_2b_file.read()
        if (gstr_2b_file.filename or "").lower().endswith(".json"):
            raw = json.loads(b2b_bytes)
            gstr_2b = raw if isinstance(raw, list) else _parse_portal_2b(raw)
        else:
            b2b_df = pd.read_excel(io.BytesIO(b2b_bytes))
            b2b_df.columns = [str(c).lower().strip().replace(" ", "_") for c in b2b_df.columns]
            gstr_2b = b2b_df.to_dict(orient="records")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"File parsing error: {exc}")

    client = await get_or_create_client(db, current_user, gstin=gstin, company_name=company_name, client_id=client_id)
    result = engine.reconcile(gstin, period, purchase_register, gstr_2b)
    result_dict = result.to_dict()
    rec = await ReconciliationRepo.create(db, firm_id=current_user.firm_id, client_id=client.id, company_name=company_name, source="file_upload", result_json=result_dict, created_by=current_user.user_id)
    await AuditRepo.log(db, current_user.firm_id, current_user.user_id, "reconciliation.upload.created", "reconciliation", rec.id, {"gstin": gstin, "period": period})
    return {"reconciliation_id": rec.id, "client": client_to_dict(client), "result": result_dict}


@app.post("/reconcile/from-tally")
async def reconcile_from_tally(
    gstin: str,
    period: str,
    company_name: str,
    tally_host: str = "localhost",
    tally_port: int = 9000,
    tally_company: str = "",
    gstr_2b: list[dict] = [],
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    config = TallyConfig(host=tally_host, port=tally_port, company_name=tally_company)
    connector = TallyConnector(config)
    try:
        purchase_register = await connector.get_purchase_register(period)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    client = await get_or_create_client(db, current_user, gstin=gstin, company_name=company_name)
    result = engine.reconcile(gstin, period, purchase_register, gstr_2b)
    result_dict = result.to_dict()
    rec = await ReconciliationRepo.create(db, firm_id=current_user.firm_id, client_id=client.id, company_name=company_name, source="tally", result_json=result_dict, created_by=current_user.user_id)
    return {"reconciliation_id": rec.id, "result": result_dict, "tally_invoices_fetched": len(purchase_register)}


@app.get("/reconciliations")
async def list_reconciliations(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    recs = await ReconciliationRepo.list_for_firm(db, current_user.firm_id)
    return {"reconciliations": [rec_to_dict(r) for r in recs]}


@app.get("/reconcile/{reconciliation_id}")
async def get_reconciliation(reconciliation_id: str, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rec = await ReconciliationRepo.get(db, reconciliation_id, current_user.firm_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    return {"meta": rec_to_dict(rec), "result": rec.result_json}


async def _get_rec_and_mismatch(db: AsyncSession, current_user: CurrentUser, rec_id: str, mismatch_id: str):
    rec = await ReconciliationRepo.get(db, rec_id, current_user.firm_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    mismatch = await MismatchRepo.get_by_public_id(db, current_user.firm_id, rec_id, mismatch_id)
    if not mismatch:
        raise HTTPException(status_code=404, detail="Mismatch not found")
    return rec, mismatch


@app.post("/ai/explain-mismatch")
async def explain_mismatch_endpoint(reconciliation_id: str, mismatch_id: str, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rec, mismatch = await _get_rec_and_mismatch(db, current_user, reconciliation_id, mismatch_id)
    m_obj = _dict_to_mismatch(mismatch.raw_json)
    explanation = await ai_explain_mismatch(m_obj)
    await MismatchRepo.save_ai_explanation(db, mismatch, explanation)
    return {"mismatch_id": mismatch_id, "explanation": explanation}


@app.post("/ai/vendor-email")
async def vendor_email_endpoint(request: VendorEmailRequest, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rec, mismatch = await _get_rec_and_mismatch(db, current_user, request.reconciliation_id, request.mismatch_id)
    email = await draft_vendor_email(_dict_to_mismatch(mismatch.raw_json), request.sender_company, request.sender_gstin, rec.period)
    await MismatchRepo.save_vendor_email(db, mismatch, email)
    return {"mismatch_id": request.mismatch_id, "email_draft": email}


@app.post("/ai/summary")
async def summary_endpoint(reconciliation_id: str, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rec = await ReconciliationRepo.get(db, reconciliation_id, current_user.firm_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    summary = await generate_reconciliation_summary(_dict_to_result(rec.result_json), rec.company_name)
    rec.ai_summary = summary
    return {"summary": summary}


@app.post("/ai/filing-qa")
async def filing_qa_endpoint(request: FilingQARequest, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rec = await ReconciliationRepo.get(db, request.reconciliation_id, current_user.firm_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    qa = await filing_qa_check(_dict_to_result(rec.result_json), request.return_type, request.draft_return_summary)
    rec.filing_qa = qa
    return {"qa_result": qa}


@app.post("/ai/notice-reply")
async def notice_reply_endpoint(request: NoticeReplyRequest, current_user: CurrentUser = Depends(get_current_user)):
    reply = await draft_notice_reply(
        notice_number=request.notice_number,
        notice_date=request.notice_date,
        notice_type=request.notice_type,
        notice_content=request.notice_content,
        taxpayer_gstin=request.taxpayer_gstin,
        taxpayer_name=request.taxpayer_name,
        supporting_facts=request.supporting_facts,
    )
    return {"notice_number": request.notice_number, "draft_reply": reply, "disclaimer": "Review by qualified CA required before submission."}


@app.post("/mismatches/{reconciliation_id}/{mismatch_id}/resolve")
async def resolve_mismatch(reconciliation_id: str, mismatch_id: str, request: ResolveMismatchRequest, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    _, mismatch = await _get_rec_and_mismatch(db, current_user, reconciliation_id, mismatch_id)
    await MismatchRepo.resolve(db, mismatch, current_user.user_id, request.notes, request.status)
    return {"message": "Mismatch updated", "mismatch_id": mismatch_id, "status": request.status}


@app.get("/export/{reconciliation_id}/xlsx")
async def export_excel(reconciliation_id: str, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rec = await ReconciliationRepo.get(db, reconciliation_id, current_user.firm_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    xlsx_bytes = generate_to_bytes(rec.result_json, rec.company_name)
    filename = f"GST_Recon_{rec.company_name[:20].replace(' ', '_')}_{rec.period}.xlsx"
    return Response(content=xlsx_bytes, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.post("/send-vendor-email")
async def send_vendor_email(request: SendEmailRequest, background_tasks: BackgroundTasks, current_user: CurrentUser = Depends(get_current_user)):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    if not all([smtp_host, smtp_user, smtp_pass]):
        return {"status": "config_missing", "message": "SMTP not configured", "email_draft": request.body}
    background_tasks.add_task(_send_smtp_email, smtp_host, smtp_user, smtp_pass, request.to_email, request.to_name, request.subject, request.body, current_user.firm_name)
    return {"status": "queued", "message": f"Email queued for {request.to_email}", "mismatch_id": request.mismatch_id}


async def _send_smtp_email(host, user, password, to_email, to_name, subject, body, from_name):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{user}>"
    msg["To"] = f"{to_name} <{to_email}>"
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP_SSL(host, 465) as server:
        server.login(user, password)
        server.sendmail(user, to_email, msg.as_string())


def _dict_to_mismatch(m: dict):
    from reconciliation_engine import Mismatch, MismatchAction, MismatchSeverity, MismatchType
    return Mismatch(
        mismatch_id=m.get("mismatch_id", ""),
        mismatch_type=MismatchType(m["mismatch_type"]),
        severity=MismatchSeverity(m["severity"]),
        supplier_gstin=m.get("supplier_gstin", ""),
        supplier_name=m.get("supplier_name", ""),
        invoice_number=m.get("invoice_number", ""),
        invoice_date=m.get("invoice_date", ""),
        pr_taxable_value=m.get("pr_taxable_value"),
        b2b_taxable_value=m.get("b2b_taxable_value"),
        pr_tax_amount=m.get("pr_tax_amount"),
        b2b_tax_amount=m.get("b2b_tax_amount"),
        tax_impact=m.get("tax_impact", 0.0),
        recommended_action=MismatchAction(m.get("recommended_action", "No action required")),
        action_deadline=m.get("action_deadline"),
        notes=m.get("notes", ""),
    )


def _dict_to_result(r: dict):
    from reconciliation_engine import ReconciliationResult
    return ReconciliationResult(
        gstin=r["gstin"],
        period=r["period"],
        reconciled_at=r["reconciled_at"],
        total_pr_invoices=r["total_pr_invoices"],
        total_2b_invoices=r["total_2b_invoices"],
        matched_invoices=r["matched_invoices"],
        mismatched_invoices=r["mismatched_invoices"],
        missing_in_2b=r["missing_in_2b"],
        missing_in_pr=r["missing_in_pr"],
        total_itc_as_per_2b=r["total_itc_as_per_2b"],
        total_itc_as_per_pr=r["total_itc_as_per_pr"],
        itc_difference=r["itc_difference"],
        high_severity_count=r["high_severity_count"],
        medium_severity_count=r["medium_severity_count"],
        low_severity_count=r["low_severity_count"],
        mismatches=[],
        summary_stats=r.get("summary_stats", {}),
    )


def _parse_portal_2b(data: dict) -> list[dict]:
    records = []
    for supplier in data.get("data", {}).get("docdata", {}).get("b2b", []):
        for inv in supplier.get("inv", []):
            for item in inv.get("items", [{}]):
                records.append({
                    "supplier_gstin": supplier.get("ctin", ""),
                    "supplier_name": supplier.get("trdnm", ""),
                    "invoice_number": inv.get("inum", ""),
                    "invoice_date": inv.get("idt", ""),
                    "taxable_value": item.get("txval", 0),
                    "igst": item.get("igst", 0),
                    "cgst": item.get("cgst", 0),
                    "sgst": item.get("sgst", 0),
                    "reverse_charge": inv.get("rev", "N") == "Y",
                })
    return records


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
