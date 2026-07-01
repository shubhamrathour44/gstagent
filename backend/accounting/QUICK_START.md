# Accounting Module - Quick Start Guide

## 10-Minute Setup

### 1. Create Chart of Accounts

**Create Cash Account (Asset)**
```bash
curl -X POST http://localhost:8000/accounting/chart-of-accounts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_code": "1000",
    "account_name": "Cash in Hand",
    "account_type": "Asset",
    "category": "Current Assets",
    "sub_category": "Cash & Bank",
    "opening_balance": 100000.00,
    "opening_balance_type": "debit"
  }'
```

**Create Revenue Account**
```bash
curl -X POST http://localhost:8000/accounting/chart-of-accounts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_code": "4000",
    "account_name": "Service Revenue",
    "account_type": "Revenue",
    "category": "Income",
    "opening_balance": 0.00
  }'
```

**Create Expense Account**
```bash
curl -X POST http://localhost:8000/accounting/chart-of-accounts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_code": "5100",
    "account_name": "Salary Expense",
    "account_type": "Expense",
    "category": "Personnel",
    "opening_balance": 0.00
  }'
```

### 2. Record a Transaction

**Journal Entry: Received Payment**
```bash
curl -X POST http://localhost:8000/accounting/journal-entries \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entry_date": "2026-01-15T00:00:00",
    "description": "Received payment for audit services",
    "reference": "INV-001",
    "lines": [
      {
        "account_id": "1000-uuid",
        "debit": 50000.00,
        "credit": 0.00,
        "description": "Cash received"
      },
      {
        "account_id": "4000-uuid",
        "debit": 0.00,
        "credit": 50000.00,
        "description": "Service revenue earned"
      }
    ]
  }'
```

**Golden Rule**: Debit = Credit (Total = ₹50,000)

### 3. Post the Entry

```bash
curl -X POST http://localhost:8000/accounting/journal-entries/{entry_id}/post \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. View General Ledger

```bash
curl -X GET "http://localhost:8000/accounting/general-ledger/1000-uuid" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "account_code": "1000",
  "account_name": "Cash in Hand",
  "opening_balance": 100000.00,
  "total_debit": 50000.00,
  "total_credit": 0.00,
  "closing_balance": 150000.00,
  "transactions": [
    {
      "transaction_date": "2026-01-15T00:00:00",
      "description": "Received payment for audit services",
      "debit": 50000.00,
      "credit": 0.00,
      "running_balance": 150000.00
    }
  ]
}
```

### 5. Generate Trial Balance

```bash
curl -X GET "http://localhost:8000/accounting/trial-balance?as_on_date=2026-01-31" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response Shows:**
- All accounts with opening balance, debits, credits
- Total debits = Total credits ✓
- Each account's closing balance

### 6. View P&L Statement

```bash
curl -X GET "http://localhost:8000/accounting/income-statement?as_on_date=2026-01-31" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "statement_period": "Month",
  "revenue": [
    {
      "account_code": "4000",
      "account_name": "Service Revenue",
      "amount": 50000.00
    }
  ],
  "total_revenue": 50000.00,
  "expenses": [],
  "total_expenses": 0.00,
  "profit_before_tax": 50000.00,
  "profit_after_tax": 50000.00
}
```

### 7. View Balance Sheet

```bash
curl -X GET "http://localhost:8000/accounting/balance-sheet?as_on_date=2026-01-31" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "as_on_date": "2026-01-31T00:00:00",
  "assets": [
    {
      "account_code": "1000",
      "account_name": "Cash in Hand",
      "amount": 150000.00
    }
  ],
  "total_assets": 150000.00,
  "liabilities": [],
  "total_liabilities": 0.00,
  "equity": [],
  "total_equity": 0.00,
  "is_balanced": false
}
```

---

## Common Transactions

### Transaction 1: Pay Salary

```bash
curl -X POST http://localhost:8000/accounting/journal-entries \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entry_date": "2026-01-25T00:00:00",
    "description": "Salary payment for January",
    "lines": [
      {
        "account_id": "5100-uuid",  # Salary Expense
        "debit": 30000.00,
        "credit": 0.00
      },
      {
        "account_id": "1000-uuid",  # Cash
        "debit": 0.00,
        "credit": 30000.00
      }
    ]
  }'
```

