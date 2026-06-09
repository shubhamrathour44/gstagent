from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import DateTime, String, Text, select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from auth import CurrentUser, get_current_user
from database import Base, get_db, new_id


router = APIRouter(prefix="/tasks", tags=["Task & Staff Management"])


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True)

    client_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    client_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    task_type: Mapped[str] = mapped_column(String(100), default="general")
    priority: Mapped[str] = mapped_column(String(50), default="medium")
    status: Mapped[str] = mapped_column(String(50), default="pending")

    assigned_staff: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    assigned_staff_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    linked_notice_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    linked_compliance_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    linked_document_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaskCreate(BaseModel):
    client_id: Optional[str] = None
    client_name: Optional[str] = None

    title: str
    description: Optional[str] = None

    task_type: str = "general"
    priority: str = "medium"
    status: str = "pending"

    assigned_staff: Optional[str] = None
    assigned_staff_email: Optional[str] = None

    due_date: Optional[datetime] = None

    linked_notice_id: Optional[str] = None
    linked_compliance_id: Optional[str] = None
    linked_document_id: Optional[str] = None

    remarks: Optional[str] = None


class TaskUpdate(BaseModel):
    client_id: Optional[str] = None
    client_name: Optional[str] = None

    title: Optional[str] = None
    description: Optional[str] = None

    task_type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None

    assigned_staff: Optional[str] = None
    assigned_staff_email: Optional[str] = None

    due_date: Optional[datetime] = None

    linked_notice_id: Optional[str] = None
    linked_compliance_id: Optional[str] = None
    linked_document_id: Optional[str] = None

    remarks: Optional[str] = None


def task_to_dict(t: Task) -> dict:
    return {
        "id": t.id,
        "firm_id": t.firm_id,
        "client_id": t.client_id,
        "client_name": t.client_name,
        "title": t.title,
        "description": t.description,
        "task_type": t.task_type,
        "priority": t.priority,
        "status": t.status,
        "assigned_staff": t.assigned_staff,
        "assigned_staff_email": t.assigned_staff_email,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "linked_notice_id": t.linked_notice_id,
        "linked_compliance_id": t.linked_compliance_id,
        "linked_document_id": t.linked_document_id,
        "remarks": t.remarks,
        "created_by": t.created_by,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


async def get_task_or_404(db: AsyncSession, firm_id: str, task_id: str) -> Task:
    result = await db.execute(
        select(Task).where(
            and_(
                Task.id == task_id,
                Task.firm_id == firm_id
            )
        )
    )

    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@router.get("/status")
async def tasks_status(current_user: CurrentUser = Depends(get_current_user)):
    return {
        "status": "ok",
        "module": "task_staff_management",
        "storage": "postgresql",
        "firm_id": current_user.firm_id,
        "features": [
            "create_task",
            "list_tasks",
            "search_tasks",
            "dashboard",
            "update_task",
            "delete_task",
            "mark_completed",
            "firm_isolation"
        ]
    }


@router.post("/create")
async def create_task(
    payload: TaskCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    task = Task(
        firm_id=current_user.firm_id,
        client_id=payload.client_id,
        client_name=payload.client_name,
        title=payload.title,
        description=payload.description,
        task_type=payload.task_type,
        priority=payload.priority,
        status=payload.status,
        assigned_staff=payload.assigned_staff,
        assigned_staff_email=payload.assigned_staff_email,
        due_date=payload.due_date,
        linked_notice_id=payload.linked_notice_id,
        linked_compliance_id=payload.linked_compliance_id,
        linked_document_id=payload.linked_document_id,
        remarks=payload.remarks,
        created_by=current_user.user_id,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    return {
        "message": "Task created",
        "task": task_to_dict(task)
    }


@router.get("/list")
async def list_tasks(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Task)
        .where(Task.firm_id == current_user.firm_id)
        .order_by(desc(Task.created_at))
    )

    tasks = result.scalars().all()

    return {
        "tasks": [task_to_dict(t) for t in tasks],
        "count": len(tasks)
    }


@router.get("/search")
async def search_tasks(
    q: str = "",
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    like = f"%{q}%"

    result = await db.execute(
        select(Task)
        .where(
            and_(
                Task.firm_id == current_user.firm_id,
                or_(
                    Task.client_name.ilike(like),
                    Task.title.ilike(like),
                    Task.description.ilike(like),
                    Task.task_type.ilike(like),
                    Task.priority.ilike(like),
                    Task.status.ilike(like),
                    Task.assigned_staff.ilike(like),
                    Task.assigned_staff_email.ilike(like),
                    Task.remarks.ilike(like),
                )
            )
        )
        .order_by(desc(Task.created_at))
    )

    tasks = result.scalars().all()

    return {
        "query": q,
        "tasks": [task_to_dict(t) for t in tasks],
        "count": len(tasks)
    }


@router.get("/dashboard")
async def tasks_dashboard(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    firm_filter = Task.firm_id == current_user.firm_id

    total_tasks = await db.scalar(
        select(func.count()).select_from(Task).where(firm_filter)
    ) or 0

    pending_tasks = await db.scalar(
        select(func.count()).select_from(Task).where(and_(firm_filter, Task.status == "pending"))
    ) or 0

    in_progress_tasks = await db.scalar(
        select(func.count()).select_from(Task).where(and_(firm_filter, Task.status == "in_progress"))
    ) or 0

    review_tasks = await db.scalar(
        select(func.count()).select_from(Task).where(and_(firm_filter, Task.status == "review"))
    ) or 0

    completed_tasks = await db.scalar(
        select(func.count()).select_from(Task).where(and_(firm_filter, Task.status == "completed"))
    ) or 0

    high_priority_tasks = await db.scalar(
        select(func.count()).select_from(Task).where(and_(firm_filter, Task.priority == "high"))
    ) or 0

    overdue_tasks = await db.scalar(
        select(func.count())
        .select_from(Task)
        .where(
            and_(
                firm_filter,
                Task.status != "completed",
                Task.due_date < datetime.utcnow()
            )
        )
    ) or 0

    result = await db.execute(
        select(Task)
        .where(firm_filter)
        .order_by(desc(Task.created_at))
        .limit(10)
    )

    recent_tasks = result.scalars().all()

    return {
        "total_tasks": total_tasks,
        "pending_tasks": pending_tasks,
        "in_progress_tasks": in_progress_tasks,
        "review_tasks": review_tasks,
        "completed_tasks": completed_tasks,
        "high_priority_tasks": high_priority_tasks,
        "overdue_tasks": overdue_tasks,
        "recent_tasks": [task_to_dict(t) for t in recent_tasks]
    }


@router.put("/update/{task_id}")
async def update_task(
    task_id: str,
    payload: TaskUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    task = await get_task_or_404(db, current_user.firm_id, task_id)

    updates = payload.model_dump(exclude_unset=True)

    for key, value in updates.items():
        setattr(task, key, value)

    task.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(task)

    return {
        "message": "Task updated",
        "task": task_to_dict(task)
    }


@router.put("/mark-completed/{task_id}")
async def mark_completed(
    task_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    task = await get_task_or_404(db, current_user.firm_id, task_id)

    task.status = "completed"
    task.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(task)

    return {
        "message": "Task marked completed",
        "task": task_to_dict(task)
    }


@router.delete("/delete/{task_id}")
async def delete_task(
    task_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    task = await get_task_or_404(db, current_user.firm_id, task_id)

    await db.delete(task)
    await db.commit()

    return {
        "message": "Task deleted",
        "id": task_id
    }