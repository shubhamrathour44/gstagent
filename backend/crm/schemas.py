from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CRMClientCreate(BaseModel):
    client_name: str
    trade_name: Optional[str] = None
    pan: Optional[str] = None
    gstin: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    business_type: Optional[str] = None
    assigned_staff: Optional[str] = None
    status: str = "active"
    gst_enabled: bool = True
    income_tax_enabled: bool = True
    tds_enabled: bool = False
    audit_enabled: bool = False
    monthly_gst_fee: float = 0.0
    itr_fee: float = 0.0
    notice_fee: float = 0.0
    audit_fee: float = 0.0
    notes: Optional[str] = None


class CRMClientUpdate(BaseModel):
    client_name: Optional[str] = None
    trade_name: Optional[str] = None
    pan: Optional[str] = None
    gstin: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    business_type: Optional[str] = None
    assigned_staff: Optional[str] = None
    status: Optional[str] = None
    gst_enabled: Optional[bool] = None
    income_tax_enabled: Optional[bool] = None
    tds_enabled: Optional[bool] = None
    audit_enabled: Optional[bool] = None
    monthly_gst_fee: Optional[float] = None
    itr_fee: Optional[float] = None
    notice_fee: Optional[float] = None
    audit_fee: Optional[float] = None
    notes: Optional[str] = None


class CRMBillingCreate(BaseModel):
    client_id: str
    service_type: str = "gst"
    description: str
    amount: float
    status: str = "unpaid"
    due_date: Optional[str] = None


class CRMNoticeCreate(BaseModel):
    client_id: str
    notice_type: str
    department: str = "gst"
    notice_number: Optional[str] = None
    received_date: Optional[str] = None
    due_date: Optional[str] = None
    status: str = "open"
    summary: Optional[str] = None
    response_notes: Optional[str] = None


class CRMDocumentCreate(BaseModel):
    client_id: str
    document_type: str
    file_name: str
    file_url: Optional[str] = None
    notes: Optional[str] = None
