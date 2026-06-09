"""FastAPI routes for GSP integration — Path Aligned Configuration."""

from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from auth import CurrentUser, get_current_user
from database import AuditRepo, ClientRepo, ReconciliationRepo, get_db
from reconciliation_engine import GSTReconciliationEngine

from .client import get_provider, provider_status
from .schemas import GSPFetchRequest, GSTR3BDraftRequest, ReconcileFromGSPRequest

# We define the router cleanly without a strict top-level prefix conflict
gsp_router = APIRouter(tags=["GSP Connector"])
_engine = GSTReconciliationEngine()

async def _get_or_create_client(db: AsyncSession, current_user: CurrentUser, gstin: str, company_name: str | None = None, client_id: str | None = None):
    if client_id:
        client = await ClientRepo.get(db, client_id, current_user.firm_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found for this firm")
        return client
    client = await ClientRepo.get_by_gstin(db, gstin, current_user.firm_id)
    if client:
        return client
    return await ClientRepo.create(db, current_user.firm_id, {"name": company_name or f"GSTIN {gstin}", "gstin": gstin})

# --- HEALTH & CORE AUTH PROFILE ROUTING ---
@gsp_router.get("/me")
@gsp_router.get("/gsp/me")
async def get_current_me_profile(current_user: CurrentUser = Depends(get_current_user)):
    return {"status": "authenticated", "firm_id": current_user.firm_id, "user_id": current_user.user_id}

@gsp_router.get("/status")
@gsp_router.get("/gsp/status")
async def gsp_status(current_user: CurrentUser = Depends(get_current_user)):
    return {"firm_id": current_user.firm_id, **provider_status()}


# --- VERIFY ENDPOINTS (Catches raw query strings and embedded path parameters) ---
@gsp_router.get("/verify")
@gsp_router.get("/gsp/verify")
@gsp_router.get("/gstin/{gstin}/verify")
@gsp_router.get("/gsp/gstin/{gstin}/verify")
async def verify_gstin_dashboard(
    gstin: str = "27AABCD1234F1Z5", 
    provider: str | None = None, 
    current_user: CurrentUser = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    gstin = gstin.upper().strip()
    result = await get_provider(provider).verify_gstin(gstin)
    await AuditRepo.log(db, current_user.firm_id, current_user.user_id, "gsp.gstin.verify", "gstin", gstin, {"provider": result.source, "status": result.source})
    return result


# --- FETCH DATA OVERLAYS (GSTR-2B / GSTR-1) ---
@gsp_router.post("/gstr2b")
@gsp_router.post("/gsp/gstr2b")
@gsp_router.post("/gsp/gstr2b/fetch")
async def fetch_gstr2b(request: GSPFetchRequest, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await get_provider(request.provider).fetch_gstr2b(request.gstin, request.period)
    await AuditRepo.log(db, current_user.firm_id, current_user.user_id, "gsp.gstr2b.fetch", "gstin", request.gstin, {"period": request.period, "provider": result.source, "invoice_count": len(result.invoices)})
    return result

@gsp_router.post("/gstr1")
@gsp_router.post("/gsp/gstr1")
@gsp_router.post("/gsp/gstr1/fetch")
async def fetch_gstr1(request: GSPFetchRequest, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await get_provider(request.provider).fetch_gstr1(request.gstin, request.period)
    await AuditRepo.log(db, current_user.firm_id, current_user.user_id, "gsp.gstr1.fetch", "gstin", request.gstin, {"period": request.period, "provider": result.source, "invoice_count": len(result.invoices)})
    return result


# --- FILING STATUS & RETURN DRAFS ---
@gsp_router.get("/filing-status")
@gsp_router.get("/gsp/filing-status")
async def filing_status(gstin: str, period: str, return_type: str = "GSTR3B", provider: str | None = None, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await get_provider(provider).get_filing_status(gstin.upper().strip(), period.strip(), return_type.upper().strip())
    await AuditRepo.log(db, current_user.firm_id, current_user.user_id, "gsp.filing_status", "gstin", gstin, {"period": period, "return_type": return_type, "status": result.status, "provider": result.source})
    return result

@gsp_router.post("/draft")
@gsp_router.post("/gsp/draft")
@gsp_router.post("/gsp/gstr3b/draft")
async def create_gstr3b_draft(request: GSTR3BDraftRequest, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    payload = {
        "outward_taxable_value": request.outward_taxable_value,
        "outward_tax_amount": request.outward_tax_amount,
        "eligible_itc": request.eligible_itc,
        "reverse_charge_tax": request.reverse_charge_tax,
        "net_tax_payable": max(request.outward_tax_amount + request.reverse_charge_tax - request.eligible_itc, 0),
    }
    result = await get_provider(request.provider).create_gstr3b_draft(request.gstin.upper().strip(), request.period, payload)
    await AuditRepo.log(db, current_user.firm_id, current_user.user_id, "gsp.gstr3b.draft", "gstin", request.gstin, {"period": request.period, "provider": result.get("source")})
    return result


# --- RECONCILIATION ENGINE PASS ---
@gsp_router.post("/reconcile/gstr2b")
@gsp_router.post("/gsp/reconcile/gstr2b")
async def reconcile_with_gsp_2b(request: ReconcileFromGSPRequest, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    client = await _get_or_create_client(db, current_user, request.gstin, request.company_name, request.client_id)
    gstr2b = await get_provider(request.provider).fetch_gstr2b(request.gstin, request.period)
    result = _engine.reconcile(request.gstin, request.period, request.purchase_register, gstr2b.invoices)
    result_dict = result.to_dict()
    rec = await ReconciliationRepo.create(
        db,
        firm_id=current_user.firm_id,
        client_id=client.id,
        company_name=request.company_name,
        source=f"gsp:{gstr2b.source}",
        result_json=result_dict,
        created_by=current_user.user_id,
    )
    await AuditRepo.log(db, current_user.firm_id, current_user.user_id, "gsp.reconciliation.created", "reconciliation", rec.id, {"gstin": request.gstin, "period": request.period, "provider": gstr2b.source})
    return {"reconciliation_id": rec.id, "provider": gstr2b.source, "gstr2b_invoice_count": len(gstr2b.invoices), "result": result_dict}