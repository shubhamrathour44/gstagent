from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from auth import CurrentUser, get_current_user
from compliance.schemas import ComplianceCreate, ComplianceUpdate

# Added clear prefix binding to ensure clean path lookups
compliance_router = APIRouter(prefix="/compliance", tags=["Compliance"])

COMPLIANCE_STORE = {}

@compliance_router.get("/status")
async def compliance_status(current_user: CurrentUser = Depends(get_current_user)):
    return {
        "status": "ok",
        "module": "compliance_tracker",
        "version": "1.0.0",
        "firm_id": current_user.firm_id
    }

@compliance_router.post("/create")
async def create_compliance(payload: ComplianceCreate, current_user: CurrentUser = Depends(get_current_user)):
    item_id = str(uuid4())
    item = {
        "id": item_id,
        "firm_id": current_user.firm_id,
        "client_name": payload.client_name,
        "gstin": payload.gstin,
        "pan": payload.pan,
        "gst_status": payload.gst_status,
        "itr_status": payload.itr_status,
        "tds_status": payload.tds_status,
        "notice_status": payload.notice_status,
        "gst_due_date": str(payload.gst_due_date) if payload.gst_due_date else None,
        "itr_due_date": str(payload.itr_due_date) if payload.itr_due_date else None,
        "tds_due_date": str(payload.tds_due_date) if payload.tds_due_date else None,
        "assigned_staff": payload.assigned_staff,
        "remarks": payload.remarks,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    COMPLIANCE_STORE[item_id] = item
    return {"message": "Compliance record created", "record": item}

@compliance_router.get("/list")
async def list_compliance(current_user: CurrentUser = Depends(get_current_user)):
    records = [item for item in COMPLIANCE_STORE.values() if item["firm_id"] == current_user.firm_id]
    return {"records": records, "count": len(records)}

@compliance_router.get("/dashboard")
async def compliance_dashboard(current_user: CurrentUser = Depends(get_current_user)):
    records = [item for item in COMPLIANCE_STORE.values() if item["firm_id"] == current_user.firm_id]
    return {
        "total_clients": len(records),
        "gst_pending": sum(1 for r in records if r["gst_status"] == "pending"),
        "gst_filed": sum(1 for r in records if r["gst_status"] == "filed"),
        "itr_pending": sum(1 for r in records if r["itr_status"] == "pending"),
        "itr_filed": sum(1 for r in records if r["itr_status"] == "filed"),
        "tds_pending": sum(1 for r in records if r["tds_status"] == "pending"),
        "tds_filed": sum(1 for r in records if r["tds_status"] == "filed"),
        "open_notices": sum(1 for r in records if r["notice_status"] in ["open", "pending"]),
    }