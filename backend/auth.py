"""GSTAgent authentication with real database-backed register/login."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Firm, FirmRepo, UserRepo, get_db

SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "change-this-in-production-use-256-bit-random-key"
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 8))
)

security = HTTPBearer()


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * ((4 - len(data) % 4) % 4))


def create_access_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    payload = {
        **data,
        "exp": time.time() + expires_minutes * 60,
        "iat": time.time()
    }

    header = _b64url_encode(
        json.dumps(
            {"alg": "HS256", "typ": "JWT"},
            separators=(",", ":")
        ).encode()
    )

    body = _b64url_encode(
        json.dumps(payload, separators=(",", ":")).encode()
    )

    signature = hmac.new(
        SECRET_KEY.encode(),
        f"{header}.{body}".encode(),
        hashlib.sha256
    ).digest()

    return f"{header}.{body}.{_b64url_encode(signature)}"


def verify_token(token: str) -> dict:
    try:
        header, body, sig = token.split(".")

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

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"}
        )


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )

    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        180000
    )

    return base64.b64encode(salt + key).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        decoded = base64.b64decode(hashed.encode())
        salt = decoded[:32]
        stored_key = decoded[32:]

        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            180000
        )

        return hmac.compare_digest(key, stored_key)

    except Exception:
        return False


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


def _token_for(user, firm) -> TokenResponse:
    token = create_access_token({
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
        role=user.role
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> CurrentUser:
    payload = verify_token(credentials.credentials)

    return CurrentUser(
        user_id=payload["sub"],
        firm_id=payload["firm_id"],
        firm_name=payload["firm_name"],
        email=payload["email"],
        name=payload["name"],
        role=payload["role"],
    )


def require_role(*roles: str):
    async def _check(
        current_user: CurrentUser = Depends(get_current_user)
    ):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{current_user.role}' is not authorised"
            )

        return current_user

    return _check


auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post("/register", response_model=TokenResponse)
async def register_firm(
    request: RegisterFirmRequest,
    db: AsyncSession = Depends(get_db)
):
    existing_firm = await FirmRepo.get_by_email(db, request.email)
    existing_user = await UserRepo.get_by_email(db, request.email)

    if existing_firm or existing_user:
        raise HTTPException(
            status_code=409,
            detail="This email is already registered"
        )

    firm = await FirmRepo.create(
        db,
        name=request.firm_name.strip(),
        email=request.email,
        phone=request.phone,
        city=request.city
    )

    user = await UserRepo.create(
        db,
        firm_id=firm.id,
        email=request.email,
        name=request.admin_name.strip(),
        hashed_password=hash_password(request.password),
        role="ca_admin"
    )

    return _token_for(user, firm)


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    user = await UserRepo.get_by_email(db, request.email)

    if (
        not user
        or not user.is_active
        or not verify_password(request.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    result = await db.execute(
        select(Firm).where(Firm.id == user.firm_id)
    )

    firm = result.scalar_one_or_none()

    if not firm or not firm.is_active:
        raise HTTPException(
            status_code=403,
            detail="Firm account is inactive"
        )

    user.last_login = __import__("datetime").datetime.datetime.utcnow()

    await db.commit()

    return _token_for(user, firm)


@auth_router.get("/me")
async def get_me(
    current_user: CurrentUser = Depends(get_current_user)
):
    return current_user


class InviteStaffRequest(BaseModel):
    email: str
    name: str
    role: str = "ca_staff"


@auth_router.post("/invite-staff")
async def invite_staff(
    request: InviteStaffRequest,
    current_user: CurrentUser = Depends(require_role("ca_admin")),
    db: AsyncSession = Depends(get_db)
):
    existing_user = await UserRepo.get_by_email(db, request.email)

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="User already exists"
        )

    temp_password = base64.b64encode(os.urandom(9)).decode()[:12]

    await UserRepo.create(
        db,
        firm_id=current_user.firm_id,
        email=request.email,
        name=request.name,
        hashed_password=hash_password(temp_password),
        role=request.role
    )

    return {
        "message": f"Staff user created for {request.email}",
        "temp_password": temp_password,
        "note": "Send this password securely and force change later."
    }


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@auth_router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user = await UserRepo.get_by_email(db, current_user.email)

    if not user or not verify_password(request.old_password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Old password is incorrect"
        )

    user.hashed_password = hash_password(request.new_password)

    await db.commit()

    return {"message": "Password updated"}