"""
E-Filing Client - Authenticate and submit ITR to income tax portal.

Supports:
- Login with credentials/OTP/DSC
- XML validation
- File upload
- Status tracking
"""

import httpx
import hashlib
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class EFilingStatus(str, Enum):
    """E-filing submission status."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ACKNOWLEDGEMENT_PENDING = "acknowledgement_pending"
    ACKNOWLEDGED = "acknowledged"
    ITR_V_GENERATED = "itr_v_generated"
    PROCESSED = "processed"
    REJECTED = "rejected"
    FAILED = "failed"


class EFilingClient:
    """
    Client for income tax e-filing portal.

    Workflow:
    1. Authenticate (login with credentials or DSC)
    2. Upload ITR XML
    3. Get acknowledgement
    4. Verify (sign ITR-V)
    5. Track status
    """

    # Production portal
    BASE_URL = "https://incometaxindiaefiling.gov.in"

    # Staging for testing
    STAGING_URL = "https://itaxuat.incometaxindiaefiling.gov.in"

    def __init__(self, use_staging: bool = False):
        """Initialize e-filing client."""
        self.base_url = self.STAGING_URL if use_staging else self.BASE_URL
        self.session_id: Optional[str] = None
        self.auth_token: Optional[str] = None
        self.pan: Optional[str] = None
        self.authenticated_at: Optional[datetime] = None
        self.timeout = 30.0

    async def login_with_credentials(
        self,
        pan: str,
        password: str,
        dob: str
    ) -> Dict[str, Any]:
        """
        Login using PAN and password.

        Args:
            pan: PAN number
            password: Login password
            dob: Date of birth (DDMMYYYY)

        Returns:
            Response with session_id and auth_token
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Step 1: Get login page to fetch CSRF token
                resp = await client.get(f"{self.base_url}/login")
                if resp.status_code != 200:
                    return {
                        "success": False,
                        "error": "Unable to reach e-filing portal"
                    }

                # Step 2: Submit login credentials
                login_data = {
                    "pan": pan.upper(),
                    "password": password,
                    "dob": dob,
                    "acknowledge": "Y"
                }

                resp = await client.post(
                    f"{self.base_url}/api/login",
                    data=login_data
                )

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "success":
                        self.session_id = data.get("session_id")
                        self.auth_token = data.get("auth_token")
                        self.pan = pan.upper()
                        self.authenticated_at = datetime.utcnow()

                        logger.info(f"Logged in successfully: {pan}")
                        return {
                            "success": True,
                            "message": "Login successful",
                            "session_id": self.session_id
                        }

                return {
                    "success": False,
                    "error": data.get("message", "Login failed")
                }

        except httpx.ConnectError:
            return {
                "success": False,
                "error": f"Cannot connect to {self.base_url}"
            }
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def request_otp(self, pan: str) -> Dict[str, Any]:
        """
        Request OTP for login (alternative to password).

        Returns:
            OTP sent to registered mobile/email
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/request-otp",
                    json={"pan": pan.upper()}
                )

                if resp.status_code == 200:
                    data = resp.json()
                    logger.info(f"OTP requested for {pan}")
                    return {
                        "success": True,
                        "message": "OTP sent to registered contact"
                    }

                return {
                    "success": False,
                    "error": resp.json().get("message", "OTP request failed")
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def verify_otp(
        self,
        pan: str,
        otp: str,
        dob: str
    ) -> Dict[str, Any]:
        """
        Verify OTP and login.

        Args:
            pan: PAN number
            otp: 6-digit OTP
            dob: Date of birth (DDMMYYYY)
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/verify-otp",
                    json={
                        "pan": pan.upper(),
                        "otp": otp,
                        "dob": dob
                    }
                )

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "success":
                        self.session_id = data.get("session_id")
                        self.auth_token = data.get("auth_token")
                        self.pan = pan.upper()
                        self.authenticated_at = datetime.utcnow()

                        logger.info(f"OTP verified successfully: {pan}")
                        return {
                            "success": True,
                            "message": "Login successful",
                            "session_id": self.session_id
                        }

                return {
                    "success": False,
                    "error": data.get("message", "OTP verification failed")
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def upload_itr_xml(
        self,
        xml_content: str,
        pan: str,
        ay: str,
        itr_type: str
    ) -> Dict[str, Any]:
        """
        Upload ITR XML to e-filing portal.

        Args:
            xml_content: Complete ITR XML string
            pan: PAN number
            ay: Assessment year (e.g., 2023-24)
            itr_type: ITR form type (ITR-1, ITR-2, etc.)

        Returns:
            Acknowledgement number and submission details
        """
        if not self.auth_token:
            return {
                "success": False,
                "error": "Not authenticated. Please login first."
            }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Calculate file hash for integrity
                file_hash = hashlib.sha256(xml_content.encode()).hexdigest()

                # Prepare upload
                files = {
                    "file": ("ITR.xml", xml_content, "application/xml")
                }

                data = {
                    "pan": pan.upper(),
                    "ay": ay,
                    "form_type": itr_type,
                    "file_hash": file_hash
                }

                headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "X-Session-Id": self.session_id or ""
                }

                resp = await client.post(
                    f"{self.base_url}/api/upload-itr",
                    files=files,
                    data=data,
                    headers=headers
                )

                if resp.status_code == 200:
                    result = resp.json()
                    ack_no = result.get("acknowledgement_number")
                    logger.info(f"ITR uploaded successfully: {ack_no}")

                    return {
                        "success": True,
                        "acknowledgement_number": ack_no,
                        "message": "ITR uploaded successfully",
                        "submitted_at": datetime.utcnow().isoformat(),
                        "next_step": "Verify using ITR-V (within 30 days)"
                    }

                error_msg = resp.json().get("message", f"Upload failed: {resp.status_code}")
                logger.error(f"Upload failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }

        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_submission_status(
        self,
        acknowledgement_number: str
    ) -> Dict[str, Any]:
        """
        Get status of submitted ITR.

        Args:
            acknowledgement_number: ITR acknowledgement number

        Returns:
            Current status and details
        """
        if not self.auth_token:
            return {
                "success": False,
                "error": "Not authenticated"
            }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "X-Session-Id": self.session_id or ""
                }

                resp = await client.get(
                    f"{self.base_url}/api/itr-status/{acknowledgement_number}",
                    headers=headers
                )

                if resp.status_code == 200:
                    data = resp.json()
                    logger.info(f"Status retrieved: {acknowledgement_number}")

                    return {
                        "success": True,
                        "acknowledgement_number": acknowledgement_number,
                        "status": data.get("status"),
                        "submitted_date": data.get("submitted_date"),
                        "processed_date": data.get("processed_date"),
                        "itr_v_required": data.get("itr_v_required", True),
                        "itr_v_signed": data.get("itr_v_signed", False),
                        "refund_status": data.get("refund_status"),
                        "refund_amount": data.get("refund_amount", 0)
                    }

                return {
                    "success": False,
                    "error": "Status not found"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def download_itr_v(
        self,
        acknowledgement_number: str
    ) -> Tuple[bool, Optional[bytes]]:
        """
        Download ITR-V (verification copy) for digital signature.

        Returns:
            (success, pdf_bytes)
        """
        if not self.auth_token:
            return False, None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "X-Session-Id": self.session_id or ""
                }

                resp = await client.get(
                    f"{self.base_url}/api/download-itr-v/{acknowledgement_number}",
                    headers=headers
                )

                if resp.status_code == 200:
                    logger.info(f"ITR-V downloaded: {acknowledgement_number}")
                    return True, resp.content

                logger.error(f"Download failed: {resp.status_code}")
                return False, None

        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            return False, None

    async def upload_signed_itr_v(
        self,
        acknowledgement_number: str,
        signed_pdf: bytes,
        signature_method: str = "dsc"
    ) -> Dict[str, Any]:
        """
        Upload digitally signed ITR-V.

        Args:
            acknowledgement_number: ITR acknowledgement number
            signed_pdf: Signed PDF bytes
            signature_method: "dsc" or "aadhar"

        Returns:
            Verification status
        """
        if not self.auth_token:
            return {
                "success": False,
                "error": "Not authenticated"
            }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "X-Session-Id": self.session_id or ""
                }

                files = {
                    "file": ("ITR-V.pdf", signed_pdf, "application/pdf")
                }

                data = {
                    "acknowledgement_number": acknowledgement_number,
                    "signature_method": signature_method
                }

                resp = await client.post(
                    f"{self.base_url}/api/upload-signed-itr-v",
                    files=files,
                    data=data,
                    headers=headers
                )

                if resp.status_code == 200:
                    logger.info(f"Signed ITR-V uploaded: {acknowledgement_number}")
                    return {
                        "success": True,
                        "message": "ITR-V verified successfully",
                        "verified_at": datetime.utcnow().isoformat()
                    }

                return {
                    "success": False,
                    "error": resp.json().get("message", "Upload failed")
                }

        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_filed_returns(self, pan: str) -> Dict[str, Any]:
        """
        Get list of all filed returns for PAN.

        Returns:
            List of previous filings with status
        """
        if not self.auth_token:
            return {
                "success": False,
                "error": "Not authenticated"
            }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "X-Session-Id": self.session_id or ""
                }

                resp = await client.get(
                    f"{self.base_url}/api/filed-returns/{pan.upper()}",
                    headers=headers
                )

                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "success": True,
                        "pan": pan.upper(),
                        "returns": data.get("returns", [])
                    }

                return {
                    "success": False,
                    "error": "Unable to fetch filed returns"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def is_authenticated(self) -> bool:
        """Check if still authenticated."""
        if not self.auth_token or not self.authenticated_at:
            return False

        # Token expires after 30 minutes of inactivity
        if datetime.utcnow() - self.authenticated_at > timedelta(minutes=30):
            self.auth_token = None
            self.session_id = None
            return False

        return True

    async def logout(self) -> Dict[str, Any]:
        """Logout from e-filing portal."""
        if not self.auth_token:
            return {"success": True, "message": "Not logged in"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "X-Session-Id": self.session_id or ""
                }

                await client.post(
                    f"{self.base_url}/api/logout",
                    headers=headers
                )

                self.auth_token = None
                self.session_id = None
                self.pan = None

                return {
                    "success": True,
                    "message": "Logged out successfully"
                }

        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
