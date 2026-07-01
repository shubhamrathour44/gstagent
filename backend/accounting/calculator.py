"""Accounting calculation logic - Double entry bookkeeping, GL, P&L, and BS."""

from datetime import datetime
from typing import Tuple, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from database import ChartOfAccounts, JournalEntry, JournalEntryLine, GeneralLedger, TrialBalance


class DoubleEntryValidator:
    """Validates double-entry bookkeeping principles."""

    @staticmethod
    def validate_entry(total_debit: float, total_credit: float, tolerance: float = 0.01) -> Tuple[bool, str]:
        """Verify that debits equal credits."""
        if abs(total_debit - total_credit) > tolerance:
            return False, f"Entry not balanced: Debit {total_debit} != Credit {total_credit}"
        return True, "Entry is balanced"


class GLCalculator:
    """Calculates general ledger balances and account positions."""

    @staticmethod
    async def get_account_balance(
        db: AsyncSession, account_id: str, as_on_date: Optional[datetime] = None
    ) -> Tuple[float, float, float]:
        """
        Get account balance (opening + debit - credit).
        Returns: (opening_balance, total_debit, total_credit)
        """
        account_result = await db.execute(
            select(ChartOfAccounts).where(ChartOfAccounts.id == account_id)
        )
        account = account_result.scalar_one_or_none()
        if not account:
            return 0.0, 0.0, 0.0

        query = select(GeneralLedger).where(GeneralLedger.account_id == account_id)
        if as_on_date:
            query = query.where(GeneralLedger.posted_at <= as_on_date)

        result = await db.execute(query)
        transactions = result.scalars().all()

        opening_balance = account.opening_balance
        total_debit = sum(t.debit for t in transactions)
        total_credit = sum(t.credit for t in transactions)

        return opening_balance, total_debit, total_credit

    @staticmethod
    def calculate_closing_balance(
        opening_balance: float, opening_type: str, total_debit: float, total_credit: float
    ) -> Tuple[float, str]:
        """
        Calculate closing balance based on opening balance and debits/credits.
        Returns: (closing_balance, balance_type)
        """
        if opening_type == "debit":
            net = opening_balance + total_debit - total_credit
        else:
            net = opening_balance + total_credit - total_debit

        balance = abs(net)
        balance_type = "debit" if net >= 0 else "credit"

        return balance, balance_type


class TrialBalanceCalculator:
    """Generates trial balance from GL data."""

    @staticmethod
    async def generate_trial_balance(
        db: AsyncSession, firm_id: str, as_on_date: datetime
    ) -> Dict:
        """Generate trial balance as on a specific date."""
        accounts_result = await db.execute(
            select(ChartOfAccounts).where(
                and_(ChartOfAccounts.firm_id == firm_id, ChartOfAccounts.is_active == True)
            )
        )
        accounts = accounts_result.scalars().all()

        total_opening_debit = 0.0
        total_opening_credit = 0.0
        total_debit = 0.0
        total_credit = 0.0
        total_closing_debit = 0.0
        total_closing_credit = 0.0

        trial_balance_lines = []

        for account in accounts:
            opening_bal = account.opening_balance
            opening_type = account.opening_balance_type

            gl_result = await db.execute(
                select(GeneralLedger).where(
                    and_(
                        GeneralLedger.account_id == account.id,
                        GeneralLedger.posted_at <= as_on_date,
                    )
                )
            )
            transactions = gl_result.scalars().all()

            acc_debit = sum(t.debit for t in transactions)
            acc_credit = sum(t.credit for t in transactions)

            closing_bal, closing_type = GLCalculator.calculate_closing_balance(
                opening_bal, opening_type, acc_debit, acc_credit
            )

            if opening_type == "debit":
                total_opening_debit += opening_bal
            else:
                total_opening_credit += opening_bal

            total_debit += acc_debit
            total_credit += acc_credit

            if closing_type == "debit":
                total_closing_debit += closing_bal
            else:
                total_closing_credit += closing_bal

            if closing_bal > 0:
                trial_balance_lines.append(
                    {
                        "account_code": account.account_code,
                        "account_name": account.account_name,
                        "account_type": account.account_type,
                        "opening_balance": opening_bal,
                        "opening_balance_type": opening_type,
                        "total_debit": acc_debit,
                        "total_credit": acc_credit,
                        "closing_balance": closing_bal,
                        "closing_balance_type": closing_type,
                    }
                )

        is_balanced = abs(total_closing_debit - total_closing_credit) < 0.01

        return {
            "as_on_date": as_on_date,
            "total_opening_debit": round(total_opening_debit, 2),
            "total_opening_credit": round(total_opening_credit, 2),
            "total_debit": round(total_debit, 2),
            "total_credit": round(total_credit, 2),
            "total_closing_debit": round(total_closing_debit, 2),
            "total_closing_credit": round(total_closing_credit, 2),
            "is_balanced": is_balanced,
            "accounts": trial_balance_lines,
        }


