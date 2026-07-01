from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class EmployeeCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    pan: Optional[str] = None
    aadhar: Optional[str] = None
    upi_id: Optional[str] = None
    bank_account: Optional[str] = None
    bank_ifsc: Optional[str] = None
    designation: str
    department: Optional[str] = None
    joining_date: datetime
    basic_salary: float = 0.0
    hra: float = 0.0
    dearness_allowance: float = 0.0
    other_allowances: float = 0.0
    pf_applicable: bool = True
    esi_applicable: bool = True
    pt_applicable: bool = False


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    designation: Optional[str] = None
    department: Optional[str] = None
    basic_salary: Optional[float] = None
    hra: Optional[float] = None
    dearness_allowance: Optional[float] = None
    other_allowances: Optional[float] = None
    pf_applicable: Optional[bool] = None
    esi_applicable: Optional[bool] = None
    pt_applicable: Optional[bool] = None
    status: Optional[str] = None


class EmployeeResponse(BaseModel):
    id: str
    name: str
    email: Optional[str]
    phone: Optional[str]
    designation: str
    department: Optional[str]
    joining_date: datetime
    basic_salary: float
    hra: float
    dearness_allowance: float
    status: str
    pf_applicable: bool
    esi_applicable: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AttendanceCreate(BaseModel):
    employee_id: str
    attendance_date: datetime
    status: str = "present"
    hours_worked: float = 8.0
    remarks: Optional[str] = None


class AttendanceResponse(BaseModel):
    id: str
    employee_id: str
    attendance_date: datetime
    status: str
    hours_worked: float
    remarks: Optional[str]

    class Config:
        from_attributes = True


class SalaryStructureCreate(BaseModel):
    employee_id: str
    effective_from: datetime
    effective_to: Optional[datetime] = None
    basic: float = 0.0
    hra: float = 0.0
    dearness_allowance: float = 0.0
    travel_allowance: float = 0.0
    medical_allowance: float = 0.0
    other_allowances: float = 0.0
    pf_rate: float = 12.0
    esi_rate: float = 0.75
    pt_rate: float = 0.0


class SalaryStructureResponse(BaseModel):
    id: str
    employee_id: str
    effective_from: datetime
    basic: float
    hra: float
    dearness_allowance: float
    travel_allowance: float
    medical_allowance: float
    other_allowances: float
    pf_rate: float
    esi_rate: float

    class Config:
        from_attributes = True


class PayrollCreate(BaseModel):
    employee_id: str
    month: str = Field(..., description="Format: YYYY-MM")
    working_days: int = 26
    actual_days_worked: int = 26
    income_tax: float = 0.0
    other_deductions: float = 0.0


class PayrollResponse(BaseModel):
    id: str
    employee_id: str
    month: str
    status: str
    gross_salary: float
    pf_deduction: float
    esi_deduction: float
    pt_deduction: float
    income_tax: float
    total_deductions: float
    net_salary: float
    created_at: datetime

    class Config:
        from_attributes = True


class PayrollDetailResponse(PayrollResponse):
    basic_salary: float
    hra: float
    dearness_allowance: float
    travel_allowance: float
    medical_allowance: float
    other_allowances: float
    other_deductions: float
    working_days: int
    actual_days_worked: int


class SalarySlip(BaseModel):
    employee_name: str
    employee_id: str
    month: str
    designation: str
    joining_date: datetime

    basic_salary: float
    hra: float
    dearness_allowance: float
    travel_allowance: float
    medical_allowance: float
    other_allowances: float
    gross_salary: float

    pf_deduction: float
    esi_deduction: float
    pt_deduction: float
    income_tax: float
    other_deductions: float
    total_deductions: float
    net_salary: float

    working_days: int
    actual_days_worked: int
    payment_method: Optional[str] = None
    payment_date: Optional[datetime] = None


class PayrollStats(BaseModel):
    total_employees: int
    active_employees: int
    total_gross_salary: float
    total_deductions: float
    total_net_salary: float
    processing_month: str
