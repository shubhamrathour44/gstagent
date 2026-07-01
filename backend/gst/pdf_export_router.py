"""
PDF Export API Router

REST endpoints for exporting forms to PDF format.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any
from gst.pdf_export_engine import (
    GSTR3BPDFGenerator,
    ITR1PDFGenerator,
    ITR2PDFGenerator,
    ITR3PDFGenerator
)

pdf_export_router = APIRouter(prefix="/pdf-export", tags=["PDF Export"])


# ═══════════════════════════════════════════════════════════════════════════
# GSTR-3B PDF EXPORT
# ═══════════════════════════════════════════════════════════════════════════

@pdf_export_router.post("/gstr3b")
async def export_gstr3b_pdf(form_data: Dict[str, Any]):
    """Export GSTR-3B form to PDF"""
    try:
        pdf_buffer = GSTR3BPDFGenerator.generate_pdf(form_data)

        gstin = form_data.get('gstin', 'GSTR3B')
        period = form_data.get('period', '042026')
        filename = f"GSTR3B_{gstin}_{period}.pdf"

        return StreamingResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF generation failed: {str(e)}")


@pdf_export_router.post("/gstr3b/from-calculation")
async def export_gstr3b_from_calculation(form_data: Dict[str, Any]):
    """Export GSTR-3B PDF from form calculation data"""
    try:
        from gst.gstr3b_engine import GSTR3BFormGenerator

        gstin = form_data.get('gstin')
        month = form_data.get('month')
        year = form_data.get('year')
        outward_supplies = form_data.get('outward_supplies', [])
        inward_supplies = form_data.get('inward_supplies', [])

        form = GSTR3BFormGenerator.generate_form(
            gstin=gstin,
            month=month,
            year=year,
            outward_supplies=outward_supplies,
            inward_supplies=inward_supplies
        )

        pdf_buffer = GSTR3BPDFGenerator.generate_pdf(form)

        period = f"{month:02d}{year}"
        filename = f"GSTR3B_{gstin}_{period}.pdf"

        return StreamingResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF generation failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════
# ITR-1 PDF EXPORT
# ═══════════════════════════════════════════════════════════════════════════

@pdf_export_router.post("/itr1")
async def export_itr1_pdf(form_data: Dict[str, Any]):
    """Export ITR-1 form to PDF"""
    try:
        pdf_buffer = ITR1PDFGenerator.generate_pdf(form_data)

        pan = form_data.get('pan', 'ITR1')
        fy = form_data.get('financial_year', '2026')
        filename = f"ITR1_{pan}_{fy}.pdf"

        return StreamingResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF generation failed: {str(e)}")


@pdf_export_router.post("/itr1/from-calculation")
async def export_itr1_from_calculation(form_data: Dict[str, Any]):
    """Export ITR-1 PDF from calculation data"""
    try:
        from gst.itr_forms_engine import (
            ITR1FormGenerator, ITR1Calculator,
            SalaryIncome, HousePropertyIncome, OtherIncome
        )

        pan = form_data.get('pan')
        financial_year = form_data.get('financial_year')

        salary = SalaryIncome(
            gross_salary=form_data.get('salary', {}).get('gross_salary', 0),
            allowances=form_data.get('salary', {}).get('allowances', 0),
            deductions=form_data.get('salary', {}).get('deductions', 0)
        )

        house_property = HousePropertyIncome(
            annual_value=form_data.get('house_property', {}).get('annual_value', 0),
            interest_paid=form_data.get('house_property', {}).get('interest_paid', 0),
            other_expenditure=form_data.get('house_property', {}).get('other_expenditure', 0)
        )

        other_income = [
            OtherIncome(income_type=oi.get('income_type'), amount=oi.get('amount'))
            for oi in form_data.get('other_income', [])
        ]

        form = ITR1FormGenerator.generate_form(
            pan=pan,
            financial_year=financial_year,
            salary=salary,
            house_property=house_property,
            other_income=other_income,
            tds_deducted=form_data.get('tds_deducted', 0),
            advance_tax_paid=form_data.get('advance_tax_paid', 0)
        )

        pdf_buffer = ITR1PDFGenerator.generate_pdf(form)

        filename = f"ITR1_{pan}_{financial_year}.pdf"

        return StreamingResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF generation failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════
# ITR-2 PDF EXPORT
# ═══════════════════════════════════════════════════════════════════════════

@pdf_export_router.post("/itr2")
async def export_itr2_pdf(form_data: Dict[str, Any]):
    """Export ITR-2 form to PDF"""
    try:
        pdf_buffer = ITR2PDFGenerator.generate_pdf(form_data)

        pan = form_data.get('pan', 'ITR2')
        fy = form_data.get('financial_year', '2026')
        filename = f"ITR2_{pan}_{fy}.pdf"

        return StreamingResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF generation failed: {str(e)}")


@pdf_export_router.post("/itr2/from-calculation")
async def export_itr2_from_calculation(form_data: Dict[str, Any]):
    """Export ITR-2 PDF from calculation data"""
    try:
        from gst.itr_forms_engine import (
            ITR2FormGenerator, CapitalGain
        )

        pan = form_data.get('pan')
        financial_year = form_data.get('financial_year')

        capital_gains = [
            CapitalGain(
                asset_type=cg.get('asset_type'),
                cost_of_acquisition=cg.get('cost_of_acquisition'),
                selling_price=cg.get('selling_price'),
                holding_period=cg.get('holding_period'),
                selling_date=cg.get('selling_date')
            )
            for cg in form_data.get('capital_gains', [])
        ]

        form = ITR2FormGenerator.generate_form(
            pan=pan,
            financial_year=financial_year,
            salary_income=form_data.get('salary_income', 0),
            house_property_income=form_data.get('house_property_income', 0),
            capital_gains=capital_gains,
            other_income=form_data.get('other_income', 0),
            tds_deducted=form_data.get('tds_deducted', 0)
        )

        pdf_buffer = ITR2PDFGenerator.generate_pdf(form)

        filename = f"ITR2_{pan}_{financial_year}.pdf"

        return StreamingResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF generation failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════
# ITR-3 PDF EXPORT
# ═══════════════════════════════════════════════════════════════════════════

@pdf_export_router.post("/itr3")
async def export_itr3_pdf(form_data: Dict[str, Any]):
    """Export ITR-3 form to PDF"""
    try:
        pdf_buffer = ITR3PDFGenerator.generate_pdf(form_data)

        pan = form_data.get('pan', 'ITR3')
        fy = form_data.get('financial_year', '2026')
        filename = f"ITR3_{pan}_{fy}.pdf"

        return StreamingResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF generation failed: {str(e)}")


@pdf_export_router.post("/itr3/from-calculation")
async def export_itr3_from_calculation(form_data: Dict[str, Any]):
    """Export ITR-3 PDF from calculation data"""
    try:
        from gst.itr_forms_engine import (
            ITR3FormGenerator, BusinessIncome, BusinessExpense
        )

        pan = form_data.get('pan')
        financial_year = form_data.get('financial_year')

        expenses = [
            BusinessExpense(
                expense_type=exp.get('expense_type'),
                amount=exp.get('amount')
            )
            for exp in form_data.get('business', {}).get('operating_expenses', [])
        ]

        business = BusinessIncome(
            gross_receipts=form_data.get('business', {}).get('gross_receipts', 0),
            cost_of_goods_sold=form_data.get('business', {}).get('cost_of_goods_sold', 0),
            operating_expenses=expenses
        )

        form = ITR3FormGenerator.generate_form(
            pan=pan,
            financial_year=financial_year,
            business=business,
            salary_income=form_data.get('salary_income', 0),
            house_property_income=form_data.get('house_property_income', 0),
            other_income=form_data.get('other_income', 0),
            tds_deducted=form_data.get('tds_deducted', 0)
        )

        pdf_buffer = ITR3PDFGenerator.generate_pdf(form)

        filename = f"ITR3_{pan}_{financial_year}.pdf"

        return StreamingResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF generation failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════
# STATUS
# ═══════════════════════════════════════════════════════════════════════════

@pdf_export_router.get("/status")
async def pdf_export_status():
    """Get PDF export module status"""
    return {
        "status": "ACTIVE",
        "forms": ["GSTR-3B", "ITR-1", "ITR-2", "ITR-3"],
        "endpoints": 8,
        "format": "PDF",
        "library": "reportlab",
        "version": "1.0.0"
    }
