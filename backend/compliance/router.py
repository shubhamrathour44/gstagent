from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Date, DateTime, String, Text, select, func, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from auth import CurrentUser, get_current_user
from database import Base, get_db, new_id


compliance_router = APIRouter(prefix="/compliance", tags=["Compliance"])


class ComplianceRecord(Base):
    __tablename__ = "compliance_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True)

    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    gstin: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    pan: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    gst_status: Mapped[str] = mapped_column(String(50), default="pending")
    itr_status: Mapped[str] = mapped_column(String(50), default="pending")
    tds_status: Mapped[str] = mapped_column(String(50), default="pending")
    notice_status: Mapped[str] = mapped_column(String(50), default="none")

    gst_due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    itr_due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    tds_due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    assigned_staff: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ComplianceCreate(BaseModel):
    client_name: str
    gstin: Optional[str] = None
    pan: Optional[str] = None

    gst_status: str = "pending"
    itr_status: str = "pending"
    tds_status: str = "pending"
    notice_status: str = "none"

    gst_due_date: Optional[date] = None
    itr_due_date: Optional[date] = None
    tds_due_date: Optional[date] = None

    assigned_staff: Optional[str] = None
    remarks: Optional[str] = None


class ComplianceUpdate(BaseModel):
    client_name: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None

    gst_status: Optional[str] = None
    itr_status: Optional[str] = None
    tds_status: Optional[str] = None
    notice_status: Optional[str] = None

    gst_due_date: Optional[date] = None
    itr_due_date: Optional[date] = None
    tds_due_date: Optional[date] = None

    assigned_staff: Optional[str] = None
    remarks: Optional[str] = None


def record_to_dict(r: ComplianceRecord) -> dict:
    return {
        "id": r.id,
        "firm_id": r.firm_id,
        "client_name": r.client_name,
        "gstin": r.gstin,
        "pan": r.pan,
        "gst_status": r.gst_status,
        "itr_status": r.itr_status,
        "tds_status": r.tds_status,
        "notice_status": r.notice_status,
        "gst_due_date": str(r.gst_due_date) if r.gst_due_date else None,
        "itr_due_date": str(r.itr_due_date) if r.itr_due_date else None,
        "tds_due_date": str(r.tds_due_date) if r.tds_due_date else None,
        "assigned_staff": r.assigned_staff,
        "remarks": r.remarks,
        "created_by": r.created_by,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


async def get_record_or_404(
    db: AsyncSession,
    firm_id: str,
    record_id: str
) -> ComplianceRecord:
    result = await db.execute(
        select(ComplianceRecord).where(
            and_(
                ComplianceRecord.id == record_id,
                ComplianceRecord.firm_id == firm_id
            )
        )
    )

    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="Compliance record not found")

    return record


@compliance_router.get("/status")
async def compliance_status(
    current_user: CurrentUser = Depends(get_current_user)
):
    return {
        "status": "ok",
        "module": "compliance_tracker",
        "storage": "postgresql",
        "firm_id": current_user.firm_id,
        "features": [
            "create_compliance",
            "list_compliance",
            "search_compliance",
            "dashboard",
            "update_compliance",
            "delete_compliance",
            "firm_isolation"
        ]
    }


@compliance_router.post("/create")
async def create_compliance(
    payload: ComplianceCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    record = ComplianceRecord(
        firm_id=current_user.firm_id,
        client_name=payload.client_name,
        gstin=payload.gstin,
        pan=payload.pan,
        gst_status=payload.gst_status,
        itr_status=payload.itr_status,
        tds_status=payload.tds_status,
        notice_status=payload.notice_status,
        gst_due_date=payload.gst_due_date,
        itr_due_date=payload.itr_due_date,
        tds_due_date=payload.tds_due_date,
        assigned_staff=payload.assigned_staff,
        remarks=payload.remarks,
        created_by=current_user.user_id,
    )

    db.add(record)
    await db.commit()
    await db.refresh(record)

    return {
        "message": "Compliance record created",
        "record": record_to_dict(record)
    }


@compliance_router.get("/list")
async def list_compliance(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ComplianceRecord)
        .where(ComplianceRecord.firm_id == current_user.firm_id)
        .order_by(desc(ComplianceRecord.created_at))
    )

    records = result.scalars().all()

    return {
        "records": [record_to_dict(r) for r in records],
        "count": len(records)
    }


