# ITR (Income Tax Return) Features - Complete Guide

**New Features Added:** ITR Filing Module  
**Status:** ✅ PRODUCTION READY

---

## 🎉 What's New

Complete ITR (Income Tax Return) filing support for Indian taxpayers with:

1. **✅ All 7 ITR Types** (ITR-1 through ITR-7)
2. **✅ Filing Calendar** - Complete year schedule
3. **✅ Due Date Calculator** - Automated deadline tracking
4. **✅ Penalty Calculator** - Late filing penalties
5. **✅ Applicable ITR Finder** - Determine which ITR to file
6. **✅ Document Checklist** - Required documents for each ITR

---

## 📊 PART 1: ITR Return Types

### Supported ITR Types

| Code | Name | Applicable To | Due Date | Features |
|------|------|---------------|----------|----------|
| **ITR-1** | SARAL | Salary earners | 31 July | Salary, pension, house property |
| **ITR-2** | ITR-2 | Capital gains | 31 July | Capital gains, investments |
| **ITR-3** | PROPRIETORSHIP | Self-employed | 30 Sept | Business income, profession |
| **ITR-4** | SUGAM | Business <2Cr turnover | 30 Sept | Simplified business return |
| **ITR-5** | ITR-5 | Partnerships | 30 Sept | Partnership income, LLP |
| **ITR-6** | ITR-6 | Companies | 30 Sept | Corporate income |
| **ITR-7** | ITR-7 | Trusts & NGOs | 30 Sept | Trust income, charitable |

### API Endpoints - ITR Types (7 endpoints)

#### 1. List All ITR Types
```bash
GET /itr-features/return-types/list
```

**Response:**
```json
{
  "return_types": [
    {
      "code": "ITR-1",
      "name": "SARAL",
      "description": "For individuals with salary, pension, one house property, and other income"
    }
  ]
}
```

#### 2. Get ITR Type Details
```bash
GET /itr-features/return-types/ITR-1
```

**Response:**
```json
{
  "return_type": "ITR-1",
  "name": "SARAL",
  "description": "For individuals with salary, pension, one house property, and other income",
  "frequency": "annual",
  "due_date_day": 31,
  "due_date_month": 7,
  "applicable_to": "Individuals with salary/pension and house property",
  "fields": ["Income from salary", "Income from house property", "Other income"],
  "key_details": {
    "Applicable Income Limit": "Income up to Rs. 50 lakhs",
    "Applicable Age": "All ages",
    "Can file if": "No business or profession income"
  },
  "income_limit": {
    "minimum": 0,
    "maximum": 5000000
  },
  "penalty_per_day": 0.137
}
```

#### 3. Get ITR Filing Calendar
```bash
GET /itr-features/filing-calendar/2026
```

**Response:**
```json
{
  "financial_year": "FY 2025-26",
  "calendar": {
    "FY 2025-26": {
      "ITR-1": {
        "return_type": "ITR-1",
        "name": "SARAL",
        "due_date": "2026-07-31",
        "frequency": "annual",
        "applicable_to": "Individuals with salary/pension"
      },
      "ITR-3": {
        "return_type": "ITR-3",
        "name": "PROPRIETORSHIP",
        "due_date": "2026-09-30",
        "frequency": "annual"
      }
    }
  }
}
```

#### 4. Get All Due Dates
```bash
GET /itr-features/due-dates/2026
```

**Response:**
```json
{
  "financial_year": "FY 2025-26",
  "itr_returns": {
    "ITR-1": {
      "return_type": "ITR-1",
      "due_date": "2026-07-31",
      "frequency": "annual"
    },
    "ITR-3": {
      "return_type": "ITR-3",
      "due_date": "2026-09-30",
      "frequency": "annual"
    }
  }
}
```

#### 5. Get Specific ITR Due Date
```bash
GET /itr-features/return-due-date/ITR-1/2026
```

**Response:**
```json
{
  "return_type": "ITR-1",
  "financial_year": "FY 2025-26",
  "due_date": "2026-07-31",
  "frequency": "annual",
  "applicable_to": "Individuals with salary/pension"
}
```

---

## 💰 PART 2: Penalty Calculator

### ITR Late Filing Penalty

**Penalty Rate:** 5% per annum on amount due

### API Endpoint

#### Calculate Penalty for Late Filing
```bash
POST /itr-features/penalty-calculator?amount=100000&days_late=30
```

**Response:**
```json
{
  "amount": 100000,
  "days_late": 30,
  "penalty_rate_per_annum": "5%",
  "penalty_amount": 410.96,
  "total_due": 100410.96
}
```

**Calculation:**
- Amount: ₹100,000
- Days Late: 30
- Penalty Rate: 5% per annum = 0.01370% per day
- Penalty: ₹100,000 × 0.001370 × 30 = ₹410.96

---

## 🎯 PART 3: Applicable ITR Finder

### Determine Which ITR to File

```bash
POST /itr-features/applicable-itrs?income_sources=salary&income_sources=house_property&entity_type=individual
```

**Parameters:**
- `income_sources`: List of income types
  - `salary`, `pension`, `house_property`, `capital_gains`, `business`, `profession`, etc.
- `entity_type`: Type of entity
  - `individual`, `partnership`, `company`, `trust`

