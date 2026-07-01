"""
GSTR-1 & GSTR-3B Filing Router

API endpoints for GST return filing:
- GSTR-1 (Sales Return)
- GSTR-3B (Summary Return with ITC)
"""

import os
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from auth import CurrentUser, get_current_user
from database import get_db, GSTRFilingSubmission
from reconciliation_engine import GSTReconciliationEngine
from .gstr_xml_generator import GSTR1XMLGenerator, GSTR3BXMLGenerator
from .gstr_filing_client import GSTRFilingClient, GSTRFilingStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gstr-filing", tags=["GST Return Filing"])

# Configuration
XML_STORAGE_DIR = "uploads/gstr_xml"
os.makedirs(XML_STORAGE_DIR, exist_ok=True)


# ── SCHEMAS ────────────────────────────────────────────────────────────────────

class GSTR1FilingRequest(BaseModel):
    """Request to file GSTR-1."""
    gstin: str
    period: str  # MMYYYY
    company_name: str
    sales_invoices: list  # List of invoice dictionaries from sales register


class GSTR3BFilingRequest(BaseModel):
    """Request to file GSTR-3B."""
    gstin: str
    period: str  # MMYYYY
    company_name: str
    gstr1_summary: dict  # GSTR-1 aggregated data
    gstr2b_summary: dict  # GSTR-2B reconciled data
    itc_details: dict  # ITC eligibility
    payment_info: Optional[dict] = None


class GSTRFilingStatusResponse(BaseModel):
    """Status of a filed return."""
    acknowledgement_number: Optional[str]
    return_type: str
    period: str
    filing_status: str
    portal_status: Optional[str]
    total_tax: float
    submitted_at: Optional[datetime]
    processed_at: Optional[datetime]


class GSTRPortalLoginRequest(BaseModel):
    """GST portal login credentials."""
    gstin: str
    username: str
    password: str


# ── HELPERS ────────────────────────────────────────────────────────────────────

def _save_xml(firm_id: str, gstin: str, period: str, return_type: str, xml_content: str) -> str:
    """Save XML file."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{return_type}_{gstin}_{period}_{timestamp}.xml"
    firm_dir = os.path.join(XML_STORAGE_DIR, firm_id)
    os.makedirs(firm_dir, exist_ok=True)

    file_path = os.path.join(firm_dir, filename)
    with open(file_path, "w") as f:
        f.write(xml_content)

    return file_path


# ── ENDPOINTS ──────────────────────────────────────────────────────────────────

@router.post("/gstr1/prepare")
async def prepare_gstr1(
    request: GSTR1FilingRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Prepare GSTR-1 (Sales Return) XML for filing.

    Returns XML ready for submission.
    """
    try:
        # Generate XML
        xml_content = GSTR1XMLGenerator.generate(
            gstin=request.gstin,
            period=request.period,
            company_name=request.company_name,
            sales_invoices=request.sales_invoices
        )

        # Save XML
        xml_path = _save_xml(current_user.firm_id, request.gstin, request.period, "GSTR-1", xml_content)

        # Create filing record
        filing = GSTRFilingSubmission(
            firm_id=current_user.firm_id,
            gstin=request.gstin,
            period=request.period,
            return_type="GSTR-1",
            xml_file_path=xml_path,
            filing_status=GSTRFilingStatus.DRAFT,
        )
        db.add(filing)
        await db.commit()
        await db.refresh(filing)

        logger.info(f"GSTR-1 prepared: {request.gstin} {request.period}")

        return {
            "success": True,
            "filing_id": filing.id,
            "return_type": "GSTR-1",
            "gstin": request.gstin,
            "period": request.period,
            "message": "GSTR-1 prepared successfully",
            "next_step": "Submit to portal or download for review"
        }

    except Exception as e:
        logger.error(f"GSTR-1 preparation error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Preparation failed: {str(e)}")


