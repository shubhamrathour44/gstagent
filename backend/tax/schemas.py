from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


IncomeCategory = Literal[
    "salary",
    "interest",
    "dividend",
    "capital_gains",
    "business_profession",
    "house_property",
    "rent",
    "other_sources",
    "unknown",
]


class TaxDocumentRecord(BaseModel):
    source: str = "manual"
    description: str = ""
    payer_name: str = ""
    payer_pan: str = ""
    section: str = ""
    category: IncomeCategory = "unknown"
    amount: float = 0.0
    tds: float = 0.0
    transaction_date: Optional[str] = None
    raw: dict[str, Any] = Field(default_factory=dict)


class TaxProfile(BaseModel):
    client_name: str
    pan: str
    assessment_year: str = "2026-27"
    taxpayer_type: Literal["individual", "huf", "firm_llp", "company"] = "individual"
    age: int = 30
    resident_status: Literal["resident", "non_resident", "resident_not_ordinary"] = "resident"
    has_business_income: bool = False
    presumptive_income: bool = False
    has_capital_gains: bool = False
    has_foreign_assets: bool = False
    has_crypto_income: bool = False
    has_more_than_one_house: bool = False
    deductions_old_regime: float = 0.0
    advance_tax_paid: float = 0.0
    self_assessment_tax_paid: float = 0.0


class TaxAnalyzeRequest(BaseModel):
    profile: TaxProfile
    ais_records: list[dict[str, Any]] = Field(default_factory=list)
    tis_records: list[dict[str, Any]] = Field(default_factory=list)
    form26as_records: list[dict[str, Any]] = Field(default_factory=list)
    form16_records: list[dict[str, Any]] = Field(default_factory=list)
    books_records: list[dict[str, Any]] = Field(default_factory=list)


class ITRSuggestionRequest(BaseModel):
    profile: TaxProfile
    income_summary: dict[str, float] = Field(default_factory=dict)


class TaxSummaryRequest(BaseModel):
    profile: TaxProfile
    income_summary: dict[str, float] = Field(default_factory=dict)


class TaxExportRequest(BaseModel):
    analysis: dict[str, Any]
