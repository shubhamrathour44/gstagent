"""Common Pydantic schemas used across GSTAgent.

These schemas are shared by multiple modules to ensure consistency
in API responses and data contracts.
"""

from typing import Any, Optional, Generic, TypeVar, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Generic Response Wrappers
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response format."""

    status: str = "error"
    code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "code": "VALIDATION_ERROR",
                "message": "Invalid GSTIN format",
                "details": {"field": "gstin", "gstin": "invalid"}
            }
        }


class SuccessResponse(BaseModel):
    """Standard success response wrapper."""

    status: str = "success"
    message: str = Field(..., description="Success message")
    data: Optional[Any] = Field(None, description="Response data payload")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "data": {}
            }
        }


T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response format."""

    status: str = "success"
    page: int = Field(1, ge=1)
    per_page: int = Field(50, ge=1, le=1000)
    total: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=1)
    items: list[T] = Field(default_factory=list)
    has_next: bool = False
    has_prev: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "page": 1,
                "per_page": 50,
                "total": 150,
                "total_pages": 3,
                "items": [],
                "has_next": True,
                "has_prev": False
            }
        }


# ============================================================================
# Audit & Metadata
# ============================================================================

class TimestampedModel(BaseModel):
    """Base model with created_at and updated_at timestamps."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AuditableModel(TimestampedModel):
    """Base model with audit information."""

    created_by: Optional[str] = Field(None, description="User ID who created this")
    updated_by: Optional[str] = Field(None, description="User ID who last updated this")


# ============================================================================
# Common Fields
# ============================================================================

class GSTINField(BaseModel):
    """Mixin for models that include GSTIN."""

    gstin: str = Field(
        ...,
        pattern=r"^[0-9A-Z]{15}$",
        description="15-character GST Identification Number"
    )


class PeriodField(BaseModel):
    """Mixin for models with GST return period."""

    period: str = Field(
        ...,
        pattern=r"^\d{6}$",
        description="GST return period in MMYYYY format (e.g., 042026)"
    )


class FirmScopedModel(BaseModel):
    """Base for models that are scoped to a firm (multi-tenant)."""

    firm_id: str = Field(..., description="Tenant firm ID for isolation")


class ClientScopedModel(GSTINField):
    """Base for models that belong to a specific client."""

    client_id: str = Field(..., description="Client ID this relates to")


# ============================================================================
# Health & Status
# ============================================================================

class HealthResponse(BaseModel):
    """API health check response."""

    status: str = "healthy"
    service: str = "gstagent-backend"
    version: str = "2.1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "gstagent-backend",
                "version": "2.1.0",
                "timestamp": "2026-06-30T12:00:00"
            }
        }


class ModuleInfo(BaseModel):
    """Information about available modules."""

    name: str
    version: str
    description: str
    endpoints: int


class ModulesResponse(BaseModel):
    """List of available modules."""

    status: str = "success"
    modules: list[ModuleInfo]

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "modules": [
                    {
                        "name": "auth",
                        "version": "1.0.0",
                        "description": "User authentication and management",
                        "endpoints": 5
                    }
                ]
            }
        }


# ============================================================================
# Pagination Request
# ============================================================================

class PaginationParams(BaseModel):
    """Query parameters for paginated endpoints."""

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(50, ge=1, le=1000, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


# ============================================================================
# Filtering & Search
# ============================================================================

class FilterOperator(str, Enum):
    """Supported filter operators."""

    EQ = "eq"                   # equals
    NEQ = "neq"                 # not equals
    GT = "gt"                   # greater than
    GTE = "gte"                 # greater than or equal
    LT = "lt"                   # less than
    LTE = "lte"                 # less than or equal
    IN = "in"                   # in list
    CONTAINS = "contains"       # contains substring
    STARTS_WITH = "starts_with" # starts with
    ENDS_WITH = "ends_with"     # ends with


class FilterCondition(BaseModel):
    """Single filter condition."""

    field: str = Field(..., description="Field to filter on")
    operator: FilterOperator = Field(default=FilterOperator.EQ, description="Filter operator")
    value: Any = Field(..., description="Filter value")


class BatchOperation(BaseModel):
    """Generic batch operation request."""

    operation: str = Field(..., description="Operation to perform (e.g., 'delete', 'export')")
    ids: list[str] = Field(..., min_items=1, description="List of resource IDs")
    parameters: Optional[dict] = Field(None, description="Additional operation parameters")


class BatchOperationResponse(BaseModel):
    """Response from batch operation."""

    status: str = "success"
    operation: str
    total: int = Field(..., description="Total items requested")
    succeeded: int = Field(..., description="Successfully processed")
    failed: int = Field(..., description="Failed to process")
    errors: list[dict] = Field(default_factory=list, description="Detailed error info")


# ============================================================================
# Entity Metadata
# ============================================================================

class EntityMetadata(BaseModel):
    """Metadata about an entity."""

    id: str
    type: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    version: int = Field(default=1, ge=1, description="Record version for optimistic locking")


class EntityReference(BaseModel):
    """Reference to another entity."""

    id: str = Field(..., description="Entity ID")
    type: str = Field(..., description="Entity type (e.g., 'client', 'reconciliation')")
    name: Optional[str] = Field(None, description="Display name")
    url: Optional[str] = Field(None, description="API endpoint URL for this entity")