class IncomeStatementCalculator:
    """Generates P&L statement from trial balance."""

    @staticmethod
    async def generate_income_statement(
        db: AsyncSession, firm_id: str, as_on_date: datetime, period: str = "Month"
    ) -> Dict:
        """Generate P&L statement (Income Statement)."""
        trial_balance = await TrialBalanceCalculator.generate_trial_balance(db, firm_id, as_on_date)

        revenue_lines = []
        expense_lines = []
        total_revenue = 0.0
        total_expenses = 0.0

        for account in trial_balance["accounts"]:
            if account["account_type"] in ["Revenue", "Income"]:
                amount = account["closing_balance"]
                total_revenue += amount
                revenue_lines.append(
                    {
                        "line_type": "revenue",
                        "account_code": account["account_code"],
                        "account_name": account["account_name"],
                        "amount": round(amount, 2),
                    }
                )
            elif account["account_type"] == "Expense":
                amount = account["closing_balance"]
                total_expenses += amount
                expense_lines.append(
                    {
                        "line_type": "expense",
                        "account_code": account["account_code"],
                        "account_name": account["account_name"],
                        "amount": round(amount, 2),
                    }
                )

        profit_before_tax = total_revenue - total_expenses
        tax = 0.0
        profit_after_tax = profit_before_tax - tax

        return {
            "statement_period": period,
            "as_on_date": as_on_date,
            "revenue": revenue_lines,
            "total_revenue": round(total_revenue, 2),
            "expenses": expense_lines,
            "total_expenses": round(total_expenses, 2),
            "profit_before_tax": round(profit_before_tax, 2),
            "tax": round(tax, 2),
            "profit_after_tax": round(profit_after_tax, 2),
        }


class BalanceSheetCalculator:
    """Generates balance sheet from trial balance."""

    @staticmethod
    async def generate_balance_sheet(
        db: AsyncSession, firm_id: str, as_on_date: datetime, period: str = "Month"
    ) -> Dict:
        """Generate Balance Sheet."""
        trial_balance = await TrialBalanceCalculator.generate_trial_balance(db, firm_id, as_on_date)

        asset_lines = []
        liability_lines = []
        equity_lines = []
        total_assets = 0.0
        total_liabilities = 0.0
        total_equity = 0.0

        for account in trial_balance["accounts"]:
            if account["account_type"] == "Asset":
                amount = account["closing_balance"]
                total_assets += amount
                asset_lines.append(
                    {
                        "line_type": "asset",
                        "account_code": account["account_code"],
                        "account_name": account["account_name"],
                        "amount": round(amount, 2),
                    }
                )
            elif account["account_type"] == "Liability":
                amount = account["closing_balance"]
                total_liabilities += amount
                liability_lines.append(
                    {
                        "line_type": "liability",
                        "account_code": account["account_code"],
                        "account_name": account["account_name"],
                        "amount": round(amount, 2),
                    }
                )
            elif account["account_type"] == "Equity":
                amount = account["closing_balance"]
                total_equity += amount
                equity_lines.append(
                    {
                        "line_type": "equity",
                        "account_code": account["account_code"],
                        "account_name": account["account_name"],
                        "amount": round(amount, 2),
                    }
                )

        is_balanced = abs(total_assets - (total_liabilities + total_equity)) < 0.01

        return {
            "as_on_date": as_on_date,
            "statement_period": period,
            "assets": asset_lines,
            "total_assets": round(total_assets, 2),
            "liabilities": liability_lines,
            "total_liabilities": round(total_liabilities, 2),
            "equity": equity_lines,
            "total_equity": round(total_equity, 2),
            "is_balanced": is_balanced,
        }


class JournalEntryProcessor:
    """Processes and posts journal entries to GL."""

    @staticmethod
    def generate_entry_number(sequence: int) -> str:
        """Generate unique entry number."""
        return f"JE-{sequence:06d}"

    @staticmethod
    async def post_journal_entry(
        db: AsyncSession, journal_entry: JournalEntry, lines: List[JournalEntryLine], firm_id: str
    ) -> bool:
        """Post a journal entry to general ledger."""
        if journal_entry.is_posted:
            return True

        for line in lines:
            account = await db.execute(
                select(ChartOfAccounts).where(ChartOfAccounts.id == line.account_id)
            )
            acc = account.scalar_one_or_none()
            if not acc:
                continue

            gl_entry = GeneralLedger(
                firm_id=firm_id,
                account_id=line.account_id,
                journal_entry_id=journal_entry.id,
                account_code=acc.account_code,
                account_name=acc.account_name,
                transaction_date=journal_entry.entry_date,
                description=journal_entry.description,
                reference=journal_entry.reference,
                debit=line.debit,
                credit=line.credit,
                running_balance=0.0,
                balance_type="debit",
            )
            db.add(gl_entry)

        journal_entry.is_posted = True
        await db.flush()
        return True
