"""
ITR (Income Tax Return) Router

API endpoints for ITR filing, deadlines, and compliance tracking.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from gst.itr_types_engine import ITRTypesEngine, ITRType

itr_router = APIRouter(prefix="/itr-features", tags=["ITR Features"])


# ═══════════════════════════════════════════════════════════════════════════
# ITR TYPES ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@itr_router.get("/return-types/list")
async def list_itr_types():
    """Get all available ITR return types"""
    return {
        "return_types": [
            {
                "code": rt.value,
                "name": rt.name,
                "description": ITRTypesEngine.get_return_config(rt).description
            }
            for rt in ITRType
        ]
    }


@itr_router.get("/return-types/{return_type}")
async def get_itr_type_info(return_type: str):
    """Get detailed info for a specific ITR type"""
    try:
        rt = ITRType[return_type.upper().replace("-", "_")]
        return ITRTypesEngine.get_return_summary(rt)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"ITR type {return_type} not found")


@itr_router.get("/filing-calendar/{financial_year}")
async def get_itr_filing_calendar(financial_year: int):
    """Get complete ITR filing calendar for a financial year"""
    try:
        if financial_year < 2020 or financial_year > 2050:
            raise ValueError("Invalid financial year")

        return {
            "financial_year": f"{financial_year-1}-{financial_year}",
            "calendar": ITRTypesEngine.get_filing_calendar(financial_year)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@itr_router.get("/due-dates/{financial_year}")
async def get_all_itr_due_dates(financial_year: int):
    """Get all ITR due dates for a financial year"""
    try:
        if financial_year < 2020 or financial_year > 2050:
            raise ValueError("Invalid financial year")

        return {
            "financial_year": f"{financial_year-1}-{financial_year}",
            "itr_returns": ITRTypesEngine.get_all_returns_for_fy(financial_year)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@itr_router.get("/return-due-date/{return_type}/{financial_year}")
async def get_itr_return_due_date(return_type: str, financial_year: int):
    """Get due date for a specific ITR return"""
    try:
        rt = ITRType[return_type.upper().replace("-", "_")]
        due_date = ITRTypesEngine.get_due_date(rt, financial_year)
        config = ITRTypesEngine.get_return_config(rt)

        return {
            "return_type": return_type,
            "financial_year": f"{financial_year-1}-{financial_year}",
            "due_date": due_date,
            "frequency": config.frequency.value,
            "applicable_to": config.applicable_to
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@itr_router.post("/penalty-calculator")
async def calculate_itr_penalty(
    amount: float = Query(...),
    days_late: int = Query(...)
):
    """Calculate penalty for late ITR filing"""
    try:
        if amount <= 0 or days_late < 0:
            raise ValueError("Invalid amount or days_late")

        penalty = ITRTypesEngine.calculate_penalty(amount, days_late)

        return {
            "amount": amount,
            "days_late": days_late,
            "penalty_rate_per_annum": "5%",
            "penalty_amount": penalty,
            "total_due": amount + penalty
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@itr_router.post("/applicable-itrs")
async def get_applicable_itrs(
    income_sources: List[str] = Query(...),
    entity_type: str = Query(...)
):
    """Determine which ITRs are applicable based on income sources"""
    try:
        applicable = ITRTypesEngine.get_applicable_itrs(income_sources, entity_type)

        return {
            "entity_type": entity_type,
            "income_sources": income_sources,
            "applicable_itrs": applicable,
            "recommended": applicable[0] if applicable else "ITR-1"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@itr_router.get("/filing-checklist/{return_type}")
async def get_filing_checklist(return_type: str):
    """Get required documents checklist for ITR filing"""
    try:
        rt = ITRType[return_type.upper().replace("-", "_")]
        checklist = ITRTypesEngine.get_itr_checklist(rt)
        return checklist
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# STATUS ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@itr_router.get("/features-status")
async def itr_features_status():
    """Get status of all ITR features"""
    return {
        "status": "All ITR features enabled",
        "itr_return_types": {
            "status": "ACTIVE",
            "supports": "ITR-1, 2, 3, 4, 5, 6, 7",
            "endpoints": 6
        },
        "itr_filing": {
            "status": "ACTIVE",
            "features": ["filing_calendar", "due_dates", "penalty_calculation", "applicable_itrs", "document_checklist"],
            "endpoints": 5
        },
        "total_new_endpoints": 11
    }
