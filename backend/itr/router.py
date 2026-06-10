"""
GSTAgent — ITR Filing Module v2
Covers: ITR-1, ITR-2, ITR-3, ITR-4, ITR-7
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import String, DateTime, Text, Float, Integer, JSON, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from auth import CurrentUser, get_current_user
from database import Base, get_db, new_id

router = APIRouter(prefix="/itr", tags=["ITR Filing"])


# ── MODEL ──────────────────────────────────────────────────────────────────────

class ITRReturn(Base):
    __tablename__ = "itr_returns"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True)
    client_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    client_name: Mapped[str] = mapped_column(String(255))
    pan: Mapped[str] = mapped_column(String(10), index=True)
    ay: Mapped[str] = mapped_column(String(10))
    itr_type: Mapped[str] = mapped_column(String(10))
    filing_type: Mapped[str] = mapped_column(String(20), default="original")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    income_data: Mapped[dict] = mapped_column(JSON, default=dict)
    tax_computation: Mapped[dict] = mapped_column(JSON, default=dict)
    acknowledgement_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    filed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    refund_amount: Mapped[float] = mapped_column(Float, default=0.0)
    tax_payable: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── SCHEMAS ────────────────────────────────────────────────────────────────────

class ITR1IncomeData(BaseModel):
    salary_income: float = 0.0
    hra_exemption: float = 0.0
    standard_deduction: float = 50000.0
    other_allowances_exempt: float = 0.0
    income_from_house_property: float = 0.0
    interest_income: float = 0.0
    other_income: float = 0.0
    sec_80c: float = 0.0
    sec_80d: float = 0.0
    sec_80e: float = 0.0
    sec_80g: float = 0.0
    sec_80tta: float = 0.0
    sec_24b: float = 0.0
    tds_employer: float = 0.0
    tds_bank: float = 0.0
    tds_other: float = 0.0
    advance_tax: float = 0.0
    self_assessment_tax: float = 0.0
    new_tax_regime: bool = False


class ITR2IncomeData(BaseModel):
    # Salary
    salary_income: float = 0.0
    hra_exemption: float = 0.0
    standard_deduction: float = 50000.0
    other_allowances_exempt: float = 0.0
    # House Property
    annual_rental_value: float = 0.0
    self_occupied_loan_interest: float = 0.0
    let_out_loan_interest: float = 0.0
    house_property_income: float = 0.0
    # Capital Gains
    stcg_111a: float = 0.0       # Equity/MF STCG @ 20%
    stcg_other: float = 0.0      # Other STCG at slab
    ltcg_112a: float = 0.0       # Equity/MF LTCG @ 12.5% above 1.25L
    ltcg_other: float = 0.0      # Other LTCG @ 20% with indexation
    # Other Income
    interest_income: float = 0.0
    dividend_income: float = 0.0
    other_income: float = 0.0
    # Foreign
    foreign_income: float = 0.0
    foreign_tax_paid: float = 0.0
    # Deductions
    sec_80c: float = 0.0
    sec_80d: float = 0.0
    sec_80e: float = 0.0
    sec_80g: float = 0.0
    sec_80tta: float = 0.0
    sec_80ttb: float = 0.0
    # Tax paid
    tds_salary: float = 0.0
    tds_other: float = 0.0
    advance_tax: float = 0.0
    self_assessment_tax: float = 0.0
    new_tax_regime: bool = False
    age: int = 30


class ITR3IncomeData(BaseModel):
    business_income: float = 0.0
    profession_income: float = 0.0
    speculative_income: float = 0.0
    capital_gains_stcg: float = 0.0
    capital_gains_ltcg: float = 0.0
    salary_income: float = 0.0
    house_property_income: float = 0.0
    other_income: float = 0.0
    business_expenses: float = 0.0
    depreciation: float = 0.0
    sec_80c: float = 0.0
    sec_80d: float = 0.0
    sec_80g: float = 0.0
    tds_total: float = 0.0
    advance_tax: float = 0.0
    self_assessment_tax: float = 0.0
    new_tax_regime: bool = False


class ITR4IncomeData(BaseModel):
    section: str = "44AD"
    gross_turnover: float = 0.0
    presumptive_income: float = 0.0
    other_income: float = 0.0
    sec_80c: float = 0.0
    sec_80d: float = 0.0
    tds_total: float = 0.0
    advance_tax: float = 0.0
    self_assessment_tax: float = 0.0
    new_tax_regime: bool = False


class ITR7IncomeData(BaseModel):
    entity_type: str = "trust"
    filing_section: str = "139(4A)"
    gross_receipts: float = 0.0
    voluntary_contributions: float = 0.0
    corpus_donations: float = 0.0
    anonymous_donations: float = 0.0
    business_income: float = 0.0
    investment_income: float = 0.0
    applied_for_objects: float = 0.0
    accumulated_income: float = 0.0
    sec_11_exemption: float = 0.0
    sec_12_exemption: float = 0.0
    sec_13_violation: bool = False
    registration_no: str = ""
    registration_date: str = ""
    tds_total: float = 0.0
    advance_tax: float = 0.0
    self_assessment_tax: float = 0.0


class CreateITRRequest(BaseModel):
    client_id: Optional[str] = None
    client_name: str
    pan: str
    ay: str
    itr_type: str
    filing_type: str = "original"
    income_data: dict
    notes: Optional[str] = None


class UpdateITRRequest(BaseModel):
    income_data: Optional[dict] = None
    status: Optional[str] = None
    acknowledgement_no: Optional[str] = None
    notes: Optional[str] = None


# ── TAX COMPUTATION ENGINES ────────────────────────────────────────────────────

def compute_old_regime_tax(taxable_income: float) -> float:
    tax = 0.0
    if taxable_income <= 250000:
        tax = 0
    elif taxable_income <= 500000:
        tax = (taxable_income - 250000) * 0.05
    elif taxable_income <= 1000000:
        tax = 12500 + (taxable_income - 500000) * 0.20
    else:
        tax = 112500 + (taxable_income - 1000000) * 0.30
    if taxable_income > 10000000:
        tax += tax * 0.15
    elif taxable_income > 5000000:
        tax += tax * 0.10
    tax += tax * 0.04
    if taxable_income <= 500000:
        tax = max(0, tax - 12500)
    return round(tax, 2)


def compute_new_regime_tax(taxable_income: float) -> float:
    tax = 0.0
    slabs = [(300000,0),(600000,0.05),(900000,0.10),(1200000,0.15),(1500000,0.20),(float('inf'),0.30)]
    prev = 0
    for limit, rate in slabs:
        if taxable_income <= limit:
            tax += (taxable_income - prev) * rate
            break
        tax += (limit - prev) * rate
        prev = limit
    tax += tax * 0.04
    if taxable_income <= 700000:
        tax = max(0, tax - 25000)
    return round(tax, 2)


def compute_itr1(data: dict) -> dict:
    d = ITR1IncomeData(**data)
    gross_salary = max(0, d.salary_income - d.hra_exemption - d.standard_deduction - d.other_allowances_exempt)
    gross_total = gross_salary + d.income_from_house_property + d.interest_income + d.other_income
    deductions = d.sec_80c + d.sec_80d + d.sec_80e + d.sec_80g + d.sec_80tta
    taxable_income = max(0, gross_total - (0 if d.new_tax_regime else deductions))
    gross_tax = compute_new_regime_tax(taxable_income) if d.new_tax_regime else compute_old_regime_tax(taxable_income)
    total_tds = d.tds_employer + d.tds_bank + d.tds_other
    tax_paid = total_tds + d.advance_tax + d.self_assessment_tax
    return {
        "gross_salary": round(gross_salary, 2),
        "gross_total_income": round(gross_total, 2),
        "total_deductions": round(deductions, 2),
        "taxable_income": round(taxable_income, 2),
        "gross_tax": gross_tax,
        "total_tds_paid": round(total_tds, 2),
        "tax_payable": round(max(0, gross_tax - tax_paid), 2),
        "refund_amount": round(max(0, tax_paid - gross_tax), 2),
        "regime": "New" if d.new_tax_regime else "Old",
        "recommended_regime": "New" if compute_new_regime_tax(taxable_income) < compute_old_regime_tax(taxable_income) else "Old"
    }


def compute_itr2(data: dict) -> dict:
    d = ITR2IncomeData(**data)
    net_salary = max(0, d.salary_income - d.hra_exemption - d.standard_deduction - d.other_allowances_exempt)
    sop_loss = min(d.self_occupied_loan_interest, 200000)
    let_out_net = d.annual_rental_value * 0.7 - d.let_out_loan_interest
    hp_net = d.house_property_income + let_out_net - sop_loss
    hp_setoff = max(-200000, hp_net)
    other = d.interest_income + d.dividend_income + d.other_income + d.foreign_income
    gross_total = net_salary + hp_setoff + other
    deductions = d.sec_80c + d.sec_80d + d.sec_80e + d.sec_80g + d.sec_80tta + d.sec_80ttb
    taxable_normal = max(0, gross_total - (0 if d.new_tax_regime else deductions))
    normal_tax = compute_new_regime_tax(taxable_normal) if d.new_tax_regime else compute_old_regime_tax(taxable_normal)
    # Capital gains taxes
    stcg_111a_tax = d.stcg_111a * 0.20
    stcg_other_tax = compute_old_regime_tax(taxable_normal + d.stcg_other) - compute_old_regime_tax(taxable_normal)
    ltcg_112a_tax = max(0, d.ltcg_112a - 125000) * 0.125
    ltcg_other_tax = d.ltcg_other * 0.20
    cg_tax = stcg_111a_tax + stcg_other_tax + ltcg_112a_tax + ltcg_other_tax
    ftc = min(d.foreign_tax_paid, d.foreign_income * 0.30)
    gross_tax = round((normal_tax + cg_tax - ftc) * 1.04, 2)
    gross_tax = max(0, gross_tax)
    tax_paid = d.tds_salary + d.tds_other + d.advance_tax + d.self_assessment_tax
    return {
        "net_salary": round(net_salary, 2),
        "house_property_income": round(hp_setoff, 2),
        "gross_total_income": round(gross_total, 2),
        "total_deductions": round(deductions, 2),
        "taxable_income_normal": round(taxable_normal, 2),
        "stcg_111a": d.stcg_111a,
        "stcg_other": d.stcg_other,
        "ltcg_112a": d.ltcg_112a,
        "ltcg_other": d.ltcg_other,
        "normal_tax": round(normal_tax, 2),
        "capital_gains_tax": round(cg_tax, 2),
        "foreign_tax_credit": round(ftc, 2),
        "gross_tax": gross_tax,
        "tax_paid": round(tax_paid, 2),
        "tax_payable": round(max(0, gross_tax - tax_paid), 2),
        "refund_amount": round(max(0, tax_paid - gross_tax), 2),
        "regime": "New" if d.new_tax_regime else "Old",
        "notes": ["STCG on equity @ 20%", "LTCG on equity @ 12.5% above ₹1.25L", "HP loss capped at ₹2L"]
    }


def compute_itr3(data: dict) -> dict:
    d = ITR3IncomeData(**data)
    net_business = d.business_income + d.profession_income - d.business_expenses - d.depreciation
    gross_total = net_business + d.speculative_income + d.capital_gains_stcg + d.capital_gains_ltcg + d.salary_income + d.house_property_income + d.other_income
    deductions = d.sec_80c + d.sec_80d + d.sec_80g
    taxable_income = max(0, gross_total - (0 if d.new_tax_regime else deductions))
    gross_tax = compute_new_regime_tax(taxable_income) if d.new_tax_regime else compute_old_regime_tax(taxable_income)
    stcg_tax = d.capital_gains_stcg * 0.15
    ltcg_tax = max(0, d.capital_gains_ltcg - 100000) * 0.10
    total_tax = gross_tax + stcg_tax + ltcg_tax
    tax_paid = d.tds_total + d.advance_tax + d.self_assessment_tax
    return {
        "net_business_income": round(net_business, 2),
        "gross_total_income": round(gross_total, 2),
        "taxable_income": round(taxable_income, 2),
        "gross_tax": round(total_tax, 2),
        "stcg_tax": round(stcg_tax, 2),
        "ltcg_tax": round(ltcg_tax, 2),
        "tax_paid": round(tax_paid, 2),
        "tax_payable": round(max(0, total_tax - tax_paid), 2),
        "refund_amount": round(max(0, tax_paid - total_tax), 2),
        "regime": "New" if d.new_tax_regime else "Old"
    }


def compute_itr4(data: dict) -> dict:
    d = ITR4IncomeData(**data)
    rates = {"44AD": 0.08, "44ADA": 0.50, "44AE": 0.075}
    presumptive = d.presumptive_income or round(d.gross_turnover * rates.get(d.section, 0.08), 2)
    gross_total = presumptive + d.other_income
    deductions = d.sec_80c + d.sec_80d
    taxable_income = max(0, gross_total - (0 if d.new_tax_regime else deductions))
    gross_tax = compute_new_regime_tax(taxable_income) if d.new_tax_regime else compute_old_regime_tax(taxable_income)
    tax_paid = d.tds_total + d.advance_tax + d.self_assessment_tax
    return {
        "section": d.section,
        "gross_turnover": d.gross_turnover,
        "presumptive_income": presumptive,
        "gross_total_income": round(gross_total, 2),
        "taxable_income": round(taxable_income, 2),
        "gross_tax": gross_tax,
        "tax_paid": round(tax_paid, 2),
        "tax_payable": round(max(0, gross_tax - tax_paid), 2),
        "refund_amount": round(max(0, tax_paid - gross_tax), 2),
        "regime": "New" if d.new_tax_regime else "Old"
    }


def compute_itr7(data: dict) -> dict:
    d = ITR7IncomeData(**data)
    total_income = d.gross_receipts + d.voluntary_contributions + d.business_income + d.investment_income
    anonymous_tax = d.anonymous_donations * 0.30
    if d.sec_13_violation:
        taxable_income = total_income
        shortfall = 0
    elif d.filing_section in ["139(4A)", "139(4C)"]:
        required = total_income * 0.85
        shortfall = max(0, required - d.applied_for_objects)
        sec11_exempt = min(d.applied_for_objects, total_income - d.corpus_donations)
        taxable_income = max(0, total_income - d.corpus_donations - sec11_exempt - d.sec_11_exemption)
    else:
        shortfall = 0
        taxable_income = max(0, total_income - d.sec_11_exemption - d.sec_12_exemption)
    normal_tax = taxable_income * 0.30 * 1.04
    total_tax = normal_tax + anonymous_tax
    tax_paid = d.tds_total + d.advance_tax + d.self_assessment_tax
    warnings = []
    if d.sec_13_violation:
        warnings.append("⚠️ Section 13 violation — full income taxable, exemption forfeited")
    if shortfall > 0:
        warnings.append(f"⚠️ Application shortfall ₹{shortfall:,.0f} — 85% rule not met")
    return {
        "entity_type": d.entity_type,
        "filing_section": d.filing_section,
        "total_income": round(total_income, 2),
        "corpus_donations_exempt": round(d.corpus_donations, 2),
        "income_applied": round(d.applied_for_objects, 2),
        "required_application_85pct": round(total_income * 0.85, 2),
        "shortfall": round(shortfall, 2) if not d.sec_13_violation else 0,
        "taxable_income": round(taxable_income, 2),
        "anonymous_donation_tax": round(anonymous_tax, 2),
        "normal_tax": round(normal_tax, 2),
        "gross_tax": round(total_tax, 2),
        "tax_paid": round(tax_paid, 2),
        "tax_payable": round(max(0, total_tax - tax_paid), 2),
        "refund_amount": round(max(0, tax_paid - total_tax), 2),
        "registration_no": d.registration_no,
        "warnings": [w for w in warnings if w]
    }


def _compute(itr_type: str, data: dict) -> dict:
    if itr_type == "ITR-1": return compute_itr1(data)
    elif itr_type == "ITR-2": return compute_itr2(data)
    elif itr_type == "ITR-3": return compute_itr3(data)
    elif itr_type == "ITR-4": return compute_itr4(data)
    elif itr_type == "ITR-7": return compute_itr7(data)
    raise HTTPException(400, "Supported types: ITR-1, ITR-2, ITR-3, ITR-4, ITR-7")


# ── ROUTES ─────────────────────────────────────────────────────────────────────

@router.get("/status")
async def status(current_user: CurrentUser = Depends(get_current_user)):
    return {
        "status": "ok",
        "module": "itr_filing",
        "supported": ["ITR-1", "ITR-2", "ITR-3", "ITR-4", "ITR-7"],
        "ay_available": ["2024-25", "2025-26"],
        "features": ["tax_computation", "old_vs_new_regime", "capital_gains", "trust_filing", "refund_calculator"]
    }


@router.post("/create")
async def create_itr(
    req: CreateITRRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    computation = _compute(req.itr_type, req.income_data)
    itr = ITRReturn(
        firm_id=current_user.firm_id,
        client_id=req.client_id,
        client_name=req.client_name,
        pan=req.pan.upper(),
        ay=req.ay,
        itr_type=req.itr_type,
        filing_type=req.filing_type,
        income_data=req.income_data,
        tax_computation=computation,
        tax_payable=computation.get("tax_payable", 0),
        refund_amount=computation.get("refund_amount", 0),
        notes=req.notes,
        created_by=current_user.user_id,
    )
    db.add(itr)
    await db.commit()
    await db.refresh(itr)
    return {"message": f"{req.itr_type} created for {req.client_name}", "itr": _itr_dict(itr)}


@router.get("/list")
async def list_itrs(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ay: Optional[str] = None
):
    q = select(ITRReturn).where(ITRReturn.firm_id == current_user.firm_id)
    if ay:
        q = q.where(ITRReturn.ay == ay)
    result = await db.execute(q.order_by(desc(ITRReturn.created_at)))
    records = result.scalars().all()
    return {"count": len(records), "returns": [_itr_dict(r) for r in records]}


@router.get("/dashboard/summary")
async def itr_dashboard(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ITRReturn).where(ITRReturn.firm_id == current_user.firm_id))
    all_itrs = result.scalars().all()
    return {
        "total_returns": len(all_itrs),
        "by_status": {s: sum(1 for i in all_itrs if i.status == s) for s in ["draft","ready","filed","verified"]},
        "by_type": {t: sum(1 for i in all_itrs if i.itr_type == t) for t in ["ITR-1","ITR-2","ITR-3","ITR-4","ITR-7"]},
        "total_refund_pending": round(sum(i.refund_amount for i in all_itrs if i.status != "verified"), 2),
        "total_tax_payable": round(sum(i.tax_payable for i in all_itrs if i.status == "draft"), 2),
    }


@router.get("/{itr_id}")
async def get_itr(itr_id: str, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    itr = await db.get(ITRReturn, itr_id)
    if not itr or itr.firm_id != current_user.firm_id:
        raise HTTPException(404, "ITR not found")
    return _itr_dict(itr)


@router.put("/{itr_id}")
async def update_itr(itr_id: str, req: UpdateITRRequest, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    itr = await db.get(ITRReturn, itr_id)
    if not itr or itr.firm_id != current_user.firm_id:
        raise HTTPException(404, "Not found")
    if req.income_data:
        itr.income_data = req.income_data
        itr.tax_computation = _compute(itr.itr_type, req.income_data)
        itr.tax_payable = itr.tax_computation.get("tax_payable", 0)
        itr.refund_amount = itr.tax_computation.get("refund_amount", 0)
    if req.status:
        itr.status = req.status
        if req.status == "filed": itr.filed_at = datetime.utcnow()
        if req.status == "verified": itr.verified_at = datetime.utcnow()
    if req.acknowledgement_no: itr.acknowledgement_no = req.acknowledgement_no
    if req.notes: itr.notes = req.notes
    await db.commit()
    await db.refresh(itr)
    return {"message": "ITR updated", "itr": _itr_dict(itr)}


@router.post("/regime-compare")
async def compare_regimes(
    itr_type: str,
    income_data: dict,
    current_user: CurrentUser = Depends(get_current_user)
):
    if itr_type == "ITR-7":
        raise HTTPException(400, "Regime comparison not applicable for ITR-7")
    old = _compute(itr_type, {**income_data, "new_tax_regime": False})
    new = _compute(itr_type, {**income_data, "new_tax_regime": True})
    saving = old.get("gross_tax", 0) - new.get("gross_tax", 0)
    return {
        "old_regime": old,
        "new_regime": new,
        "recommended": "New regime" if saving > 0 else "Old regime",
        "saving": abs(round(saving, 2)),
        "note": f"{'New' if saving > 0 else 'Old'} regime saves ₹{abs(round(saving, 2)):,.0f}"
    }


def _itr_dict(itr: ITRReturn) -> dict:
    return {
        "id": itr.id, "client_name": itr.client_name, "pan": itr.pan,
        "ay": itr.ay, "itr_type": itr.itr_type, "filing_type": itr.filing_type,
        "status": itr.status, "tax_payable": itr.tax_payable, "refund_amount": itr.refund_amount,
        "acknowledgement_no": itr.acknowledgement_no, "tax_computation": itr.tax_computation,
        "filed_at": itr.filed_at.isoformat() if itr.filed_at else None,
        "verified_at": itr.verified_at.isoformat() if itr.verified_at else None,
        "notes": itr.notes, "created_at": itr.created_at.isoformat()
    }
