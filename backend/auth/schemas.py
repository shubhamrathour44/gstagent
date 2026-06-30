"""Pydantic schemas for authentication endpoints."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator
from core.validators import validate_email, validate_password, validate_name


class RegisterFirmRequest(BaseModel):
    """Request to register a new CA firm."""

    firm_name: str = Field(..., min_length=3, max_length=200, description="CA firm name")
    email: str = Field(..., description="Email for firm and admin user")
    password: str = Field(..., min_length=8, description="Admin user password")
    admin_name: str = Field(..., min_length=2, max_length=200, description="Admin user full name")
    phone: Optional[str] = Field(None, description="Firm contact phone")
    city: Optional[str] = Field(None, description="Firm location")

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, v: str) -> str:
        return validate_email(v)

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, v: str) -> str:
        return validate_password(v)

    @field_validator("firm_name")
    @classmethod
    def normalize_firm_name(cls, v: str) -> str:
        return validate_name(v, min_length=3, max_length=200)

    @field_validator("admin_name")
    @classmethod
    def normalize_admin_name(cls, v: str) -> str:
        return validate_name(v, min_length=2, max_length=200)


class LoginRequest(BaseModel):
    """Request to login a user."""

    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, v: str) -> str:
        return validate_email(v)


class TokenResponse(BaseModel):
    """JWT token response on successful authentication."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    firm_id: str = Field(..., description="Firm ID")
    firm_name: str = Field(..., description="Firm name")
    user_id: str = Field(..., description="User ID")
    user_name: str = Field(..., description="User full name")
    role: str = Field(..., description="User role (ca_admin, ca_staff)")
    expires_in: int = Field(..., description="Token expiry in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "firm_id": "550e8400-e29b-41d4-a716-446655440000",
                "firm_name": "ABC Chartered Accountants",
                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                "user_name": "Raj Kumar",
                "role": "ca_admin",
                "expires_in": 28800
            }
        }


class CurrentUser(BaseModel):
    """Authenticated user information from JWT token."""

    user_id: str = Field(..., description="User ID")
    firm_id: str = Field(..., description="Firm ID (tenant)")
    firm_name: str = Field(..., description="Firm name")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User full name")
    role: str = Field(..., description="User role")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                "firm_id": "550e8400-e29b-41d4-a716-446655440000",
                "firm_name": "ABC Chartered Accountants",
                "email": "rajkumar@abc.com",
                "name": "Raj Kumar",
                "role": "ca_admin"
            }
        }


class InviteStaffRequest(BaseModel):
    """Request to invite a staff member to the firm."""

    email: str = Field(..., description="Staff member email")
    name: str = Field(..., min_length=2, max_length=200, description="Staff member full name")
    role: str = Field("ca_staff", description="Staff role (ca_staff, ca_viewer, etc.)")

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, v: str) -> str:
        return validate_email(v)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return validate_name(v, min_length=2, max_length=200)


class InviteStaffResponse(BaseModel):
    """Response after inviting staff."""

    message: str = Field(..., description="Confirmation message")
    temp_password: str = Field(..., description="Temporary password for staff member")
    note: str = Field(
        default="Send this password securely and force change later.",
        description="Instructions for password handling"
    )


class ChangePasswordRequest(BaseModel):
    """Request to change password."""

    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password(v)


class ChangePasswordResponse(BaseModel):
    """Response after password change."""

    message: str = Field(..., description="Confirmation message")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Password updated successfully"
            }
        }


class VerifyTokenRequest(BaseModel):
    """Request to verify a token."""

    token: str = Field(..., description="JWT token to verify")


class VerifyTokenResponse(BaseModel):
    """Response from token verification."""

    valid: bool = Field(..., description="Whether token is valid")
    user: Optional[CurrentUser] = Field(None, description="User info if valid")
    message: str = Field(..., description="Verification result message")
