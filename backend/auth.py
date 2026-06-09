```python
from datetime import datetime
from sqlalchemy import select

@auth_router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    user = await UserRepo.get_by_email(db, request.email)

    if (
        not user
        or not user.is_active
        or not verify_password(request.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    result = await db.execute(
        select(CAFirm).where(CAFirm.id == user.firm_id)
    )

    firm = result.scalar_one_or_none()

    if not firm:
        raise HTTPException(
            status_code=404,
            detail="Firm not found"
        )

    if not firm.is_active:
        raise HTTPException(
            status_code=403,
            detail="Firm account is inactive"
        )

    user.last_login = datetime.utcnow()

    await db.commit()
    await db.refresh(user)

    return _token_for(user, firm)
```
