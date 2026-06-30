"""Input validators for common fields across GSTAgent.

All validators raise specific exception types that can be handled by
FastAPI exception handlers to return appropriate HTTP responses.
"""

import re
from typing import Optional
from core.exceptions import InvalidGSTINError, InvalidPANError, ValidationError


def validate_gstin(gstin: str) -> str:
    """Validate and normalize GSTIN.

    GSTIN format: 15 alphanumeric characters
    Pattern: {2-digit state code}{10-digit PAN}{1-digit entity code}{1-digit check digit}

    Args:
        gstin: GST Identification Number to validate

    Returns:
        Normalized (uppercase) GSTIN

    Raises:
        InvalidGSTINError: If GSTIN format is invalid
    """
    if not gstin:
        raise InvalidGSTINError("")

    # Normalize: uppercase and strip whitespace
    gstin = gstin.upper().strip()

    # Validate length
    if len(gstin) != 15:
        raise InvalidGSTINError(gstin)

    # Validate format: first 5 chars alphanumeric, next 10 alphanumeric, last 1 char
    if not re.match(r"^[0-9A-Z]{15}$", gstin):
        raise InvalidGSTINError(gstin)

    # Basic check digit validation (simplified - full validation requires complex algorithm)
    # For now, just ensure it's not all zeros or all same character
    if len(set(gstin)) == 1:
        raise InvalidGSTINError(gstin)

    return gstin


def validate_pan(pan: str) -> str:
    """Validate and normalize PAN.

    PAN format: 10 alphanumeric characters
    Pattern: {5 letters}{4 digits}{1 letter}

    Args:
        pan: Permanent Account Number to validate

    Returns:
        Normalized (uppercase) PAN

    Raises:
        InvalidPANError: If PAN format is invalid
    """
    if not pan:
        raise InvalidPANError("")

    # Normalize: uppercase and strip whitespace
    pan = pan.upper().strip()

    # Validate length
    if len(pan) != 10:
        raise InvalidPANError(pan)

    # Validate format: 5 letters, 4 digits, 1 letter (e.g., AAAAA1234A)
    if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan):
        raise InvalidPANError(pan)

    return pan


def validate_email(email: str) -> str:
    """Validate and normalize email address.

    Args:
        email: Email address to validate

    Returns:
        Normalized (lowercase) email

    Raises:
        ValidationError: If email format is invalid
    """
    if not email:
        raise ValidationError("Email is required", field="email")

    # Normalize: lowercase and strip whitespace
    email = email.lower().strip()

    # Simple email validation (RFC 5322 simplified)
    pattern = r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$"
    if not re.match(pattern, email):
        raise ValidationError(f"Invalid email format: {email}", field="email")

    # Additional checks
    if len(email) > 254:
        raise ValidationError("Email is too long", field="email")

    return email


def validate_invoice_number(invoice_number: str) -> str:
    """Validate invoice number format.

    Invoice numbers can vary but generally should:
    - Not be empty
    - Not contain special characters except hyphens and slashes
    - Be reasonably short (< 50 chars)

    Args:
        invoice_number: Invoice number to validate

    Returns:
        Normalized invoice number (stripped whitespace)

    Raises:
        ValidationError: If invoice number is invalid
    """
    if not invoice_number:
        raise ValidationError("Invoice number is required", field="invoice_number")

    # Strip whitespace
    invoice_number = invoice_number.strip()

    # Check length
    if len(invoice_number) > 50:
        raise ValidationError("Invoice number is too long", field="invoice_number")

    # Allow alphanumeric, hyphens, slashes, dots
    if not re.match(r"^[A-Za-z0-9\-/.\s]+$", invoice_number):
        raise ValidationError(
            "Invoice number contains invalid characters",
            field="invoice_number"
        )

    return invoice_number


