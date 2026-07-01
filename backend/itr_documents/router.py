import os
import mimetypes
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from auth import CurrentUser, get_current_user
from database import get_db, ITRDocument
from .schemas import (
    DocumentResponse,
    DocumentListResponse,
    DocumentExtractionResult,
    DocumentStatistics,
)
from .parser import DocumentParserFactory

router = APIRouter(prefix="/itr-documents", tags=["ITR Documents"])

# Configuration
UPLOAD_DIR = "uploads/itr_documents"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_TYPES = {"AIS", "26AS", "Form 26AS", "Form 16", "Form16"}

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _get_file_path(firm_id: str, filename: str) -> str:
    """Generate safe file path for upload."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{timestamp}_{filename}"
    return os.path.join(UPLOAD_DIR, firm_id, safe_name)


def _save_file(firm_id: str, file: UploadFile) -> tuple[str, int]:
    """Save uploaded file to disk."""
    file_path = _get_file_path(firm_id, file.filename)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Check file size
    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {MAX_FILE_SIZE / (1024*1024):.0f}MB"
        )

    with open(file_path, "wb") as f:
        f.write(content)

    return file_path, len(content)


def _extract_text_from_file(file_path: str) -> str:
    """Extract text from PDF or text file."""
    # For MVP, support text files and simple extraction
    # Full PDF support would need PyPDF2 or pdfplumber
    try:
        if file_path.lower().endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif file_path.lower().endswith('.pdf'):
            # For MVP: return placeholder
            # TODO: Add PyPDF2 for PDF text extraction
            return "[PDF Content - Requires PyPDF2 for extraction]"
        elif file_path.lower().endswith(('.xlsx', '.xls')):
            # For MVP: return placeholder
            # TODO: Add openpyxl for Excel extraction
            return "[Excel Content - Requires openpyxl for extraction]"
        else:
            return ""
    except Exception as e:
        return f"[Extraction Error: {str(e)}]"


async def _process_document(
    db: AsyncSession,
    doc: ITRDocument,
    file_path: str
) -> None:
    """Process document: extract text and parse data."""
    try:
        # Extract text from file
        text_content = _extract_text_from_file(file_path)

        if not text_content or text_content.startswith("["):
            doc.extraction_status = "pending_manual"
            doc.extraction_errors = "File format requires manual review"
            return

        # Parse document
        parsed_data = DocumentParserFactory.parse(doc.document_type, text_content)

        doc.extracted_data = parsed_data
        doc.extraction_status = "completed"

        # Update PAN and AY if extracted
        if parsed_data.get("pan"):
            doc.pan = parsed_data["pan"]
        if parsed_data.get("assessment_year"):
            doc.assessment_year = parsed_data["assessment_year"]

    except Exception as e:
        doc.extraction_status = "failed"
        doc.extraction_errors = str(e)


@router.get("/status")
async def status(current_user: CurrentUser = Depends(get_current_user)):
    return {
        "status": "ok",
        "module": "itr_documents",
        "supported_types": list(ALLOWED_TYPES),
        "max_file_size_mb": MAX_FILE_SIZE / (1024 * 1024),
        "features": [
            "file_upload",
            "data_extraction",
            "ais_parsing",
            "form26as_parsing",
            "form16_parsing",
            "document_linking"
        ]
    }


@router.post("/upload")
async def upload_document(
    document_type: str = Form(...),
    itr_return_id: Optional[str] = Form(None),
    pan: Optional[str] = Form(None),
    assessment_year: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload ITR document (AIS, 26AS, or Form 16)."""

    # Validate document type
    if document_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document type. Supported: {', '.join(ALLOWED_TYPES)}"
        )

    # Save file
    try:
        file_path, file_size = _save_file(current_user.firm_id, file)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")

    # Create document record
    mime_type, _ = mimetypes.guess_type(file.filename)
    doc = ITRDocument(
        firm_id=current_user.firm_id,
        itr_return_id=itr_return_id,
        document_type=document_type,
        document_name=file.filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type or "application/octet-stream",
        pan=pan,
        assessment_year=assessment_year,
        extraction_status="processing",
        uploaded_by=current_user.id,
    )
    db.add(doc)
    await db.flush()

    # Process document (extract data)
    await _process_document(db, doc, file_path)

    await db.commit()
    await db.refresh(doc)

    return {
        "message": f"{document_type} document uploaded successfully",
        "document": DocumentResponse.model_validate(doc)
    }