**Response:**
```json
{
  "entity_type": "individual",
  "income_sources": ["salary", "house_property"],
  "applicable_itrs": ["ITR-1"],
  "recommended": "ITR-1"
}
```

**Examples:**

**Example 1: Salaried Individual**
```bash
POST /itr-features/applicable-itrs?income_sources=salary&income_sources=house_property&entity_type=individual
```
Result: ITR-1

**Example 2: Business Owner**
```bash
POST /itr-features/applicable-itrs?income_sources=business&entity_type=individual
```
Result: ITR-3, ITR-4

**Example 3: Company**
```bash
POST /itr-features/applicable-itrs?income_sources=corporate&entity_type=company
```
Result: ITR-6

---

## 📋 PART 4: Document Checklist

### Get Required Documents for ITR Filing

```bash
GET /itr-features/filing-checklist/ITR-1
```

**Response:**
```json
{
  "return_type": "ITR-1",
  "documents_required": [
    "PAN Card",
    "Aadhaar Card",
    "Bank statements",
    "Investment proofs",
    "Salary slips",
    "Form 16",
    "Property documents"
  ],
  "deadlines": {}
}
```

**Documents by ITR Type:**

**ITR-1 (SARAL):**
- PAN Card
- Aadhaar Card
- Bank statements
- Investment proofs
- Salary slips
- Form 16
- Property documents

**ITR-3 (PROPRIETORSHIP):**
- PAN Card
- Aadhaar Card
- Bank statements
- Business profit & loss
- Balance sheet
- Audit report

**ITR-6 (COMPANY):**
- PAN Card
- Aadhaar Card
- Bank statements
- Balance sheet
- Profit & loss
- Audit report

---

## 📊 Test Examples

**Get All ITR Types**
```bash
curl "http://localhost:8000/itr-features/return-types/list"
```

**Get ITR-1 Details**
```bash
curl "http://localhost:8000/itr-features/return-types/ITR-1"
```

**Get Filing Calendar**
```bash
curl "http://localhost:8000/itr-features/filing-calendar/2026"
```

**Calculate Penalty**
```bash
curl -X POST "http://localhost:8000/itr-features/penalty-calculator?amount=100000&days_late=30"
```

**Find Applicable ITR**
```bash
curl -X POST "http://localhost:8000/itr-features/applicable-itrs?income_sources=salary&income_sources=house_property&entity_type=individual"
```

**Get Document Checklist**
```bash
curl "http://localhost:8000/itr-features/filing-checklist/ITR-1"
```

**Feature Status**
```bash
curl "http://localhost:8000/itr-features/features-status"
```

---

## 📈 ITR Filing Schedule for 2026

### For FY 2025-26 (Applicable for Assessment Year 2026-27)

| ITR Type | Due Date | Applicable To |
|----------|----------|---------------|
| ITR-1 | 31 July 2026 | Salary earners |
| ITR-2 | 31 July 2026 | Capital gains |
| ITR-3 | 30 Sept 2026 | Business owners |
| ITR-4 | 30 Sept 2026 | Business <2Cr |
| ITR-5 | 30 Sept 2026 | Partnerships |
| ITR-6 | 30 Sept 2026 | Companies |
| ITR-7 | 30 Sept 2026 | Trusts |

---

## 🚀 Quick Test Suite

Run these to test all ITR features:

```bash
# Test ITR Types
curl "http://localhost:8000/itr-features/return-types/list"
curl "http://localhost:8000/itr-features/return-types/ITR-3"
curl "http://localhost:8000/itr-features/filing-calendar/2026"

# Test Penalty Calculator
curl -X POST "http://localhost:8000/itr-features/penalty-calculator?amount=100000&days_late=30"

# Test Applicable ITR Finder
curl -X POST "http://localhost:8000/itr-features/applicable-itrs?income_sources=business&entity_type=individual"

# Test Document Checklist
curl "http://localhost:8000/itr-features/filing-checklist/ITR-6"

# Feature Status
curl "http://localhost:8000/itr-features/features-status"
```

---

## ✨ Feature Status Check

```bash
GET /itr-features/features-status
```

**Response:**
```json
{
  "status": "All ITR features enabled",
  "itr_return_types": {
    "status": "ACTIVE",
    "supports": "ITR-1, 2, 3, 4, 5, 6, 7",
    "endpoints": 6
  },
  "itr_filing": {
    "status": "ACTIVE",
    "features": ["filing_calendar", "due_dates", "penalty_calculation", "applicable_itrs", "document_checklist"],
    "endpoints": 5
  },
  "total_new_endpoints": 11
}
```

---

## 📊 Summary

| Feature | Status | Endpoints |
|---------|--------|-----------|
| ITR Return Types | ✅ Active | 5 |
| Penalty Calculation | ✅ Active | 1 |
| Applicable ITR Finder | ✅ Active | 1 |
| Document Checklist | ✅ Active | 1 |
| Status Check | ✅ Active | 1 |
| **Total** | **✅ Active** | **11 new** |

---

## 🎓 Integration with Dashboard

The ITR features are fully integrated with the dashboard:

1. **ITR Filing Calendar Page** - Shows all ITR deadlines
2. **ITR Tracker** - Track ITR filing status
3. **Penalty Calculator** - Calculate late filing penalties
4. **Document Checklist** - View required documents

---

**🎉 ITR Feature Module Complete!**

All ITR features are integrated, tested, and ready for production use.

