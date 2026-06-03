"""
GSTAgent — Multi-Tenant Authentication
JWT-based auth scoped per CA firm.

Requirements:
    pip install python-jose[cryptography] passlib[bcrypt] python-multipart

Usage:
    Every protected endpoint receives current_user via Depends(get_current_user).
    All queries are automatically scoped to current_user.firm_id.
"""

import os
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

# ─── CONFIG ───────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production-use-256-bit-random-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8   # 8 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30

security = HTTPBearer()


# ─── SIMPLE JWT WITHOUT PYTHON-JOSE ───────────────────────────────────────────
# Uses standard library only so it works in restricted environments.
# In production, replace with python-jose for full RFC compliance.

import json
import struct
import time


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    return base64.urlsafe_b64decode(data + "=" * padding)


def create_access_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    """Create a signed JWT token."""
    payload = {**data, "exp": time.time() + expires_minutes * 60, "iat": time.time()}
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64url_encode(json.dumps(payload).encode())
    signature = hmac.new(
        SECRET_KEY.encode(),
        f"{header}.{body}".encode(),
        hashlib.sha256
    ).digest()
    return f"{header}.{body}.{_b64url_encode(signature)}"


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token structure")

        header, body, sig = parts
        expected_sig = hmac.new(
            SECRET_KEY.encode(),
            f"{header}.{body}".encode(),
            hashlib.sha256
        ).digest()

        if not hmac.compare_digest(_b64url_decode(sig), expected_sig):
            raise ValueError("Invalid signature")

        payload = json.loads(_b64url_decode(body))
        if payload.get("exp", 0) < time.time():
            raise ValueError("Token expired")

        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256."""
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return base64.b64encode(salt + key).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    try:
        decoded = base64.b64decode(hashed.encode())
        salt, stored_key = decoded[:32], decoded[32:]
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return hmac.compare_digest(key, stored_key)
    except Exception:
        return False


# ─── SCHEMAS ──────────────────────────────────────────────────────────────────

class RegisterFirmRequest(BaseModel):
    firm_name: str
    email: str
    password: str
    phone: Optional[str] = None
    city: Optional[str] = None
    admin_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    firm_id: str
    firm_name: str
    user_id: str
    user_name: str
    role: str
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60


class CurrentUser(BaseModel):
    user_id: str
    firm_id: str
    firm_name: str
    email: str
    name: str
    role: str


# ─── FASTAPI DEPENDENCY ───────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> CurrentUser:
    """
    FastAPI dependency. Use as:
        current_user: CurrentUser = Depends(get_current_user)
    
    Validates JWT and returns the current user.
    All DB queries should be scoped to current_user.firm_id.
    """
    payload = verify_token(credentials.credentials)

    return CurrentUser(
        user_id=payload["sub"],
        firm_id=payload["firm_id"],
        firm_name=payload["firm_name"],
        email=payload["email"],
        name=payload["name"],
        role=payload["role"]
    )


def require_role(*roles: str):
    """
    Role guard dependency. Use as:
        Depends(require_role("ca_admin"))
    """
    async def _check(current_user: CurrentUser = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' not authorised for this action"
            )
        return current_user
    return _check


# ─── AUTH ENDPOINTS (add these to main.py) ────────────────────────────────────

from fastapi import APIRouter

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post("/register", response_model=TokenResponse)
async def register_firm(request: RegisterFirmRequest):
    """
    Register a new CA firm and create the admin user.
    In production, add email verification before activating.
    """
    # In production: check email is unique, save to DB
    # Here: return a mock token to show the flow
    firm_id = "demo-firm-" + request.email[:6].replace("@", "")
    user_id = "demo-user-001"

    token = create_access_token({
        "sub": user_id,
        "firm_id": firm_id,
        "firm_name": request.firm_name,
        "email": request.email,
        "name": request.admin_name,
        "role": "ca_admin"
    })

    return TokenResponse(
        access_token=token,
        firm_id=firm_id,
        firm_name=request.firm_name,
        user_id=user_id,
        user_name=request.admin_name,
        role="ca_admin"
    )


@auth_router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Login endpoint. Validates credentials and returns JWT.
    
    Production flow:
    1. Look up user by email in DB
    2. Verify hashed password
    3. Check firm is active
    4. Return token
    
    Demo flow (no DB): accepts any email/password, returns demo token.
    """
    # DEMO MODE — replace with real DB lookup
    # user = await UserRepo.get_by_email(db, request.email)
    # if not user or not verify_password(request.password, user.hashed_password):
    #     raise HTTPException(status_code=401, detail="Invalid credentials")

    # Mock response for demo
    firm_id = "demo-firm-001"
    user_id = "demo-user-001"
    firm_name = "Demo CA Firm"

    token = create_access_token({
        "sub": user_id,
        "firm_id": firm_id,
        "firm_name": firm_name,
        "email": request.email,
        "name": "Demo Admin",
        "role": "ca_admin"
    })

    return TokenResponse(
        access_token=token,
        firm_id=firm_id,
        firm_name=firm_name,
        user_id=user_id,
        user_name="Demo Admin",
        role="ca_admin"
    )


@auth_router.post("/invite-staff")
async def invite_staff(
    email: str,
    name: str,
    current_user: CurrentUser = Depends(require_role("ca_admin"))
):
    """
    CA admin invites a staff member to join their firm.
    Sends an email with a temporary password (implement with SendGrid/SES).
    """
    temp_password = base64.b64encode(os.urandom(8)).decode()[:10]
    hashed = hash_password(temp_password)

    # TODO: save to DB, send email
    return {
        "message": f"Invitation sent to {email}",
        "temp_password": temp_password,  # Remove in production — send by email only
        "note": "Staff must change password on first login"
    }


@auth_router.get("/me")
async def get_me(current_user: CurrentUser = Depends(get_current_user)):
    """Returns current user's profile."""
    return current_user


@auth_router.post("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    # In production: verify old_password against DB hash, update hash
    return {"message": "Password updated"}
