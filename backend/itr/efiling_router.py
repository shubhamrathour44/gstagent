"""
E-Filing Router - API endpoints for ITR submission to tax portal.

Endpoints:
- POST /prepare - Generate ITR XML (ready to submit)
- POST /submit - Submit to e-filing portal
- GET /status/{ack_no} - Track submission status
- GET /download-itr-v/{ack_no} - Download ITR-V for verification
- POST /upload-signed-itr-v/{ack_no} - Upload digitally signed ITR-V
- GET /filed-returns - List all filed returns
"""

import os
import hashlib
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from auth import CurrentUser, get_current_user
from database import get_db, EFilingSubmission
from .router import ITRReturn
from .xml_generator import ITRXMLGenerator
from .efiling_client import EFilingClient, EFilingStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/itr-efiling", tags=["ITR E-Filing"])

# Configuration
XML_STORAGE_DIR = "uploads/itr_xml"
os.makedirs(XML_STORAGE_DIR, exist_ok=True)


# ── SCHEMAS ────────────────────────────────────────────────────────────────────

class PrepareEFilingRequest(BaseModel):
    """Request to generate ITR XML."""
    itr_return_id: str
    pan: str
    name: str
    dob: Optional[str] = None  # DDMMYYYY, required for ITR-1/2/7
    age: Optional[int] = None  # For ITR-2


class EFilingStatusResponse(BaseModel):
    """E-filing submission status."""
    acknowledgement_number: Optional[str]
    submission_status: str
    itr_type: str
    submitted_at: Optional[datetime]
    itr_v_signed: bool
    portal_status: Optional[str]
    refund_status: Optional[str]
    refund_amount: float


class SubmitEFilingRequest(BaseModel):
    """Request to submit ITR to portal."""
    pan: str
    password: str
    itr_return_id: str
    use_otp: bool = False  # If True, user must verify OTP


class PortalCredentialsRequest(BaseModel):
    """Portal login credentials."""
    pan: str
    password: Optional[str] = None
    otp: Optional[str] = None
    dob: Optional[str] = None


# ── HELPERS ────────────────────────────────────────────────────────────────────

