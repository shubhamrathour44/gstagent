"""Basic tests for core module to ensure imports work correctly."""

import pytest
from core.config import JWT_SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, GSP_PROVIDER
from core.exceptions import (
    GSTError, TenantError, ValidationError, NotFoundError,
    InvalidGSTINError, InvalidPANError
)
from core.validators import (
    validate_gstin, validate_pan, validate_email,
    validate_invoice_number, validate_password
)
from core.schemas import ErrorResponse, SuccessResponse, HealthResponse


def test_config_imports():
    """Test that config loads correctly."""
    assert JWT_SECRET_KEY
    assert ACCESS_TOKEN_EXPIRE_MINUTES > 0
    assert GSP_PROVIDER in ["mock", "mastergst", "whitebooks", "iris", "gsthero"]


def test_exception_hierarchy():
    """Test exception classes."""
    exc = GSTError("Test error", "TEST_CODE")
    assert exc.message == "Test error"
    assert exc.code == "TEST_CODE"

    tenant_exc = TenantError()
    assert tenant_exc.code == "TENANT_ERROR"

    val_exc = ValidationError("Invalid input", field="test_field")
    assert val_exc.details["field"] == "test_field"


def test_validate_gstin_valid():
    """Test valid GSTIN validation."""
    valid_gstin = "05ABCDE1234F1Z5"
    result = validate_gstin(valid_gstin)
    assert result == valid_gstin


def test_validate_gstin_invalid():
    """Test invalid GSTIN raises error."""
    with pytest.raises(InvalidGSTINError):
        validate_gstin("invalid")

    with pytest.raises(InvalidGSTINError):
        validate_gstin("00000000000000")  # All zeros


def test_validate_pan_valid():
    """Test valid PAN validation."""
    valid_pan = "AAAAP1234A"
    result = validate_pan(valid_pan)
    assert result == valid_pan


def test_validate_pan_invalid():
    """Test invalid PAN raises error."""
    with pytest.raises(InvalidPANError):
        validate_pan("invalid")


def test_validate_email_valid():
    """Test valid email validation."""
    valid_email = "test@example.com"
    result = validate_email(valid_email)
    assert result == valid_email.lower()


def test_validate_email_invalid():
    """Test invalid email raises error."""
    with pytest.raises(ValidationError):
        validate_email("invalid-email")


def test_validate_password_valid():
    """Test valid password."""
    valid_password = "ValidPass123"
    result = validate_password(valid_password)
    assert result == valid_password


def test_validate_password_invalid():
    """Test invalid passwords."""
    with pytest.raises(ValidationError):
        validate_password("short")  # Too short

    with pytest.raises(ValidationError):
        validate_password("nouppercase123")  # No uppercase

    with pytest.raises(ValidationError):
        validate_password("NOLOWERCASE123")  # No lowercase

    with pytest.raises(ValidationError):
        validate_password("NoDigits")  # No digits


def test_schema_error_response():
    """Test error response schema."""
    response = ErrorResponse(
        code="TEST_ERROR",
        message="Test error message",
        details={"field": "test"}
    )
    assert response.status == "error"
    assert response.code == "TEST_ERROR"
    assert response.message == "Test error message"
    assert response.details["field"] == "test"


def test_schema_success_response():
    """Test success response schema."""
    response = SuccessResponse(
        message="Operation successful",
        data={"id": "123"}
    )
    assert response.status == "success"
    assert response.message == "Operation successful"
    assert response.data["id"] == "123"


def test_schema_health_response():
    """Test health response schema."""
    response = HealthResponse()
    assert response.status == "healthy"
    assert response.service == "gstagent-backend"
    assert response.version == "2.1.0"


if __name__ == "__main__":
    # Run basic tests
    test_config_imports()
    test_exception_hierarchy()
    test_validate_gstin_valid()
    test_validate_email_valid()
    test_validate_password_valid()
    test_schema_error_response()
    print("✅ All core module tests passed!")
