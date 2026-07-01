"""
GST Return Filing Client - Submit GSTR-1 & GSTR-3B to GSP/Portal

Handles:
- Authentication with GSP
- XML submission
- Filing status tracking
- Amendment support
"""

import httpx
import hashlib
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class GSTRFilingStatus(str, Enum):
    """GST return filing status."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    PROCESSED = "processed"
    REJECTED = "rejected"
    AMENDED = "amended"
    FAILED = "failed"


class GSTRFilingClient:
    """
    Client for GST return filing via GSP.

    Workflow:
    1. Prepare XML (offline)
    2. Authenticate with GSP
    3. Submit XML
    4. Get acknowledgement
    5. Track status
    """

    # Production portal
    BASE_URL = "https://services.gst.gov.in"

    # Staging for testing
    STAGING_URL = "https://services-staging.gst.gov.in"

    def __init__(self, use_staging: bool = False):
        """Initialize GST filing client."""
        self.base_url = self.STAGING_URL if use_staging else self.BASE_URL
        self.session_id: Optional[str] = None
        self.auth_token: Optional[str] = None
        self.gstin: Optional[str] = None
        self.authenticated_at: Optional[datetime] = None
        self.timeout = 30.0

    async def login_with_credentials(
        self,
        gstin: str,
        username: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Login with GST username/password.

        Args:
            gstin: 15-digit GSTIN
            username: GST portal username
            password: GST portal password

        Returns:
            Response with session_id and auth_token
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                login_data = {
                    "gstin": gstin.upper(),
                    "username": username,
                    "password": password
                }

                resp = await client.post(
                    f"{self.base_url}/api/authenticate",
                    json=login_data
                )

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "success":
                        self.session_id = data.get("session_id")
                        self.auth_token = data.get("auth_token")
                        self.gstin = gstin.upper()
                        self.authenticated_at = datetime.utcnow()

                        logger.info(f"GST authentication successful: {gstin}")
                        return {
                            "success": True,
                            "message": "Authentication successful",
                            "session_id": self.session_id
                        }

                return {
                    "success": False,
                    "error": data.get("message", "Authentication failed")
                }

        except httpx.ConnectError:
            return {
                "success": False,
                "error": f"Cannot connect to {self.base_url}"
            }
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def submit_gstr1(
        self,
        gstin: str,
        period: str,
        xml_content: str
    ) -> Dict[str, Any]:
        """
        Submit GSTR-1 (Sales Return) to GSP.

        Args:
            gstin: GSTIN
            period: MMYYYY format
            xml_content: Complete GSTR-1 XML

        Returns:
            Acknowledgement details
        """
        if not self.auth_token:
            return {
                "success": False,
                "error": "Not authenticated. Please login first."
            }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Calculate file hash
                file_hash = hashlib.sha256(xml_content.encode()).hexdigest()

                data = {
                    "gstin": gstin.upper(),
                    "period": period,
                    "return_type": "GSTR1",
                    "xml_hash": file_hash,
                    "xml_content": xml_content
                }

                headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "X-Session-Id": self.session_id or ""
                }

                resp = await client.post(
                    f"{self.base_url}/api/submit-gstr1",
                    json=data,
                    headers=headers
                )

                if resp.status_code == 200:
                    result = resp.json()
                    ack_no = result.get("acknowledgement_number")
                    logger.info(f"GSTR-1 submitted successfully: {ack_no}")

                    return {
                        "success": True,
                        "return_type": "GSTR-1",
                        "acknowledgement_number": ack_no,
                        "gstin": gstin,
                        "period": period,
                        "submitted_at": datetime.utcnow().isoformat(),
                        "message": "GSTR-1 submitted successfully"
                    }

                error_msg = resp.json().get("message", f"Submission failed: {resp.status_code}")
                logger.error(f"GSTR-1 submission failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }

        except Exception as e:
            logger.error(f"Submission error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def submit_gstr3b(
        self,
        gstin: str,
        period: str,
        xml_content: str
    ) -> Dict[str, Any]:
        """
        Submit GSTR-3B (Summary Return) to GSP.

        Args:
            gstin: GSTIN
            period: MMYYYY format
            xml_content: Complete GSTR-3B XML

        Returns:
            Acknowledgement details
        """
        if not self.auth_token:
            return {
                "success": False,
                "error": "Not authenticated. Please login first."
            }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                file_hash = hashlib.sha256(xml_content.encode()).hexdigest()

                data = {
                    "gstin": gstin.upper(),
                    "period": period,
                    "return_type": "GSTR3B",
                    "xml_hash": file_hash,
                    "xml_content": xml_content
                }

                headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "X-Session-Id": self.session_id or ""
                }

                resp = await client.post(
                    f"{self.base_url}/api/submit-gstr3b",
                    json=data,
                    headers=headers
                )

                if resp.status_code == 200:
                    result = resp.json()
                    ack_no = result.get("acknowledgement_number")
                    logger.info(f"GSTR-3B submitted successfully: {ack_no}")

                    return {
                        "success": True,
                        "return_type": "GSTR-3B",
                        "acknowledgement_number": ack_no,
                        "gstin": gstin,
                        "period": period,
                        "submitted_at": datetime.utcnow().isoformat(),
                        "message": "GSTR-3B submitted successfully"
                    }

                error_msg = resp.json().get("message", f"Submission failed")
                logger.error(f"GSTR-3B submission failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }

        except Exception as e:
            logger.error(f"Submission error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_filing_status(
        self,
        acknowledgement_number: str
    ) -> Dict[str, Any]:
        """
        Get status of filed return.

        Args:
            acknowledgement_number: Return acknowledgement number

        Returns:
            Filing status and details
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
                    f"{self.base_url}/api/filing-status/{acknowledgement_number}",
                    headers=headers
                )

                if resp.status_code == 200:
                    data = resp.json()
                    logger.info(f"Status retrieved: {acknowledgement_number}")

                    return {
                        "success": True,
                        "acknowledgement_number": acknowledgement_number,
                        "return_type": data.get("return_type"),
                        "status": data.get("status"),
                        "gstin": data.get("gstin"),
                        "period": data.get("period"),
                        "submitted_date": data.get("submitted_date"),
                        "processed_date": data.get("processed_date"),
                        "total_value": data.get("total_value", 0),
                        "errors": data.get("errors", [])
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

    async def amend_return(
        self,
        acknowledgement_number: str,
        amended_xml: str
    ) -> Dict[str, Any]:
        """
        Submit amended return.

        Args:
            acknowledgement_number: Original return's ACK number
            amended_xml: Amended XML content

        Returns:
            Amendment submission result
        """
        if not self.auth_token:
            return {
                "success": False,
                "error": "Not authenticated"
            }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                file_hash = hashlib.sha256(amended_xml.encode()).hexdigest()

                data = {
                    "original_ack_no": acknowledgement_number,
                    "xml_hash": file_hash,
                    "xml_content": amended_xml
                }

                headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "X-Session-Id": self.session_id or ""
                }

                resp = await client.post(
                    f"{self.base_url}/api/amend-return",
                    json=data,
                    headers=headers
                )

                if resp.status_code == 200:
                    result = resp.json()
                    ack_no = result.get("acknowledgement_number")
                    logger.info(f"Amendment submitted: {ack_no}")

                    return {
                        "success": True,
                        "amendment_ack_no": ack_no,
                        "original_ack_no": acknowledgement_number,
                        "message": "Amendment submitted successfully"
                    }

                return {
                    "success": False,
                    "error": resp.json().get("message", "Amendment failed")
                }

        except Exception as e:
            logger.error(f"Amendment error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_filed_returns(
        self,
        gstin: str,
        year: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get list of all filed returns.

        Args:
            gstin: GSTIN
            year: Optional financial year (YYYY-YY)

        Returns:
            List of previous filings
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

                params = {"gstin": gstin.upper()}
                if year:
                    params["year"] = year

                resp = await client.get(
                    f"{self.base_url}/api/filed-returns",
                    headers=headers,
                    params=params
                )

                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "success": True,
                        "gstin": gstin,
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

        # Token expires after 60 minutes
        if datetime.utcnow() - self.authenticated_at > timedelta(minutes=60):
            self.auth_token = None
            self.session_id = None
            return False

        return True

    async def logout(self) -> Dict[str, Any]:
        """Logout from GST portal."""
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
                self.gstin = None

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
