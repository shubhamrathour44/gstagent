from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from auth import CurrentUser, get_current_user
from database import (
    get_db,
    ChartOfAccounts,
    JournalEntry,
    JournalEntryLine,
    GeneralLedger,
    TrialBalance,
    FinancialStatement,
)
from .schemas import (
    ChartOfAccountsCreate,
    ChartOfAccountsUpdate,
    ChartOfAccountsResponse,
    JournalEntryCreate,
    JournalEntryResponse,
    GeneralLedgerResponse,
    TrialBalanceResponse,
    IncomeStatementResponse,
    BalanceSheetResponse,
    AccountBalanceResponse,
    AccountingStatusResponse,
)
from .calculator import (
    DoubleEntryValidator,
    GLCalculator,
    TrialBalanceCalculator,
    IncomeStatementCalculator,
    BalanceSheetCalculator,
    JournalEntryProcessor,
)

accounting_router = APIRouter(prefix="/accounting", tags=["Accounting"])


@accounting_router.get("/status")
async def accounting_status(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    coa_result = await db.execute(
        select(func.count(ChartOfAccounts.id)).where(
            and_(ChartOfAccounts.firm_id == current_user.firm_id, ChartOfAccounts.is_active == True)
        )
    )
    active_accounts = coa_result.scalar() or 0

    total_coa_result = await db.execute(
        select(func.count(ChartOfAccounts.id)).where(ChartOfAccounts.firm_id == current_user.firm_id)
    )
    total_accounts = total_coa_result.scalar() or 0

    je_result = await db.execute(
        select(func.count(JournalEntry.id)).where(JournalEntry.firm_id == current_user.firm_id)
    )
    total_entries = je_result.scalar() or 0

    posted_result = await db.execute(
        select(func.count(JournalEntry.id)).where(
            and_(JournalEntry.firm_id == current_user.firm_id, JournalEntry.is_posted == True)
        )
    )
    posted_entries = posted_result.scalar() or 0

    return AccountingStatusResponse(
        status="ok",
        total_accounts=total_accounts,
        active_accounts=active_accounts,
        total_journal_entries=total_entries,
        posted_entries=posted_entries,
        unposted_entries=total_entries - posted_entries,
    )


@accounting_router.post("/chart-of-accounts")
async def create_account(
    account: ChartOfAccountsCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(ChartOfAccounts).where(
            and_(
                ChartOfAccounts.firm_id == current_user.firm_id,
                ChartOfAccounts.account_code == account.account_code,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Account code already exists")

    coa = ChartOfAccounts(
        firm_id=current_user.firm_id,
        created_by=current_user.id,
        **account.model_dump(),
    )
    db.add(coa)
    await db.flush()
    return ChartOfAccountsResponse.model_validate(coa)


@accounting_router.get("/chart-of-accounts")
async def list_accounts(
    account_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0),
    limit: int = Query(100),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(ChartOfAccounts).where(ChartOfAccounts.firm_id == current_user.firm_id)

    if account_type:
        query = query.where(ChartOfAccounts.account_type == account_type)
    if category:
        query = query.where(ChartOfAccounts.category == category)
    if is_active is not None:
        query = query.where(ChartOfAccounts.is_active == is_active)

    result = await db.execute(
        query.order_by(ChartOfAccounts.account_code).offset(skip).limit(limit)
    )
    accounts = result.scalars().all()

    return {
        "count": len(accounts),
        "accounts": [ChartOfAccountsResponse.model_validate(a) for a in accounts],
    }


@accounting_router.get("/chart-of-accounts/{account_id}")
async def get_account(
    account_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChartOfAccounts).where(
            and_(ChartOfAccounts.id == account_id, ChartOfAccounts.firm_id == current_user.firm_id)
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return ChartOfAccountsResponse.model_validate(account)


@accounting_router.patch("/chart-of-accounts/{account_id}")
async def update_account(
    account_id: str,
    update_data: ChartOfAccountsUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChartOfAccounts).where(
            and_(ChartOfAccounts.id == account_id, ChartOfAccounts.firm_id == current_user.firm_id)
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(account, key, value)

    await db.flush()
    return ChartOfAccountsResponse.model_validate(account)


@accounting_router.post("/journal-entries")
async def create_journal_entry(
    entry: JournalEntryCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if len(entry.lines) < 2:
        raise HTTPException(status_code=400, detail="Journal entry must have at least 2 lines")

    total_debit = sum(line.debit for line in entry.lines)
    total_credit = sum(line.credit for line in entry.lines)

    is_balanced, message = DoubleEntryValidator.validate_entry(total_debit, total_credit)
    if not is_balanced:
        raise HTTPException(status_code=400, detail=message)

    seq_result = await db.execute(
        select(func.count(JournalEntry.id)).where(JournalEntry.firm_id == current_user.firm_id)
    )
    seq = (seq_result.scalar() or 0) + 1
    entry_number = JournalEntryProcessor.generate_entry_number(seq)

    je = JournalEntry(
        firm_id=current_user.firm_id,
        entry_number=entry_number,
        entry_date=entry.entry_date,
        description=entry.description,
        reference=entry.reference,
        total_debit=total_debit,
        total_credit=total_credit,
        is_posted=False,
        created_by=current_user.id,
    )
    db.add(je)
    await db.flush()

    for idx, line in enumerate(entry.lines):
        account_result = await db.execute(
            select(ChartOfAccounts).where(
                and_(ChartOfAccounts.id == line.account_id, ChartOfAccounts.firm_id == current_user.firm_id)
            )
        )
        account = account_result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=404, detail=f"Account not found for line {idx + 1}")

        jel = JournalEntryLine(
            firm_id=current_user.firm_id,
            journal_entry_id=je.id,
            account_id=line.account_id,
            account_code=account.account_code,
            account_name=account.account_name,
            debit=line.debit,
            credit=line.credit,
            description=line.description,
            line_number=idx + 1,
        )
        db.add(jel)

    await db.flush()

    result = await db.execute(
        select(JournalEntry).where(JournalEntry.id == je.id)
    )
    je_fresh = result.scalar_one_or_none()

    lines_result = await db.execute(
        select(JournalEntryLine).where(JournalEntryLine.journal_entry_id == je.id)
    )
    lines = lines_result.scalars().all()

    return JournalEntryResponse(
        id=je_fresh.id,
        entry_number=je_fresh.entry_number,
        entry_date=je_fresh.entry_date,
        description=je_fresh.description,
        reference=je_fresh.reference,
        total_debit=je_fresh.total_debit,
        total_credit=je_fresh.total_credit,
        is_posted=je_fresh.is_posted,
        lines=[
            {
                "id": line.id,
                "account_code": line.account_code,
                "account_name": line.account_name,
                "debit": line.debit,
                "credit": line.credit,
                "description": line.description,
            }
            for line in lines
        ],
        created_at=je_fresh.created_at,
    )


@accounting_router.get("/journal-entries")
async def list_journal_entries(
    is_posted: Optional[bool] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(JournalEntry).where(JournalEntry.firm_id == current_user.firm_id)

    if is_posted is not None:
        query = query.where(JournalEntry.is_posted == is_posted)

    result = await db.execute(query.order_by(desc(JournalEntry.entry_date)).offset(skip).limit(limit))
    entries = result.scalars().all()

    return {
        "count": len(entries),
        "entries": [
            {
                "id": e.id,
                "entry_number": e.entry_number,
                "entry_date": e.entry_date,
                "description": e.description,
                "total_debit": e.total_debit,
                "total_credit": e.total_credit,
                "is_posted": e.is_posted,
                "created_at": e.created_at,
            }
            for e in entries
        ],
    }


@accounting_router.post("/journal-entries/{entry_id}/post")
async def post_journal_entry(
    entry_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(JournalEntry).where(
            and_(JournalEntry.id == entry_id, JournalEntry.firm_id == current_user.firm_id)
        )
    )
    je = result.scalar_one_or_none()
    if not je:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if je.is_posted:
        raise HTTPException(status_code=400, detail="Entry is already posted")

    lines_result = await db.execute(
        select(JournalEntryLine).where(JournalEntryLine.journal_entry_id == entry_id)
    )
    lines = lines_result.scalars().all()

    await JournalEntryProcessor.post_journal_entry(db, je, lines, current_user.firm_id)

    return {"status": "posted", "entry_number": je.entry_number}


@accounting_router.get("/general-ledger/{account_id}")
async def get_general_ledger(
    account_id: str,
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account_result = await db.execute(
        select(ChartOfAccounts).where(
            and_(ChartOfAccounts.id == account_id, ChartOfAccounts.firm_id == current_user.firm_id)
        )
    )
    account = account_result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    query = select(GeneralLedger).where(
        and_(GeneralLedger.account_id == account_id, GeneralLedger.firm_id == current_user.firm_id)
    )

    if from_date:
        query = query.where(GeneralLedger.transaction_date >= from_date)
    if to_date:
        query = query.where(GeneralLedger.transaction_date <= to_date)

    result = await db.execute(query.order_by(GeneralLedger.transaction_date))
    transactions = result.scalars().all()

    opening_bal, total_debit, total_credit = await GLCalculator.get_account_balance(
        db, account_id, to_date or datetime.now()
    )

    return GeneralLedgerResponse(
        account_code=account.account_code,
        account_name=account.account_name,
        account_type=account.account_type,
        opening_balance=opening_bal,
        total_debit=total_debit,
        total_credit=total_credit,
        closing_balance=opening_bal + total_debit - total_credit if account.opening_balance_type == "debit" else opening_bal + total_credit - total_debit,
        transactions=[
            {
                "id": t.id,
                "transaction_date": t.transaction_date,
                "description": t.description,
                "reference": t.reference,
                "debit": t.debit,
                "credit": t.credit,
                "running_balance": t.running_balance,
                "balance_type": t.balance_type,
            }
            for t in transactions
        ],
    )


@accounting_router.get("/trial-balance")
async def get_trial_balance(
    as_on_date: Optional[datetime] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not as_on_date:
        as_on_date = datetime.now()

    trial_balance = await TrialBalanceCalculator.generate_trial_balance(db, current_user.firm_id, as_on_date)

    return TrialBalanceResponse(**trial_balance)


@accounting_router.get("/income-statement")
async def get_income_statement(
    as_on_date: Optional[datetime] = Query(None),
    period: str = Query("Month"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not as_on_date:
        as_on_date = datetime.now()

    income_statement = await IncomeStatementCalculator.generate_income_statement(
        db, current_user.firm_id, as_on_date, period
    )

    return IncomeStatementResponse(**income_statement)


@accounting_router.get("/balance-sheet")
async def get_balance_sheet(
    as_on_date: Optional[datetime] = Query(None),
    period: str = Query("Month"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not as_on_date:
        as_on_date = datetime.now()

    balance_sheet = await BalanceSheetCalculator.generate_balance_sheet(
        db, current_user.firm_id, as_on_date, period
    )

    return BalanceSheetResponse(**balance_sheet)


@accounting_router.get("/account-balance/{account_id}")
async def get_account_balance(
    account_id: str,
    as_on_date: Optional[datetime] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account_result = await db.execute(
        select(ChartOfAccounts).where(
            and_(ChartOfAccounts.id == account_id, ChartOfAccounts.firm_id == current_user.firm_id)
        )
    )
    account = account_result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    opening_bal, total_debit, total_credit = await GLCalculator.get_account_balance(
        db, account_id, as_on_date or datetime.now()
    )

    closing_bal, closing_type = GLCalculator.calculate_closing_balance(
        opening_bal, account.opening_balance_type, total_debit, total_credit
    )

    return AccountBalanceResponse(
        account_code=account.account_code,
        account_name=account.account_name,
        account_type=account.account_type,
        opening_balance=opening_bal,
        total_debit=total_debit,
        total_credit=total_credit,
        closing_balance=closing_bal,
        balance_type=closing_type,
    )