@compliance_router.get("/search")
async def search_compliance(
    q: str = "",
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    like = f"%{q}%"

    result = await db.execute(
        select(ComplianceRecord)
        .where(
            and_(
                ComplianceRecord.firm_id == current_user.firm_id,
                or_(
                    ComplianceRecord.client_name.ilike(like),
                    ComplianceRecord.gstin.ilike(like),
                    ComplianceRecord.pan.ilike(like),
                    ComplianceRecord.gst_status.ilike(like),
                    ComplianceRecord.itr_status.ilike(like),
                    ComplianceRecord.tds_status.ilike(like),
                    ComplianceRecord.notice_status.ilike(like),
                    ComplianceRecord.assigned_staff.ilike(like),
                )
            )
        )
        .order_by(desc(ComplianceRecord.created_at))
    )

    records = result.scalars().all()

    return {
        "query": q,
        "count": len(records),
        "records": [record_to_dict(r) for r in records]
    }


@compliance_router.get("/dashboard")
async def compliance_dashboard(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    firm_filter = ComplianceRecord.firm_id == current_user.firm_id

    total_clients = await db.scalar(
        select(func.count())
        .select_from(ComplianceRecord)
        .where(firm_filter)
    ) or 0

    gst_pending = await db.scalar(
        select(func.count())
        .select_from(ComplianceRecord)
        .where(and_(firm_filter, ComplianceRecord.gst_status == "pending"))
    ) or 0

    gst_filed = await db.scalar(
        select(func.count())
        .select_from(ComplianceRecord)
        .where(and_(firm_filter, ComplianceRecord.gst_status == "filed"))
    ) or 0

    itr_pending = await db.scalar(
        select(func.count())
        .select_from(ComplianceRecord)
        .where(and_(firm_filter, ComplianceRecord.itr_status == "pending"))
    ) or 0

    itr_filed = await db.scalar(
        select(func.count())
        .select_from(ComplianceRecord)
        .where(and_(firm_filter, ComplianceRecord.itr_status == "filed"))
    ) or 0

    tds_pending = await db.scalar(
        select(func.count())
        .select_from(ComplianceRecord)
        .where(and_(firm_filter, ComplianceRecord.tds_status == "pending"))
    ) or 0

    tds_filed = await db.scalar(
        select(func.count())
        .select_from(ComplianceRecord)
        .where(and_(firm_filter, ComplianceRecord.tds_status == "filed"))
    ) or 0

    open_notices = await db.scalar(
        select(func.count())
        .select_from(ComplianceRecord)
        .where(
            and_(
                firm_filter,
                ComplianceRecord.notice_status.in_(["open", "pending"])
            )
        )
    ) or 0

    overdue_gst = await db.scalar(
        select(func.count())
        .select_from(ComplianceRecord)
        .where(
            and_(
                firm_filter,
                ComplianceRecord.gst_status == "pending",
                ComplianceRecord.gst_due_date < date.today()
            )
        )
    ) or 0

    overdue_itr = await db.scalar(
        select(func.count())
        .select_from(ComplianceRecord)
        .where(
            and_(
                firm_filter,
                ComplianceRecord.itr_status == "pending",
                ComplianceRecord.itr_due_date < date.today()
            )
        )
    ) or 0

    overdue_tds = await db.scalar(
        select(func.count())
        .select_from(ComplianceRecord)
        .where(
            and_(
                firm_filter,
                ComplianceRecord.tds_status == "pending",
                ComplianceRecord.tds_due_date < date.today()
            )
        )
    ) or 0

    return {
        "total_clients": total_clients,
        "gst_pending": gst_pending,
        "gst_filed": gst_filed,
        "itr_pending": itr_pending,
        "itr_filed": itr_filed,
        "tds_pending": tds_pending,
        "tds_filed": tds_filed,
        "open_notices": open_notices,
        "overdue_gst": overdue_gst,
        "overdue_itr": overdue_itr,
        "overdue_tds": overdue_tds,
        "total_overdue": overdue_gst + overdue_itr + overdue_tds
    }


@compliance_router.put("/update/{record_id}")
async def update_compliance(
    record_id: str,
    payload: ComplianceUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    record = await get_record_or_404(db, current_user.firm_id, record_id)

    updates = payload.model_dump(exclude_unset=True)

    for key, value in updates.items():
        setattr(record, key, value)

    record.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(record)

    return {
        "message": "Compliance record updated",
        "record": record_to_dict(record)
    }


@compliance_router.put("/mark-filed/{record_id}/{return_type}")
async def mark_filed(
    record_id: str,
    return_type: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    record = await get_record_or_404(db, current_user.firm_id, record_id)

    if return_type == "gst":
        record.gst_status = "filed"
    elif return_type == "itr":
        record.itr_status = "filed"
    elif return_type == "tds":
        record.tds_status = "filed"
    else:
        raise HTTPException(
            status_code=400,
            detail="return_type must be gst, itr, or tds"
        )

    record.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(record)

    return {
        "message": f"{return_type.upper()} marked as filed",
        "record": record_to_dict(record)
    }


@compliance_router.delete("/delete/{record_id}")
async def delete_compliance(
    record_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    record = await get_record_or_404(db, current_user.firm_id, record_id)

    await db.delete(record)
    await db.commit()

    return {
        "message": "Compliance record deleted",
        "id": record_id
    }