# Accounting Module - GSTAgent

Complete double-entry bookkeeping system with General Ledger, Trial Balance, P&L Statement, and Balance Sheet.

## Features

✅ **Chart of Accounts (COA)**
- Predefined account types: Asset, Liability, Equity, Revenue, Expense
- Flexible categorization and sub-categories
- Opening balance management
- Account code-based tracking
- Active/Inactive status management

✅ **Journal Entries**
- Double-entry bookkeeping validation
- Automatic debit-credit balancing
- Entry numbering (JE-000001, etc.)
- Draft and Posted status
- Line-level transaction details
- Reference tracking for audit trail

✅ **General Ledger**
- Account-wise transaction history
- Running balance calculation
- Date range filtering
- Posted transaction tracking
- Complete audit trail

✅ **Trial Balance**
- Automatic generation from GL data
- Debit and credit totals
- Opening and closing balances
- Balance verification (Assets = Liabilities + Equity)
- Point-in-time reporting

✅ **Financial Statements**
- **Profit & Loss Statement (Income Statement)**
  - Revenue summary
  - Expense breakdown
  - Profit before tax
  - Net profit calculation

- **Balance Sheet**
  - Assets section
  - Liabilities section
  - Equity section
  - Balance verification (Assets = Liabilities + Equity)

✅ **Reporting & Analytics**
- Account balance inquiry
- GL account analysis
- Financial statement generation
- Monthly/quarterly/annual reporting

---

## Core Concepts

### Double Entry Bookkeeping

Every transaction affects two accounts:
- **Debit**: Left side (increases assets/expenses, decreases liabilities/revenue)
- **Credit**: Right side (increases liabilities/revenue, decreases assets/expenses)

**Golden Rule**: Debit Total = Credit Total (Always!)

### Account Types

| Type | Nature | Debit | Credit |
|------|--------|-------|--------|
| **Asset** | Increase | ✅ | - |
| **Liability** | Increase | - | ✅ |
| **Equity** | Increase | - | ✅ |
| **Revenue** | Increase | - | ✅ |
| **Expense** | Increase | ✅ | - |

### Account Balance Calculation

```
Closing Balance = Opening Balance + Debits - Credits (for Asset/Expense accounts)
Closing Balance = Opening Balance + Credits - Debits (for Liability/Revenue/Equity accounts)
```

---

## API Endpoints

### Chart of Accounts Management

#### Create Account
```bash
POST /accounting/chart-of-accounts
Content-Type: application/json

{
  "account_code": "1000",
  "account_name": "Cash in Hand",
  "account_type": "Asset",
  "category": "Current Assets",
  "sub_category": "Cash & Bank",
  "description": "Cash kept in office",
  "opening_balance": 50000.00,
  "opening_balance_type": "debit"
}
```

**Account Types**: Asset, Liability, Equity, Revenue, Expense

#### List Accounts
```bash
GET /accounting/chart-of-accounts?account_type=Asset&is_active=true&skip=0&limit=100
```

#### Get Account Details
```bash
GET /accounting/chart-of-accounts/{account_id}
```

#### Update Account
```bash
PATCH /accounting/chart-of-accounts/{account_id}
{
  "account_name": "Cash in Hand (Updated)",
  "is_active": true
}
```

---

### Journal Entry Management

#### Create Journal Entry
```bash
POST /accounting/journal-entries
Content-Type: application/json

{
  "entry_date": "2026-01-15T00:00:00",
  "description": "Purchase office supplies",
  "reference": "INV-001",
  "lines": [
    {
      "account_id": "acc-uuid-1",
      "debit": 5000.00,
      "credit": 0.00,
      "description": "Office supplies expense"
    },
    {
      "account_id": "acc-uuid-2",
      "debit": 0.00,
      "credit": 5000.00,
      "description": "Cash payment"
    }
  ]
}
```

**Validation**: Total Debits MUST equal Total Credits

#### List Journal Entries
```bash
GET /accounting/journal-entries?is_posted=false&skip=0&limit=50
```

#### Post Journal Entry
```bash
POST /accounting/journal-entries/{entry_id}/post
```

Once posted, the entry is transferred to General Ledger.

---

### General Ledger Queries

#### Get Account Ledger
```bash
GET /accounting/general-ledger/{account_id}?from_date=2026-01-01&to_date=2026-01-31
```