def validate_phone(phone: str) -> str:
    """Validate phone number format (India-focused).

    Accepts:
    - 10-digit numbers
    - +91 country code variations

    Args:
        phone: Phone number to validate

    Returns:
        Normalized phone number

    Raises:
        ValidationError: If phone format is invalid
    """
    if not phone:
        raise ValidationError("Phone number is required", field="phone")

    # Remove common separators
    phone = re.sub(r"[\s\-()]+", "", phone)

    # Check if it starts with +91 (India)
    if phone.startswith("+91"):
        phone = phone[3:]
    elif phone.startswith("91"):
        phone = phone[2:]

    # Should be 10 digits
    if not re.match(r"^[0-9]{10}$", phone):
        raise ValidationError("Phone number must be 10 digits", field="phone")

    return phone


def validate_name(name: str, min_length: int = 2, max_length: int = 200) -> str:
    """Validate and normalize name field.

    Args:
        name: Name to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length

    Returns:
        Normalized name (trimmed whitespace)

    Raises:
        ValidationError: If name format is invalid
    """
    if not name:
        raise ValidationError("Name is required", field="name")

    name = name.strip()

    if len(name) < min_length:
        raise ValidationError(
            f"Name must be at least {min_length} characters",
            field="name"
        )

    if len(name) > max_length:
        raise ValidationError(
            f"Name must not exceed {max_length} characters",
            field="name"
        )

    return name


def validate_password(password: str, min_length: int = 8) -> str:
    """Validate password strength.

    Requirements:
    - Minimum length (default: 8)
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit

    Args:
        password: Password to validate
        min_length: Minimum required length

    Returns:
        The password (unchanged)

    Raises:
        ValidationError: If password does not meet requirements
    """
    if not password:
        raise ValidationError("Password is required", field="password")

    if len(password) < min_length:
        raise ValidationError(
            f"Password must be at least {min_length} characters",
            field="password"
        )

    if not re.search(r"[A-Z]", password):
        raise ValidationError(
            "Password must contain at least one uppercase letter",
            field="password"
        )

    if not re.search(r"[a-z]", password):
        raise ValidationError(
            "Password must contain at least one lowercase letter",
            field="password"
        )

    if not re.search(r"[0-9]", password):
        raise ValidationError(
            "Password must contain at least one digit",
            field="password"
        )

    return password


def validate_taxable_value(value: float) -> float:
    """Validate taxable value is non-negative.

    Args:
        value: Taxable value to validate

    Returns:
        The validated value

    Raises:
        ValidationError: If value is invalid
    """
    if value is None:
        raise ValidationError("Taxable value is required", field="taxable_value")

    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValidationError("Taxable value must be a number", field="taxable_value")

    if value < 0:
        raise ValidationError("Taxable value cannot be negative", field="taxable_value")

    return value


def validate_tax_rate(rate: float) -> float:
    """Validate GST tax rate is in valid range.

    Args:
        rate: Tax rate (as decimal, e.g., 0.18 for 18%)

    Returns:
        The validated rate

    Raises:
        ValidationError: If rate is invalid
    """
    if rate is None:
        raise ValidationError("Tax rate is required", field="tax_rate")

    try:
        rate = float(rate)
    except (TypeError, ValueError):
        raise ValidationError("Tax rate must be a number", field="tax_rate")

    if rate < 0:
        raise ValidationError("Tax rate cannot be negative", field="tax_rate")

    if rate > 1:  # Assuming rates are decimals (0-1)
        raise ValidationError("Tax rate must be between 0 and 1", field="tax_rate")

    return rate


def validate_period(period: str) -> str:
    """Validate GST return period format.

    Format: MMYYYY (e.g., 042026 for April 2026)

    Args:
        period: Period string to validate

    Returns:
        The validated period

    Raises:
        ValidationError: If period format is invalid
    """
    if not period:
        raise ValidationError("Period is required", field="period")

    period = period.strip()

    if not re.match(r"^\d{6}$", period):
        raise ValidationError(
            "Period must be in MMYYYY format (e.g., 042026)",
            field="period"
        )

    month = int(period[:2])
    if month < 1 or month > 12:
        raise ValidationError("Month must be between 01 and 12", field="period")

    return period
