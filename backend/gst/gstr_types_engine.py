"""
GST Return Types Engine

Supports all GST return types:
- GSTR-1: Sales invoices (Regular traders)
- GSTR-2: Purchases (Regular traders)
- GSTR-3: Summary before 3B (Regular traders)
- GSTR-3B: Summary with tax (Regular traders)
- GSTR-4: Simplified return (Composite traders)
- GSTR-5: Non-resident suppliers
- GSTR-6: Input Service Distribution
- GSTR-7: TDS on E-commerce
- GSTR-8: TCS on E-commerce
- GSTR-9: Annual return
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum
from datetime import datetime, timedelta


class ReturnType(str, Enum):
    """GST Return Types"""
    GSTR_1 = "GSTR-1"      # Sales invoices
    GSTR_2 = "GSTR-2"      # Purchases
    GSTR_3 = "GSTR-3"      # Summary
    GSTR_3B = "GSTR-3B"    # Tax summary
    GSTR_4 = "GSTR-4"      # Simplified (Composite)
    GSTR_5 = "GSTR-5"      # Non-resident
    GSTR_6 = "GSTR-6"      # ISD
    GSTR_7 = "GSTR-7"      # TDS
    GSTR_8 = "GSTR-8"      # TCS
    GSTR_9 = "GSTR-9"      # Annual


class ReturnFrequency(str, Enum):
    """Filing Frequency"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    HALF_YEARLY = "half_yearly"
    ANNUAL = "annual"


@dataclass
class ReturnDetails:
    """Details for each return type"""
    return_type: ReturnType
    frequency: ReturnFrequency
    due_date_day: int
    applicable_to: str
    description: str
    fields: List[str]


class GSTReturnTypesEngine:
    """Manages different GST return types and their details"""

    # Return type configurations
    RETURN_CONFIGS = {
        ReturnType.GSTR_1: ReturnDetails(
            return_type=ReturnType.GSTR_1,
            frequency=ReturnFrequency.MONTHLY,
            due_date_day=11,
            applicable_to="All registered traders",
            description="Details of outward supplies",
            fields=["B2B invoices", "B2C", "Exports", "HSN summary"]
        ),
        ReturnType.GSTR_2: ReturnDetails(
            return_type=ReturnType.GSTR_2,
            frequency=ReturnFrequency.MONTHLY,
            due_date_day=15,
            applicable_to="All registered traders",
            description="Details of inward supplies",
            fields=["Purchase invoices", "ITC eligible", "Payment status"]
        ),
        ReturnType.GSTR_3: ReturnDetails(
            return_type=ReturnType.GSTR_3,
            frequency=ReturnFrequency.MONTHLY,
            due_date_day=20,
            applicable_to="All registered traders (OPTIONAL)",
            description="Summary before GSTR-3B",
            fields=["Outward supplies", "Inward supplies", "Provisional ITC"]
        ),
        ReturnType.GSTR_3B: ReturnDetails(
            return_type=ReturnType.GSTR_3B,
            frequency=ReturnFrequency.MONTHLY,
            due_date_day=20,
            applicable_to="All registered traders",
            description="Summary with tax liability",
            fields=["Output tax", "Input tax", "Tax payable", "Refund"]
        ),
        ReturnType.GSTR_4: ReturnDetails(
            return_type=ReturnType.GSTR_4,
            frequency=ReturnFrequency.QUARTERLY,
            due_date_day=18,
            applicable_to="Composite traders (turnover ≤ ₹1.5 Cr)",
            description="Simplified quarterly return",
            fields=["Quarterly turnover", "Tax paid", "ITC not available"]
        ),
        ReturnType.GSTR_5: ReturnDetails(
            return_type=ReturnType.GSTR_5,
            frequency=ReturnFrequency.MONTHLY,
            due_date_day=20,
            applicable_to="Non-resident supplies",
            description="Non-resident taxable persons",
            fields=["Supplies from foreign", "Tax payable", "Bank details"]
        ),
        ReturnType.GSTR_6: ReturnDetails(
            return_type=ReturnType.GSTR_6,
            frequency=ReturnFrequency.MONTHLY,
            due_date_day=15,
            applicable_to="Distributors of ISD",
            description="Input Service Distribution",
            fields=["Input services", "Distribution", "ITC claimed"]
        ),
        ReturnType.GSTR_7: ReturnDetails(
            return_type=ReturnType.GSTR_7,
            frequency=ReturnFrequency.MONTHLY,
            due_date_day=10,
            applicable_to="TDS deductors (E-commerce)",
            description="Tax Deducted at Source",
            fields=["TDS rate (1-5%)", "Amount deducted", "Suppliers"]
        ),
        ReturnType.GSTR_8: ReturnDetails(
            return_type=ReturnType.GSTR_8,
            frequency=ReturnFrequency.MONTHLY,
            due_date_day=10,
            applicable_to="TCS collectors (E-commerce)",
            description="Tax Collected at Source",
            fields=["TCS rate (0.5-5%)", "Amount collected", "Buyers"]
        ),
        ReturnType.GSTR_9: ReturnDetails(
            return_type=ReturnType.GSTR_9,
            frequency=ReturnFrequency.ANNUAL,
            due_date_day=31,
            applicable_to="All registered traders",
            description="Annual return with reconciliation",
            fields=["Annual summary", "GSTR reconciliation", "ITC reversal"]
        ),
    }

    @staticmethod
    def get_return_config(return_type: ReturnType) -> ReturnDetails:
        """Get configuration for a return type"""
        return GSTReturnTypesEngine.RETURN_CONFIGS.get(
            return_type,
            GSTReturnTypesEngine.RETURN_CONFIGS[ReturnType.GSTR_3B]
        )

    @staticmethod
    def get_due_date(return_type: ReturnType, period: str) -> str:
        """
        Calculate due date for a return type.

        Args:
            return_type: Type of GST return
            period: MMYYYY format

        Returns:
            Due date in YYYY-MM-DD format
        """
        config = GSTReturnTypesEngine.get_return_config(return_type)
        month = int(period[:2])
        year = int(period[2:])

        # For monthly returns, due date is in next month
        if config.frequency == ReturnFrequency.MONTHLY:
            next_month = month + 1
            next_year = year
            if next_month > 12:
                next_month = 1
                next_year += 1

            # Handle day overflow (e.g., Feb 31)
            try:
                due_date = datetime(next_year, next_month, config.due_date_day)
            except ValueError:
                # If day doesn't exist, use last day of month
                if next_month == 2:
                    due_date = datetime(next_year, 3, 1) - timedelta(days=1)
                else:
                    due_date = datetime(next_year, next_month + 1, 1) - timedelta(days=1)

            return due_date.strftime("%Y-%m-%d")

        # For quarterly returns (GSTR-4)
        elif config.frequency == ReturnFrequency.QUARTERLY:
            quarter = (month - 1) // 3 + 1
            quarter_end_month = quarter * 3
            quarter_year = year
            if quarter_end_month > 12:
                quarter_year += 1

            due_date = datetime(quarter_year, quarter_end_month % 12 or 12, config.due_date_day)
            return due_date.strftime("%Y-%m-%d")

        # For annual returns (GSTR-9)
        elif config.frequency == ReturnFrequency.ANNUAL:
            # Due by 31st of December following FY
            due_date = datetime(year + 1, 12, 31)
            return due_date.strftime("%Y-%m-%d")

    @staticmethod
    def get_all_returns_for_period(period: str) -> dict:
        """Get all applicable returns for a period with due dates"""
        returns = {}
        for return_type in ReturnType:
            due_date = GSTReturnTypesEngine.get_due_date(return_type, period)
            config = GSTReturnTypesEngine.get_return_config(return_type)

            returns[return_type.value] = {
                "return_type": return_type.value,
                "due_date": due_date,
                "frequency": config.frequency.value,
                "applicable_to": config.applicable_to,
                "description": config.description,
                "fields": config.fields
            }

        return returns

    @staticmethod
    def get_filing_calendar(year: int) -> dict:
        """
        Get complete filing calendar for a year.

        Args:
            year: Financial year

        Returns:
            Calendar with all due dates
        """
        calendar = {}

        # Get all months in FY (April to March)
        for month in range(4, 16):  # April to March next year
            actual_month = month if month <= 12 else month - 12
            actual_year = year if month <= 12 else year + 1

            period = f"{actual_month:02d}{actual_year}"
            calendar[period] = GSTReturnTypesEngine.get_all_returns_for_period(period)

        return calendar

    @staticmethod
    def get_return_summary(return_type: ReturnType) -> dict:
        """Get detailed summary of a return type"""
        config = GSTReturnTypesEngine.get_return_config(return_type)

        return {
            "return_type": return_type.value,
            "frequency": config.frequency.value,
            "due_date_day": config.due_date_day,
            "applicable_to": config.applicable_to,
            "description": config.description,
            "fields": config.fields,
            "key_details": GSTReturnTypesEngine._get_key_details(return_type)
        }

    @staticmethod
    def _get_key_details(return_type: ReturnType) -> dict:
        """Get key details for each return type"""
        details = {
            ReturnType.GSTR_1: {
                "B2B invoices": "B2B sales with HSN",
                "B2C": "B2C sales >₹1L",
                "Exports": "Zero-rated supplies",
                "HSN summary": "Summary by HSN code"
            },
            ReturnType.GSTR_3B: {
                "Output tax": "CGST, SGST, IGST",
                "Input tax credit": "From GSTR-2B",
                "Tax payable": "Output - Input",
                "Refund": "If Input > Output"
            },
            ReturnType.GSTR_4: {
                "Turnover": "Quarterly turnover",
                "Tax rate": "1-5% depending on State",
                "No ITC": "Input tax not available",
                "Payment": "Quarterly liability"
            },
            ReturnType.GSTR_5: {
                "Supply type": "B2B/B2C",
                "GST rate": "Applicable rate",
                "Payment": "Monthly by 20th",
                "No ITC": "No input tax credit"
            },
            ReturnType.GSTR_7: {
                "TDS rate": "1-5% on payments",
                "Deductors": "E-commerce platforms",
                "Payment": "Monthly by 10th",
                "Credit": "TDS credit to supplier"
            },
            ReturnType.GSTR_8: {
                "TCS rate": "0.5-5% on sales",
                "Collectors": "E-commerce operators",
                "Payment": "Monthly by 10th",
                "Credit": "TCS credit to buyer"
            },
            ReturnType.GSTR_9: {
                "Annual summary": "Full year reconciliation",
                "GSTR matching": "Monthly vs annual",
                "ITC reversal": "Items not allowed",
                "Reconciliation": "Mismatches correction"
            }
        }
        return details.get(return_type, {})


# Quick reference function
def get_gst_return_info(return_type_name: str) -> dict:
    """Quick function to get return type info by name"""
    try:
        return_type = ReturnType[return_type_name.upper()]
        return GSTReturnTypesEngine.get_return_summary(return_type)
    except KeyError:
        return {"error": f"Return type {return_type_name} not found"}
