"""FastAPI dependency injection functions for authentication."""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.exceptions import AuthenticationError, AuthorizationError
from core.logger import get_logger
from auth.schemas import CurrentUser
from auth.service import default_auth_service

logger = get_logger(__name__)
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> CurrentUser:
    """Extract and validate JWT token from request header.

    This dependency verifies the Bearer token and returns the authenticated user.

    Args:
        credentials: HTTP Bearer credentials from request

    Returns:
        CurrentUser with decoded token claims

    Raises:
        HTTPException: 401 Unauthorized if token is invalid or expired
    """
    try:
        payload = default_auth_service.verify_token(credentials.credentials)

        return CurrentUser(
            user_id=payload["sub"],
            firm_id=payload["firm_id"],
            firm_name=payload["firm_name"],
            email=payload["email"],
            name=payload["name"],
            role=payload["role"],
        )

    except AuthenticationError as e:
        logger.warning(
            "Authentication failed",
            extra_data={"reason": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(
            "Unexpected error during authentication",
            extra_data={"error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(*roles: str):
    """Dependency to require specific roles.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(current_user: CurrentUser = Depends(require_role("ca_admin"))):
            ...

    Args:
        roles: Allowed roles (ca_admin, ca_staff, ca_viewer, etc.)

    Returns:
        Dependency function that checks user role

    Raises:
        HTTPException: 403 Forbidden if user role is not in allowed list
    """
    async def _check_role(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in roles:
            logger.warning(
                "Authorization failed",
                extra_data={
                    "user_id": current_user.user_id,
                    "required_roles": roles,
                    "user_role": current_user.role,
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not authorized for this resource"
            )
        return current_user

    return _check_role


def optional_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[CurrentUser]:
    """Optionally extract user from token (doesn't fail if token missing).

    Usage:
        @router.get("/public-data")
        async def public_endpoint(current_user: Optional[CurrentUser] = Depends(optional_current_user)):
            if current_user:
                # Show personalized data
            else:
                # Show public data

    Args:
        credentials: Optional HTTP Bearer credentials

    Returns:
        CurrentUser if valid token present, None otherwise
    """
    if not credentials:
        return None

    try:
        payload = default_auth_service.verify_token(credentials.credentials)

        return CurrentUser(
            user_id=payload["sub"],
            firm_id=payload["firm_id"],
            firm_name=payload["firm_name"],
            email=payload["email"],
            name=payload["name"],
            role=payload["role"],
        )

    except AuthenticationError:
        # Token invalid, but that's okay for optional auth
        return None
    except Exception:
        return None


def require_firm_access(firm_id: str) -> callable:
    """Dependency to verify user has access to a specific firm.

    Usage:
        @router.get("/firms/{firm_id}/data")
        async def get_firm_data(
            firm_id: str,
            current_user: CurrentUser = Depends(require_firm_access(firm_id))
        ):
            ...

    Args:
        firm_id: Firm ID to check access for

    Returns:
        Dependency function that verifies firm access

    Raises:
        HTTPException: 403 Forbidden if user is not from that firm
    """
    async def _check_firm_access(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.firm_id != firm_id:
            logger.warning(
                "Firm access denied",
                extra_data={
                    "user_id": current_user.user_id,
                    "user_firm": current_user.firm_id,
                    "requested_firm": firm_id,
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this firm"
            )
        return current_user

    return _check_firm_access
