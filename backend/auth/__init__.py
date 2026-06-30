"""Authentication module for GSTAgent.

Provides JWT token management, password hashing, user registration, and login.

Public API:
  - router: FastAPI router for auth endpoints
  - AuthService: Business logic (testable, database-agnostic)
  - Schemas: Pydantic models for requests/responses
  - Dependencies: Dependency injection for auth
"""

from auth.router import router
from auth.service import AuthService, default_auth_service
from auth.schemas import (
    RegisterFirmRequest,
    LoginRequest,
    TokenResponse,
    CurrentUser,
    InviteStaffRequest,
    InviteStaffResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
)
from auth.dependencies import (
    get_current_user,
    require_role,
    optional_current_user,
    require_firm_access,
)

__all__ = [
    # Router
    "router",
    # Service
    "AuthService",
    "default_auth_service",
    # Schemas
    "RegisterFirmRequest",
    "LoginRequest",
    "TokenResponse",
    "CurrentUser",
    "InviteStaffRequest",
    "InviteStaffResponse",
    "ChangePasswordRequest",
    "ChangePasswordResponse",
    # Dependencies
    "get_current_user",
    "require_role",
    "optional_current_user",
    "require_firm_access",
]
