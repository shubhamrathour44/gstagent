"""
GSTR-3B API Router

Endpoints for generating, validating, and exporting GSTR-3B forms
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from gst.gstr3b_engine import (
    GSTR3BFormGenerator,
    GSTR3BCalculationEngine,
    GSTR3BValidator,
    OutwardSupply,
    InwardSupply,
    SupplyType
)

gstr3b_router = APIRouter(prefix="/gstr3b", tags=["GSTR-3B"])


# ═══════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════

class SupplyRequest(BaseModel):
    """Supply details in request"""
    supply_type: str
    taxable_value: float
    cgst: float = 0
    sgst: float = 0
    igst: float = 0
    cess: float = 0
    invoices_count: int = 0


class OutwardSupplyRequest(SupplyRequest):
    """Outward supply request"""
    pass


class InwardSupplyRequest(SupplyRequest):
    """Inward supply request"""
    eligible_cgst: float = 0
    eligible_sgst: float = 0
    eligible_igst: float = 0
    eligible_cess: float = 0


class GSTR3BGenerateRequest(BaseModel):
    """GSTR-3B generation request"""
    gstin: str
    month: int
    year: int
    outward_supplies: List[OutwardSupplyRequest]
    inward_supplies: List[InwardSupplyRequest]
    amendments: Optional[List[dict]] = None


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@gstr3b_router.post("/generate")
async def generate_gstr3b_form(request: GSTR3BGenerateRequest):
    """
    Generate GSTR-3B form

    Request:
    {
        "gstin": "27ABCDE1234F1Z5",
        "month": 4,
        "year": 2026,
        "outward_supplies": [
            {
                "supply_type": "b2b",
                "taxable_value": 100000,
                "cgst": 9000,
                "sgst": 9000,
                "igst": 0,
                "invoices_count": 10
            }
        ],
        "inward_supplies": [
            {
                "supply_type": "b2b",
                "taxable_value": 50000,
                "cgst": 4500,
                "sgst": 4500,
                "igst": 0,
                "eligible_cgst": 4500,
                "eligible_sgst": 4500,
                "invoices_count": 5
            }
        ]
    }

    Response: Complete GSTR-3B form with calculations
    """
    try:
        # Validate GSTIN
        if not request.gstin or len(request.gstin) != 15:
            raise ValueError("Invalid GSTIN format")

        # Validate period
        if request.month < 1 or request.month > 12:
            raise ValueError("Month must be between 1 and 12")

        # Convert request to engine objects
        outward_supplies = []
        for supply in request.outward_supplies:
            outward_supplies.append(
                OutwardSupply(
                    supply_type=SupplyType[supply.supply_type.upper()],
                    taxable_value=supply.taxable_value,
                    cgst=supply.cgst,
                    sgst=supply.sgst,
                    igst=supply.igst,
                    cess=supply.cess,
                    invoices_count=supply.invoices_count
                )
            )

        inward_supplies = []
        for supply in request.inward_supplies:
            inward_supplies.append(
                InwardSupply(
                    supply_type=SupplyType[supply.supply_type.upper()],
                    taxable_value=supply.taxable_value,
                    cgst=supply.cgst,
                    sgst=supply.sgst,
                    igst=supply.igst,
                    cess=supply.cess,
                    invoices_count=supply.invoices_count,
                    eligible_cgst=supply.eligible_cgst,
                    eligible_sgst=supply.eligible_sgst,
                    eligible_igst=supply.eligible_igst,
                    eligible_cess=supply.eligible_cess
                )
            )

        # Generate form
        form = GSTR3BFormGenerator.generate_form(
            gstin=request.gstin,
            month=request.month,
            year=request.year,
            outward_supplies=outward_supplies,
            inward_supplies=inward_supplies,
            amendments=request.amendments
        )

        return {
            "status": "success",
            "form": form
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@gstr3b_router.post("/validate")
async def validate_gstr3b_form(request: GSTR3BGenerateRequest):
    """
    Validate GSTR-3B form for compliance

    Returns:
    - is_valid: boolean
    - errors: list of critical errors
    - warnings: list of warnings
    - can_file: whether form can be filed
    """
    try:
        # First generate the form
        outward_supplies = []
        for supply in request.outward_supplies:
            outward_supplies.append(
                OutwardSupply(
                    supply_type=SupplyType[supply.supply_type.upper()],
                    taxable_value=supply.taxable_value,
                    cgst=supply.cgst,
                    sgst=supply.sgst,
                    igst=supply.igst,
                    cess=supply.cess,
                    invoices_count=supply.invoices_count
                )
            )

        inward_supplies = []
        for supply in request.inward_supplies:
            inward_supplies.append(
                InwardSupply(
                    supply_type=SupplyType[supply.supply_type.upper()],
                    taxable_value=supply.taxable_value,
                    cgst=supply.cgst,
                    sgst=supply.sgst,
                    igst=supply.igst,
                    cess=supply.cess,
                    invoices_count=supply.invoices_count,
                    eligible_cgst=supply.eligible_cgst,
                    eligible_sgst=supply.eligible_sgst,
                    eligible_igst=supply.eligible_igst,
                    eligible_cess=supply.eligible_cess
                )
            )

        form = GSTR3BFormGenerator.generate_form(
            gstin=request.gstin,
            month=request.month,
            year=request.year,
            outward_supplies=outward_supplies,
            inward_supplies=inward_supplies,
            amendments=request.amendments
        )

        # Validate
        validation_result = GSTR3BValidator.validate_form(form)

        return {
            "status": "success",
            "validation": validation_result
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@gstr3b_router.post("/calculate")
async def calculate_tax_liability(request: GSTR3BGenerateRequest):
    """
    Calculate tax liability only (without full form)

    Returns:
    - outward_tax: breakdown of output tax
    - itc_available: breakdown of input tax credit
    - net_liability: final tax payable
    """
    try:
        # Convert request to engine objects
        outward_supplies = []
        for supply in request.outward_supplies:
            outward_supplies.append(
                OutwardSupply(
                    supply_type=SupplyType[supply.supply_type.upper()],
                    taxable_value=supply.taxable_value,
                    cgst=supply.cgst,
                    sgst=supply.sgst,
                    igst=supply.igst,
                    cess=supply.cess,
                    invoices_count=supply.invoices_count
                )
            )

        inward_supplies = []
        for supply in request.inward_supplies:
            inward_supplies.append(
                InwardSupply(
                    supply_type=SupplyType[supply.supply_type.upper()],
                    taxable_value=supply.taxable_value,
                    cgst=supply.cgst,
                    sgst=supply.sgst,
                    igst=supply.igst,
                    cess=supply.cess,
                    invoices_count=supply.invoices_count,
                    eligible_cgst=supply.eligible_cgst,
                    eligible_sgst=supply.eligible_sgst,
                    eligible_igst=supply.eligible_igst,
                    eligible_cess=supply.eligible_cess
                )
            )

        # Calculate
        outward_calc = GSTR3BCalculationEngine.calculate_outward_supplies(outward_supplies)
        inward_calc = GSTR3BCalculationEngine.calculate_inward_supplies(inward_supplies)
        tax_liability = GSTR3BCalculationEngine.calculate_tax_liability(
            outward_calc, inward_calc
        )

        return {
            "status": "success",
            "calculations": {
                "outward_tax": tax_liability.get("outward_tax"),
                "itc_available": tax_liability.get("itc_available"),
                "net_liability": tax_liability.get("net_liability"),
                "reconciliation": tax_liability.get("reconciliation")
            }
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@gstr3b_router.post("/summary")
async def get_form_summary(request: GSTR3BGenerateRequest):
    """
    Get quick summary of GSTR-3B form

    Returns quick metrics for the form
    """
    try:
        # Convert and generate
        outward_supplies = []
        for supply in request.outward_supplies:
            outward_supplies.append(
                OutwardSupply(
                    supply_type=SupplyType[supply.supply_type.upper()],
                    taxable_value=supply.taxable_value,
                    cgst=supply.cgst,
                    sgst=supply.sgst,
                    igst=supply.igst,
                    cess=supply.cess,
                    invoices_count=supply.invoices_count
                )
            )

        inward_supplies = []
        for supply in request.inward_supplies:
            inward_supplies.append(
                InwardSupply(
                    supply_type=SupplyType[supply.supply_type.upper()],
                    taxable_value=supply.taxable_value,
                    cgst=supply.cgst,
                    sgst=supply.sgst,
                    igst=supply.igst,
                    cess=supply.cess,
                    invoices_count=supply.invoices_count,
                    eligible_cgst=supply.eligible_cgst,
                    eligible_sgst=supply.eligible_sgst,
                    eligible_igst=supply.eligible_igst,
                    eligible_cess=supply.eligible_cess
                )
            )

        form = GSTR3BFormGenerator.generate_form(
            gstin=request.gstin,
            month=request.month,
            year=request.year,
            outward_supplies=outward_supplies,
            inward_supplies=inward_supplies,
            amendments=request.amendments
        )

        summary = GSTR3BFormGenerator.get_form_summary(form)

        return {
            "status": "success",
            "summary": summary
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@gstr3b_router.get("/demo/{gstin}/{month}/{year}")
async def get_demo_form(gstin: str, month: int, year: int):
    """
    Get demo GSTR-3B form with sample data

    For testing purposes
    """
    try:
        # Sample data
        outward_supplies = [
            OutwardSupply(
                supply_type=SupplyType.B2B,
                taxable_value=100000,
                cgst=9000,
                sgst=9000,
                invoices_count=10
            ),
            OutwardSupply(
                supply_type=SupplyType.B2C,
                taxable_value=50000,
                cgst=4500,
                sgst=4500,
                invoices_count=5
            ),
            OutwardSupply(
                supply_type=SupplyType.EXPORT,
                taxable_value=75000,
                igst=0,
                invoices_count=3
            )
        ]

        inward_supplies = [
            InwardSupply(
                supply_type=SupplyType.B2B,
                taxable_value=80000,
                cgst=7200,
                sgst=7200,
                invoices_count=8,
                eligible_cgst=7200,
                eligible_sgst=7200
            )
        ]

        form = GSTR3BFormGenerator.generate_form(
            gstin=gstin,
            month=month,
            year=year,
            outward_supplies=outward_supplies,
            inward_supplies=inward_supplies
        )

        return {
            "status": "success",
            "form": form,
            "note": "This is demo data for testing purposes"
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@gstr3b_router.get("/status")
async def gstr3b_status():
    """Get GSTR-3B module status"""
    return {
        "status": "ACTIVE",
        "features": [
            "form_generation",
            "tax_calculation",
            "validation",
            "pdf_export",
            "excel_export"
        ],
        "endpoints": 6,
        "version": "1.0.0"
    }
