"""
GSTAgent — Postgres Database Layer
Replaces in-memory store with full persistence.

Requirements:
    pip install sqlalchemy asyncpg alembic

Setup:
    export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/gstagent"
    python database.py  # creates all tables
"""

from sqlalchemy import (
    Column, String, Float, Boolean, Integer, DateTime, Text,
    ForeignKey, Index, Enum as SAEnum, JSON
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import os
import enum


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/gstagent"
)

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# ─── ENUMS ────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"   # GSTAgent staff
    CA_ADMIN    = "ca_admin"      # CA firm owner
    CA_STAFF    = "ca_staff"      # Junior staff at CA firm
    CLIENT      = "client"        # Client self-service (future)


class MismatchSeverity(str, enum.Enum):
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"


class MismatchStatus(str, enum.Enum):
    OPEN     = "open"
    RESOLVED = "resolved"
    DEFERRED = "deferred"
    INVALID  = "invalid"


class IntegrationSource(str, enum.Enum):
    FILE_UPLOAD = "file_upload"
    TALLY       = "tally"
    ZOHO        = "zoho"
    GSP         = "gsp"


# ─── MODELS ───────────────────────────────────────────────────────────────────

class CAFirm(Base):
    """
    Top-level tenant. One CA firm = one tenant.
    All data is scoped under firm_id.
    """
    __tablename__ = "ca_firms"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name       = Column(String(200), nullable=False)
    email      = Column(String(200), unique=True, nullable=False)
    phone      = Column(String(20))
    city       = Column(String(100))
    plan       = Column(String(50), default="starter")   # starter | growth | enterprise
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users   = relationship("User", back_populates="firm", cascade="all, delete-orphan")
    clients = relationship("GSTClient", back_populates="firm", cascade="all, delete-orphan")


class User(Base):
    """
    Staff members of a CA firm. Scoped to one firm.
    """
    __tablename__ = "users"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id       = Column(UUID(as_uuid=True), ForeignKey("ca_firms.id"), nullable=False)
    email         = Column(String(200), unique=True, nullable=False)
    name          = Column(String(200), nullable=False)
    hashed_password = Column(String(300), nullable=False)
    role          = Column(SAEnum(UserRole), default=UserRole.CA_STAFF)
    is_active     = Column(Boolean, default=True)
    last_login    = Column(DateTime)
    created_at    = Column(DateTime, default=datetime.utcnow)

    firm = relationship("CAFirm", back_populates="users")

    __table_args__ = (Index("ix_users_firm_id", "firm_id"),)


class GSTClient(Base):
    """
    A single GSTIN managed by a CA firm.
    One client can have multiple GSTINs (one row per GSTIN).
    """
    __tablename__ = "gst_clients"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id      = Column(UUID(as_uuid=True), ForeignKey("ca_firms.id"), nullable=False)
    name         = Column(String(200), nullable=False)
    gstin        = Column(String(15), nullable=False)
    trade_name   = Column(String(200))
    city         = Column(String(100))
    state_code   = Column(String(2))
    business_type = Column(String(100))   # Manufacturing, Trading, Services etc.
    contact_email = Column(String(200))
    contact_phone = Column(String(20))
    tally_company = Column(String(200))   # Tally company name for ODBC
    zoho_org_id  = Column(String(100))    # Zoho Books org ID
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    firm             = relationship("CAFirm", back_populates="clients")
    reconciliations  = relationship("Reconciliation", back_populates="client", cascade="all, delete-orphan")
    notices          = relationship("GSTNotice", back_populates="client", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_gst_clients_firm_id", "firm_id"),
        Index("ix_gst_clients_gstin", "gstin"),
    )


