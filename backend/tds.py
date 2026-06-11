from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/tds", tags=["tds"])

@router.get("/list")
async def list_tds_returns(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return {"returns": [], "count": 0}