def _save_xml(firm_id: str, pan: str, ay: str, xml_content: str) -> str:
    """Save XML to disk and return file path."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"ITR_{pan}_{ay}_{timestamp}.xml"
    firm_dir = os.path.join(XML_STORAGE_DIR, firm_id)
    os.makedirs(firm_dir, exist_ok=True)

    file_path = os.path.join(firm_dir, filename)
    with open(file_path, "w") as f:
        f.write(xml_content)

    return file_path


def _calculate_file_hash(content: str) -> str:
    """Calculate SHA256 hash of XML content."""
    return hashlib.sha256(content.encode()).hexdigest()


# ── ENDPOINTS ──────────────────────────────────────────────────────────────────

@router.post("/prepare")
async def prepare_efiling(
    request: PrepareEFilingRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate ITR XML ready for e-filing submission.

    Returns XML that can be submitted to the portal.
    """
    # Get ITR return
    result = await db.execute(
        select(ITRReturn).where(
            and_(
                ITRReturn.id == request.itr_return_id,
                ITRReturn.firm_id == current_user.firm_id
            )
        )
    )
    itr = result.scalar_one_or_none()

    if not itr:
        raise HTTPException(status_code=404, detail="ITR return not found")

    try:
        income_data = itr.income_data or {}
        tax_computation = itr.tax_computation or {}

        # Merge for XML generation
        merged_data = {**income_data, **tax_computation}

        # Generate XML based on ITR type
        if itr.itr_type == "ITR-1":
            xml_content = ITRXMLGenerator.generate_itr1(
                pan=itr.pan,
                name=itr.client_name,
                dob=request.dob or "",
                ay=itr.ay,
                income_data=merged_data
            )
        elif itr.itr_type == "ITR-2":
            xml_content = ITRXMLGenerator.generate_itr2(
                pan=itr.pan,
                name=itr.client_name,
                dob=request.dob or "",
                age=request.age or 30,
                ay=itr.ay,
                income_data=merged_data
            )
        elif itr.itr_type == "ITR-3":
            xml_content = ITRXMLGenerator.generate_itr3(
                pan=itr.pan,
                name=itr.client_name,
                ay=itr.ay,
                income_data=merged_data
            )
        elif itr.itr_type == "ITR-4":
            xml_content = ITRXMLGenerator.generate_itr4(
                pan=itr.pan,
                name=itr.client_name,
                ay=itr.ay,
                income_data=merged_data
            )
        elif itr.itr_type == "ITR-7":
            xml_content = ITRXMLGenerator.generate_itr7(
                pan=itr.pan,
                entity_name=itr.client_name,
                ay=itr.ay,
                income_data=merged_data
            )
        else:
            raise ValueError(f"Unsupported ITR type: {itr.itr_type}")

        # Save XML
        xml_path = _save_xml(current_user.firm_id, itr.pan, itr.ay, xml_content)
        file_hash = _calculate_file_hash(xml_content)

        # Create/update submission record
        submission = EFilingSubmission(
            firm_id=current_user.firm_id,
            itr_return_id=request.itr_return_id,
            pan=itr.pan,
            assessment_year=itr.ay,
            itr_type=itr.itr_type,
            xml_file_path=xml_path,
            xml_file_hash=file_hash,
            submission_status=EFilingStatus.DRAFT,
        )
        db.add(submission)
        await db.commit()
        await db.refresh(submission)

        logger.info(f"ITR XML prepared for {itr.pan} AY {itr.ay}")

        return {
            "success": True,
            "submission_id": submission.id,
            "message": f"{itr.itr_type} XML prepared successfully",
            "pan": itr.pan,
            "ay": itr.ay,
            "file_hash": file_hash,
            "file_size": len(xml_content),
            "next_step": "Submit to portal or download for manual review"
        }

    except Exception as e:
        logger.error(f"XML generation error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"XML generation failed: {str(e)}")


@router.post("/submit")
async def submit_to_portal(
    request: SubmitEFilingRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit ITR to e-filing portal.

    Authenticates with portal and uploads XML.
    """
    # Get submission record
    result = await db.execute(
        select(EFilingSubmission).where(
            and_(
                EFilingSubmission.itr_return_id == request.itr_return_id,
                EFilingSubmission.firm_id == current_user.firm_id
            )
        )
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="E-filing submission not found")

    if not submission.xml_file_path or not os.path.exists(submission.xml_file_path):
        raise HTTPException(status_code=400, detail="XML file not found. Prepare XML first.")

    try:
        # Initialize e-filing client
        client = EFilingClient(use_staging=True)  # Use staging by default

        # Authenticate
        if request.use_otp:
            # Request OTP
            auth_result = await client.request_otp(request.pan)
            if not auth_result.get("success"):
                return {
                    "success": False,
                    "message": "OTP requested. Please verify with OTP.",
                    "next_step": "Call /verify-otp endpoint"
                }
        else:
            # Login with password
            auth_result = await client.login_with_credentials(
                pan=request.pan,
                password=request.password,
                dob=""
            )

            if not auth_result.get("success"):
                return {
                    "success": False,
                    "error": auth_result.get("error", "Authentication failed")
                }

        # Read XML file
        with open(submission.xml_file_path, "r") as f:
            xml_content = f.read()

        # Upload to portal
        upload_result = await client.upload_itr_xml(
            xml_content=xml_content,
            pan=submission.pan,
            ay=submission.assessment_year,
            itr_type=submission.itr_type
        )

        if upload_result.get("success"):
            # Update submission record
            submission.acknowledgement_number = upload_result.get("acknowledgement_number")
            submission.submission_status = EFilingStatus.SUBMITTED
            submission.submitted_at = datetime.utcnow()
            submission.submitted_by = current_user.id
            submission.portal_status = "submitted"

            await db.commit()
            await db.refresh(submission)

            logger.info(f"ITR submitted: ACK {submission.acknowledgement_number}")

            return {
                "success": True,
                "acknowledgement_number": submission.acknowledgement_number,
                "message": "ITR submitted successfully to e-filing portal",
                "submitted_at": submission.submitted_at.isoformat(),
                "next_step": "Download ITR-V for verification within 30 days"
            }
        else:
            submission.submission_status = EFilingStatus.FAILED
            submission.error_message = upload_result.get("error")
            await db.commit()

            return {
                "success": False,
                "error": upload_result.get("error", "Upload failed")
            }

    except Exception as e:
        logger.error(f"Submission error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/verify-otp")
async def verify_otp_and_submit(
    pan: str,
    otp: str,
    dob: str,
    itr_return_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify OTP and submit ITR (step 2 of OTP flow).
    """
    result = await db.execute(
        select(EFilingSubmission).where(
            and_(
                EFilingSubmission.itr_return_id == itr_return_id,
                EFilingSubmission.firm_id == current_user.firm_id
            )
        )
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="E-filing submission not found")

    try:
        client = EFilingClient(use_staging=True)

        # Verify OTP
        auth_result = await client.verify_otp(
            pan=pan,
            otp=otp,
            dob=dob
        )

        if not auth_result.get("success"):
            return {
                "success": False,
                "error": auth_result.get("error", "OTP verification failed")
            }

        # Read XML
        with open(submission.xml_file_path, "r") as f:
            xml_content = f.read()

        # Upload
        upload_result = await client.upload_itr_xml(
            xml_content=xml_content,
            pan=submission.pan,
            ay=submission.assessment_year,
            itr_type=submission.itr_type
        )

        if upload_result.get("success"):
            submission.acknowledgement_number = upload_result.get("acknowledgement_number")
            submission.submission_status = EFilingStatus.SUBMITTED
            submission.submitted_at = datetime.utcnow()
            submission.submitted_by = current_user.id

            await db.commit()

            return {
                "success": True,
                "acknowledgement_number": submission.acknowledgement_number,
                "message": "ITR submitted successfully"
            }

        return {
            "success": False,
            "error": upload_result.get("error", "Upload failed")
        }

    except Exception as e:
        logger.error(f"OTP verification error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/status/{acknowledgement_number}")
async def get_submission_status(
    acknowledgement_number: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get status of submitted ITR from portal."""
    result = await db.execute(
        select(EFilingSubmission).where(
            and_(
                EFilingSubmission.acknowledgement_number == acknowledgement_number,
                EFilingSubmission.firm_id == current_user.firm_id
            )
        )
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Try to get updated status from portal
    if submission.acknowledgement_number:
        try:
            client = EFilingClient(use_staging=True)
            portal_status = await client.get_submission_status(acknowledgement_number)

            if portal_status.get("success"):
                # Update local record with portal status
                submission.portal_status = portal_status.get("status")
                submission.refund_status = portal_status.get("refund_status")
                submission.refund_amount = portal_status.get("refund_amount", 0)

                if portal_status.get("processed_date"):
                    submission.processed_at = datetime.fromisoformat(
                        portal_status.get("processed_date")
                    )

                await db.commit()
        except Exception as e:
            logger.warning(f"Could not fetch portal status: {str(e)}")

    return EFilingStatusResponse(
        acknowledgement_number=submission.acknowledgement_number,
        submission_status=submission.submission_status,
        itr_type=submission.itr_type,
        submitted_at=submission.submitted_at,
        itr_v_signed=submission.itr_v_signed,
        portal_status=submission.portal_status,
        refund_status=submission.refund_status,
        refund_amount=submission.refund_amount
    )


@router.get("/download-itr-v/{acknowledgement_number}")
async def download_itr_v(
    acknowledgement_number: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download ITR-V (verification copy) for digital signature."""
    result = await db.execute(
        select(EFilingSubmission).where(
            and_(
                EFilingSubmission.acknowledgement_number == acknowledgement_number,
                EFilingSubmission.firm_id == current_user.firm_id
            )
        )
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if not submission.acknowledgement_number:
        raise HTTPException(status_code=400, detail="ITR not submitted to portal yet")

    try:
        client = EFilingClient(use_staging=True)
        success, pdf_bytes = await client.download_itr_v(acknowledgement_number)

        if not success or not pdf_bytes:
            raise HTTPException(status_code=400, detail="Could not download ITR-V")

        # Save locally
        itr_v_dir = os.path.join(XML_STORAGE_DIR, current_user.firm_id, "itr_v")
        os.makedirs(itr_v_dir, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"ITR-V_{submission.pan}_{timestamp}.pdf"
        file_path = os.path.join(itr_v_dir, filename)

        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        submission.itr_v_generated = True
        submission.itr_v_file_path = file_path
        await db.commit()

        logger.info(f"ITR-V downloaded: {acknowledgement_number}")

        return {
            "success": True,
            "message": "ITR-V downloaded successfully",
            "file_size": len(pdf_bytes),
            "pan": submission.pan,
            "ay": submission.assessment_year,
            "next_step": "Sign the PDF with DSC/Aadhar and upload"
        }

    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/upload-signed-itr-v/{acknowledgement_number}")
async def upload_signed_itr_v(
    acknowledgement_number: str,
    signed_pdf: UploadFile = File(...),
    signature_method: str = "dsc",
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload digitally signed ITR-V to complete verification."""
    result = await db.execute(
        select(EFilingSubmission).where(
            and_(
                EFilingSubmission.acknowledgement_number == acknowledgement_number,
                EFilingSubmission.firm_id == current_user.firm_id
            )
        )
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    try:
        # Read PDF content
        pdf_content = await signed_pdf.read()

        # Upload to portal
        client = EFilingClient(use_staging=True)
        upload_result = await client.upload_signed_itr_v(
            acknowledgement_number=acknowledgement_number,
            signed_pdf=pdf_content,
            signature_method=signature_method
        )

        if upload_result.get("success"):
            submission.itr_v_signed = True
            submission.itr_v_signed_at = datetime.utcnow()
            submission.signature_method = signature_method
            submission.submission_status = EFilingStatus.ITR_V_GENERATED

            await db.commit()

            logger.info(f"Signed ITR-V uploaded: {acknowledgement_number}")

            return {
                "success": True,
                "message": "ITR-V verification completed successfully",
                "verified_at": submission.itr_v_signed_at.isoformat()
            }

        return {
            "success": False,
            "error": upload_result.get("error", "Upload failed")
        }

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/filed-returns")
async def get_filed_returns(
    pan: Optional[str] = Query(None),
    ay: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get list of all filed returns for the firm."""
    query = select(EFilingSubmission).where(
        EFilingSubmission.firm_id == current_user.firm_id
    )

    if pan:
        query = query.where(EFilingSubmission.pan == pan.upper())
    if ay:
        query = query.where(EFilingSubmission.assessment_year == ay)

    result = await db.execute(
        query.where(
            EFilingSubmission.submission_status != EFilingStatus.DRAFT
        ).order_by(desc(EFilingSubmission.submitted_at))
    )
    submissions = result.scalars().all()

    return {
        "total_filed": len(submissions),
        "returns": [
            EFilingStatusResponse(
                acknowledgement_number=s.acknowledgement_number,
                submission_status=s.submission_status,
                itr_type=s.itr_type,
                submitted_at=s.submitted_at,
                itr_v_signed=s.itr_v_signed,
                portal_status=s.portal_status,
                refund_status=s.refund_status,
                refund_amount=s.refund_amount
            )
            for s in submissions
        ]
    }


@router.get("/status")
async def efiling_status(current_user: CurrentUser = Depends(get_current_user)):
    """Get e-filing module status and capabilities."""
    return {
        "status": "ok",
        "module": "itr_efiling",
        "capabilities": [
            "generate_itr_xml",
            "submit_to_portal",
            "track_status",
            "download_itr_v",
            "upload_signed_itr_v",
            "filed_returns_list"
        ],
        "supported_forms": ["ITR-1", "ITR-2", "ITR-3", "ITR-4", "ITR-7"],
        "authentication_methods": ["password", "otp", "dsc"],
        "portal": "staging (for testing)",
        "note": "Use production URL in settings for live submissions"
    }
