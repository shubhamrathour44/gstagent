from fastapi import APIRouter
from .schemas import ComplianceRecord

compliance_router = APIRouter(
    prefix="/compliance",
    tags=["Compliance Tracker"]
)

records = []

@compliance_router.get("/status")
async def status():
    return {
        "status": "ok",
        "module": "compliance_tracker"
    }

@compliance_router.get("/dashboard")
async def dashboard():

    return {
        "total_clients": len(records),
        "gst_pending": sum(1 for r in records if r.gst_status=="Pending"),
        "itr_pending": sum(1 for r in records if r.itr_status=="Pending"),
        "tds_pending": sum(1 for r in records if r.tds_status=="Pending"),
        "open_notices": sum(1 for r in records if r.notice_status!="None")
    }

@compliance_router.get("/list")
async def get_records():
    return records

@compliance_router.post("/create")
async def create_record(record: ComplianceRecord):
    records.append(record.dict())
    return {
        "success": True,
        "message": "Record created"
    }