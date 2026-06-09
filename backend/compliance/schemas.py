from pydantic import BaseModel
from typing import Optional

class ComplianceRecord(BaseModel):
    client_name: str
    gst_status: str = "Pending"
    itr_status: str = "Pending"
    tds_status: str = "Pending"
    notice_status: str = "None"
    assigned_staff: Optional[str] = ""
    due_date: Optional[str] = ""
    remarks: Optional[str] = ""