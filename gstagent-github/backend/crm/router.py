from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Boolean, DateTime, Float, String, Text, and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from auth import CurrentUser, get_current_user
from database import Base, get_db, new_id
from .schemas import CRMClientCreate, CRMClientUpdate, CRMBillingCreate, CRMNoticeCreate, CRMDocumentCreate

crm_router = APIRouter(prefix="/crm", tags=["Client CRM"])


class CRMClient(Base):
    __tablename__ = "crm_clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    client_name: Mapped[str] = mapped_column(String(200), nullable=False)
    trade_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    pan: Mapped[Optional[str]] = mapped_column(String(10), index=True, nullable=True)
    gstin: Mapped[Optional[str]] = mapped_column(String(15), index=True, nullable=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    business_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    assigned_staff: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    gst_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    income_tax_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    tds_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    audit_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    monthly_gst_fee: Mapped[float] = mapped_column(Float, default=0.0)
    itr_fee: Mapped[float] = mapped_column(Float, default=0.0)
    notice_fee: Mapped[float] = mapped_column(Float, default=0.0)
    audit_fee: Mapped[float] = mapped_column(Float, default=0.0)
    outstanding_amount: Mapped[float] = mapped_column(Float, default=0.0)
    paid_amount: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CRMDocument(Base):
    __tablename__ = "crm_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    client_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_name: Mapped[str] = mapped_column(String(300), nullable=False)
    file_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CRMBillingItem(Base):
    __tablename__ = "crm_billing_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    client_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    service_type: Mapped[str] = mapped_column(String(50), default="gst")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30), default="unpaid", index=True)
    due_date: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CRMNotice(Base):
    __tablename__ = "crm_notices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    client_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    notice_type: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str] = mapped_column(String(50), default="gst", index=True)
    notice_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    received_date: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    due_date: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def client_to_dict(c: CRMClient) -> dict:
    return {
        "id": c.id,
        "firm_id": c.firm_id,
        "client_name": c.client_name,
        "trade_name": c.trade_name,
        "pan": c.pan,
        "gstin": c.gstin,
        "mobile": c.mobile,
        "email": c.email,
        "address": c.address,
        "city": c.city,
        "state": c.state,
        "business_type": c.business_type,
        "assigned_staff": c.assigned_staff,
        "status": c.status,
        "gst_enabled": c.gst_enabled,
        "income_tax_enabled": c.income_tax_enabled,
        "tds_enabled": c.tds_enabled,
        "audit_enabled": c.audit_enabled,
        "monthly_gst_fee": c.monthly_gst_fee,
        "itr_fee": c.itr_fee,
        "notice_fee": c.notice_fee,
        "audit_fee": c.audit_fee,
        "outstanding_amount": c.outstanding_amount,
        "paid_amount": c.paid_amount,
        "notes": c.notes,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def row_to_dict(row) -> dict:
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in row.__dict__.items() if not k.startswith("_")}


async def get_client_or_404(db: AsyncSession, firm_id: str, client_id: str) -> CRMClient:
    result = await db.execute(select(CRMClient).where(and_(CRMClient.id == client_id, CRMClient.firm_id == firm_id)))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="CRM client not found")
    return client


@crm_router.get("/status")
async def crm_status(current_user: CurrentUser = Depends(get_current_user)):
    return {"status": "ok", "module": "client_crm", "version": "1.0.0", "firm_id": current_user.firm_id}


