from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import (
    String,
    DateTime,
    Text,
    Integer,
    select,
    func,
    and_,
    or_,
    desc
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from auth import CurrentUser, get_current_user
from database import Base, get_db, new_id


router = APIRouter(
    prefix="/notices",
    tags=["Notice Management"]
)


# =====================================================
# DATABASE MODEL
# =====================================================

class Notice(Base):
    __tablename__ = "notices"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=new_id
    )

    firm_id: Mapped[str] = mapped_column(
        String(36),
        index=True
    )

    client_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True
    )

    client_name: Mapped[str] = mapped_column(
        String(255)
    )

    notice_type: Mapped[str] = mapped_column(
        String(100)
    )

    department: Mapped[str] = mapped_column(
        String(100),
        default="GST"
    )

    subject: Mapped[str] = mapped_column(
        String(500)
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        default="medium"
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="open"
    )

    notice_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    assigned_staff: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    notice_document_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    reply_document_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    tax_demand: Mapped[float] = mapped_column(
        default=0.0
    )

    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    created_by: Mapped[str] = mapped_column(
        String(36)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


# =====================================================
# SCHEMAS
# =====================================================

class NoticeCreate(BaseModel):
    client_id: Optional[str] = None
    client_name: str

    notice_type: str
    department: str = "GST"

    subject: str
    description: Optional[str] = None

    priority: str = "medium"

    status: str = "open"

    notice_number: Optional[str] = None

    assigned_staff: Optional[str] = None

    notice_document_url: Optional[str] = None
    reply_document_url: Optional[str] = None

    tax_demand: float = 0.0

    due_date: Optional[datetime] = None


class NoticeUpdate(BaseModel):
    client_name: Optional[str] = None

    notice_type: Optional[str] = None
    department: Optional[str] = None

    subject: Optional[str] = None
    description: Optional[str] = None

    priority: Optional[str] = None
    status: Optional[str] = None

    notice_number: Optional[str] = None

    assigned_staff: Optional[str] = None

    notice_document_url: Optional[str] = None
    reply_document_url: Optional[str] = None

    tax_demand: Optional[float] = None

    due_date: Optional[datetime] = None


# =====================================================
# HELPERS
# =====================================================

def notice_to_dict(n: Notice):
    return {
        "id": n.id,
        "firm_id": n.firm_id,
        "client_id": n.client_id,
        "client_name": n.client_name,
        "notice_type": n.notice_type,
        "department": n.department,
        "subject": n.subject,
        "description": n.description,
        "priority": n.priority,
        "status": n.status,
        "notice_number": n.notice_number,
        "assigned_staff": n.assigned_staff,
        "notice_document_url": n.notice_document_url,
        "reply_document_url": n.reply_document_url,
        "tax_demand": n.tax_demand,
        "due_date": n.due_date.isoformat() if n.due_date else None,
        "created_at": n.created_at.isoformat(),
        "updated_at": n.updated_at.isoformat(),
    }


# =====================================================
# STATUS
# =====================================================

@router.get("/status")
async def status(
    current_user: CurrentUser = Depends(get_current_user)
):
    return {
        "status": "ok",
        "module": "notice_management",
        "storage": "postgresql",
        "firm_id": current_user.firm_id
    }


# =====================================================
# CREATE
# =====================================================

@router.post("/create")
async def create_notice(
    payload: NoticeCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    notice = Notice(
        firm_id=current_user.firm_id,
        client_id=payload.client_id,
        client_name=payload.client_name,
        notice_type=payload.notice_type,
        department=payload.department,
        subject=payload.subject,
        description=payload.description,
        priority=payload.priority,
        status=payload.status,
        notice_number=payload.notice_number,
        assigned_staff=payload.assigned_staff,
        notice_document_url=payload.notice_document_url,
        reply_document_url=payload.reply_document_url,
        tax_demand=payload.tax_demand,
        due_date=payload.due_date,
        created_by=current_user.user_id
    )

    db.add(notice)
    await db.commit()
    await db.refresh(notice)

    return {
        "message": "Notice created",
        "notice": notice_to_dict(notice)
    }


# =====================================================
# LIST
# =====================================================

@router.get("/list")
async def list_notices(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Notice)
        .where(Notice.firm_id == current_user.firm_id)
        .order_by(desc(Notice.created_at))
    )

    notices = result.scalars().all()

    return {
        "count": len(notices),
        "notices": [notice_to_dict(n) for n in notices]
    }


# =====================================================
# SEARCH
# =====================================================

@router.get("/search")
async def search_notices(
    q: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    like = f"%{q}%"

    result = await db.execute(
        select(Notice)
        .where(
            and_(
                Notice.firm_id == current_user.firm_id,
                or_(
                    Notice.client_name.ilike(like),
                    Notice.subject.ilike(like),
                    Notice.notice_number.ilike(like),
                    Notice.department.ilike(like)
                )
            )
        )
    )

    notices = result.scalars().all()

    return {
        "count": len(notices),
        "notices": [notice_to_dict(n) for n in notices]
    }


# =====================================================
# DASHBOARD
# =====================================================

@router.get("/dashboard")
async def dashboard(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    firm_filter = Notice.firm_id == current_user.firm_id

    total = await db.scalar(
        select(func.count())
        .select_from(Notice)
        .where(firm_filter)
    ) or 0

    open_count = await db.scalar(
        select(func.count())
        .select_from(Notice)
        .where(and_(firm_filter, Notice.status == "open"))
    ) or 0

    submitted = await db.scalar(
        select(func.count())
        .select_from(Notice)
        .where(and_(firm_filter, Notice.status == "submitted"))
    ) or 0

    closed = await db.scalar(
        select(func.count())
        .select_from(Notice)
        .where(and_(firm_filter, Notice.status == "closed"))
    ) or 0

    high_priority = await db.scalar(
        select(func.count())
        .select_from(Notice)
        .where(and_(firm_filter, Notice.priority == "high"))
    ) or 0

    return {
        "total_notices": total,
        "open_notices": open_count,
        "submitted_notices": submitted,
        "closed_notices": closed,
        "high_priority": high_priority
    }


# =====================================================
# UPDATE
# =====================================================

@router.put("/update/{notice_id}")
async def update_notice(
    notice_id: str,
    payload: NoticeUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Notice).where(
            and_(
                Notice.id == notice_id,
                Notice.firm_id == current_user.firm_id
            )
        )
    )

    notice = result.scalar_one_or_none()

    if not notice:
        raise HTTPException(404, "Notice not found")

    updates = payload.model_dump(exclude_unset=True)

    for k, v in updates.items():
        setattr(notice, k, v)

    notice.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(notice)

    return {
        "message": "Notice updated",
        "notice": notice_to_dict(notice)
    }


# =====================================================
# DELETE
# =====================================================

@router.delete("/delete/{notice_id}")
async def delete_notice(
    notice_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Notice).where(
            and_(
                Notice.id == notice_id,
                Notice.firm_id == current_user.firm_id
            )
        )
    )

    notice = result.scalar_one_or_none()

    if not notice:
        raise HTTPException(404, "Notice not found")

    await db.delete(notice)
    await db.commit()

    return {
        "message": "Notice deleted"
    }