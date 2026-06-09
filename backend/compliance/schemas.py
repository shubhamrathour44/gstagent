from pydantic import BaseModel
from typing import Optional
from datetime import date

class ComplianceCreate(BaseModel):
    client_name: str
    gstin: Optional[str] = None
    pan: Optional[str] = None
    gst_status: str = "pending"
    itr_status: str = "pending"
    tds_status: str = "pending"
    notice_status: str = "none"
    gst_due_date: Optional[date] = None
    itr_due_date: Optional[date] = None
    tds_due_date: Optional[date] = None
    assigned_staff: Optional[str] = None
    remarks: Optional[str] = None

class ComplianceUpdate(BaseModel):
    client_name: Optional[str] = None
    gst_status: Optional[str] = None
    itr_status: Optional[str] = None
    tds_status: Optional[str] = None
    notice_status: Optional[str] = None
    assigned_staff: Optional[str] = None
    remarks: Optional[str] = None