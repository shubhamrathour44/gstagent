"""Configuration management for GSTAgent.

Centralizes environment variables and constants to avoid duplication.
"""

import os
from typing import Optional

# JWT & Authentication
JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "change-this-in-production-use-256-bit-random-key"
)
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

# Database
DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
SQL_ECHO = os.getenv("SQL_ECHO", "0") == "1"

# GSP (GST Portal) Configuration
GSP_PROVIDER = os.getenv("GSP_PROVIDER", "mock")  # mock, mastergst, whitebooks, iris, gsthero

# GSP Provider-specific URLs and credentials (loaded from env)
MASTERGST_BASE_URL = os.getenv("MASTERGST_BASE_URL")
MASTERGST_API_KEY = os.getenv("MASTERGST_API_KEY")
MASTERGST_API_SECRET = os.getenv("MASTERGST_API_SECRET")

WHITEBOOKS_BASE_URL = os.getenv("WHITEBOOKS_BASE_URL")
WHITEBOOKS_API_KEY = os.getenv("WHITEBOOKS_API_KEY")

# Caching
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))  # 5 minutes default

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", None)

# Feature Flags
ENABLE_AI_RECOMMENDATIONS = os.getenv("ENABLE_AI_RECOMMENDATIONS", "1") == "1"
ENABLE_ASYNC_RECONCILIATION = os.getenv("ENABLE_ASYNC_RECONCILIATION", "0") == "1"

# Application Info
APP_NAME = "GSTAgent"
APP_VERSION = "2.1.0"
APP_DESCRIPTION = "Backend API engine for GSTAgent CA Practice Management Platform"

# Allowed CORS origins
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "https://gstagent.co.in",
    "https://www.gstagent.co.in",
    "https://gstagent.vercel.app",
    "https://www.gstagent.vercel.app",
]

# File upload limits
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
ALLOWED_UPLOAD_TYPES = {"csv", "xlsx", "xls"}

# Reconciliation thresholds
MISMATCH_SEVERITY_THRESHOLDS = {
    "high": 10000,      # Tax impact > ₹10,000
    "medium": 1000,     # Tax impact ₹1,000 - ₹10,000
    "low": 0,           # Tax impact < ₹1,000
}

# GST-specific constants
GSTIN_LENGTH = 15
GST_RATE_STANDARD = 0.18
GST_RATE_REDUCED = 0.05
GST_RATE_ZERO = 0.0
GST_RATE_EXEMPT = None

# Entity constraints
MIN_FIRM_NAME_LENGTH = 3
MAX_FIRM_NAME_LENGTH = 200
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
