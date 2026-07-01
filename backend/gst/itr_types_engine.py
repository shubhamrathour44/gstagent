"""
ITR (Income Tax Return) Types Engine

Handles all Indian income tax return types with filing deadlines,
applicable categories, and compliance tracking.
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class ITRType(Enum):
    """All ITR types for Indian taxpayers"""
    ITR_1 = "SARAL"           # Individuals with salary, pension, etc.
    ITR_2 = "ITR_2"           # Individuals with capital gains
    ITR_3 = "PROPRIETORSHIP"  # Individuals with business/profession
    ITR_4 = "SUGAM"           # Business with <2Cr turnover (optional)
    ITR_5 = "ITR_5"           # Partnerships
    ITR_6 = "ITR_6"           # Companies (not covered by ITR-7)
    ITR_7 = "ITR_7"           # Trusts and organizations


class ITRFrequency(Enum):
    """Filing frequency"""
    ANNUAL = "annual"


class ITRApplicability(Enum):
    """Who can file each ITR"""
    INDIVIDUALS = "individuals"
    BUSINESS = "business"
    PARTNERSHIP = "partnership"
    COMPANY = "company"
    TRUST = "trust"


@dataclass
class ITRDetails:
    """ITR type configuration"""
    code: str
    name: str
    description: str
    frequency: ITRFrequency
    due_date_day: int
    due_date_month: int
    applicable_to: str
    fields: List[str]
    key_details: Dict[str, str]
    income_limit_min: float
    income_limit_max: Optional[float]
    penalty_per_day: float  # Penalty per day for late filing


class ITRTypesEngine:
    """ITR return type management and scheduling"""

    # Annual rate for penalty: 5% per annum = 0.0001370% per day
    PENALTY_RATE = 0.000137

    ITR_CONFIGURATIONS = {
        ITRType.ITR_1: ITRDetails(
            code="ITR-1",
            name="SARAL",
            description="For individuals with salary, pension, one house property, and other income",
            frequency=ITRFrequency.ANNUAL,
            due_date_day=31,
            due_date_month=7,
            applicable_to="Individuals with salary/pension and house property",
            fields=["Income from salary", "Income from house property", "Other income", "Deductions"],
            key_details={
                "Applicable Income Limit": "Income up to Rs. 50 lakhs",
                "Applicable Age": "All ages",
                "Can file if": "No business or profession income, single house property"
            },
            income_limit_min=0,
            income_limit_max=5000000,
            penalty_per_day=0.137
        ),
        ITRType.ITR_2: ITRDetails(
            code="ITR-2",
            name="ITR-2",
            description="For individuals with capital gains and other sources of income",
            frequency=ITRFrequency.ANNUAL,
            due_date_day=31,
            due_date_month=7,
            applicable_to="Individuals with capital gains or multiple income sources",
            fields=["Capital gains", "Income from other sources", "Deductions"],
            key_details={
                "Applicable Income Limit": "Income up to Rs. 50 lakhs",
                "Applicable Age": "All ages",
                "Can file if": "No business income, capital gains present"
            },
            income_limit_min=0,
            income_limit_max=5000000,
            penalty_per_day=0.137
        ),
        ITRType.ITR_3: ITRDetails(
            code="ITR-3",
            name="PROPRIETORSHIP",
            description="For individuals with business or profession income",
            frequency=ITRFrequency.ANNUAL,
            due_date_day=30,
            due_date_month=9,
            applicable_to="Sole proprietors and professionals",
            fields=["Business income", "Profit & loss statement", "Balance sheet", "Schedule for income"],
            key_details={
                "Applicable Income Limit": "No income limit",
                "Applicable Age": "All ages",
                "Can file if": "Has business or profession income"
            },
            income_limit_min=0,
            income_limit_max=None,
            penalty_per_day=0.137
        ),
        ITRType.ITR_4: ITRDetails(
            code="ITR-4",
            name="SUGAM",
            description="Simplified return for business with presumptive income",
            frequency=ITRFrequency.ANNUAL,
            due_date_day=30,
            due_date_month=9,
            applicable_to="Business with turnover <2 Crores (optional for them)",
            fields=["Business turnover", "Presumptive income", "Deductions"],
            key_details={
                "Applicable Income Limit": "Business turnover <Rs. 2 crores",
                "Applicable Age": "All ages",
                "Can file if": "Has business income, turnover <2Cr (optional for ITR-3 filers)"
            },
            income_limit_min=0,
            income_limit_max=20000000,
            penalty_per_day=0.137
        ),
        ITRType.ITR_5: ITRDetails(
            code="ITR-5",
            name="ITR-5",
            description="For partnerships, LLPs, and associations of persons",
            frequency=ITRFrequency.ANNUAL,
            due_date_day=30,
            due_date_month=9,
            applicable_to="Partnership firms and LLPs",
            fields=["Partnership income", "Balance sheet", "Profit & loss"],
            key_details={
                "Applicable Entities": "Partnerships, LLPs, AOP",
                "Applicable Income Limit": "No income limit",
                "Can file if": "Partnership or LLP entity"
            },
            income_limit_min=0,
            income_limit_max=None,
            penalty_per_day=0.137
        ),
        ITRType.ITR_6: ITRDetails(
            code="ITR-6",
            name="ITR-6",
            description="For companies not covered by ITR-7",
            frequency=ITRFrequency.ANNUAL,
            due_date_day=30,
            due_date_month=9,
            applicable_to="Corporate entities",
            fields=["Company income", "Balance sheet", "Profit & loss", "Tax computed"],
            key_details={
                "Applicable Entities": "Companies (not covered by ITR-7)",
                "Applicable Income Limit": "No income limit",
                "Can file if": "Registered company"
            },
            income_limit_min=0,
            income_limit_max=None,
            penalty_per_day=0.137
        ),
        ITRType.ITR_7: ITRDetails(
            code="ITR-7",
            name="ITR-7",
            description="For trusts, associations, and institutions",
            frequency=ITRFrequency.ANNUAL,
            due_date_day=30,
            due_date_month=9,
            applicable_to="Trusts, NGOs, and charitable organizations",
            fields=["Trust income", "Schedule of income", "Balance sheet"],
            key_details={
                "Applicable Entities": "Trusts, NGOs, educational institutions",
                "Applicable Income Limit": "No income limit",
                "Can file if": "Registered trust or organization"
            },
            income_limit_min=0,
            income_limit_max=None,
            penalty_per_day=0.137
        ),
    }

    @staticmethod
    def get_return_config(return_type: ITRType) -> ITRDetails:
        """Get configuration for specific ITR type"""
        return ITRTypesEngine.ITR_CONFIGURATIONS.get(return_type)

    @staticmethod
    def get_return_summary(return_type: ITRType) -> Dict:
        """Get summary of ITR type with all details"""
        config = ITRTypesEngine.get_return_config(return_type)
        if not config:
            raise ValueError(f"Unknown ITR type: {return_type}")

        return {
            "return_type": config.code,
            "name": config.name,
            "description": config.description,
            "frequency": config.frequency.value,
            "due_date_day": config.due_date_day,
            "due_date_month": config.due_date_month,
            "applicable_to": config.applicable_to,
            "fields": config.fields,
            "key_details": config.key_details,
            "income_limit": {
                "minimum": config.income_limit_min,
                "maximum": config.income_limit_max
            },
            "penalty_per_day": config.penalty_per_day
        }

    @staticmethod
    def get_due_date(return_type: ITRType, financial_year: int) -> str:
        """
        Get due date for ITR filing
        Financial year: 2026 = FY 2025-26 (Apr 2025 - Mar 2026)
        Due date is in next financial year
        """
        config = ITRTypesEngine.get_return_config(return_type)
        if not config:
            raise ValueError(f"Unknown ITR type: {return_type}")

        # ITR for FY 2025-26 is due on 31 July 2026
        due_date = datetime(financial_year, config.due_date_month, config.due_date_day)
        return due_date.strftime("%Y-%m-%d")

    @staticmethod
    def get_all_returns_for_fy(financial_year: int) -> Dict:
        """Get all ITR types and their due dates for a financial year"""
        returns = {}
        for itr_type in ITRType:
            config = ITRTypesEngine.get_return_config(itr_type)
            due_date = ITRTypesEngine.get_due_date(itr_type, financial_year)

            returns[config.code] = {
                "return_type": config.code,
                "name": config.name,
                "due_date": due_date,
                "frequency": config.frequency.value,
                "applicable_to": config.applicable_to,
                "description": config.description
            }

        return returns

    @staticmethod
    def get_filing_calendar(financial_year: int) -> Dict:
        """Get complete ITR filing calendar for a financial year"""
        calendar = {}

        for itr_type in ITRType:
            config = ITRTypesEngine.get_return_config(itr_type)
            due_date = ITRTypesEngine.get_due_date(itr_type, financial_year)

            # Create period label (FY 2025-26)
            fy_label = f"FY {financial_year-1}-{financial_year}"

            if fy_label not in calendar:
                calendar[fy_label] = {}

            calendar[fy_label][config.code] = {
                "return_type": config.code,
                "name": config.name,
                "due_date": due_date,
                "frequency": config.frequency.value,
                "applicable_to": config.applicable_to,
                "penalty_per_day": config.penalty_per_day
            }

        return calendar

    @staticmethod
    def calculate_penalty(amount: float, days_late: int) -> float:
        """Calculate penalty for late ITR filing"""
        # Penalty: 5% per annum
        penalty = amount * ITRTypesEngine.PENALTY_RATE * days_late
        return round(penalty, 2)

    @staticmethod
    def get_applicable_itrs(income_sources: List[str], entity_type: str) -> List[str]:
        """
        Determine applicable ITRs based on income sources and entity type

        Args:
            income_sources: List of income sources (e.g., ['salary', 'capital_gains'])
            entity_type: Type of entity (individual, partnership, company, trust)

        Returns:
            List of applicable ITR codes
        """
        applicable = []

        if entity_type == "individual":
            if 'salary' in income_sources and 'house_property' in income_sources:
                if not any(x in income_sources for x in ['business', 'capital_gains']):
                    applicable.append("ITR-1")

            if 'capital_gains' in income_sources:
                applicable.append("ITR-2")

            if 'business' in income_sources or 'profession' in income_sources:
                applicable.append("ITR-3")
                if 'turnover' in income_sources:
                    applicable.append("ITR-4")

        elif entity_type == "partnership":
            applicable.append("ITR-5")
        elif entity_type == "company":
            applicable.append("ITR-6")
        elif entity_type == "trust":
            applicable.append("ITR-7")

        return applicable if applicable else ["ITR-1"]  # Default to ITR-1

    @staticmethod
    def get_itr_checklist(itr_type: ITRType) -> Dict:
        """Get checklist of documents required for ITR filing"""
        config = ITRTypesEngine.get_return_config(itr_type)

        checklist = {
            "return_type": config.code,
            "documents_required": [],
            "deadlines": {}
        }

        # Common documents
        common_docs = [
            "PAN Card",
            "Aadhaar Card",
            "Bank statements",
            "Investment proofs"
        ]

        if config.code == "ITR-1":
            checklist["documents_required"] = common_docs + [
                "Salary slips",
                "Form 16",
                "Property documents"
            ]

        elif config.code == "ITR-2":
            checklist["documents_required"] = common_docs + [
                "Capital gains documents",
                "Investment proof"
            ]

        elif config.code in ["ITR-3", "ITR-4"]:
            checklist["documents_required"] = common_docs + [
                "Business profit & loss",
                "Balance sheet",
                "Audit report"
            ]

        elif config.code == "ITR-5":
            checklist["documents_required"] = common_docs + [
                "Partnership deed",
                "Balance sheet",
                "Profit & loss"
            ]

        elif config.code == "ITR-6":
            checklist["documents_required"] = common_docs + [
                "Balance sheet",
                "Profit & loss",
                "Audit report"
            ]

        elif config.code == "ITR-7":
            checklist["documents_required"] = common_docs + [
                "Trust deed",
                "Balance sheet",
                "Audit report"
            ]

        return checklist