@router.get("/list")
async def list_documents(
    document_type: Optional[str] = Query(None),
    pan: Optional[str] = Query(None),
    assessment_year: Optional[str] = Query(None),
    extraction_status: Optional[str] = Query(None),
    itr_return_id: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List uploaded documents."""

    query = select(ITRDocument).where(ITRDocument.firm_id == current_user.firm_id)

    if document_type:
        query = query.where(ITRDocument.document_type == document_type)
    if pan:
        query = query.where(ITRDocument.pan == pan.upper())
    if assessment_year:
        query = query.where(ITRDocument.assessment_year == assessment_year)
    if extraction_status:
        query = query.where(ITRDocument.extraction_status == extraction_status)
    if itr_return_id:
        query = query.where(ITRDocument.itr_return_id == itr_return_id)

    result = await db.execute(
        query.order_by(desc(ITRDocument.uploaded_at)).offset(skip).limit(limit)
    )
    documents = result.scalars().all()

    return DocumentListResponse(
        count=len(documents),
        documents=[DocumentResponse.model_validate(doc) for doc in documents]
    )


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get single document with extracted data."""

    result = await db.execute(
        select(ITRDocument).where(
            and_(
                ITRDocument.id == document_id,
                ITRDocument.firm_id == current_user.firm_id
            )
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse.model_validate(doc)


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete uploaded document."""

    result = await db.execute(
        select(ITRDocument).where(
            and_(
                ITRDocument.id == document_id,
                ITRDocument.firm_id == current_user.firm_id
            )
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            # Log but don't fail if file deletion fails
            pass

    await db.delete(doc)
    await db.commit()

    return {"message": "Document deleted successfully"}


@router.post("/{document_id}/extract-data")
async def reprocess_document(
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-process document to extract data."""

    result = await db.execute(
        select(ITRDocument).where(
            and_(
                ITRDocument.id == document_id,
                ITRDocument.firm_id == current_user.firm_id
            )
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=400, detail="Document file not found on disk")

    # Process document
    doc.extraction_status = "processing"
    await _process_document(db, doc, doc.file_path)
    await db.commit()

    return {
        "message": "Document re-processed",
        "document": DocumentResponse.model_validate(doc)
    }


@router.get("/download/{document_id}")
async def download_document(
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download uploaded document."""

    result = await db.execute(
        select(ITRDocument).where(
            and_(
                ITRDocument.id == document_id,
                ITRDocument.firm_id == current_user.firm_id
            )
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return {
        "download_path": doc.file_path,
        "filename": doc.document_name,
        "size": doc.file_size
    }


@router.get("/statistics")
async def document_statistics(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get document upload statistics."""

    # Total documents
    total_result = await db.execute(
        select(func.count(ITRDocument.id)).where(ITRDocument.firm_id == current_user.firm_id)
    )
    total_docs = total_result.scalar() or 0

    # By type
    by_type_result = await db.execute(
        select(
            ITRDocument.document_type,
            func.count(ITRDocument.id)
        ).where(
            ITRDocument.firm_id == current_user.firm_id
        ).group_by(ITRDocument.document_type)
    )
    by_type = {row[0]: row[1] for row in by_type_result.fetchall()}

    # By extraction status
    status_result = await db.execute(
        select(
            ITRDocument.extraction_status,
            func.count(ITRDocument.id)
        ).where(
            ITRDocument.firm_id == current_user.firm_id
        ).group_by(ITRDocument.extraction_status)
    )
    by_status = {row[0]: row[1] for row in status_result.fetchall()}

    # Total file size
    size_result = await db.execute(
        select(func.sum(ITRDocument.file_size)).where(ITRDocument.firm_id == current_user.firm_id)
    )
    total_size = size_result.scalar() or 0

    return DocumentStatistics(
        total_documents=total_docs,
        by_type=by_type,
        extraction_status=by_status,
        total_file_size_mb=total_size / (1024 * 1024)
    )


@router.post("/{document_id}/link-to-itr/{itr_id}")
async def link_document_to_itr(
    document_id: str,
    itr_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Link document to ITR return."""

    result = await db.execute(
        select(ITRDocument).where(
            and_(
                ITRDocument.id == document_id,
                ITRDocument.firm_id == current_user.firm_id
            )
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.itr_return_id = itr_id
    await db.commit()
    await db.refresh(doc)

    return {
        "message": "Document linked to ITR",
        "document": DocumentResponse.model_validate(doc)
    }
