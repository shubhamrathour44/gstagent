"""
GSTAgent — Password Reset / Forgot Password
Uses email OTP (no SMTP needed — works with Gmail SMTP)
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import String, DateTime, Boolean, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
import secrets, os, hashlib

from database import Base, get_db, new_id
from auth import get_password_hash, get_current_user, CurrentUser

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


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ── EMAIL HELPER ───────────────────────────────────────────────────────────────

async def send_reset_email(email: str, otp: str, name: str = ""):
    """Send OTP email using SMTP."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    from_email = os.getenv("SMTP_FROM", smtp_user)

    if not smtp_user or not smtp_pass:
        # SMTP not configured — return OTP in response for testing
        return False

    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    subject = "GSTAgent — Password Reset OTP"
    body = f"""
    <html><body style="font-family:sans-serif;background:#07090F;color:#E2E8F0;padding:32px">
    <div style="max-width:480px;margin:0 auto;background:#0D1117;border:1px solid rgba(255,255,255,.07);border-radius:14px;padding:32px">
        <h2 style="color:#6366F1;margin-bottom:8px">GSTAgent</h2>
        <h3 style="margin-bottom:16px">Password Reset OTP</h3>
        <p>Hi {name or email},</p>
        <p>Your OTP for password reset is:</p>
        <div style="background:#161B22;border:1px solid rgba(99,102,241,.3);border-radius:10px;padding:20px;text-align:center;margin:20px 0">
            <span style="font-size:36px;font-weight:800;letter-spacing:12px;color:#6366F1">{otp}</span>
        </div>
        <p style="color:#94A3B8;font-size:13px">This OTP is valid for <strong>10 minutes</strong>.</p>
        <p style="color:#94A3B8;font-size:13px">If you did not request this, ignore this email.</p>
        <hr style="border-color:rgba(255,255,255,.07);margin:20px 0"/>
        <p style="color:#475569;font-size:11px">GSTAgent — AI-powered CA Practice Management</p>
    </div>
    </body></html>
    """

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
    """Request password reset OTP."""
    from auth import User

    # Check if user exists
    result = await db.execute(select(User).where(User.email == req.email.lower().strip()))
    user = result.scalar_one_or_none()

    # Always return success (don't reveal if email exists)
    if not user:
        return {"message": "If this email is registered, you will receive an OTP shortly."}

    # Generate 6-digit OTP
    otp = str(secrets.randbelow(900000) + 100000)
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Invalidate old tokens
    old_tokens = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.email == req.email.lower(),
            PasswordResetToken.used == False
        )
    )
    for t in old_tokens.scalars().all():
        t.used = True

    # Save new token
    reset_token = PasswordResetToken(
        email=req.email.lower().strip(),
        token_hash=token_hash,
        otp=otp,
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.add(reset_token)
    await db.commit()

    # Send email
    email_sent = await send_reset_email(req.email, otp, user.name or "")

    if email_sent:
        return {"message": "OTP sent to your email. Valid for 10 minutes."}
    else:
        # SMTP not configured — return OTP directly (for testing/demo)
        return {
            "message": "OTP generated. Note: Email not configured, showing OTP here for testing.",
            "otp": otp,
            "note": "Configure SMTP_HOST, SMTP_USER, SMTP_PASS in Railway to send emails"
        }


@router.post("/verify-otp")
async def verify_otp(
    req: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify OTP before allowing password reset."""
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

    return {"message": "OTP verified. You can now reset your password.", "valid": True}


@router.post("/reset-password")
async def reset_password(
    req: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Reset password using OTP."""
    from auth import User

    if len(req.new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    # Verify OTP
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

    # Find user and update password
    user_result = await db.execute(select(User).where(User.email == req.email.lower()))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    user.hashed_password = get_password_hash(req.new_password)
    token.used = True
    await db.commit()

    return {"message": "Password reset successfully. You can now log in with your new password."}


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change password when logged in."""
    from auth import User, verify_password

    if len(req.new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    if not verify_password(req.current_password, user.hashed_password):
        raise HTTPException(400, "Current password is incorrect")

    user.hashed_password = get_password_hash(req.new_password)
    await db.commit()

    return {"message": "Password changed successfully."}
