"""
ITR Forms API Router

Endpoints for generating ITR-1, ITR-2, ITR-3 forms
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from gst.itr_forms_engine import (
    ITR1FormGenerator, ITR1Calculator, SalaryIncome, HousePropertyIncome, OtherIncome,
    ITR2FormGenerator, ITR2Calculator, CapitalGain,
    ITR3FormGenerator, ITR3Calculator, BusinessIncome, BusinessExpense
)

itr_forms_router = APIRouter(prefix="/itr-forms", tags=["ITR Forms"])


# ═══════════════════════════════════════════════════════════════════════════
# REQUEST MODELS
# ═══════════════════════════════════════════════════════════════════════════

class SalaryIncomeRequest(BaseModel):
    gross_salary: float
    allowances: float = 0
    deductions: float = 0


class HousePropertyRequest(BaseModel):
    annual_value: float
    tax_paid: float = 0
    interest_paid: float = 0
    other_expenditure: float = 0


class OtherIncomeRequest(BaseModel):
    income_type: str
    amount: float
    tax_deducted: float = 0


class ITR1GenerateRequest(BaseModel):
    pan: str
    financial_year: int
    salary: SalaryIncomeRequest
    house_property: HousePropertyRequest
    other_income: List[OtherIncomeRequest] = []
    tds_deducted: float = 0
    advance_tax_paid: float = 0


class CapitalGainRequest(BaseModel):
    asset_type: str
    cost_of_acquisition: float
    selling_price: float
    holding_period: int
    selling_date: str


class ITR2GenerateRequest(BaseModel):
    pan: str
    financial_year: int
    salary_income: float = 0
    house_property_income: float = 0
    capital_gains: List[CapitalGainRequest]
    other_income: float = 0
    tds_deducted: float = 0


class BusinessExpenseRequest(BaseModel):
    expense_type: str
    amount: float


class BusinessIncomeRequest(BaseModel):
    gross_receipts: float
    cost_of_goods_sold: float = 0
    operating_expenses: List[BusinessExpenseRequest] = []


class ITR3GenerateRequest(BaseModel):
    pan: str
    financial_year: int
    business: BusinessIncomeRequest
    salary_income: float = 0
    house_property_income: float = 0
    other_income: float = 0
    tds_deducted: float = 0


# ═══════════════════════════════════════════════════════════════════════════
# ITR-1 ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@itr_forms_router.post("/itr1/generate")
async def generate_itr1(request: ITR1GenerateRequest):
    """Generate ITR-1 (SARAL) Form for Salary Earners"""
    try:
        salary = SalaryIncome(
            gross_salary=request.salary.gross_salary,
            allowances=request.salary.allowances,
            deductions=request.salary.deductions
        )

        house_property = HousePropertyIncome(
            annual_value=request.house_property.annual_value,
            tax_paid=request.house_property.tax_paid,
            interest_paid=request.house_property.interest_paid,
            other_expenditure=request.house_property.other_expenditure
        )

        other_income = [
            OtherIncome(
                income_type=oi.income_type,
                amount=oi.amount,
                tax_deducted=oi.tax_deducted
            )
            for oi in request.other_income
        ]

        form = ITR1FormGenerator.generate_form(
            pan=request.pan,
            financial_year=request.financial_year,
            salary=salary,
            house_property=house_property,
            other_income=other_income,
            tds_deducted=request.tds_deducted,
            advance_tax_paid=request.advance_tax_paid
        )

        return {
            "status": "success",
            "form": form
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@itr_forms_router.post("/itr1/calculate")
async def calculate_itr1(request: ITR1GenerateRequest):
    """Calculate ITR-1 tax only"""
    try:
        salary = SalaryIncome(
            gross_salary=request.salary.gross_salary,
            allowances=request.salary.allowances,
            deductions=request.salary.deductions
        )

        house_property = HousePropertyIncome(
            annual_value=request.house_property.annual_value,
            interest_paid=request.house_property.interest_paid,
            other_expenditure=request.house_property.other_expenditure
        )

        other_income = [
            OtherIncome(income_type=oi.income_type, amount=oi.amount)
            for oi in request.other_income
        ]

        income = ITR1Calculator.calculate_taxable_income(salary, house_property, other_income)
        tax = ITR1Calculator.calculate_income_tax(income["taxable_income"])

        return {
            "status": "success",
            "income_calculation": income,
            "tax_calculation": tax
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# ITR-2 ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@itr_forms_router.post("/itr2/generate")
async def generate_itr2(request: ITR2GenerateRequest):
    """Generate ITR-2 Form for Capital Gains"""
    try:
        capital_gains = [
            CapitalGain(
                asset_type=cg.asset_type,
                cost_of_acquisition=cg.cost_of_acquisition,
                selling_price=cg.selling_price,
                holding_period=cg.holding_period,
                selling_date=cg.selling_date
            )
            for cg in request.capital_gains
        ]

        form = ITR2FormGenerator.generate_form(
            pan=request.pan,
            financial_year=request.financial_year,
            salary_income=request.salary_income,
            house_property_income=request.house_property_income,
            capital_gains=capital_gains,
            other_income=request.other_income,
            tds_deducted=request.tds_deducted
        )

        return {
            "status": "success",
            "form": form
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@itr_forms_router.post("/itr2/calculate")
async def calculate_itr2(request: ITR2GenerateRequest):
    """Calculate ITR-2 tax only"""
    try:
        capital_gains = [
            CapitalGain(
                asset_type=cg.asset_type,
                cost_of_acquisition=cg.cost_of_acquisition,
                selling_price=cg.selling_price,
                holding_period=cg.holding_period,
                selling_date=cg.selling_date
            )
            for cg in request.capital_gains
        ]

        gains_calc = ITR2Calculator.categorize_gains(capital_gains)
        income = ITR2Calculator.calculate_taxable_income(
            request.salary_income,
            request.house_property_income,
            gains_calc,
            request.other_income
        )
        tax = ITR2Calculator.calculate_income_tax(
            income["taxable_income"],
            gains_calc.get("total_short_term", 0)
        )

        return {
            "status": "success",
            "gains_categorization": {
                "short_term": round(gains_calc.get("total_short_term", 0), 2),
                "long_term": round(gains_calc.get("total_long_term", 0), 2)
            },
            "income_calculation": income,
            "tax_calculation": tax
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# ITR-3 ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@itr_forms_router.post("/itr3/generate")
async def generate_itr3(request: ITR3GenerateRequest):
    """Generate ITR-3 Form for Business Income"""
    try:
        expenses = [
            BusinessExpense(
                expense_type=exp.expense_type,
                amount=exp.amount
            )
            for exp in request.business.operating_expenses
        ]

        business = BusinessIncome(
            gross_receipts=request.business.gross_receipts,
            cost_of_goods_sold=request.business.cost_of_goods_sold,
            operating_expenses=expenses
        )

        form = ITR3FormGenerator.generate_form(
            pan=request.pan,
            financial_year=request.financial_year,
            business=business,
            salary_income=request.salary_income,
            house_property_income=request.house_property_income,
            other_income=request.other_income,
            tds_deducted=request.tds_deducted
        )

        return {
            "status": "success",
            "form": form
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@itr_forms_router.post("/itr3/calculate")
async def calculate_itr3(request: ITR3GenerateRequest):
    """Calculate ITR-3 tax only"""
    try:
        expenses = [
            BusinessExpense(expense_type=exp.expense_type, amount=exp.amount)
            for exp in request.business.operating_expenses
        ]

        business = BusinessIncome(
            gross_receipts=request.business.gross_receipts,
            cost_of_goods_sold=request.business.cost_of_goods_sold,
            operating_expenses=expenses
        )

        net_profit = ITR3Calculator.calculate_net_profit(business)
        income = ITR3Calculator.calculate_taxable_income(
            net_profit,
            request.salary_income,
            request.house_property_income,
            request.other_income
        )
        tax = ITR3Calculator.calculate_income_tax(income["taxable_income"])

        return {
            "status": "success",
            "business_summary": {
                "gross_receipts": round(request.business.gross_receipts, 2),
                "cost_of_goods_sold": round(request.business.cost_of_goods_sold, 2),
                "total_expenses": round(sum(e.amount for e in expenses), 2),
                "net_profit": round(net_profit, 2)
            },
            "income_calculation": income,
            "tax_calculation": tax
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# DEMO & STATUS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@itr_forms_router.get("/itr1/demo/{pan}")
async def get_itr1_demo(pan: str, financial_year: int = 2026):
    """Get demo ITR-1 form"""
    try:
        salary = SalaryIncome(
            gross_salary=1200000,
            allowances=100000,
            deductions=50000
        )

        house_property = HousePropertyIncome(
            annual_value=200000,
            interest_paid=50000,
            other_expenditure=10000
        )

        other_income = [
            OtherIncome(income_type="Interest", amount=5000, tax_deducted=500)
        ]

        form = ITR1FormGenerator.generate_form(
            pan=pan,
            financial_year=financial_year,
            salary=salary,
            house_property=house_property,
            other_income=other_income,
            tds_deducted=50000,
            advance_tax_paid=0
        )

        return {
            "status": "success",
            "form": form,
            "note": "This is demo data for testing ITR-1"
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@itr_forms_router.get("/itr2/demo/{pan}")
async def get_itr2_demo(pan: str, financial_year: int = 2026):
    """Get demo ITR-2 form"""
    try:
        capital_gains = [
            CapitalGain(
                asset_type="Shares",
                cost_of_acquisition=100000,
                selling_price=150000,
                holding_period=1,
                selling_date="2026-03-31"
            ),
            CapitalGain(
                asset_type="Property",
                cost_of_acquisition=1000000,
                selling_price=1300000,
                holding_period=5,
                selling_date="2026-02-15"
            )
        ]

        form = ITR2FormGenerator.generate_form(
            pan=pan,
            financial_year=financial_year,
            salary_income=800000,
            house_property_income=100000,
            capital_gains=capital_gains,
            other_income=10000,
            tds_deducted=30000
        )

        return {
            "status": "success",
            "form": form,
            "note": "This is demo data for testing ITR-2"
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@itr_forms_router.get("/itr3/demo/{pan}")
async def get_itr3_demo(pan: str, financial_year: int = 2026):
    """Get demo ITR-3 form"""
    try:
        business = BusinessIncome(
            gross_receipts=5000000,
            cost_of_goods_sold=2000000,
            operating_expenses=[
                BusinessExpense(expense_type="Salary", amount=500000),
                BusinessExpense(expense_type="Rent", amount=300000),
                BusinessExpense(expense_type="Utilities", amount=50000),
                BusinessExpense(expense_type="Depreciation", amount=100000),
            ]
        )

        form = ITR3FormGenerator.generate_form(
            pan=pan,
            financial_year=financial_year,
            business=business,
            salary_income=0,
            house_property_income=50000,
            other_income=5000,
            tds_deducted=100000
        )

        return {
            "status": "success",
            "form": form,
            "note": "This is demo data for testing ITR-3"
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@itr_forms_router.get("/status")
async def itr_forms_status():
    """Get ITR Forms module status"""
    return {
        "status": "ACTIVE",
        "forms": ["ITR-1", "ITR-2", "ITR-3"],
        "itr1_endpoints": 2,
        "itr2_endpoints": 2,
        "itr3_endpoints": 2,
        "demo_endpoints": 3,
        "total_endpoints": 9,
        "version": "1.0.0"
    }
