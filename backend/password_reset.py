"""
GSTAgent — Password Reset / Forgot Password
Uses UserRepo pattern matching existing auth.py
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import String, DateTime, Boolean, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
import secrets, os, hashlib

from database import Base, get_db, new_id, UserRepo
from auth import hash_password, verify_password, get_current_user, CurrentUser

router = APIRouter(prefix="/auth", tags=["Password Reset"])


# ── MODEL ──────────────────────────────────────────────────────────────────────

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), index=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    otp: Mapped[str] = mapped_column(String(6))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── SCHEMAS ────────────────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: str

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str

class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str

class ChangePasswordResetRequest(BaseModel):
    current_password: str
    new_password: str


# ── EMAIL ──────────────────────────────────────────────────────────────────────

async def send_reset_email(email: str, otp: str, name: str = ""):
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    from_email = os.getenv("SMTP_FROM", smtp_user)
    if not smtp_user or not smtp_pass:
        return False
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    subject = "GSTAgent — Password Reset OTP"
    body = f"""<html><body style="font-family:sans-serif;padding:32px">
    <h2 style="color:#6366F1">GSTAgent Password Reset</h2>
    <p>Hi {name or email},</p>
    <p>Your OTP is: <strong style="font-size:24px;letter-spacing:8px">{otp}</strong></p>
    <p>Valid for 10 minutes.</p>
    </body></html>"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = email
    msg.attach(MIMEText(body, "html"))
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


# ── ROUTES ─────────────────────────────────────────────────────────────────────

@router.post("/forgot-password")
async def forgot_password(
    req: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    user = await UserRepo.get_by_email(db, req.email.lower().strip())

    if not user:
        return {"message": "If this email is registered, you will receive an OTP shortly."}

    otp = str(secrets.randbelow(900000) + 100000)
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Invalidate old tokens
    old = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.email == req.email.lower(),
            PasswordResetToken.used == False
        )
    )
    for t in old.scalars().all():
        t.used = True

    reset_token = PasswordResetToken(
        email=req.email.lower().strip(),
        token_hash=token_hash,
        otp=otp,
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.add(reset_token)
    await db.commit()

    email_sent = await send_reset_email(req.email, otp, getattr(user, 'name', '') or "")

    if email_sent:
        return {"message": "OTP sent to your email. Valid for 10 minutes."}
    else:
        return {
            "message": "OTP generated successfully.",
            "otp": otp,
            "note": "Configure SMTP in Railway to send emails instead of showing OTP here."
        }


@router.post("/verify-otp")
async def verify_otp(
    req: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.email == req.email.lower(),
            PasswordResetToken.otp == req.otp,
            PasswordResetToken.used == False
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(400, "Invalid OTP")
    if datetime.utcnow() > token.expires_at:
        raise HTTPException(400, "OTP expired. Please request a new one.")
    return {"message": "OTP verified.", "valid": True}


@router.post("/reset-password")
async def reset_password(
    req: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    if len(req.new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.email == req.email.lower(),
            PasswordResetToken.otp == req.otp,
            PasswordResetToken.used == False
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(400, "Invalid OTP")
    if datetime.utcnow() > token.expires_at:
        raise HTTPException(400, "OTP expired. Please request a new one.")

    user = await UserRepo.get_by_email(db, req.email.lower())
    if not user:
        raise HTTPException(404, "User not found")

    user.hashed_password = hash_password(req.new_password)
    token.used = True
    await db.commit()

    return {"message": "Password reset successfully. You can now log in with your new password."}


@router.post("/reset/change-password")
async def change_password_authenticated(
    req: ChangePasswordResetRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if len(req.new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    user = await UserRepo.get_by_email(db, current_user.email)
    if not user:
        raise HTTPException(404, "User not found")

    if not verify_password(req.current_password, user.hashed_password):
        raise HTTPException(400, "Current password is incorrect")

    user.hashed_password = hash_password(req.new_password)
    await db.commit()

    return {"message": "Password changed successfully."}