class Reconciliation(Base):
    """
    One reconciliation run = one row.
    Contains summary stats. Mismatches stored in separate table.
    """
    __tablename__ = "reconciliations"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id       = Column(UUID(as_uuid=True), ForeignKey("gst_clients.id"), nullable=False)
    firm_id         = Column(UUID(as_uuid=True), nullable=False)   # Denormalised for fast queries
    period          = Column(String(6), nullable=False)   # MMYYYY e.g. 032025
    source          = Column(SAEnum(IntegrationSource), default=IntegrationSource.FILE_UPLOAD)

    # Summary stats
    pr_count        = Column(Integer, default=0)
    b2b_count       = Column(Integer, default=0)
    matched         = Column(Integer, default=0)
    mismatch_count  = Column(Integer, default=0)
    match_rate      = Column(Float, default=0.0)
    itc_as_per_2b   = Column(Float, default=0.0)
    itc_as_per_pr   = Column(Float, default=0.0)
    itc_difference  = Column(Float, default=0.0)
    high_count      = Column(Integer, default=0)
    medium_count    = Column(Integer, default=0)
    low_count       = Column(Integer, default=0)

    ai_summary      = Column(Text)          # Cached Claude summary
    filing_qa       = Column(Text)          # Cached filing QA result
    created_at      = Column(DateTime, default=datetime.utcnow)
    created_by      = Column(UUID(as_uuid=True))   # User who ran it

    client     = relationship("GSTClient", back_populates="reconciliations")
    mismatches = relationship("Mismatch", back_populates="reconciliation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_reconciliations_client_period", "client_id", "period"),
        Index("ix_reconciliations_firm_id", "firm_id"),
    )


class Mismatch(Base):
    """
    Individual mismatch within a reconciliation.
    """
    __tablename__ = "mismatches"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reconciliation_id = Column(UUID(as_uuid=True), ForeignKey("reconciliations.id"), nullable=False)
    mismatch_code     = Column(String(10))   # MM0001, MM0002 etc.
    mismatch_type     = Column(String(100), nullable=False)
    severity          = Column(SAEnum(MismatchSeverity), nullable=False)
    status            = Column(SAEnum(MismatchStatus), default=MismatchStatus.OPEN)

    supplier_name     = Column(String(200))
    supplier_gstin    = Column(String(15))
    invoice_number    = Column(String(100))
    invoice_date      = Column(String(20))
    pr_tax_amount     = Column(Float)
    b2b_tax_amount    = Column(Float)
    tax_impact        = Column(Float)
    recommended_action = Column(String(300))
    notes             = Column(Text)

    ai_explanation    = Column(Text)    # Cached Claude explanation
    vendor_email_draft = Column(Text)   # Cached vendor email

    resolved_at       = Column(DateTime)
    resolved_by       = Column(UUID(as_uuid=True))
    resolution_notes  = Column(Text)
    created_at        = Column(DateTime, default=datetime.utcnow)

    reconciliation = relationship("Reconciliation", back_populates="mismatches")

    __table_args__ = (
        Index("ix_mismatches_reconciliation_id", "reconciliation_id"),
        Index("ix_mismatches_severity", "severity"),
        Index("ix_mismatches_status", "status"),
    )


class GSTNotice(Base):
    """
    GST notices received by a client. Tracks draft replies and status.
    """
    __tablename__ = "gst_notices"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id       = Column(UUID(as_uuid=True), ForeignKey("gst_clients.id"), nullable=False)
    firm_id         = Column(UUID(as_uuid=True), nullable=False)
    notice_number   = Column(String(100), nullable=False)
    notice_date     = Column(String(20))
    notice_type     = Column(String(50))   # ASMT-10, DRC-01, etc.
    notice_content  = Column(Text)
    supporting_facts = Column(Text)
    draft_reply     = Column(Text)         # Claude-generated reply
    status          = Column(String(50), default="draft")   # draft | filed | closed
    due_date        = Column(String(20))
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by      = Column(UUID(as_uuid=True))

    client = relationship("GSTClient", back_populates="notices")

    __table_args__ = (Index("ix_gst_notices_client_id", "client_id"),)


class IntegrationConfig(Base):
    """
    Stores Tally / Zoho / GSP integration settings per client.
    Credentials encrypted at rest (use AWS KMS or Vault in production).
    """
    __tablename__ = "integration_configs"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id    = Column(UUID(as_uuid=True), ForeignKey("gst_clients.id"), nullable=False, unique=True)
    tally_host   = Column(String(200), default="localhost")
    tally_port   = Column(Integer, default=9000)
    tally_company = Column(String(200))
    zoho_client_id     = Column(String(200))
    zoho_client_secret = Column(String(300))   # Encrypted in production
    zoho_refresh_token = Column(String(500))   # Encrypted in production
    zoho_org_id        = Column(String(100))
    gsp_username       = Column(String(200))
    gsp_password       = Column(String(300))   # Encrypted in production
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    """
    Immutable audit trail. Every significant action logged here.
    Required for CA firm regulatory compliance.
    """
    __tablename__ = "audit_logs"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id     = Column(UUID(as_uuid=True), nullable=False)
    user_id     = Column(UUID(as_uuid=True))
    action      = Column(String(100), nullable=False)   # reconciliation.run, notice.draft, etc.
    entity_type = Column(String(50))    # reconciliation, mismatch, notice
    entity_id   = Column(UUID(as_uuid=True))
    details     = Column(JSON)          # Extra context
    ip_address  = Column(String(50))
    created_at  = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_audit_logs_firm_id", "firm_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )


