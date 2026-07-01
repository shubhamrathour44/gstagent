from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class DocumentUploadRequest(BaseModel):
    document_type: str
    pan: Optional[str] = None
    assessment_year: Optional[str] = None
    itr_return_id: Optional[str] = None


class DocumentResponse(BaseModel):
    id: str
    document_type: str
    document_name: str
    file_size: int
    mime_type: str
    pan: Optional[str]
    assessment_year: Optional[str]
    extraction_status: str
    extracted_data: Dict[str, Any]
    uploaded_at: datetime

    class Config:
        from_attributes = True


class AISExtraction(BaseModel):
    """Extracted data from AIS (Annual Information Statement)"""
    pan: Optional[str] = None
    assessment_year: Optional[str] = None
    salary_income: Optional[float] = None
    hra_received: Optional[float] = None
    other_income: Optional[float] = None
    tds_salary: Optional[float] = None
    tds_interest: Optional[float] = None
    tds_other: Optional[float] = None
    total_tds: Optional[float] = None
    extracted_fields: Dict[str, str] = {}


class Form26ASExtraction(BaseModel):
    """Extracted data from Form 26AS (Tax Collected at Source)"""
    pan: Optional[str] = None
    assessment_year: Optional[str] = None
    gross_total_income: Optional[float] = None
    tds_entries: list = []
    total_tds: Optional[float] = None
    deposit_entries: list = []
    extracted_fields: Dict[str, str] = {}


class Form16Extraction(BaseModel):
    """Extracted data from Form 16 (TDS Certificate for Salary)"""
    pan: Optional[str] = None
    employee_pan: Optional[str] = None
    assessment_year: Optional[str] = None
    salary_paid: Optional[float] = None
    salary_credited: Optional[float] = None
    hra_paid: Optional[float] = None
    hra_exemption: Optional[float] = None
    standard_deduction: Optional[float] = None
    gross_total_income: Optional[float] = None
    tds_deducted: Optional[float] = None
    tds_deposited: Optional[float] = None
    employee_name: Optional[str] = None
    employer_name: Optional[str] = None
    extracted_fields: Dict[str, str] = {}


class DocumentExtractionResult(BaseModel):
    """Result of document parsing/extraction"""
    document_id: str
    document_type: str
    status: str
    extracted_data: Dict[str, Any]
    errors: Optional[str] = None
    warnings: list = []
    extracted_fields: Dict[str, str] = {}


class DocumentListResponse(BaseModel):
    count: int
    documents: list[DocumentResponse]


class DocumentStatistics(BaseModel):
    """Statistics about uploaded documents"""
    total_documents: int
    by_type: Dict[str, int]
    extraction_status: Dict[str, int]
    total_file_size_mb: float