Returns:
- Account details
- Transaction history
- Running balance
- Date-wise breakdown

**Response:**
```json
{
  "account_code": "1000",
  "account_name": "Cash in Hand",
  "account_type": "Asset",
  "opening_balance": 50000.00,
  "total_debit": 25000.00,
  "total_credit": 10000.00,
  "closing_balance": 65000.00,
  "transactions": [
    {
      "transaction_date": "2026-01-15T00:00:00",
      "description": "Purchase office supplies",
      "debit": 5000.00,
      "credit": 0.00,
      "running_balance": 60000.00
    }
  ]
}
```

---

### Financial Reports

#### Trial Balance
```bash
GET /accounting/trial-balance?as_on_date=2026-01-31
```

**Response:**
```json
{
  "as_on_date": "2026-01-31T00:00:00",
  "total_opening_debit": 100000.00,
  "total_opening_credit": 100000.00,
  "total_debit": 50000.00,
  "total_credit": 50000.00,
  "total_closing_debit": 150000.00,
  "total_closing_credit": 150000.00,
  "is_balanced": true,
  "accounts": [
    {
      "account_code": "1000",
      "account_name": "Cash in Hand",
      "account_type": "Asset",
      "opening_balance": 50000.00,
      "total_debit": 25000.00,
      "total_credit": 10000.00,
      "closing_balance": 65000.00,
      "closing_balance_type": "debit"
    }
  ]
}
```

#### Income Statement (P&L)
```bash
GET /accounting/income-statement?as_on_date=2026-01-31&period=Month
```

**Response:**
```json
{
  "statement_period": "Month",
  "as_on_date": "2026-01-31T00:00:00",
  "revenue": [
    {
      "line_type": "revenue",
      "account_code": "4000",
      "account_name": "Service Revenue",
      "amount": 100000.00
    }
  ],
  "total_revenue": 100000.00,
  "expenses": [
    {
      "line_type": "expense",
      "account_code": "5100",
      "account_name": "Salary Expense",
      "amount": 50000.00
    }
  ],
  "total_expenses": 50000.00,
  "profit_before_tax": 50000.00,
  "tax": 5000.00,
  "profit_after_tax": 45000.00
}
```

#### Balance Sheet
```bash
GET /accounting/balance-sheet?as_on_date=2026-01-31&period=Month
```

**Response:**
```json
{
  "as_on_date": "2026-01-31T00:00:00",
  "statement_period": "Month",
  "assets": [
    {
      "line_type": "asset",
      "account_code": "1000",
      "account_name": "Cash in Hand",
      "amount": 65000.00
    }
  ],
  "total_assets": 150000.00,
  "liabilities": [
    {
      "line_type": "liability",
      "account_code": "2100",
      "account_name": "Accounts Payable",
      "amount": 25000.00
    }
  ],
  "total_liabilities": 25000.00,
  "equity": [
    {
      "line_type": "equity",
      "account_code": "3000",
      "account_name": "Capital",
      "amount": 125000.00
    }
  ],
  "total_equity": 125000.00,
  "is_balanced": true
}
```

#### Account Balance
```bash
GET /accounting/account-balance/{account_id}?as_on_date=2026-01-31
```

---

## Database Schema

### chart_of_accounts
```
id (UUID)
firm_id → ca_firms
account_code (unique)
account_name, account_type, category, sub_category
description
is_active, opening_balance, opening_balance_type
created_by, created_at, updated_at
```

### journal_entries
```
id (UUID)
firm_id
entry_number (unique, auto-generated)
entry_date, description, reference
total_debit, total_credit
is_posted, is_reversed
created_by, created_at, updated_at
```

### journal_entry_lines
```
id (UUID)
firm_id, journal_entry_id, account_id
account_code, account_name
debit, credit, description, line_number
created_at
```

### general_ledger
```
id (UUID)
firm_id, account_id, journal_entry_id
account_code, account_name
transaction_date, description, reference
debit, credit
running_balance, balance_type
posted_at
```

### trial_balance
```
id (UUID)
firm_id, account_id
account_code, account_name, account_type
opening_balance, opening_balance_type
total_debit, total_credit
closing_balance, closing_balance_type
as_on_date, created_at
```

### financial_statements
```
id (UUID)
firm_id
statement_type (Income Statement, Balance Sheet)
statement_period
as_on_date
data (JSON)
created_by, created_at
```