### Transaction 2: Purchase Office Supplies

```bash
curl -X POST http://localhost:8000/accounting/journal-entries \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entry_date": "2026-01-28T00:00:00",
    "description": "Purchase office supplies",
    "reference": "PO-002",
    "lines": [
      {
        "account_id": "5200-uuid",  # Office Supplies Expense
        "debit": 5000.00,
        "credit": 0.00
      },
      {
        "account_id": "1000-uuid",  # Cash
        "debit": 0.00,
        "credit": 5000.00
      }
    ]
  }'
```

### Transaction 3: Owner Investment

```bash
curl -X POST http://localhost:8000/accounting/journal-entries \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entry_date": "2026-01-05T00:00:00",
    "description": "Owner investment",
    "lines": [
      {
        "account_id": "1000-uuid",  # Cash
        "debit": 200000.00,
        "credit": 0.00
      },
      {
        "account_id": "3000-uuid",  # Capital (Equity)
        "debit": 0.00,
        "credit": 200000.00
      }
    ]
  }'
```

---

## Account Types Reference

| Type | Default Balance | Used For | Example |
|------|-----------------|----------|---------|
| **Asset** | Debit | Things owned | Cash, Equipment, Receivables |
| **Liability** | Credit | Debts owed | Payables, Loans |
| **Equity** | Credit | Owner's stake | Capital, Retained Earnings |
| **Revenue** | Credit | Income sources | Sales, Service Revenue |
| **Expense** | Debit | Costs incurred | Salary, Rent, Utilities |

---

## Golden Rules

### Rule 1: Double Entry
Every transaction affects TWO accounts.

**Example:**
```
Received ₹50,000 payment
→ Debit Cash (+50,000)
→ Credit Revenue (+50,000)
```

### Rule 2: Balance Check
Debit Total MUST = Credit Total

```
Journal Entry Total:
  Debits: ₹50,000 ✓
  Credits: ₹50,000 ✓
  Balanced: YES
```

### Rule 3: Balance Equation
Assets = Liabilities + Equity

```
Assets: ₹150,000
Liabilities: ₹0
Equity: ₹150,000
Balanced: YES (150,000 = 0 + 150,000)
```

---

## Troubleshooting

**Issue: "Entry not balanced"**
- Check: Debit total = Credit total
- Example: If debits = 50,000, credits must also = 50,000

**Issue: "Account not found"**
- Ensure account_id exists in your chart of accounts
- Create the account first using POST /chart-of-accounts

**Issue: "Balance sheet not balanced"**
- Verify trial balance is balanced first
- Check for unposted journal entries
- Ensure all accounts are properly classified

**Issue: "Cannot post posted entry"**
- Posted entries are immutable
- Create a reversal entry if correction needed

---

## Workflow Checklist

- [ ] Create Chart of Accounts (5-10 accounts minimum)
- [ ] Record daily transactions as journal entries
- [ ] Post entries at end of day/week
- [ ] Review GL for each account
- [ ] Generate trial balance (should balance)
- [ ] Generate P&L statement
- [ ] Generate Balance Sheet
- [ ] Verify Balance Sheet equation
- [ ] Review for accuracy
- [ ] Archive/close period

---

## Sample Chart of Accounts

```
ASSETS (Debit Balance)
1000    Cash in Hand
1100    Bank Account
1200    Accounts Receivable

LIABILITIES (Credit Balance)
2000    Accounts Payable
2100    Short-term Loans

EQUITY (Credit Balance)
3000    Capital Account
3100    Retained Earnings

REVENUE (Credit Balance)
4000    Service Revenue
4100    Consulting Revenue
4200    Other Income

EXPENSES (Debit Balance)
5000    Salary Expense
5100    Rent Expense
5200    Utilities
5300    Office Supplies
5400    Travel Expense
5500    Depreciation
```

---

## Next Steps

1. Create your COA
2. Record January transactions
3. Post all entries
4. View trial balance
5. Generate P&L and BS
6. Review for accuracy
7. Close the period
8. Repeat for next month

