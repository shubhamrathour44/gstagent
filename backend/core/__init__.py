"""Core utilities module for GSTAgent.

Provides:
  - Configuration management
  - Custom exceptions
  - Input validators
  - Common Pydantic schemas
  - Logging utilities
"""

from core.config import (
    JWT_SECRET_KEY,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    DATABASE_URL,
    GSP_PROVIDER,
    SQL_ECHO,
)
from core.exceptions import (
    GSTError,
    TenantError,
    ValidationError,
    NotFoundError,
    AuthenticationError,
    AuthorizationError,
)
from core.validators import (
    validate_gstin,
    validate_email,
    validate_invoice_number,
    validate_pan,
)
from core.schemas import (
    ErrorResponse,
    SuccessResponse,
)

__all__ = [
    # Config
    "JWT_SECRET_KEY",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "DATABASE_URL",
    "GSP_PROVIDER",
    "SQL_ECHO",
    # Exceptions
    "GSTError",
    "TenantError",
    "ValidationError",
    "NotFoundError",
    "AuthenticationError",
    "AuthorizationError",
    # Validators
    "validate_gstin",
    "validate_email",
    "validate_invoice_number",
    "validate_pan",
    # Schemas
    "ErrorResponse",
    "SuccessResponse",
]
