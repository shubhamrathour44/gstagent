from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import DateTime, String, Text, select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from auth import CurrentUser, get_current_user
from database import Base, get_db, new_id


router = APIRouter(prefix="/documents", tags=["Document Vault"])


class DocumentVault(Base):
    __tablename__ = "document_vault"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    firm_id: Mapped[str] = mapped_column(String(36), index=True)

    client_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    client_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    document_type: Mapped[str] = mapped_column(String(100), default="other")
    category: Mapped[str] = mapped_column(String(100), default="general")

    file_name: Mapped[str] = mapped_column(String(255))
    file_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    uploaded_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DocumentCreate(BaseModel):
    client_id: Optional[str] = None
    client_name: Optional[str] = None

    document_type: str = "other"
    category: str = "general"

    file_name: str
    file_url: Optional[str] = None
    file_size: Optional[str] = None
    mime_type: Optional[str] = None

    remarks: Optional[str] = None


class DocumentUpdate(BaseModel):
    client_id: Optional[str] = None
    client_name: Optional[str] = None

    document_type: Optional[str] = None
    category: Optional[str] = None

    file_name: Optional[str] = None
    file_url: Optional[str] = None
    file_size: Optional[str] = None
    mime_type: Optional[str] = None

    remarks: Optional[str] = None


def document_to_dict(doc: DocumentVault) -> dict:
    return {
        "id": doc.id,
        "firm_id": doc.firm_id,
        "client_id": doc.client_id,
        "client_name": doc.client_name,
        "document_type": doc.document_type,
        "category": doc.category,
        "file_name": doc.file_name,
        "file_url": doc.file_url,
        "file_size": doc.file_size,
        "mime_type": doc.mime_type,
        "remarks": doc.remarks,
        "uploaded_by": doc.uploaded_by,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }


async def get_document_or_404(
    db: AsyncSession,
    firm_id: str,
    document_id: str
) -> DocumentVault:
    result = await db.execute(
        select(DocumentVault).where(
            and_(
                DocumentVault.id == document_id,
                DocumentVault.firm_id == firm_id
            )
        )
    )

    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return doc


@router.get("/status")
async def documents_status(
    current_user: CurrentUser = Depends(get_current_user)
):
    return {
        "status": "ok",
        "module": "document_vault",
        "storage": "postgresql",
        "firm_id": current_user.firm_id,
        "features": [
            "create_document",
            "list_documents",
            "search_documents",
            "client_documents",
            "dashboard",
            "update_document",
            "delete_document",
            "firm_isolation"
        ]
    }


@router.post("/create")
async def create_document(
    payload: DocumentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    doc = DocumentVault(
        firm_id=current_user.firm_id,
        client_id=payload.client_id,
        client_name=payload.client_name,
        document_type=payload.document_type,
        category=payload.category,
        file_name=payload.file_name,
        file_url=payload.file_url,
        file_size=payload.file_size,
        mime_type=payload.mime_type,
        remarks=payload.remarks,
        uploaded_by=current_user.user_id,
    )

    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return {
        "message": "Document saved",
        "document": document_to_dict(doc)
    }


@router.get("/list")
async def list_documents(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(DocumentVault)
        .where(DocumentVault.firm_id == current_user.firm_id)
        .order_by(desc(DocumentVault.uploaded_at))
    )

    documents = result.scalars().all()

    return {
        "documents": [document_to_dict(d) for d in documents],
        "count": len(documents)
    }


@router.get("/client/{client_id}")
async def client_documents(
    client_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(DocumentVault)
        .where(
            and_(
                DocumentVault.firm_id == current_user.firm_id,
                DocumentVault.client_id == client_id
            )
        )
        .order_by(desc(DocumentVault.uploaded_at))
    )

    documents = result.scalars().all()

    return {
        "client_id": client_id,
        "documents": [document_to_dict(d) for d in documents],
        "count": len(documents)
    }


@router.get("/search")
async def search_documents(
    q: str = "",
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    like = f"%{q}%"

    result = await db.execute(
        select(DocumentVault)
        .where(
            and_(
                DocumentVault.firm_id == current_user.firm_id,
                or_(
                    DocumentVault.client_name.ilike(like),
                    DocumentVault.document_type.ilike(like),
                    DocumentVault.category.ilike(like),
                    DocumentVault.file_name.ilike(like),
                    DocumentVault.remarks.ilike(like),
                )
            )
        )
        .order_by(desc(DocumentVault.uploaded_at))
    )

    documents = result.scalars().all()

    return {
        "query": q,
        "documents": [document_to_dict(d) for d in documents],
        "count": len(documents)
    }


@router.get("/dashboard")
async def documents_dashboard(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    firm_filter = DocumentVault.firm_id == current_user.firm_id

    total_documents = await db.scalar(
        select(func.count()).select_from(DocumentVault).where(firm_filter)
    ) or 0

    gst_documents = await db.scalar(
        select(func.count())
        .select_from(DocumentVault)
        .where(and_(firm_filter, DocumentVault.category == "gst"))
    ) or 0

    itr_documents = await db.scalar(
        select(func.count())
        .select_from(DocumentVault)
        .where(and_(firm_filter, DocumentVault.category == "itr"))
    ) or 0

    notice_documents = await db.scalar(
        select(func.count())
        .select_from(DocumentVault)
        .where(and_(firm_filter, DocumentVault.category == "notice"))
    ) or 0

    result = await db.execute(
        select(DocumentVault)
        .where(firm_filter)
        .order_by(desc(DocumentVault.uploaded_at))
        .limit(10)
    )

    recent_documents = result.scalars().all()

    return {
        "total_documents": total_documents,
        "gst_documents": gst_documents,
        "itr_documents": itr_documents,
        "notice_documents": notice_documents,
        "recent_documents": [document_to_dict(d) for d in recent_documents]
    }


@router.put("/update/{document_id}")
async def update_document(
    document_id: str,
    payload: DocumentUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    doc = await get_document_or_404(db, current_user.firm_id, document_id)

    updates = payload.model_dump(exclude_unset=True)

    for key, value in updates.items():
        setattr(doc, key, value)

    doc.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(doc)

    return {
        "message": "Document updated",
        "document": document_to_dict(doc)
    }


@router.delete("/delete/{document_id}")
async def delete_document(
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    doc = await get_document_or_404(db, current_user.firm_id, document_id)

    await db.delete(doc)
    await db.commit()

    return {
        "message": "Document deleted",
        "id": document_id
    }