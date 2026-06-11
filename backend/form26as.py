from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/form26as", tags=["form26as"])

@router.get("/mismatches")
async def get_mismatches(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return {"mismatches": [], "count": 0}