# ─── DATABASE HELPERS ─────────────────────────────────────────────────────────

async def get_db():
    """FastAPI dependency — yields a DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all tables. Run once on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("All tables created.")


async def drop_tables():
    """Drop all tables. Use in dev only."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ─── CRUD OPERATIONS ──────────────────────────────────────────────────────────

from sqlalchemy import select, and_, desc


class ReconciliationRepo:
    """All DB operations for reconciliations."""

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> Reconciliation:
        rec = Reconciliation(**{k: v for k, v in data.items() if k != "mismatches"})
        db.add(rec)
        await db.flush()   # Get the ID before inserting mismatches

        for m_data in data.get("mismatches", []):
            m = Mismatch(reconciliation_id=rec.id, **m_data)
            db.add(m)

        return rec

    @staticmethod
    async def get(db: AsyncSession, rec_id: str, firm_id: str) -> Reconciliation | None:
        result = await db.execute(
            select(Reconciliation).where(
                and_(
                    Reconciliation.id == rec_id,
                    Reconciliation.firm_id == firm_id
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_for_client(
        db: AsyncSession,
        client_id: str,
        firm_id: str,
        limit: int = 20
    ) -> list[Reconciliation]:
        result = await db.execute(
            select(Reconciliation)
            .where(and_(
                Reconciliation.client_id == client_id,
                Reconciliation.firm_id == firm_id
            ))
            .order_by(desc(Reconciliation.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def update_summary(db: AsyncSession, rec_id: str, ai_summary: str):
        rec = await db.get(Reconciliation, rec_id)
        if rec:
            rec.ai_summary = ai_summary


class MismatchRepo:
    @staticmethod
    async def resolve(
        db: AsyncSession,
        mismatch_id: str,
        user_id: str,
        notes: str,
        status: MismatchStatus = MismatchStatus.RESOLVED
    ):
        m = await db.get(Mismatch, mismatch_id)
        if m:
            m.status = status
            m.resolved_at = datetime.utcnow()
            m.resolved_by = user_id
            m.resolution_notes = notes

    @staticmethod
    async def save_ai_explanation(db: AsyncSession, mismatch_id: str, explanation: str):
        m = await db.get(Mismatch, mismatch_id)
        if m:
            m.ai_explanation = explanation

    @staticmethod
    async def save_vendor_email(db: AsyncSession, mismatch_id: str, email_draft: str):
        m = await db.get(Mismatch, mismatch_id)
        if m:
            m.vendor_email_draft = email_draft


class ClientRepo:
    @staticmethod
    async def list_for_firm(db: AsyncSession, firm_id: str) -> list[GSTClient]:
        result = await db.execute(
            select(GSTClient)
            .where(and_(GSTClient.firm_id == firm_id, GSTClient.is_active == True))
            .order_by(GSTClient.name)
        )
        return result.scalars().all()

    @staticmethod
    async def get(db: AsyncSession, client_id: str, firm_id: str) -> GSTClient | None:
        result = await db.execute(
            select(GSTClient).where(
                and_(GSTClient.id == client_id, GSTClient.firm_id == firm_id)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> GSTClient:
        client = GSTClient(**data)
        db.add(client)
        return client


class AuditRepo:
    @staticmethod
    async def log(
        db: AsyncSession,
        firm_id: str,
        user_id: str,
        action: str,
        entity_type: str = None,
        entity_id: str = None,
        details: dict = None,
        ip_address: str = None
    ):
        entry = AuditLog(
            firm_id=firm_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
            ip_address=ip_address
        )
        db.add(entry)


# ─── RUN ONCE TO CREATE TABLES ────────────────────────────────────────────────
if __name__ == "__main__":
    import asyncio
    asyncio.run(create_tables())
