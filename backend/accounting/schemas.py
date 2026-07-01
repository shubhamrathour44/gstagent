from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ChartOfAccountsCreate(BaseModel):
    account_code: str = Field(..., description="Unique account code (e.g., 1000)")
    account_name: str
    account_type: str = Field(..., description="Asset, Liability, Equity, Revenue, Expense")
    category: str
    sub_category: Optional[str] = None
    description: Optional[str] = None
    opening_balance: float = 0.0
    opening_balance_type: str = "debit"


class ChartOfAccountsUpdate(BaseModel):
    account_name: Optional[str] = None
    account_type: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ChartOfAccountsResponse(BaseModel):
    id: str
    account_code: str
    account_name: str
    account_type: str
    category: str
    sub_category: Optional[str]
    description: Optional[str]
    opening_balance: float
    opening_balance_type: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class JournalEntryLineCreate(BaseModel):
    account_id: str
    debit: float = 0.0
    credit: float = 0.0
    description: Optional[str] = None


class JournalEntryCreate(BaseModel):
    entry_date: datetime
    description: str
    reference: Optional[str] = None
    lines: List[JournalEntryLineCreate]


class JournalEntryLineResponse(BaseModel):
    id: str
    account_code: str
    account_name: str
    debit: float
    credit: float
    description: Optional[str]

    class Config:
        from_attributes = True


class JournalEntryResponse(BaseModel):
    id: str
    entry_number: str
    entry_date: datetime
    description: str
    reference: Optional[str]
    total_debit: float
    total_credit: float
    is_posted: bool
    lines: List[JournalEntryLineResponse]
    created_at: datetime

    class Config:
        from_attributes = True


class GeneralLedgerLineResponse(BaseModel):
    id: str
    transaction_date: datetime
    description: str
    reference: Optional[str]
    debit: float
    credit: float
    running_balance: float
    balance_type: str

    class Config:
        from_attributes = True


class GeneralLedgerResponse(BaseModel):
    account_code: str
    account_name: str
    account_type: str
    opening_balance: float
    total_debit: float
    total_credit: float
    closing_balance: float
    transactions: List[GeneralLedgerLineResponse]


class TrialBalanceLineResponse(BaseModel):
    account_code: str
    account_name: str
    account_type: str
    opening_balance: float
    opening_balance_type: str
    total_debit: float
    total_credit: float
    closing_balance: float
    closing_balance_type: str


class TrialBalanceResponse(BaseModel):
    as_on_date: datetime
    total_opening_debit: float
    total_opening_credit: float
    total_debit: float
    total_credit: float
    total_closing_debit: float
    total_closing_credit: float
    accounts: List[TrialBalanceLineResponse]
    is_balanced: bool


class IncomeStatementLineResponse(BaseModel):
    line_type: str
    account_code: str
    account_name: str
    amount: float


class IncomeStatementResponse(BaseModel):
    statement_period: str
    as_on_date: datetime

    revenue: List[IncomeStatementLineResponse]
    total_revenue: float

    expenses: List[IncomeStatementLineResponse]
    total_expenses: float

    profit_before_tax: float
    tax: float
    profit_after_tax: float


class BalanceSheetLineResponse(BaseModel):
    line_type: str
    account_code: str
    account_name: str
    amount: float


class BalanceSheetResponse(BaseModel):
    as_on_date: datetime
    statement_period: str

    assets: List[BalanceSheetLineResponse]
    total_assets: float

    liabilities: List[BalanceSheetLineResponse]
    total_liabilities: float

    equity: List[BalanceSheetLineResponse]
    total_equity: float

    is_balanced: bool


class AccountBalanceResponse(BaseModel):
    account_code: str
    account_name: str
    account_type: str
    opening_balance: float
    total_debit: float
    total_credit: float
    closing_balance: float
    balance_type: str


class AccountingStatusResponse(BaseModel):
    status: str
    total_accounts: int
    active_accounts: int
    total_journal_entries: int
    posted_entries: int
    unposted_entries: int
