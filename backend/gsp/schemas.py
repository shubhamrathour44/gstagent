"""Schemas for GST Suvidha Provider (GSP) connector module.

The module supports a safe sandbox/mock mode by default and provider adapters
for MasterGST/WhiteBooks style APIs. Production credentials must be supplied by
the GSP after ASP onboarding.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class GSTINVerificationResponse(BaseModel):
    gstin: str
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    status: str = "unknown"
    taxpayer_type: Optional[str] = None
    registration_date: Optional[str] = None
    cancellation_date: Optional[str] = None
    state_code: Optional[str] = None
    address: Optional[str] = None
    source: str
    raw: dict[str, Any] = Field(default_factory=dict)


class GSPFetchRequest(BaseModel):
    gstin: str
    period: str = Field(..., description="Return period in MMYYYY format, e.g. 042026")
    client_id: Optional[str] = None
    provider: Optional[str] = None

    @field_validator("gstin")
    @classmethod
    def clean_gstin(cls, value: str) -> str:
        value = value.upper().strip()
        if len(value) != 15:
            raise ValueError("GSTIN must be 15 characters")
        return value

    @field_validator("period")
    @classmethod
    def clean_period(cls, value: str) -> str:
        value = value.strip()
        if len(value) != 6 or not value.isdigit():
            raise ValueError("Period must be MMYYYY, e.g. 042026")
        return value


class GSTR2BFetchResponse(BaseModel):
    gstin: str
    period: str
    source: str
    fetched_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    invoices: list[dict[str, Any]]
    raw: dict[str, Any] = Field(default_factory=dict)


class GSTR1FetchResponse(BaseModel):
    gstin: str
    period: str
    source: str
    fetched_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    invoices: list[dict[str, Any]]
    raw: dict[str, Any] = Field(default_factory=dict)


class GSTR3BDraftRequest(BaseModel):
    gstin: str
    period: str
    outward_taxable_value: float = 0.0
    outward_tax_amount: float = 0.0
    eligible_itc: float = 0.0
    reverse_charge_tax: float = 0.0
    provider: Optional[str] = None


class FilingStatusResponse(BaseModel):
    gstin: str
    period: str
    return_type: str
    status: str
    filed_on: Optional[str] = None
    arn: Optional[str] = None
    source: str
    raw: dict[str, Any] = Field(default_factory=dict)


class ReconcileFromGSPRequest(BaseModel):
    gstin: str
    period: str
    company_name: str
    purchase_register: list[dict[str, Any]]
    client_id: Optional[str] = None
    provider: Optional[str] = None