---

## Workflow Example

### January 2026 Accounting Cycle

**Step 1: Create Chart of Accounts**
```bash
POST /accounting/chart-of-accounts
→ 1000: Cash in Hand (Asset)
→ 4000: Service Revenue (Revenue)
→ 5100: Salary Expense (Expense)
```

**Step 2: Record Transactions as Journal Entries**

*Jan 15: Received payment for services*
```bash
POST /accounting/journal-entries
→ Debit 1000 (Cash): 100,000
→ Credit 4000 (Revenue): 100,000
```

*Jan 20: Paid salary*
```bash
POST /accounting/journal-entries
→ Debit 5100 (Salary): 50,000
→ Credit 1000 (Cash): 50,000
```

**Step 3: Post Journal Entries**
```bash
POST /accounting/journal-entries/{entry_id}/post
```

**Step 4: View General Ledger**
```bash
GET /accounting/general-ledger/1000
→ Shows all cash transactions
```

**Step 5: Generate Trial Balance**
```bash
GET /accounting/trial-balance?as_on_date=2026-01-31
→ Verifies accounts are balanced
```

**Step 6: Generate Financial Statements**

*P&L Statement:*
```bash
GET /accounting/income-statement?as_on_date=2026-01-31
→ Revenue: 100,000
→ Expenses: 50,000
→ Profit: 50,000
```

*Balance Sheet:*
```bash
GET /accounting/balance-sheet?as_on_date=2026-01-31
→ Assets: 150,000
→ Liabilities: 25,000
→ Equity: 125,000
→ Balanced? YES ✓
```

---

## Validation Rules

✅ **Entry Balance**: Debit Total MUST equal Credit Total
✅ **Minimum Lines**: Each entry must have at least 2 lines
✅ **Account Validation**: All referenced accounts must exist and belong to the firm
✅ **Date Validation**: Entry date cannot be in the future
✅ **Posted Status**: Posted entries cannot be modified

---

## Account Classification

### Assets (Debit Balance)
- Current Assets: Cash, Accounts Receivable, Inventory
- Fixed Assets: Equipment, Buildings, Furniture
- Investments: Stocks, Bonds

### Liabilities (Credit Balance)
- Current Liabilities: Accounts Payable, Short-term Loans
- Long-term Liabilities: Long-term Loans, Bonds Payable

### Equity (Credit Balance)
- Capital/Owner's Equity
- Retained Earnings
- Profit/Loss for the Period

### Revenue (Credit Balance)
- Service Revenue
- Sales Revenue
- Interest Income
- Other Income

### Expenses (Debit Balance)
- Salary Expense
- Rent Expense
- Utilities Expense
- Office Supplies
- Depreciation Expense
- Other Expenses

---

## Financial Statement Formulas

### Profit & Loss Statement
```
Total Revenue
- Total Expenses
= Profit Before Tax
- Income Tax
= Net Profit (Loss)
```

### Balance Sheet
```
Assets = Liabilities + Equity

Where:
Assets = Current Assets + Fixed Assets + Investments
Liabilities = Current Liabilities + Long-term Liabilities
Equity = Capital + Retained Earnings + Current Period Profit
```

### Account Balance
```
Closing Balance = Opening Balance + Transactions

For Asset/Expense Accounts:
Closing = Opening + Debits - Credits

For Liability/Revenue/Equity Accounts:
Closing = Opening + Credits - Debits
```

---

## Compliance & Audit

✅ **Audit Trail**
- All entries tracked with created_by and timestamps
- Posted entries are immutable
- Reversal option available instead of deletion

✅ **Data Integrity**
- Double-entry validation enforced
- Balance sheet equation verification
- GL integrity checks

✅ **Reporting**
- Standard financial statements
- Trial balance verification
- Period-wise reporting

---

## Future Enhancements

- [ ] Bank reconciliation
- [ ] Currency support (multi-currency)
- [ ] Cost allocation
- [ ] Budget vs Actual analysis
- [ ] Recurring entries automation
- [ ] Depreciation calculation
- [ ] Consolidation reports
- [ ] Compliance reports (IFRS, Indian GAAP)
- [ ] Audit trail detailed view
- [ ] Financial ratio analysis

---

## Status

✅ Production Ready for MVP
- Core accounting complete
- Financial statements working
- GL and TB generation functional
- Entry validation implemented