@crm_router.get("/dashboard")
async def crm_dashboard(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    firm_id = current_user.firm_id
    total = await db.scalar(select(func.count()).select_from(CRMClient).where(CRMClient.firm_id == firm_id)) or 0
    active = await db.scalar(select(func.count()).select_from(CRMClient).where(and_(CRMClient.firm_id == firm_id, CRMClient.status == "active"))) or 0
    gst_clients = await db.scalar(select(func.count()).select_from(CRMClient).where(and_(CRMClient.firm_id == firm_id, CRMClient.gst_enabled == True))) or 0
    itr_clients = await db.scalar(select(func.count()).select_from(CRMClient).where(and_(CRMClient.firm_id == firm_id, CRMClient.income_tax_enabled == True))) or 0
    open_notices = await db.scalar(select(func.count()).select_from(CRMNotice).where(and_(CRMNotice.firm_id == firm_id, CRMNotice.status != "closed"))) or 0
    outstanding = await db.scalar(select(func.coalesce(func.sum(CRMBillingItem.amount), 0)).where(and_(CRMBillingItem.firm_id == firm_id, CRMBillingItem.status == "unpaid"))) or 0
    recent = await db.execute(select(CRMClient).where(CRMClient.firm_id == firm_id).order_by(desc(CRMClient.created_at)).limit(6))
    return {
        "total_clients": total,
        "active_clients": active,
        "gst_clients": gst_clients,
        "itr_clients": itr_clients,
        "open_notices": open_notices,
        "outstanding_amount": float(outstanding or 0),
        "recent_clients": [client_to_dict(c) for c in recent.scalars().all()],
    }


@crm_router.get("/clients")
async def list_clients(q: str = "", status: str = "all", current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(CRMClient).where(CRMClient.firm_id == current_user.firm_id)
    if status != "all":
        stmt = stmt.where(CRMClient.status == status)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where((CRMClient.client_name.ilike(like)) | (CRMClient.trade_name.ilike(like)) | (CRMClient.pan.ilike(like)) | (CRMClient.gstin.ilike(like)))
    stmt = stmt.order_by(desc(CRMClient.created_at))
    result = await db.execute(stmt)
    return {"clients": [client_to_dict(c) for c in result.scalars().all()]}


@crm_router.post("/clients")
async def create_client(payload: CRMClientCreate, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if payload.pan:
        payload.pan = payload.pan.upper().strip()
    if payload.gstin:
        payload.gstin = payload.gstin.upper().strip()
    client = CRMClient(firm_id=current_user.firm_id, created_by=current_user.user_id, **payload.model_dump())
    db.add(client)
    await db.flush()
    return {"client": client_to_dict(client)}


@crm_router.get("/clients/{client_id}")
async def get_client(client_id: str, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    client = await get_client_or_404(db, current_user.firm_id, client_id)
    docs = await db.execute(select(CRMDocument).where(and_(CRMDocument.firm_id == current_user.firm_id, CRMDocument.client_id == client_id)).order_by(desc(CRMDocument.created_at)))
    bills = await db.execute(select(CRMBillingItem).where(and_(CRMBillingItem.firm_id == current_user.firm_id, CRMBillingItem.client_id == client_id)).order_by(desc(CRMBillingItem.created_at)))
    notices = await db.execute(select(CRMNotice).where(and_(CRMNotice.firm_id == current_user.firm_id, CRMNotice.client_id == client_id)).order_by(desc(CRMNotice.created_at)))
    return {
        "client": client_to_dict(client),
        "documents": [row_to_dict(x) for x in docs.scalars().all()],
        "billing": [row_to_dict(x) for x in bills.scalars().all()],
        "notices": [row_to_dict(x) for x in notices.scalars().all()],
    }


@crm_router.put("/clients/{client_id}")
async def update_client(client_id: str, payload: CRMClientUpdate, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    client = await get_client_or_404(db, current_user.firm_id, client_id)
    data = payload.model_dump(exclude_unset=True)
    if "pan" in data and data["pan"]:
        data["pan"] = data["pan"].upper().strip()
    if "gstin" in data and data["gstin"]:
        data["gstin"] = data["gstin"].upper().strip()
    for key, value in data.items():
        setattr(client, key, value)
    client.updated_at = datetime.utcnow()
    return {"client": client_to_dict(client)}


@crm_router.delete("/clients/{client_id}")
async def delete_client(client_id: str, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    client = await get_client_or_404(db, current_user.firm_id, client_id)
    client.status = "inactive"
    client.updated_at = datetime.utcnow()
    return {"message": "Client marked inactive", "client_id": client_id}


@crm_router.post("/documents")
async def add_document(payload: CRMDocumentCreate, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await get_client_or_404(db, current_user.firm_id, payload.client_id)
    doc = CRMDocument(firm_id=current_user.firm_id, created_by=current_user.user_id, **payload.model_dump())
    db.add(doc)
    await db.flush()
    return {"document": row_to_dict(doc)}


@crm_router.get("/documents/{client_id}")
async def list_documents(client_id: str, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await get_client_or_404(db, current_user.firm_id, client_id)
    result = await db.execute(select(CRMDocument).where(and_(CRMDocument.firm_id == current_user.firm_id, CRMDocument.client_id == client_id)).order_by(desc(CRMDocument.created_at)))
    return {"documents": [row_to_dict(x) for x in result.scalars().all()]}


@crm_router.post("/billing")
async def add_billing(payload: CRMBillingCreate, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await get_client_or_404(db, current_user.firm_id, payload.client_id)
    item = CRMBillingItem(firm_id=current_user.firm_id, created_by=current_user.user_id, **payload.model_dump())
    db.add(item)
    await db.flush()
    return {"billing_item": row_to_dict(item)}


@crm_router.get("/billing/{client_id}")
async def list_billing(client_id: str, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await get_client_or_404(db, current_user.firm_id, client_id)
    result = await db.execute(select(CRMBillingItem).where(and_(CRMBillingItem.firm_id == current_user.firm_id, CRMBillingItem.client_id == client_id)).order_by(desc(CRMBillingItem.created_at)))
    return {"billing": [row_to_dict(x) for x in result.scalars().all()]}


@crm_router.post("/notices")
async def add_notice(payload: CRMNoticeCreate, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await get_client_or_404(db, current_user.firm_id, payload.client_id)
    notice = CRMNotice(firm_id=current_user.firm_id, created_by=current_user.user_id, **payload.model_dump())
    db.add(notice)
    await db.flush()
    return {"notice": row_to_dict(notice)}


@crm_router.get("/notices/{client_id}")
async def list_notices(client_id: str, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await get_client_or_404(db, current_user.firm_id, client_id)
    result = await db.execute(select(CRMNotice).where(and_(CRMNotice.firm_id == current_user.firm_id, CRMNotice.client_id == client_id)).order_by(desc(CRMNotice.created_at)))
    return {"notices": [row_to_dict(x) for x in result.scalars().all()]}
