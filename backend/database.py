"""
GSTAgent database foundation.

What this fixes:
- Real persistence instead of in-memory dictionaries.
- Works locally with SQLite when DATABASE_URL is missing.
- Works on Railway/Postgres when DATABASE_URL is present.
- All client/reconciliation data is scoped by firm_id for multi-tenancy.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _normalise_database_url(url: Optional[str]) -> str:
    if not url:
        return "sqlite+aiosqlite:///./gstagent.db"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


DATABASE_URL = _normalise_database_url(os.getenv("DATABASE_URL"))

_engine_kwargs = {"echo": os.getenv("SQL_ECHO", "0") == "1", "pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs = {"echo": os.getenv("SQL_ECHO", "0") == "1"}

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def new_id() -> str:
    return str(uuid.uuid4())


class CAFirm(Base):
    __tablename__ = "ca_firms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    plan: Mapped[str] = mapped_column(String(50), default="starter")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users: Mapped[list["User"]] = relationship(back_populates="firm", cascade="all, delete-orphan")
    clients: Mapped[list["GSTClient"]] = relationship(back_populates="firm", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), ForeignKey("ca_firms.id"), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(500), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="ca_staff")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    firm: Mapped[CAFirm] = relationship(back_populates="users")


class GSTClient(Base):
    __tablename__ = "gst_clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), ForeignKey("ca_firms.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    gstin: Mapped[str] = mapped_column(String(15), index=True, nullable=False)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    business_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    tally_company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    zoho_org_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    firm: Mapped[CAFirm] = relationship(back_populates="clients")
    reconciliations: Mapped[list["Reconciliation"]] = relationship(back_populates="client", cascade="all, delete-orphan")


class Reconciliation(Base):
    __tablename__ = "reconciliations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    client_id: Mapped[str] = mapped_column(String(36), ForeignKey("gst_clients.id"), index=True, nullable=False)
    gstin: Mapped[str] = mapped_column(String(15), index=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    period: Mapped[str] = mapped_column(String(6), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="file_upload")
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    pr_count: Mapped[int] = mapped_column(Integer, default=0)
    b2b_count: Mapped[int] = mapped_column(Integer, default=0)
    matched_count: Mapped[int] = mapped_column(Integer, default=0)
    mismatch_count: Mapped[int] = mapped_column(Integer, default=0)
    match_rate: Mapped[float] = mapped_column(Float, default=0.0)
    itc_difference: Mapped[float] = mapped_column(Float, default=0.0)
    high_count: Mapped[int] = mapped_column(Integer, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, default=0)
    low_count: Mapped[int] = mapped_column(Integer, default=0)

    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    filing_qa: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    client: Mapped[GSTClient] = relationship(back_populates="reconciliations")
    mismatches: Mapped[list["Mismatch"]] = relationship(back_populates="reconciliation", cascade="all, delete-orphan")


class Mismatch(Base):
    __tablename__ = "mismatches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    reconciliation_id: Mapped[str] = mapped_column(String(36), ForeignKey("reconciliations.id"), index=True, nullable=False)
    mismatch_id: Mapped[str] = mapped_column(String(20), index=True, nullable=False)  # MM0001 etc.
    mismatch_type: Mapped[str] = mapped_column(String(200), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open")

    supplier_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    supplier_gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    invoice_date: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    tax_impact: Mapped[float] = mapped_column(Float, default=0.0)
    recommended_action: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    raw_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    ai_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vendor_email_draft: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    reconciliation: Mapped[Reconciliation] = relationship(back_populates="mismatches")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), ForeignKey("ca_firms.id"), index=True, nullable=False)
    client_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    pan: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    aadhar: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    upi_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bank_account: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bank_ifsc: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)

    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    joining_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    basic_salary: Mapped[float] = mapped_column(Float, default=0.0)
    hra: Mapped[float] = mapped_column(Float, default=0.0)
    dearness_allowance: Mapped[float] = mapped_column(Float, default=0.0)
    other_allowances: Mapped[float] = mapped_column(Float, default=0.0)

    pf_applicable: Mapped[bool] = mapped_column(Boolean, default=True)
    esi_applicable: Mapped[bool] = mapped_column(Boolean, default=True)
    pt_applicable: Mapped[bool] = mapped_column(Boolean, default=False)

    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Attendance(Base):
    __tablename__ = "attendance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"), index=True, nullable=False)

    attendance_date: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="present")
    hours_worked: Mapped[float] = mapped_column(Float, default=8.0)
    remarks: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SalaryStructure(Base):
    __tablename__ = "salary_structures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"), index=True, nullable=False)

    effective_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    basic: Mapped[float] = mapped_column(Float, default=0.0)
    hra: Mapped[float] = mapped_column(Float, default=0.0)
    dearness_allowance: Mapped[float] = mapped_column(Float, default=0.0)
    travel_allowance: Mapped[float] = mapped_column(Float, default=0.0)
    medical_allowance: Mapped[float] = mapped_column(Float, default=0.0)
    other_allowances: Mapped[float] = mapped_column(Float, default=0.0)

    pf_rate: Mapped[float] = mapped_column(Float, default=12.0)
    esi_rate: Mapped[float] = mapped_column(Float, default=0.75)
    pt_rate: Mapped[float] = mapped_column(Float, default=0.0)

    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Payroll(Base):
    __tablename__ = "payrolls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"), index=True, nullable=False)

    month: Mapped[str] = mapped_column(String(7), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft")

    working_days: Mapped[int] = mapped_column(Integer, default=26)
    actual_days_worked: Mapped[int] = mapped_column(Integer, default=26)

    basic_salary: Mapped[float] = mapped_column(Float, default=0.0)
    hra: Mapped[float] = mapped_column(Float, default=0.0)
    dearness_allowance: Mapped[float] = mapped_column(Float, default=0.0)
    travel_allowance: Mapped[float] = mapped_column(Float, default=0.0)
    medical_allowance: Mapped[float] = mapped_column(Float, default=0.0)
    other_allowances: Mapped[float] = mapped_column(Float, default=0.0)

    gross_salary: Mapped[float] = mapped_column(Float, default=0.0)

    pf_deduction: Mapped[float] = mapped_column(Float, default=0.0)
    esi_deduction: Mapped[float] = mapped_column(Float, default=0.0)
    pt_deduction: Mapped[float] = mapped_column(Float, default=0.0)
    income_tax: Mapped[float] = mapped_column(Float, default=0.0)
    other_deductions: Mapped[float] = mapped_column(Float, default=0.0)

    total_deductions: Mapped[float] = mapped_column(Float, default=0.0)
    net_salary: Mapped[float] = mapped_column(Float, default=0.0)

    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    payment_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ITRDocument(Base):
    __tablename__ = "itr_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    itr_return_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("itr_returns.id"), nullable=True)

    document_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    pan: Mapped[Optional[str]] = mapped_column(String(10), index=True, nullable=True)
    assessment_year: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    extraction_status: Mapped[str] = mapped_column(String(20), default="pending")
    extracted_data: Mapped[dict] = mapped_column(JSON, default=dict)
    extraction_errors: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    uploaded_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChartOfAccounts(Base):
    __tablename__ = "chart_of_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), ForeignKey("ca_firms.id"), index=True, nullable=False)

    account_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    sub_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    opening_balance: Mapped[float] = mapped_column(Float, default=0.0)
    opening_balance_type: Mapped[str] = mapped_column(String(10), default="debit")

    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)

    entry_number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    entry_date: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)

    description: Mapped[str] = mapped_column(String(500), nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    total_debit: Mapped[float] = mapped_column(Float, default=0.0)
    total_credit: Mapped[float] = mapped_column(Float, default=0.0)

    is_posted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_reversed: Mapped[bool] = mapped_column(Boolean, default=False)

    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class JournalEntryLine(Base):
    __tablename__ = "journal_entry_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    journal_entry_id: Mapped[str] = mapped_column(String(36), ForeignKey("journal_entries.id"), index=True, nullable=False)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("chart_of_accounts.id"), index=True, nullable=False)

    account_code: Mapped[str] = mapped_column(String(20), nullable=False)
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)

    debit: Mapped[float] = mapped_column(Float, default=0.0)
    credit: Mapped[float] = mapped_column(Float, default=0.0)

    description: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    line_number: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GeneralLedger(Base):
    __tablename__ = "general_ledger"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("chart_of_accounts.id"), index=True, nullable=False)
    journal_entry_id: Mapped[str] = mapped_column(String(36), ForeignKey("journal_entries.id"), index=True, nullable=False)

    account_code: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)

    transaction_date: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    debit: Mapped[float] = mapped_column(Float, default=0.0)
    credit: Mapped[float] = mapped_column(Float, default=0.0)

    running_balance: Mapped[float] = mapped_column(Float, default=0.0)
    balance_type: Mapped[str] = mapped_column(String(10), default="debit")

    posted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TrialBalance(Base):
    __tablename__ = "trial_balance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("chart_of_accounts.id"), index=True, nullable=False)

    account_code: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)

    opening_balance: Mapped[float] = mapped_column(Float, default=0.0)
    opening_balance_type: Mapped[str] = mapped_column(String(10), default="debit")

    total_debit: Mapped[float] = mapped_column(Float, default=0.0)
    total_credit: Mapped[float] = mapped_column(Float, default=0.0)

    closing_balance: Mapped[float] = mapped_column(Float, default=0.0)
    closing_balance_type: Mapped[str] = mapped_column(String(10), default="debit")

    as_on_date: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FinancialStatement(Base):
    __tablename__ = "financial_statements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)

    statement_type: Mapped[str] = mapped_column(String(50), nullable=False)
    statement_period: Mapped[str] = mapped_column(String(20), nullable=False)
    as_on_date: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)

    data: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class FirmRepo:
    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[CAFirm]:
        result = await db.execute(select(CAFirm).where(CAFirm.email == email.lower().strip()))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, name: str, email: str, phone: str | None, city: str | None) -> CAFirm:
        firm = CAFirm(name=name, email=email.lower().strip(), phone=phone, city=city)
        db.add(firm)
        await db.flush()
        return firm


class UserRepo:
    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email.lower().strip()))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, firm_id: str, email: str, name: str, hashed_password: str, role: str) -> User:
        user = User(firm_id=firm_id, email=email.lower().strip(), name=name, hashed_password=hashed_password, role=role)
        db.add(user)
        await db.flush()
        return user


class ClientRepo:
    @staticmethod
    async def list_for_firm(db: AsyncSession, firm_id: str) -> list[GSTClient]:
        result = await db.execute(
            select(GSTClient).where(and_(GSTClient.firm_id == firm_id, GSTClient.is_active == True)).order_by(GSTClient.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get(db: AsyncSession, client_id: str, firm_id: str) -> Optional[GSTClient]:
        result = await db.execute(select(GSTClient).where(and_(GSTClient.id == client_id, GSTClient.firm_id == firm_id)))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_gstin(db: AsyncSession, gstin: str, firm_id: str) -> Optional[GSTClient]:
        result = await db.execute(select(GSTClient).where(and_(GSTClient.gstin == gstin.upper().strip(), GSTClient.firm_id == firm_id, GSTClient.is_active == True)))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, firm_id: str, data: dict) -> GSTClient:
        client = GSTClient(firm_id=firm_id, **data)
        db.add(client)
        await db.flush()
        return client


class ReconciliationRepo:
    @staticmethod
    async def create(db: AsyncSession, *, firm_id: str, client_id: str, company_name: str, source: str, result_json: dict, created_by: str | None) -> Reconciliation:
        summary = result_json.get("summary_stats", {}) or {}
        rec = Reconciliation(
            firm_id=firm_id,
            client_id=client_id,
            gstin=result_json.get("gstin", ""),
            company_name=company_name,
            period=result_json.get("period", ""),
            source=source,
            result_json=result_json,
            pr_count=int(result_json.get("total_pr_invoices", 0) or 0),
            b2b_count=int(result_json.get("total_2b_invoices", 0) or 0),
            matched_count=int(result_json.get("matched_invoices", 0) or 0),
            mismatch_count=int(result_json.get("mismatched_invoices", 0) or 0),
            match_rate=float(summary.get("match_rate", 0.0) or 0.0),
            itc_difference=float(result_json.get("itc_difference", 0.0) or 0.0),
            high_count=int(result_json.get("high_severity_count", 0) or 0),
            medium_count=int(result_json.get("medium_severity_count", 0) or 0),
            low_count=int(result_json.get("low_severity_count", 0) or 0),
            created_by=created_by,
        )
        db.add(rec)
        await db.flush()
        for item in result_json.get("mismatches", []) or []:
            db.add(Mismatch(
                firm_id=firm_id,
                reconciliation_id=rec.id,
                mismatch_id=str(item.get("mismatch_id", "")),
                mismatch_type=str(item.get("mismatch_type", "")),
                severity=str(item.get("severity", "low")),
                supplier_name=item.get("supplier_name"),
                supplier_gstin=item.get("supplier_gstin"),
                invoice_number=item.get("invoice_number"),
                invoice_date=item.get("invoice_date"),
                tax_impact=float(item.get("tax_impact", 0.0) or 0.0),
                recommended_action=item.get("recommended_action"),
                raw_json=item,
            ))
        await db.flush()
        return rec

    @staticmethod
    async def get(db: AsyncSession, rec_id: str, firm_id: str) -> Optional[Reconciliation]:
        result = await db.execute(select(Reconciliation).where(and_(Reconciliation.id == rec_id, Reconciliation.firm_id == firm_id)))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_for_firm(db: AsyncSession, firm_id: str, limit: int = 50) -> list[Reconciliation]:
        result = await db.execute(select(Reconciliation).where(Reconciliation.firm_id == firm_id).order_by(desc(Reconciliation.created_at)).limit(limit))
        return list(result.scalars().all())


class MismatchRepo:
    @staticmethod
    async def get_by_public_id(db: AsyncSession, firm_id: str, rec_id: str, mismatch_id: str) -> Optional[Mismatch]:
        result = await db.execute(select(Mismatch).where(and_(Mismatch.firm_id == firm_id, Mismatch.reconciliation_id == rec_id, Mismatch.mismatch_id == mismatch_id)))
        return result.scalar_one_or_none()

    @staticmethod
    async def save_ai_explanation(db: AsyncSession, mismatch: Mismatch, explanation: str) -> None:
        mismatch.ai_explanation = explanation

    @staticmethod
    async def save_vendor_email(db: AsyncSession, mismatch: Mismatch, email_draft: str) -> None:
        mismatch.vendor_email_draft = email_draft

    @staticmethod
    async def resolve(db: AsyncSession, mismatch: Mismatch, user_id: str, notes: str, status: str = "resolved") -> None:
        mismatch.status = status
        mismatch.resolution_notes = notes
        mismatch.resolved_by = user_id
        mismatch.resolved_at = datetime.utcnow()


class AuditRepo:
    @staticmethod
    async def log(db: AsyncSession, firm_id: str, user_id: str | None, action: str, entity_type: str | None = None, entity_id: str | None = None, details: dict | None = None) -> None:
        db.add(AuditLog(firm_id=firm_id, user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id, details=details or {}))


if __name__ == "__main__":
    import asyncio
    asyncio.run(create_tables())