@router.post("/gstr3b/prepare")
async def prepare_gstr3b(
    request: GSTR3BFilingRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Prepare GSTR-3B (Summary Return) XML for filing.

    Includes ITC reconciliation from GSTR-2B.
    """
    try:
        # Generate XML
        xml_content = GSTR3BXMLGenerator.generate(
            gstin=request.gstin,
            period=request.period,
            company_name=request.company_name,
            gstr1_data=request.gstr1_summary,
            gstr2b_data=request.gstr2b_summary,
            itc_data=request.itc_details,
            payment_data=request.payment_info
        )

        # Calculate tax summary
        output_tax = (
            request.gstr1_summary.get("total_cgst", 0) +
            request.gstr1_summary.get("total_sgst", 0) +
            request.gstr1_summary.get("total_igst", 0)
        )
        input_tax = (
            request.gstr2b_summary.get("total_cgst", 0) +
            request.gstr2b_summary.get("total_sgst", 0) +
            request.gstr2b_summary.get("total_igst", 0)
        )
        tax_payable = max(0, output_tax - input_tax)
        refund = max(0, input_tax - output_tax)

        # Save XML
        xml_path = _save_xml(current_user.firm_id, request.gstin, request.period, "GSTR-3B", xml_content)

        # Create filing record
        filing = GSTRFilingSubmission(
            firm_id=current_user.firm_id,
            gstin=request.gstin,
            period=request.period,
            return_type="GSTR-3B",
            xml_file_path=xml_path,
            filing_status=GSTRFilingStatus.DRAFT,
            total_cgst=request.gstr1_summary.get("total_cgst", 0),
            total_sgst=request.gstr1_summary.get("total_sgst", 0),
            total_igst=request.gstr1_summary.get("total_igst", 0),
            itc_claimed=input_tax,
            tax_payable=tax_payable,
            refund_available=refund,
        )
        db.add(filing)
        await db.commit()
        await db.refresh(filing)

        logger.info(f"GSTR-3B prepared: {request.gstin} {request.period}")

        return {
            "success": True,
            "filing_id": filing.id,
            "return_type": "GSTR-3B",
            "gstin": request.gstin,
            "period": request.period,
            "message": "GSTR-3B prepared successfully",
            "tax_summary": {
                "output_tax": output_tax,
                "itc_claimed": input_tax,
                "tax_payable": tax_payable,
                "refund_available": refund
            },
            "next_step": "Submit to portal"
        }

    except Exception as e:
        logger.error(f"GSTR-3B preparation error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Preparation failed: {str(e)}")


@router.post("/submit")
async def submit_return(
    filing_id: str,
    login_request: GSTRPortalLoginRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit prepared return to GST portal.

    Requires portal credentials for authentication.
    """
    # Get filing record
    result = await db.execute(
        select(GSTRFilingSubmission).where(
            and_(
                GSTRFilingSubmission.id == filing_id,
                GSTRFilingSubmission.firm_id == current_user.firm_id
            )
        )
    )
    filing = result.scalar_one_or_none()

    if not filing:
        raise HTTPException(status_code=404, detail="Filing not found")

    if not filing.xml_file_path or not os.path.exists(filing.xml_file_path):
        raise HTTPException(status_code=400, detail="XML file not found")

    try:
        # Initialize filing client
        client = GSTRFilingClient(use_staging=True)  # Use staging by default

        # Authenticate
        auth_result = await client.login_with_credentials(
            gstin=login_request.gstin,
            username=login_request.username,
            password=login_request.password
        )

        if not auth_result.get("success"):
            return {
                "success": False,
                "error": auth_result.get("error", "Authentication failed")
            }

        # Read XML
        with open(filing.xml_file_path, "r") as f:
            xml_content = f.read()

        # Submit based on return type
        if filing.return_type == "GSTR-1":
            submission_result = await client.submit_gstr1(
                gstin=login_request.gstin,
                period=filing.period,
                xml_content=xml_content
            )
        else:  # GSTR-3B
            submission_result = await client.submit_gstr3b(
                gstin=login_request.gstin,
                period=filing.period,
                xml_content=xml_content
            )

        if submission_result.get("success"):
            # Update filing record
            filing.acknowledgement_number = submission_result.get("acknowledgement_number")
            filing.filing_status = GSTRFilingStatus.SUBMITTED
            filing.portal_status = "submitted"
            filing.submitted_at = datetime.utcnow()
            filing.submitted_by = current_user.id

            await db.commit()
            await db.refresh(filing)

            logger.info(f"{filing.return_type} submitted: ACK {filing.acknowledgement_number}")

            return {
                "success": True,
                "acknowledgement_number": filing.acknowledgement_number,
                "return_type": filing.return_type,
                "message": f"{filing.return_type} submitted successfully",
                "submitted_at": filing.submitted_at.isoformat(),
                "next_step": "Check filing status regularly"
            }
        else:
            filing.filing_status = GSTRFilingStatus.FAILED
            filing.error_message = submission_result.get("error")
            await db.commit()

            return {
                "success": False,
                "error": submission_result.get("error", "Submission failed")
            }

    except Exception as e:
        logger.error(f"Submission error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/status/{acknowledgement_number}")
async def get_filing_status(
    acknowledgement_number: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get status of filed return from portal."""
    result = await db.execute(
        select(GSTRFilingSubmission).where(
            and_(
                GSTRFilingSubmission.acknowledgement_number == acknowledgement_number,
                GSTRFilingSubmission.firm_id == current_user.firm_id
            )
        )
    )
    filing = result.scalar_one_or_none()

    if not filing:
        raise HTTPException(status_code=404, detail="Filing not found")

    # Try to get updated status from portal
    if filing.acknowledgement_number:
        try:
            client = GSTRFilingClient(use_staging=True)
            portal_status = await client.get_filing_status(acknowledgement_number)

            if portal_status.get("success"):
                # Update local record
                filing.portal_status = portal_status.get("status")
                if portal_status.get("processed_date"):
                    filing.processed_at = datetime.fromisoformat(
                        portal_status.get("processed_date")
                    )
                if portal_status.get("status") == "acknowledged":
                    filing.filing_status = GSTRFilingStatus.ACKNOWLEDGED
                elif portal_status.get("status") == "processed":
                    filing.filing_status = GSTRFilingStatus.PROCESSED
                elif portal_status.get("status") == "rejected":
                    filing.filing_status = GSTRFilingStatus.REJECTED
                    filing.error_message = str(portal_status.get("errors", []))

                await db.commit()
        except Exception as e:
            logger.warning(f"Could not fetch portal status: {str(e)}")

    return GSTRFilingStatusResponse(
        acknowledgement_number=filing.acknowledgement_number,
        return_type=filing.return_type,
        period=filing.period,
        filing_status=filing.filing_status,
        portal_status=filing.portal_status,
        total_tax=filing.total_cgst + filing.total_sgst + filing.total_igst,
        submitted_at=filing.submitted_at,
        processed_at=filing.processed_at
    )


@router.get("/filed-returns")
async def get_filed_returns(
    gstin: Optional[str] = Query(None),
    return_type: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get list of all filed returns."""
    query = select(GSTRFilingSubmission).where(
        and_(
            GSTRFilingSubmission.firm_id == current_user.firm_id,
            GSTRFilingSubmission.filing_status != GSTRFilingStatus.DRAFT
        )
    )

    if gstin:
        query = query.where(GSTRFilingSubmission.gstin == gstin.upper())
    if return_type:
        query = query.where(GSTRFilingSubmission.return_type == return_type.upper())

    result = await db.execute(
        query.order_by(desc(GSTRFilingSubmission.submitted_at))
    )
    filings = result.scalars().all()

    return {
        "total_filed": len(filings),
        "returns": [
            {
                "acknowledgement_number": f.acknowledgement_number,
                "return_type": f.return_type,
                "gstin": f.gstin,
                "period": f.period,
                "filing_status": f.filing_status,
                "portal_status": f.portal_status,
                "submitted_at": f.submitted_at.isoformat() if f.submitted_at else None,
                "total_tax": f.total_cgst + f.total_sgst + f.total_igst
            }
            for f in filings
        ]
    }


@router.post("/amend/{acknowledgement_number}")
async def amend_return(
    acknowledgement_number: str,
    amended_return: GSTR1FilingRequest | GSTR3BFilingRequest,
    login_request: GSTRPortalLoginRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit amended return.

    Uses the same preparation logic but marks as amendment.
    """
    # Get original filing
    result = await db.execute(
        select(GSTRFilingSubmission).where(
            and_(
                GSTRFilingSubmission.acknowledgement_number == acknowledgement_number,
                GSTRFilingSubmission.firm_id == current_user.firm_id
            )
        )
    )
    original_filing = result.scalar_one_or_none()

    if not original_filing:
        raise HTTPException(status_code=404, detail="Original filing not found")

    try:
        # Prepare amended return (similar to prepare endpoints)
        if isinstance(amended_return, GSTR1FilingRequest):
            xml_content = GSTR1XMLGenerator.generate(
                gstin=amended_return.gstin,
                period=amended_return.period,
                company_name=amended_return.company_name,
                sales_invoices=amended_return.sales_invoices,
                amendments=True
            )
            return_type = "GSTR-1"
        else:
            xml_content = GSTR3BXMLGenerator.generate(
                gstin=amended_return.gstin,
                period=amended_return.period,
                company_name=amended_return.company_name,
                gstr1_data=amended_return.gstr1_summary,
                gstr2b_data=amended_return.gstr2b_summary,
                itc_data=amended_return.itc_details,
                payment_data=amended_return.payment_info
            )
            return_type = "GSTR-3B"

        # Save amended XML
        xml_path = _save_xml(current_user.firm_id, login_request.gstin, original_filing.period, f"{return_type}_Amended", xml_content)

        # Submit amendment
        client = GSTRFilingClient(use_staging=True)
        auth_result = await client.login_with_credentials(
            gstin=login_request.gstin,
            username=login_request.username,
            password=login_request.password
        )

        if not auth_result.get("success"):
            return {"success": False, "error": "Authentication failed"}

        amend_result = await client.amend_return(acknowledgement_number, xml_content)

        if amend_result.get("success"):
            # Create new filing record for amendment
            amendment_filing = GSTRFilingSubmission(
                firm_id=current_user.firm_id,
                gstin=login_request.gstin,
                period=original_filing.period,
                return_type=return_type,
                xml_file_path=xml_path,
                filing_status=GSTRFilingStatus.SUBMITTED,
                acknowledgement_number=amend_result.get("amendment_ack_no"),
                is_amendment=True,
                original_ack_no=acknowledgement_number,
                submitted_at=datetime.utcnow(),
                submitted_by=current_user.id,
            )
            db.add(amendment_filing)
            await db.commit()

            return {
                "success": True,
                "amendment_ack_no": amend_result.get("amendment_ack_no"),
                "message": "Amendment submitted successfully"
            }

        return {"success": False, "error": amend_result.get("error", "Amendment failed")}

    except Exception as e:
        logger.error(f"Amendment error: {str(e)}")
        return {"success": False, "error": str(e)}


@router.get("/status-check")
async def gstr_filing_status(current_user: CurrentUser = Depends(get_current_user)):
    """Get GST filing module status and capabilities."""
    return {
        "status": "ok",
        "module": "gstr_filing",
        "capabilities": [
            "prepare_gstr1",
            "prepare_gstr3b",
            "submit_to_portal",
            "track_status",
            "amend_returns",
            "multi_period_support"
        ],
        "supported_returns": ["GSTR-1", "GSTR-3B"],
        "authentication": ["portal_credentials"],
        "features": {
            "xml_generation": "Official IT schema",
            "portal_submission": "Direct to GST portal",
            "amendment_support": "Full amendment workflow",
            "status_tracking": "Real-time updates",
            "filing_history": "Complete audit trail"
        },
        "note": "Uses staging portal for testing, production URL configurable"
    }
