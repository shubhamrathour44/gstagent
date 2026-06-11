from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/tax-audit", tags=["tax_audit"])

@router.get("/list")
async def list_tax_audits(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return {"reports": [], "count": 0}
