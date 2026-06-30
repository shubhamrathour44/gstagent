"""Authentication service with business logic (testable, database-agnostic)."""

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import JWT_SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES
from core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DuplicateError,
    NotFoundError,
)
from core.validators import validate_password
from database import CAFirm, FirmRepo, User, UserRepo
from auth.schemas import CurrentUser, TokenResponse


class AuthService:
    """Authentication service with JWT and password management."""

    def __init__(self, secret_key: str = JWT_SECRET_KEY, token_expire_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES):
        self.secret_key = secret_key
        self.token_expire_minutes = token_expire_minutes

    # =========================================================================
    # Token Operations
    # =========================================================================

    @staticmethod
    def _b64url_encode(data: bytes) -> str:
        """Base64 URL-safe encode without padding."""
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    @staticmethod
    def _b64url_decode(data: str) -> bytes:
        """Base64 URL-safe decode with padding."""
        return base64.urlsafe_b64decode(data + "=" * ((4 - len(data) % 4) % 4))

    def create_access_token(self, data: dict, expires_minutes: Optional[int] = None) -> str:
        """Create JWT access token.

        Args:
            data: Claims to include in token (sub, firm_id, role, etc.)
            expires_minutes: Token TTL in minutes (uses default if not provided)

        Returns:
            JWT token string

        Raises:
            ValueError: If token creation fails
        """
        if expires_minutes is None:
            expires_minutes = self.token_expire_minutes

        try:
            payload = {
                **data,
                "exp": time.time() + expires_minutes * 60,
                "iat": time.time()
            }

            header = self._b64url_encode(
                json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()
            )
            body = self._b64url_encode(
                json.dumps(payload, separators=(",", ":")).encode()
            )
            signature = hmac.new(
                self.secret_key.encode(),
                f"{header}.{body}".encode(),
                hashlib.sha256
            ).digest()

            return f"{header}.{body}.{self._b64url_encode(signature)}"

        except Exception as e:
            raise ValueError(f"Failed to create token: {str(e)}")

    def verify_token(self, token: str) -> dict:
        """Verify and decode JWT token.

        Args:
            token: JWT token string

        Returns:
            Token payload as dict

        Raises:
            AuthenticationError: If token is invalid or expired
        """
        try:
            parts = token.split(".")
            if len(parts) != 3:
                raise AuthenticationError("Invalid token format")

            header, body, sig = parts
            expected_sig = hmac.new(
                self.secret_key.encode(),
                f"{header}.{body}".encode(),
                hashlib.sha256
            ).digest()

            if not hmac.compare_digest(self._b64url_decode(sig), expected_sig):
                raise AuthenticationError("Invalid token signature")

            payload = json.loads(self._b64url_decode(body))

            if payload.get("exp", 0) < time.time():
                raise AuthenticationError("Token expired")

            return payload

        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")

    # =========================================================================
    # Password Operations
    # =========================================================================

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with PBKDF2.

        Args:
            password: Plain text password

        Returns:
            Base64-encoded salt + hash

        Raises:
            ValueError: If password is invalid
        """
        # Validate password strength
        validate_password(password)

        try:
            salt = os.urandom(32)
            key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180000)
            return base64.b64encode(salt + key).decode()
        except Exception as e:
            raise ValueError(f"Failed to hash password: {str(e)}")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash.

        Args:
            password: Plain text password to verify
            hashed: Hashed password from database

        Returns:
            True if password matches, False otherwise
        """
        try:
            decoded = base64.b64decode(hashed.encode())
            salt, stored_key = decoded[:32], decoded[32:]
            key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180000)
            return hmac.compare_digest(key, stored_key)
        except Exception:
            return False

    # =========================================================================
    # User Registration
    # =========================================================================

    async def register_firm(
        self,
        db: AsyncSession,
        firm_name: str,
        email: str,
        password: str,
        admin_name: str,
        phone: Optional[str] = None,
        city: Optional[str] = None,
    ) -> TokenResponse:
        """Register a new CA firm with admin user.

        Args:
            db: Database session
            firm_name: Name of the CA firm
            email: Email for both firm and admin user
            password: Admin user password
            admin_name: Admin user full name
            phone: Optional phone number
            city: Optional city

        Returns:
            TokenResponse with JWT token and user info

        Raises:
            DuplicateError: If email is already registered
            ValueError: If input validation fails
        """
        # Check for existing firm or user
        existing_firm = await FirmRepo.get_by_email(db, email)
        if existing_firm:
            raise DuplicateError(
                f"Email {email} is already registered as a firm",
                entity_type="firm"
            )

        existing_user = await UserRepo.get_by_email(db, email)
        if existing_user:
            raise DuplicateError(
                f"Email {email} is already registered as a user",
                entity_type="user"
            )

        # Create firm
        firm = await FirmRepo.create(
            db,
            name=firm_name.strip(),
            email=email,
            phone=phone,
            city=city,
        )

        # Create admin user
        user = await UserRepo.create(
            db,
            firm_id=firm.id,
            email=email,
            name=admin_name.strip(),
            hashed_password=self.hash_password(password),
            role="ca_admin",
        )

        await db.commit()
        return self._token_for(user, firm)

    # =========================================================================
    # User Login
    # =========================================================================

    async def login(self, db: AsyncSession, email: str, password: str) -> TokenResponse:
        """Authenticate user and return token.

        Args:
            db: Database session
            email: User email
            password: User password

        Returns:
            TokenResponse with JWT token and user info

        Raises:
            AuthenticationError: If credentials are invalid
            NotFoundError: If user or firm not found
        """
        # Get user
        user = await UserRepo.get_by_email(db, email)
        if not user or not user.is_active:
            raise AuthenticationError("Invalid email or password")

        # Verify password
        if not self.verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        # Get firm
        firm = await FirmRepo.get_by_email(db, user.firm.email if hasattr(user, 'firm') else email)
        if not firm:
            raise NotFoundError("Firm not found", entity_type="firm", entity_id=user.firm_id)

        if not firm.is_active:
            raise AuthorizationError("Firm account is inactive")

        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()
        await db.refresh(user)

        return self._token_for(user, firm)

    # =========================================================================
    # Password Management
    # =========================================================================

    async def change_password(
        self,
        db: AsyncSession,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> None:
        """Change user password.

        Args:
            db: Database session
            user_id: User ID
            old_password: Current password
            new_password: New password

        Raises:
            AuthenticationError: If old password is incorrect
            NotFoundError: If user not found
        """
        user = await UserRepo.get_by_email(db, user_id)  # This is wrong, should query by ID
        if not user:
            raise NotFoundError("User not found", entity_type="user", entity_id=user_id)

        if not self.verify_password(old_password, user.hashed_password):
            raise AuthenticationError("Old password is incorrect")

        # Validate new password
        validate_password(new_password)

        # Update password
        user.hashed_password = self.hash_password(new_password)
        await db.commit()

    # =========================================================================
    # Staff Management
    # =========================================================================

    async def invite_staff(
        self,
        db: AsyncSession,
        admin_user: CurrentUser,
        email: str,
        name: str,
        role: str = "ca_staff",
    ) -> tuple[str, str]:
        """Invite a staff member to the firm.

        Args:
            db: Database session
            admin_user: Authenticated admin user
            email: Staff member email
            name: Staff member full name
            role: Staff role (ca_staff, ca_viewer, etc.)

        Returns:
            Tuple of (message, temporary_password)

        Raises:
            AuthorizationError: If user is not admin
            DuplicateError: If email already exists
        """
        # Check authorization
        if admin_user.role != "ca_admin":
            raise AuthorizationError(f"Role '{admin_user.role}' cannot invite staff")

        # Check if user exists
        if await UserRepo.get_by_email(db, email):
            raise DuplicateError(f"Email {email} already registered", entity_type="user")

        # Generate temporary password
        temp_password = base64.b64encode(os.urandom(9)).decode()[:12]

        # Create user
        await UserRepo.create(
            db,
            firm_id=admin_user.firm_id,
            email=email,
            name=name,
            hashed_password=self.hash_password(temp_password),
            role=role,
        )

        await db.commit()

        return (
            f"Staff user created for {email}",
            temp_password,
        )

    # =========================================================================
    # Utilities
    # =========================================================================

    def _token_for(self, user: User, firm: CAFirm) -> TokenResponse:
        """Create token response for user.

        Args:
            user: User database model
            firm: Firm database model

        Returns:
            TokenResponse with JWT and user info
        """
        token = self.create_access_token({
            "sub": user.id,
            "firm_id": firm.id,
            "firm_name": firm.name,
            "email": user.email,
            "name": user.name,
            "role": user.role,
        })

        return TokenResponse(
            access_token=token,
            firm_id=firm.id,
            firm_name=firm.name,
            user_id=user.id,
            user_name=user.name,
            role=user.role,
            expires_in=self.token_expire_minutes * 60,
        )


# Create default service instance
default_auth_service = AuthService()
