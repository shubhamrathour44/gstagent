"""
GSTR-3B Form Generation Engine

Generates complete GSTR-3B (Tax Summary) forms with:
- Outward supplies calculation
- Inward supplies & ITC
- Tax calculation
- Reconciliation
- PDF/Excel/JSON export
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class SupplyType(Enum):
    """Types of outward supplies"""
    B2B = "b2b"
    B2C = "b2c"
    EXPORT = "export"
    EXEMPT = "exempt"
    NIL_RATED = "nil_rated"


class ITCType(Enum):
    """Types of ITC (Input Tax Credit)"""
    INVOICE = "invoice"
    DEBIT_NOTE = "debit_note"
    IMPORT = "import"
    CAPITAL_GOODS = "capital_goods"


@dataclass
class OutwardSupply:
    """Outward supply details"""
    supply_type: SupplyType
    taxable_value: float
    cgst: float = 0
    sgst: float = 0
    igst: float = 0
    cess: float = 0
    invoices_count: int = 0


@dataclass
class InwardSupply:
    """Inward supply & ITC details"""
    supply_type: SupplyType
    taxable_value: float
    cgst: float = 0
    sgst: float = 0
    igst: float = 0
    cess: float = 0
    invoices_count: int = 0
    # ITC eligibility
    eligible_cgst: float = 0
    eligible_sgst: float = 0
    eligible_igst: float = 0
    eligible_cess: float = 0


@dataclass
class GSTR3BData:
    """Complete GSTR-3B form data"""
    gstin: str
    month: int  # 1-12
    year: int
    filing_date: str

    # Outward supplies
    outward_supplies: Dict[str, OutwardSupply]

    # Inward supplies
    inward_supplies: Dict[str, InwardSupply]

    # Amendments
    amendments: Optional[List[Dict]] = None

    # Other details
    currency: str = "INR"
    declaration: bool = False


class GSTR3BCalculationEngine:
    """Calculate GSTR-3B form values"""

    # Tax rates (can be configured per state)
    STANDARD_RATE = 0.18  # 18%
    REDUCED_RATE = 0.05   # 5%
    ZERO_RATE = 0.0       # 0%
    CESS_RATE = 0.01      # 1% (varies)

    @staticmethod
    def calculate_outward_supplies(supplies: List[OutwardSupply]) -> Dict:
        """Calculate total outward supplies"""

        result = {
            "b2b": {"value": 0, "tax": 0, "count": 0},
            "b2c": {"value": 0, "tax": 0, "count": 0},
            "export": {"value": 0, "tax": 0, "count": 0},
            "exempt": {"value": 0, "tax": 0, "count": 0},
            "nil_rated": {"value": 0, "tax": 0, "count": 0},
        }

        for supply in supplies:
            supply_key = supply.supply_type.value
            tax_total = supply.cgst + supply.sgst + supply.igst + supply.cess

            result[supply_key]["value"] += supply.taxable_value
            result[supply_key]["tax"] += tax_total
            result[supply_key]["count"] += supply.invoices_count

        # Calculate total outward supplies
        result["total_value"] = sum(s["value"] for s in result.values() if s != "total_value")
        result["total_tax"] = sum(s["tax"] for s in result.values() if s != "total_tax")
        result["total_count"] = sum(s["count"] for s in result.values() if s != "total_count")

        return result

    @staticmethod
    def calculate_inward_supplies(supplies: List[InwardSupply]) -> Dict:
        """Calculate total inward supplies & ITC"""

        result = {
            "supplies": {
                "b2b": {"value": 0, "tax": 0, "count": 0},
                "b2c": {"value": 0, "tax": 0, "count": 0},
                "import": {"value": 0, "tax": 0, "count": 0},
                "other": {"value": 0, "tax": 0, "count": 0},
            },
            "itc": {
                "cgst": 0,
                "sgst": 0,
                "igst": 0,
                "cess": 0,
            }
        }

        for supply in supplies:
            supply_key = supply.supply_type.value
            tax_total = supply.cgst + supply.sgst + supply.igst + supply.cess

            if supply_key in result["supplies"]:
                result["supplies"][supply_key]["value"] += supply.taxable_value
                result["supplies"][supply_key]["tax"] += tax_total
                result["supplies"][supply_key]["count"] += supply.invoices_count

            # Add eligible ITC
            result["itc"]["cgst"] += supply.eligible_cgst
            result["itc"]["sgst"] += supply.eligible_sgst
            result["itc"]["igst"] += supply.eligible_igst
            result["itc"]["cess"] += supply.eligible_cess

        # Calculate totals
        result["supplies"]["total_value"] = sum(
            s["value"] for s in result["supplies"].values()
            if isinstance(s, dict) and "value" in s
        )
        result["supplies"]["total_tax"] = sum(
            s["tax"] for s in result["supplies"].values()
            if isinstance(s, dict) and "tax" in s
        )

        result["itc"]["total"] = (
            result["itc"]["cgst"] +
            result["itc"]["sgst"] +
            result["itc"]["igst"] +
            result["itc"]["cess"]
        )

        return result

    @staticmethod
    def calculate_tax_liability(
        outward_supplies: Dict,
        inward_supplies: Dict
    ) -> Dict:
        """Calculate final tax liability"""

        # Extract tax components
        outward_cgst = sum(
            s.get("cgst", 0) for s in outward_supplies.values()
            if isinstance(s, dict) and "cgst" in s
        )
        outward_sgst = sum(
            s.get("sgst", 0) for s in outward_supplies.values()
            if isinstance(s, dict) and "sgst" in s
        )
        outward_igst = sum(
            s.get("igst", 0) for s in outward_supplies.values()
            if isinstance(s, dict) and "igst" in s
        )
        outward_cess = sum(
            s.get("cess", 0) for s in outward_supplies.values()
            if isinstance(s, dict) and "cess" in s
        )

        # ITC available
        itc_cgst = inward_supplies.get("itc", {}).get("cgst", 0)
        itc_sgst = inward_supplies.get("itc", {}).get("sgst", 0)
        itc_igst = inward_supplies.get("itc", {}).get("igst", 0)
        itc_cess = inward_supplies.get("itc", {}).get("cess", 0)

        # Calculate net liability
        net_cgst = max(0, outward_cgst - itc_cgst)
        net_sgst = max(0, outward_sgst - itc_sgst)
        net_igst = max(0, outward_igst - itc_igst)
        net_cess = max(0, outward_cess - itc_cess)

        total_tax_payable = net_cgst + net_sgst + net_igst + net_cess

        return {
            "outward_tax": {
                "cgst": round(outward_cgst, 2),
                "sgst": round(outward_sgst, 2),
                "igst": round(outward_igst, 2),
                "cess": round(outward_cess, 2),
                "total": round(outward_cgst + outward_sgst + outward_igst + outward_cess, 2)
            },
            "itc_available": {
                "cgst": round(itc_cgst, 2),
                "sgst": round(itc_sgst, 2),
                "igst": round(itc_igst, 2),
                "cess": round(itc_cess, 2),
                "total": round(itc_cgst + itc_sgst + itc_igst + itc_cess, 2)
            },
            "net_liability": {
                "cgst": round(net_cgst, 2),
                "sgst": round(net_sgst, 2),
                "igst": round(net_igst, 2),
                "cess": round(net_cess, 2),
                "total": round(total_tax_payable, 2)
            },
            "reconciliation": {
                "itc_credit": round(itc_cgst + itc_sgst + itc_igst + itc_cess, 2),
                "tax_payable": round(total_tax_payable, 2),
                "advance_paid": 0,  # To be updated by user
                "interest": 0,  # To be calculated
                "penalty": 0,  # To be calculated
                "final_payable": round(total_tax_payable, 2)
            }
        }


class GSTR3BFormGenerator:
    """Generate complete GSTR-3B form"""

    @staticmethod
    def generate_form(
        gstin: str,
        month: int,
        year: int,
        outward_supplies: List[OutwardSupply],
        inward_supplies: List[InwardSupply],
        amendments: Optional[List[Dict]] = None
    ) -> Dict:
        """Generate complete GSTR-3B form"""

        # Calculate outward supplies
        outward_calc = GSTR3BCalculationEngine.calculate_outward_supplies(
            outward_supplies
        )

        # Calculate inward supplies
        inward_calc = GSTR3BCalculationEngine.calculate_inward_supplies(
            inward_supplies
        )

        # Calculate tax liability
        tax_liability = GSTR3BCalculationEngine.calculate_tax_liability(
            outward_calc,
            inward_calc
        )

        # Format financial year and period
        fy_start = year if month >= 4 else year - 1
        fy_end = fy_start + 1
        period = f"{month:02d}{year}"

        # Generate form
        form = {
            "metadata": {
                "form_type": "GSTR-3B",
                "gstin": gstin,
                "financial_year": f"{fy_start}-{fy_end}",
                "tax_period": period,
                "period_label": f"{month:02d}/{year}",
                "filing_date": datetime.now().strftime("%Y-%m-%d"),
                "form_version": "2.0",
                "status": "NOT_FILED"
            },
            "section_1_outward_supplies": {
                "description": "Outward Supplies",
                "b2b": {
                    "value": round(outward_calc.get("b2b", {}).get("value", 0), 2),
                    "tax": round(outward_calc.get("b2b", {}).get("tax", 0), 2),
                    "invoices": outward_calc.get("b2b", {}).get("count", 0)
                },
                "b2c": {
                    "value": round(outward_calc.get("b2c", {}).get("value", 0), 2),
                    "tax": round(outward_calc.get("b2c", {}).get("tax", 0), 2),
                    "invoices": outward_calc.get("b2c", {}).get("count", 0)
                },
                "export": {
                    "value": round(outward_calc.get("export", {}).get("value", 0), 2),
                    "tax": round(outward_calc.get("export", {}).get("tax", 0), 2),
                    "invoices": outward_calc.get("export", {}).get("count", 0)
                },
                "exempt": {
                    "value": round(outward_calc.get("exempt", {}).get("value", 0), 2),
                    "tax": round(outward_calc.get("exempt", {}).get("tax", 0), 2),
                },
                "nil_rated": {
                    "value": round(outward_calc.get("nil_rated", {}).get("value", 0), 2),
                    "tax": round(outward_calc.get("nil_rated", {}).get("tax", 0), 2),
                },
                "total": {
                    "value": round(outward_calc.get("total_value", 0), 2),
                    "tax": round(outward_calc.get("total_tax", 0), 2),
                    "invoices": outward_calc.get("total_count", 0)
                }
            },
            "section_2_inward_supplies": {
                "description": "Inward Supplies",
                "supplies": {
                    "b2b": {
                        "value": round(
                            inward_calc.get("supplies", {}).get("b2b", {}).get("value", 0), 2
                        ),
                        "tax": round(
                            inward_calc.get("supplies", {}).get("b2b", {}).get("tax", 0), 2
                        ),
                        "invoices": inward_calc.get("supplies", {}).get("b2b", {}).get("count", 0)
                    },
                    "b2c": {
                        "value": round(
                            inward_calc.get("supplies", {}).get("b2c", {}).get("value", 0), 2
                        ),
                        "tax": round(
                            inward_calc.get("supplies", {}).get("b2c", {}).get("tax", 0), 2
                        ),
                        "invoices": inward_calc.get("supplies", {}).get("b2c", {}).get("count", 0)
                    },
                    "import": {
                        "value": round(
                            inward_calc.get("supplies", {}).get("import", {}).get("value", 0), 2
                        ),
                        "tax": round(
                            inward_calc.get("supplies", {}).get("import", {}).get("tax", 0), 2
                        ),
                    },
                    "total": {
                        "value": round(
                            inward_calc.get("supplies", {}).get("total_value", 0), 2
                        ),
                        "tax": round(
                            inward_calc.get("supplies", {}).get("total_tax", 0), 2
                        ),
                    }
                },
                "itc": {
                    "cgst": round(inward_calc.get("itc", {}).get("cgst", 0), 2),
                    "sgst": round(inward_calc.get("itc", {}).get("sgst", 0), 2),
                    "igst": round(inward_calc.get("itc", {}).get("igst", 0), 2),
                    "cess": round(inward_calc.get("itc", {}).get("cess", 0), 2),
                    "total": round(inward_calc.get("itc", {}).get("total", 0), 2)
                }
            },
            "section_3_tax_liability": {
                "description": "Tax Liability",
                "outward_tax": tax_liability.get("outward_tax", {}),
                "itc_available": tax_liability.get("itc_available", {}),
                "net_liability": tax_liability.get("net_liability", {}),
            },
            "section_4_reconciliation": {
                "description": "Reconciliation",
                "itc_credit_available": tax_liability.get("reconciliation", {}).get("itc_credit", 0),
                "tax_payable": tax_liability.get("reconciliation", {}).get("tax_payable", 0),
                "advance_paid": 0,
                "interest_payable": 0,
                "penalty_payable": 0,
                "total_payable": tax_liability.get("reconciliation", {}).get("final_payable", 0),
            },
            "section_5_amendments": {
                "description": "Amendments",
                "amendments": amendments or []
            },
            "section_6_declaration": {
                "description": "Declaration",
                "declared_by": "CA",
                "verification": False,
                "declaration_timestamp": datetime.now().isoformat()
            }
        }

        return form

    @staticmethod
    def get_form_summary(form: Dict) -> Dict:
        """Get summary of GSTR-3B form"""
        return {
            "gstin": form["metadata"]["gstin"],
            "period": form["metadata"]["period_label"],
            "financial_year": form["metadata"]["financial_year"],
            "outward_supplies_value": form["section_1_outward_supplies"]["total"]["value"],
            "outward_supplies_tax": form["section_1_outward_supplies"]["total"]["tax"],
            "inward_supplies_value": form["section_2_inward_supplies"]["supplies"]["total"]["value"],
            "itc_available": form["section_2_inward_supplies"]["itc"]["total"],
            "net_tax_payable": form["section_4_reconciliation"]["tax_payable"],
            "advance_paid": form["section_4_reconciliation"]["advance_paid"],
            "total_payable": form["section_4_reconciliation"]["total_payable"],
            "status": form["metadata"]["status"],
            "filing_date": form["metadata"]["filing_date"]
        }


class GSTR3BValidator:
    """Validate GSTR-3B form for compliance"""

    @staticmethod
    def validate_form(form: Dict) -> Dict:
        """Validate complete GSTR-3B form"""

        errors = []
        warnings = []

        # Validate metadata
        if not form.get("metadata", {}).get("gstin"):
            errors.append("GSTIN is required")

        # Validate tax calculations
        outward_tax = form.get("section_1_outward_supplies", {}).get("total", {}).get("tax", 0)
        itc_available = form.get("section_2_inward_supplies", {}).get("itc", {}).get("total", 0)
        net_payable = form.get("section_4_reconciliation", {}).get("tax_payable", 0)

        # Check if ITC exceeds output tax
        if itc_available > outward_tax:
            warnings.append(
                f"ITC (₹{itc_available}) exceeds output tax (₹{outward_tax}). "
                "Excess ITC will be carried forward."
            )

        # Validate amounts
        if outward_tax < 0:
            errors.append("Output tax cannot be negative")
        if itc_available < 0:
            errors.append("ITC available cannot be negative")

        # Validate invoice counts
        total_invoices = (
            form.get("section_1_outward_supplies", {}).get("total", {}).get("invoices", 0)
        )
        if total_invoices == 0:
            warnings.append("No outward supply invoices found")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "can_file": len(errors) == 0
        }
