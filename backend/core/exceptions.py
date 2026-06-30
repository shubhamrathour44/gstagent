"""Custom exception classes for GSTAgent.

These exceptions provide domain-specific error handling and can be converted
to appropriate HTTP responses by FastAPI exception handlers.
"""

from typing import Any, Optional


class GSTError(Exception):
    """Base exception for all GST-related errors."""

    def __init__(self, message: str, code: str = "GST_ERROR", details: Optional[dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class TenantError(GSTError):
    """Raised when tenant isolation is violated."""

    def __init__(self, message: str = "Tenant access denied", **kwargs):
        super().__init__(message, "TENANT_ERROR", **kwargs)


class ValidationError(GSTError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        super().__init__(message, "VALIDATION_ERROR", details)


class NotFoundError(GSTError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        message: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if entity_type:
            details["entity_type"] = entity_type
        if entity_id:
            details["entity_id"] = entity_id
        super().__init__(message, "NOT_FOUND", details)


class AuthenticationError(GSTError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, "AUTHENTICATION_ERROR", **kwargs)


class AuthorizationError(GSTError):
    """Raised when a user lacks required permissions."""

    def __init__(self, message: str = "Unauthorized access", **kwargs):
        super().__init__(message, "AUTHORIZATION_ERROR", **kwargs)


class DuplicateError(GSTError):
    """Raised when attempting to create a duplicate resource."""

    def __init__(
        self,
        message: str,
        entity_type: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if entity_type:
            details["entity_type"] = entity_type
        super().__init__(message, "DUPLICATE_ERROR", details)


class DatabaseError(GSTError):
    """Raised when database operations fail."""

    def __init__(self, message: str = "Database operation failed", **kwargs):
        super().__init__(message, "DATABASE_ERROR", **kwargs)


class ExternalServiceError(GSTError):
    """Raised when external service calls fail (GSP, Tally, Zoho, etc)."""

    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if service_name:
            details["service"] = service_name
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details)


class ReconciliationError(GSTError):
    """Raised when reconciliation processing fails."""

    def __init__(
        self,
        message: str,
        stage: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if stage:
            details["stage"] = stage  # e.g., "parsing", "matching", "analysis"
        super().__init__(message, "RECONCILIATION_ERROR", details)


class InvalidGSTINError(ValidationError):
    """Raised when GSTIN format is invalid."""

    def __init__(self, gstin: str, **kwargs):
        super().__init__(
            f"Invalid GSTIN format: {gstin}",
            field="gstin",
            details={"gstin": gstin},
            **kwargs
        )


class InvalidPANError(ValidationError):
    """Raised when PAN format is invalid."""

    def __init__(self, pan: str, **kwargs):
        super().__init__(
            f"Invalid PAN format: {pan}",
            field="pan",
            details={"pan": pan},
            **kwargs
        )


class FileUploadError(ValidationError):
    """Raised when file upload validation fails."""

    def __init__(
        self,
        message: str,
        filename: Optional[str] = None,
        file_type: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if filename:
            details["filename"] = filename
        if file_type:
            details["file_type"] = file_type
        super().__init__(message, field="file", details=details, **kwargs)


class GSPIntegrationError(ExternalServiceError):
    """Raised when GSP (GST Portal) integration fails."""

    def __init__(self, message: str, gstin: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if gstin:
            details["gstin"] = gstin
        super().__init__(
            message,
            service_name="gsp",
            details=details,
            **kwargs
        )


class TallyIntegrationError(ExternalServiceError):
    """Raised when Tally integration fails."""

    def __init__(self, message: str, company: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if company:
            details["company"] = company
        super().__init__(
            message,
            service_name="tally",
            details=details,
            **kwargs
        )


class ZohoIntegrationError(ExternalServiceError):
    """Raised when Zoho integration fails."""

    def __init__(self, message: str, org_id: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if org_id:
            details["org_id"] = org_id
        super().__init__(
            message,
            service_name="zoho",
            details=details,
            **kwargs
        )
