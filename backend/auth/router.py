"""FastAPI authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AuthenticationError, AuthorizationError, DuplicateError, NotFoundError
from core.logger import get_logger
from core.schemas import ErrorResponse
from database import get_db
from auth.dependencies import get_current_user, require_role, optional_current_user, require_firm_access
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
from auth.service import default_auth_service

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_firm(
    request: RegisterFirmRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new CA firm with admin user.

    Creates a new firm and admin user account. The admin can then invite staff members.

    Args:
        request: Registration details (firm name, email, password, admin name, etc.)
        db: Database session

    Returns:
        TokenResponse with JWT token for the new admin user

    Raises:
        409 Conflict: If email is already registered
        400 Bad Request: If validation fails
    """
    try:
        logger.info(
            "Firm registration attempt",
            extra_data={"email": request.email, "firm_name": request.firm_name}
        )

        token_response = await default_auth_service.register_firm(
            db=db,
            firm_name=request.firm_name,
            email=request.email,
            password=request.password,
            admin_name=request.admin_name,
            phone=request.phone,
            city=request.city,
        )

        logger.info(
            "Firm registered successfully",
            extra_data={"firm_id": token_response.firm_id, "email": request.email}
        )

        return token_response

    except DuplicateError as e:
        logger.warning(
            "Registration failed: duplicate email",
            extra_data={"email": request.email, "reason": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except ValueError as e:
        logger.warning(
            "Registration failed: validation error",
            extra_data={"email": request.email, "reason": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Registration failed: unexpected error",
            extra_data={"email": request.email, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user and return JWT token.

    Args:
        request: Login credentials (email and password)
        db: Database session

    Returns:
        TokenResponse with JWT token and user information

    Raises:
        401 Unauthorized: If credentials are invalid
        404 Not Found: If firm or user not found
        403 Forbidden: If firm is inactive
    """
    try:
        logger.info("Login attempt", extra_data={"email": request.email})

        token_response = await default_auth_service.login(
            db=db,
            email=request.email,
            password=request.password,
        )

        logger.info(
            "Login successful",
            extra_data={"user_id": token_response.user_id, "firm_id": token_response.firm_id}
        )

        return token_response

    except AuthenticationError as e:
        logger.warning("Login failed: authentication error", extra_data={"email": request.email})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except AuthorizationError as e:
        logger.warning("Login failed: authorization error", extra_data={"email": request.email})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except NotFoundError as e:
        logger.warning("Login failed: not found", extra_data={"email": request.email})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Login failed: unexpected error",
            extra_data={"email": request.email, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.get("/me", response_model=CurrentUser)
async def get_me(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Get current authenticated user information.

    Returns the user's profile from the JWT token.

    Returns:
        CurrentUser object with user details

    Raises:
        401 Unauthorized: If no valid token present
    """
    logger.debug(
        "Get current user",
        extra_data={"user_id": current_user.user_id}
    )
    return current_user


@router.post("/invite-staff", response_model=InviteStaffResponse)
async def invite_staff(
    request: InviteStaffRequest,
    current_user: CurrentUser = Depends(require_role("ca_admin")),
    db: AsyncSession = Depends(get_db),
) -> InviteStaffResponse:
    """Invite a staff member to the firm.

    Only CA admins can invite staff. A temporary password is generated and must be
    shared securely. The staff member should change it on first login.

    Args:
        request: Staff invitation details (email, name, role)
        current_user: Authenticated admin user
        db: Database session

    Returns:
        InviteStaffResponse with confirmation and temporary password

    Raises:
        401 Unauthorized: If no valid token
        403 Forbidden: If user is not admin
        409 Conflict: If email already registered
    """
    try:
        logger.info(
            "Staff invitation attempt",
            extra_data={
                "admin_id": current_user.user_id,
                "invited_email": request.email,
                "role": request.role,
            }
        )

        message, temp_password = await default_auth_service.invite_staff(
            db=db,
            admin_user=current_user,
            email=request.email,
            name=request.name,
            role=request.role,
        )

        logger.info(
            "Staff member invited",
            extra_data={"admin_id": current_user.user_id, "invited_email": request.email}
        )

        return InviteStaffResponse(message=message, temp_password=temp_password)

    except AuthorizationError as e:
        logger.warning(
            "Staff invitation failed: authorization",
            extra_data={"admin_id": current_user.user_id, "reason": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except DuplicateError as e:
        logger.warning(
            "Staff invitation failed: duplicate email",
            extra_data={"invited_email": request.email}
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except ValueError as e:
        logger.warning(
            "Staff invitation failed: validation error",
            extra_data={"invited_email": request.email, "reason": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Staff invitation failed: unexpected error",
            extra_data={"invited_email": request.email, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Staff invitation failed"
        )


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChangePasswordResponse:
    """Change authenticated user's password.

    Requires the current password for security verification.

    Args:
        request: Old and new passwords
        current_user: Authenticated user
        db: Database session

    Returns:
        ChangePasswordResponse with confirmation message

    Raises:
        401 Unauthorized: If old password incorrect
        400 Bad Request: If new password doesn't meet requirements
    """
    try:
        logger.info(
            "Password change attempt",
            extra_data={"user_id": current_user.user_id}
        )

        await default_auth_service.change_password(
            db=db,
            user_id=current_user.user_id,
            old_password=request.old_password,
            new_password=request.new_password,
        )

        logger.info(
            "Password changed successfully",
            extra_data={"user_id": current_user.user_id}
        )

        return ChangePasswordResponse(message="Password updated successfully")

    except AuthenticationError as e:
        logger.warning(
            "Password change failed: authentication",
            extra_data={"user_id": current_user.user_id}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValueError as e:
        logger.warning(
            "Password change failed: validation",
            extra_data={"user_id": current_user.user_id, "reason": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except NotFoundError as e:
        logger.error(
            "Password change failed: user not found",
            extra_data={"user_id": current_user.user_id}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Password change failed: unexpected error",
            extra_data={"user_id": current_user.user_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )
