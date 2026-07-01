"""
ITR Forms Generation Engine

Complete ITR-1, ITR-2, ITR-3 form generation with official tax calculations
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class ITRType(Enum):
    """ITR Form Types"""
    ITR_1 = "ITR-1"
    ITR_2 = "ITR-2"
    ITR_3 = "ITR-3"


class IncomeSource(Enum):
    """Income sources"""
    SALARY = "salary"
    HOUSE_PROPERTY = "house_property"
    CAPITAL_GAINS = "capital_gains"
    BUSINESS = "business"
    OTHER = "other"


# ═══════════════════════════════════════════════════════════════════════════
# ITR-1 (SARAL) - For Salary Earners
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SalaryIncome:
    """Salary income details"""
    gross_salary: float
    allowances: float = 0
    deductions: float = 0
    net_salary: float = 0


@dataclass
class HousePropertyIncome:
    """House property income/loss"""
    annual_value: float
    tax_paid: float = 0
    interest_paid: float = 0
    other_expenditure: float = 0
    net_income: float = 0


@dataclass
class OtherIncome:
    """Other income (interest, dividends, etc.)"""
    income_type: str
    amount: float
    tax_deducted: float = 0


class ITR1Calculator:
    """Calculate ITR-1 (SARAL) - For Salary Earners"""

    # Tax slabs for FY 2025-26 (India)
    TAX_SLABS = [
        (300000, 0),           # 0-3L: No tax
        (700000, 0.05),        # 3L-7L: 5%
        (1000000, 0.20),       # 7L-10L: 20%
        (float('inf'), 0.30),  # 10L+: 30%
    ]

    STANDARD_DEDUCTION = 50000  # Standard deduction for salaried individuals

    @staticmethod
    def calculate_taxable_income(
        salary: SalaryIncome,
        house_property: HousePropertyIncome,
        other_income: List[OtherIncome]
    ) -> Dict:
        """Calculate taxable income"""

        # Salary income (after standard deduction)
        salary_total = salary.gross_salary + salary.allowances - salary.deductions
        salary_after_deduction = max(0, salary_total - ITR1Calculator.STANDARD_DEDUCTION)

        # House property income
        house_property_net = house_property.annual_value - house_property.interest_paid - house_property.other_expenditure

        # Other income
        other_total = sum(oi.amount for oi in other_income)

        # Total income
        total_income = salary_after_deduction + house_property_net + other_total

        # Deductions (Section 80C, 80D, etc.)
        # Note: User should provide these separately
        deductions_80c = 150000  # Max ₹1.5L for 80C
        deductions_80d = 25000   # Health insurance
        deductions_other = 0     # Other deductions

        total_deductions = deductions_80c + deductions_80d + deductions_other

        # Taxable income
        taxable_income = max(0, total_income - total_deductions)

        return {
            "salary_income": round(salary_after_deduction, 2),
            "house_property_income": round(house_property_net, 2),
            "other_income": round(other_total, 2),
            "total_income": round(total_income, 2),
            "deductions": round(total_deductions, 2),
            "taxable_income": round(taxable_income, 2)
        }

    @staticmethod
    def calculate_income_tax(taxable_income: float) -> Dict:
        """Calculate income tax with surcharge and cess"""

        tax = 0
        previous_limit = 0

        # Calculate tax based on slabs
        for limit, rate in ITR1Calculator.TAX_SLABS:
            if taxable_income <= previous_limit:
                break

            income_in_slab = min(taxable_income, limit) - previous_limit
            tax += income_in_slab * rate
            previous_limit = limit

        # Health and Education Cess (4%)
        cess = tax * 0.04

        # Surcharge (varies based on income)
        surcharge = 0
        if taxable_income > 5000000:
            surcharge = tax * 0.25
        elif taxable_income > 2000000:
            surcharge = tax * 0.15
        elif taxable_income > 1000000:
            surcharge = tax * 0.10

        total_tax = tax + cess + surcharge

        return {
            "income_tax": round(tax, 2),
            "surcharge": round(surcharge, 2),
            "cess": round(cess, 2),
            "total_tax": round(total_tax, 2)
        }


class ITR1FormGenerator:
    """Generate ITR-1 (SARAL) Form"""

    @staticmethod
    def generate_form(
        pan: str,
        financial_year: int,
        salary: SalaryIncome,
        house_property: HousePropertyIncome,
        other_income: List[OtherIncome],
        tds_deducted: float = 0,
        advance_tax_paid: float = 0
    ) -> Dict:
        """Generate complete ITR-1 form"""

        # Calculate income
        income_calc = ITR1Calculator.calculate_taxable_income(salary, house_property, other_income)

        # Calculate tax
        tax_calc = ITR1Calculator.calculate_income_tax(income_calc["taxable_income"])

        # Tax reconciliation
        total_tax_payable = tax_calc["total_tax"]
        tax_paid = tds_deducted + advance_tax_paid
        tax_refund_or_payable = tax_paid - total_tax_payable

        fy_year = f"{financial_year-1}-{financial_year}"

        form = {
            "metadata": {
                "form_type": "ITR-1",
                "form_name": "SARAL",
                "pan": pan,
                "financial_year": fy_year,
                "filing_date": datetime.now().strftime("%Y-%m-%d"),
                "status": "NOT_FILED"
            },
            "section_1_income": {
                "salary": {
                    "gross_salary": round(salary.gross_salary, 2),
                    "allowances": round(salary.allowances, 2),
                    "deductions": round(salary.deductions, 2),
                    "taxable_salary": round(income_calc["salary_income"], 2)
                },
                "house_property": {
                    "annual_value": round(house_property.annual_value, 2),
                    "interest_paid": round(house_property.interest_paid, 2),
                    "other_expenditure": round(house_property.other_expenditure, 2),
                    "net_income": round(income_calc["house_property_income"], 2)
                },
                "other_income": {
                    "total": round(income_calc["other_income"], 2)
                },
                "total_income": round(income_calc["total_income"], 2)
            },
            "section_2_deductions": {
                "section_80c": 150000,  # Life insurance, PPF, etc.
                "section_80d": 25000,   # Health insurance
                "other_deductions": 0,
                "total_deductions": round(income_calc["deductions"], 2)
            },
            "section_3_taxable_income": {
                "total_income": round(income_calc["total_income"], 2),
                "deductions": round(income_calc["deductions"], 2),
                "taxable_income": round(income_calc["taxable_income"], 2)
            },
            "section_4_tax_calculation": {
                "income_tax": tax_calc["income_tax"],
                "surcharge": tax_calc["surcharge"],
                "health_education_cess": tax_calc["cess"],
                "total_tax": tax_calc["total_tax"]
            },
            "section_5_tax_reconciliation": {
                "total_tax_payable": round(total_tax_payable, 2),
                "tds_deducted": round(tds_deducted, 2),
                "advance_tax_paid": round(advance_tax_paid, 2),
                "total_tax_paid": round(tax_paid, 2),
                "refund_or_payable": round(tax_refund_or_payable, 2),
                "status": "REFUND" if tax_refund_or_payable > 0 else "PAYABLE" if tax_refund_or_payable < 0 else "NIL"
            }
        }

        return form


# ═══════════════════════════════════════════════════════════════════════════
# ITR-2 - For Capital Gains
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CapitalGain:
    """Capital gain/loss details"""
    asset_type: str  # property, shares, etc.
    cost_of_acquisition: float
    selling_price: float
    holding_period: int  # in years
    selling_date: str
    gain_or_loss: float = 0


class ITR2Calculator:
    """Calculate ITR-2 - For Capital Gains"""

    # Long-term vs short-term threshold: 2 years

    @staticmethod
    def categorize_gains(gains: List[CapitalGain]) -> Dict:
        """Categorize short-term and long-term gains"""

        short_term = []
        long_term = []

        for gain in gains:
            gain.gain_or_loss = gain.selling_price - gain.cost_of_acquisition
            if gain.holding_period >= 2:
                long_term.append(gain)
            else:
                short_term.append(gain)

        return {
            "short_term_gains": short_term,
            "long_term_gains": long_term,
            "total_short_term": sum(g.gain_or_loss for g in short_term),
            "total_long_term": sum(g.gain_or_loss for g in long_term)
        }

    @staticmethod
    def calculate_taxable_income(
        salary_income: float,
        house_property_income: float,
        capital_gains: Dict,
        other_income: float = 0,
        deductions: float = 0
    ) -> Dict:
        """Calculate taxable income including capital gains"""

        # Short-term capital gains (taxed at slab rate)
        stcg = capital_gains.get("total_short_term", 0)

        # Long-term capital gains (taxed at 20% + cess)
        ltcg = capital_gains.get("total_long_term", 0)

        # Total income
        total_income = salary_income + house_property_income + stcg + ltcg + other_income

        # Taxable income
        taxable_income = max(0, total_income - deductions)

        return {
            "salary_income": salary_income,
            "house_property_income": house_property_income,
            "short_term_capital_gains": stcg,
            "long_term_capital_gains": ltcg,
            "other_income": other_income,
            "total_income": round(total_income, 2),
            "deductions": deductions,
            "taxable_income": round(taxable_income, 2)
        }

    @staticmethod
    def calculate_income_tax(taxable_income: float, stcg: float) -> Dict:
        """Calculate tax on ITR-2"""

        # Tax on normal income (excluding STCG)
        normal_income = taxable_income - stcg

        # Use same slabs as ITR-1
        tax_slabs = [
            (300000, 0),
            (700000, 0.05),
            (1000000, 0.20),
            (float('inf'), 0.30),
        ]

        tax = 0
        previous_limit = 0

        for limit, rate in tax_slabs:
            if normal_income <= previous_limit:
                break
            income_in_slab = min(normal_income, limit) - previous_limit
            tax += income_in_slab * rate
            previous_limit = limit

        # Tax on STCG (at slab rate)
        stcg_tax = 0
        if stcg > 0:
            # STCG is added to total and taxed at applicable slab
            total_with_stcg = normal_income + stcg
            tax_with_stcg = 0
            previous_limit = 0
            for limit, rate in tax_slabs:
                if total_with_stcg <= previous_limit:
                    break
                income_in_slab = min(total_with_stcg, limit) - previous_limit
                tax_with_stcg += income_in_slab * rate
                previous_limit = limit
            stcg_tax = tax_with_stcg - tax

        total_tax = tax + stcg_tax

        # Cess
        cess = total_tax * 0.04

        # Surcharge
        surcharge = 0
        if taxable_income > 5000000:
            surcharge = total_tax * 0.25

        final_tax = total_tax + cess + surcharge

        return {
            "tax_on_normal_income": round(tax, 2),
            "tax_on_stcg": round(stcg_tax, 2),
            "total_income_tax": round(total_tax, 2),
            "surcharge": round(surcharge, 2),
            "cess": round(cess, 2),
            "final_tax": round(final_tax, 2)
        }


class ITR2FormGenerator:
    """Generate ITR-2 Form"""

    @staticmethod
    def generate_form(
        pan: str,
        financial_year: int,
        salary_income: float,
        house_property_income: float,
        capital_gains: List[CapitalGain],
        other_income: float = 0,
        tds_deducted: float = 0
    ) -> Dict:
        """Generate complete ITR-2 form"""

        # Categorize gains
        gains_calc = ITR2Calculator.categorize_gains(capital_gains)

        # Calculate income
        income_calc = ITR2Calculator.calculate_taxable_income(
            salary_income,
            house_property_income,
            gains_calc,
            other_income
        )

        # Calculate tax
        tax_calc = ITR2Calculator.calculate_income_tax(
            income_calc["taxable_income"],
            gains_calc.get("total_short_term", 0)
        )

        fy_year = f"{financial_year-1}-{financial_year}"

        form = {
            "metadata": {
                "form_type": "ITR-2",
                "pan": pan,
                "financial_year": fy_year,
                "filing_date": datetime.now().strftime("%Y-%m-%d"),
                "status": "NOT_FILED"
            },
            "section_1_income": {
                "salary_income": round(salary_income, 2),
                "house_property_income": round(house_property_income, 2),
                "short_term_capital_gains": round(gains_calc.get("total_short_term", 0), 2),
                "long_term_capital_gains": round(gains_calc.get("total_long_term", 0), 2),
                "other_income": round(other_income, 2),
                "total_income": income_calc["total_income"]
            },
            "section_2_capital_gains_details": {
                "short_term_gains": [
                    {
                        "asset": g.asset_type,
                        "cost": round(g.cost_of_acquisition, 2),
                        "selling_price": round(g.selling_price, 2),
                        "gain_loss": round(g.gain_or_loss, 2)
                    }
                    for g in gains_calc["short_term_gains"]
                ],
                "long_term_gains": [
                    {
                        "asset": g.asset_type,
                        "cost": round(g.cost_of_acquisition, 2),
                        "selling_price": round(g.selling_price, 2),
                        "gain_loss": round(g.gain_or_loss, 2)
                    }
                    for g in gains_calc["long_term_gains"]
                ]
            },
            "section_3_tax_calculation": tax_calc,
            "section_4_tax_reconciliation": {
                "total_tax_payable": tax_calc["final_tax"],
                "tds_deducted": round(tds_deducted, 2),
                "balance": round(tax_calc["final_tax"] - tds_deducted, 2)
            }
        }

        return form


# ═══════════════════════════════════════════════════════════════════════════
# ITR-3 - For Business Income
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class BusinessExpense:
    """Business expense details"""
    expense_type: str
    amount: float


@dataclass
class BusinessIncome:
    """Business income details"""
    gross_receipts: float
    cost_of_goods_sold: float = 0
    operating_expenses: List[BusinessExpense] = None
    net_profit: float = 0


class ITR3Calculator:
    """Calculate ITR-3 - For Business Income"""

    @staticmethod
    def calculate_net_profit(business: BusinessIncome) -> float:
        """Calculate net profit from business"""

        gross_profit = business.gross_receipts - business.cost_of_goods_sold
        total_expenses = sum(e.amount for e in (business.operating_expenses or []))
        net_profit = gross_profit - total_expenses

        return max(0, net_profit)

    @staticmethod
    def calculate_taxable_income(
        business_income: float,
        salary_income: float = 0,
        house_property_income: float = 0,
        other_income: float = 0,
        deductions: float = 0
    ) -> Dict:
        """Calculate taxable income including business"""

        total_income = business_income + salary_income + house_property_income + other_income
        taxable_income = max(0, total_income - deductions)

        return {
            "business_income": round(business_income, 2),
            "salary_income": round(salary_income, 2),
            "house_property_income": round(house_property_income, 2),
            "other_income": round(other_income, 2),
            "total_income": round(total_income, 2),
            "deductions": round(deductions, 2),
            "taxable_income": round(taxable_income, 2)
        }

    @staticmethod
    def calculate_income_tax(taxable_income: float) -> Dict:
        """Calculate tax for ITR-3"""

        # Use same slabs
        tax_slabs = [
            (300000, 0),
            (700000, 0.05),
            (1000000, 0.20),
            (float('inf'), 0.30),
        ]

        tax = 0
        previous_limit = 0

        for limit, rate in tax_slabs:
            if taxable_income <= previous_limit:
                break
            income_in_slab = min(taxable_income, limit) - previous_limit
            tax += income_in_slab * rate
            previous_limit = limit

        cess = tax * 0.04

        surcharge = 0
        if taxable_income > 5000000:
            surcharge = tax * 0.25
        elif taxable_income > 2000000:
            surcharge = tax * 0.15
        elif taxable_income > 1000000:
            surcharge = tax * 0.10

        total_tax = tax + cess + surcharge

        return {
            "income_tax": round(tax, 2),
            "surcharge": round(surcharge, 2),
            "cess": round(cess, 2),
            "total_tax": round(total_tax, 2)
        }


class ITR3FormGenerator:
    """Generate ITR-3 Form"""

    @staticmethod
    def generate_form(
        pan: str,
        financial_year: int,
        business: BusinessIncome,
        salary_income: float = 0,
        house_property_income: float = 0,
        other_income: float = 0,
        tds_deducted: float = 0
    ) -> Dict:
        """Generate complete ITR-3 form"""

        # Calculate net profit
        net_profit = ITR3Calculator.calculate_net_profit(business)

        # Calculate income
        income_calc = ITR3Calculator.calculate_taxable_income(
            net_profit,
            salary_income,
            house_property_income,
            other_income
        )

        # Calculate tax
        tax_calc = ITR3Calculator.calculate_income_tax(income_calc["taxable_income"])

        fy_year = f"{financial_year-1}-{financial_year}"

        form = {
            "metadata": {
                "form_type": "ITR-3",
                "pan": pan,
                "financial_year": fy_year,
                "filing_date": datetime.now().strftime("%Y-%m-%d"),
                "status": "NOT_FILED"
            },
            "section_1_business_details": {
                "gross_receipts": round(business.gross_receipts, 2),
                "cost_of_goods_sold": round(business.cost_of_goods_sold, 2),
                "gross_profit": round(business.gross_receipts - business.cost_of_goods_sold, 2),
                "operating_expenses": [
                    {"type": e.expense_type, "amount": round(e.amount, 2)}
                    for e in (business.operating_expenses or [])
                ],
                "total_expenses": round(sum(e.amount for e in (business.operating_expenses or [])), 2),
                "net_profit": round(net_profit, 2)
            },
            "section_2_other_income": {
                "salary_income": round(salary_income, 2),
                "house_property_income": round(house_property_income, 2),
                "other_income": round(other_income, 2)
            },
            "section_3_total_income": income_calc,
            "section_4_tax_calculation": tax_calc,
            "section_5_tax_reconciliation": {
                "total_tax_payable": tax_calc["total_tax"],
                "tds_deducted": round(tds_deducted, 2),
                "balance": round(tax_calc["total_tax"] - tds_deducted, 2)
            }
        }

        return form
