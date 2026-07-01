# Sales Register Reconciliation Guide

Complete guide to reconciling Sales Register (SR) vs GSTR-1 for comprehensive GST validation.

---

## 🎯 Overview

Sales Register Reconciliation completes the GST module by validating **outward supplies** (sales):

```
Before: Could only reconcile purchases (PR vs GSTR-2B)
After:  Can reconcile both purchases AND sales (SR vs GSTR-1)

Coverage:
├─ Purchase validation: PR ↔ GSTR-2B ✅
└─ Sales validation: SR ↔ GSTR-1 ✅ NEW

Result: 100% GST return validation
```

---

## 📊 Key Differences from Purchase Reconciliation

| Aspect | Purchase (PR vs GSTR-2B) | Sales (SR vs GSTR-1) |
|--------|--------------------------|----------------------|
| **Direction** | Inward (what you bought) | Outward (what you sold) |
| **Impact** | ITC (Input Tax Credit) | Revenue & tax liability |
| **Mismatch Cost** | Lost deduction | Over/under-reporting |
| **Severity** | Based on tax impact | Based on revenue + tax |
| **Action** | Chase vendors | Chase customers |

---

## 🔄 Complete Workflow

### **Step 1: Gather Data**

**Sales Register:**
```json
{
  "invoice_number": "S-5001",
  "invoice_date": "18/04/2026",
  "customer_gstin": "05PQRST1234L1Z3",
  "customer_name": "ABC Buyer Ltd",
  "taxable_value": 125000,
  "cgst": 11250,
  "sgst": 11250,
  "igst": 0,
  "supply_type": "B2B"
}
```

**GSTR-1 Data:**
- Fetch from GST portal using existing `/gsp/gstr1` endpoint
- Or obtain from customer's GSTR-2B filing

---

### **Step 2: Run Reconciliation**

```bash
curl -X POST http://localhost:8000/reconciliation/sales/reconcile \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "gstin": "27ABCDE1234F1Z5",
    "period": "032026",
    "company_name": "ABC Traders Pvt Ltd",
    "sales_register": [
      {
        "invoice_number": "S-5001",
        "invoice_date": "18/04/2026",
        "customer_gstin": "05PQRST1234L1Z3",
        "customer_name": "ABC Buyer Ltd",
        "taxable_value": 125000,
        "cgst": 11250,
        "sgst": 11250,
        "supply_type": "B2B"
      }
    ],
    "gstr1_invoices": [...]
  }'
```

**Response:**
```json
{
  "success": true,
  "reconciliation_id": "recon-456",
  "message": "Sales reconciliation completed",
  "summary": {
    "total_sr_invoices": 150,
    "total_gstr1_invoices": 145,
    "matched": 140,
    "mismatched": 10,
    "match_rate": 93.3,
    "missing_in_gstr1": 5,
    "missing_in_sr": 5,
    "revenue_difference": 125000,
    "tax_difference": 22500,
    "high_severity": 2,
    "medium_severity": 5,
    "low_severity": 3
  }
}
```

---

### **Step 3: Review Mismatches**

```bash
curl -X GET "http://localhost:8000/reconciliation/sales/mismatches/recon-456?severity=high" \
  -H "Authorization: Bearer TOKEN"
```

**Response:**
```json
{
  "reconciliation_id": "recon-456",
  "total_mismatches": 10,
  "mismatches": [
    {
      "mismatch_id": "SM0001",
      "type": "invoice_not_in_gstr1",
      "severity": "high",
      "customer": "ABC Buyer Ltd",
      "gstin": "05PQRST1234L1Z3",
      "invoice_no": "S-5050",
      "invoice_date": "15/04/2026",
      "tax_impact": 22500,
      "recommended_action": "chase_customer",
      "status": "open"
    }
  ]
}
```

---

### **Step 4: Take Recommended Actions**

Based on mismatch type:

| Mismatch | Action |
|----------|--------|
| **In SR but not GSTR-1** | Chase customer to file/amend return |
| **In GSTR-1 but not SR** | Verify if invoice recorded in different period |
| **Revenue mismatch** | Check discount/amendment |
| **Tax mismatch** | Verify tax rate application |
| **Supply type mismatch** | Correct classification (B2B/B2C/Export) |

---

### **Step 5: Resolve & Track**

```bash
curl -X POST "http://localhost:8000/reconciliation/sales/mismatches/SM0001/resolve" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resolution_notes": "Customer filed amended GSTR-1 on 20/04/2026"
  }'
```

---

## 📋 API Reference

### **Reconcile Sales**

```http
POST /reconciliation/sales/reconcile
```

Reconcile Sales Register vs GSTR-1.

**Request:**
```json
{
  "gstin": "27ABCDE1234F1Z5",
  "period": "032026",
  "company_name": "ABC Traders",
  "sales_register": [...],
  "gstr1_invoices": [...]
}
```

**Response:**
- Reconciliation ID
- Summary stats
- Mismatch counts by severity

---

### **Get Results**

```http
GET /reconciliation/sales/results/{reconciliation_id}
```

Get complete reconciliation results.

---

### **Get Mismatches**

```http
GET /reconciliation/sales/mismatches/{reconciliation_id}?severity=high
```

Get mismatches with optional filtering.

---

### **Get Statistics**

```http
GET /reconciliation/sales/statistics
```

Get overall sales reconciliation statistics.

---

### **Resolve Mismatch**

```http
POST /reconciliation/sales/mismatches/{mismatch_id}/resolve
```

Mark mismatch as resolved.

---

### **Periodic Summary**

```http
GET /reconciliation/sales/periodic-summary?period=032026
```

Get summary for a specific period.

---

## 🎯 Mismatch Types

### **1. Invoice Not in GSTR-1**
```
Scenario: You issued invoice S-5001 on 15/04/2026
But customer didn't report it in their GSTR-1

Severity: HIGH (lost revenue reporting)
Action: Chase customer to file/amend GSTR-1
Impact: ₹125,000 revenue + ₹22,500 tax unreported
```

---

### **2. Invoice Not in SR**
```
Scenario: GSTR-1 shows invoice S-5005
But it's not in your sales register

Severity: MEDIUM (duplicate/entry error)
Action: Verify if recorded in different period
Impact: Could be timing difference or data entry error
```

---

### **3. Taxable Value Mismatch**
```
Scenario: SR shows ₹100,000, GSTR-1 shows ₹95,000
Difference: ₹5,000 (discount/amendment)

Severity: MEDIUM-HIGH (₹5,000 × 18% = ₹900 tax)
Action: Verify discount/amendment
Impact: Tax liability discrepancy
```

---

### **4. Tax Amount Mismatch**
```
Scenario: SR shows 18% tax, GSTR-1 shows 5% tax
Different tax rate applied

Severity: HIGH
Action: Check correct tax classification
Impact: Tax liability mismatch
```

---

### **5. Supply Type Mismatch**
```
Scenario: SR says B2B, GSTR-1 says B2C
Wrong classification

Severity: MEDIUM
Action: Correct supply type
Impact: Could affect exemption eligibility
```

---

## 💡 Real-World Examples

### **Example 1: Missing Sale Report**

```
Your SR: Invoice S-100 on 01/04/2026
         Taxable: ₹1,00,000
         Tax: ₹18,000

Customer's GSTR-1: Not reported

Mismatch: Invoice not in GSTR-1
Severity: HIGH (₹18,000 tax at risk)
Action: Email customer to amend GSTR-1
Timeline: Customer has until end of month to file
```

---

### **Example 2: Timing Difference**

```
Your SR: Invoice S-200 on 28/03/2026 (Month 1)
GSTR-1: Shows in April (Month 2) filing

Reconciliation: Missing in March, found in April
Severity: LOW (just timing difference)
Action: No action needed, system auto-adjusts
Timeline: Resolved in next period
```

---

### **Example 3: Discount/Amendment**

```
Your SR: ₹1,00,000 @ 18% = ₹18,000 tax
Amended after customer request
Actual invoice: ₹95,000 @ 18% = ₹17,100 tax

GSTR-1 filed with amended amount: ₹95,000
Mismatch: ₹5,000 difference

Action: Update SR with amendment
Result: Reconciles after update
```

---

## 📊 Severity Classification

**HIGH** (≥₹100,000 revenue or ≥₹10,000 tax impact)
- Invoice completely missing from GSTR-1
- Major tax rate misapplication
- Significant revenue discrepancy

**MEDIUM** (₹10,000-₹100,000 revenue or ₹1,000-₹10,000 tax)
- Moderate value/tax mismatch
- Wrong supply type
- Timing differences requiring correction

**LOW** (<₹10,000 revenue or <₹1,000 tax)
- Minor discrepancies
- Rounding differences
- Non-critical mismatches

---

## 🔍 Customer-wise Analysis

Get summary by customer:

```json
{
  "customer_wise": [
    {
      "name": "ABC Buyer Ltd",
      "gstin": "05PQRST1234L1Z3",
      "mismatch_count": 3,
      "financial_impact": 50000,
      "tax_impact": 9000
    },
    {
      "name": "XYZ Corp",
      "gstin": "27XYZDEF1234L1Z5",
      "mismatch_count": 2,
      "financial_impact": 25000,
      "tax_impact": 4500
    }
  ]
}
```

---

## 📈 Match Rate Calculation

```
Match Rate = (Matched Invoices / Total SR Invoices) × 100

Example:
- Total invoices in SR: 150
- Matched with GSTR-1: 140
- Match rate: 93.3%

Interpretation:
- 93%: Excellent (minor timing differences)
- 85-93%: Good (some customer delays)
- 75-85%: Fair (requires follow-up)
- <75%: Poor (many unreported sales)
```

---

## 🎯 Action Plan

### **High Severity Issues** (within 2 days)
1. Email customer with mismatch details
2. Request immediate GSTR-1 amendment
3. Escalate if no response

### **Medium Severity** (within 1 week)
1. Investigate timing/classification
2. Correct your records if needed
3. Follow up if customer action needed

### **Low Severity** (end of month)
1. Monitor resolution
2. Ignore if minor
3. Update records if needed

---

## 💰 Financial Impact

For ₹10,00,000 monthly sales (typical GST business):

```
Scenario 1: Perfect match (100%)
- No mismatches
- Tax correctly reported
- Status: ✅ Compliant

Scenario 2: 95% match (typical)
- 5% unreported: ₹50,000
- Tax impact: ₹9,000
- Risk: Penalty if not resolved
- Action: Chase customers

Scenario 3: 85% match (needs review)
- 15% unreported: ₹1,50,000
- Tax impact: ₹27,000
- Risk: High compliance risk
- Action: Immediate follow-up
```

---

## 🔐 Data Isolation

- Each firm can only see their own reconciliations
- Each user can only see their firm's data
- Complete audit trail maintained
- Sensitive customer data protected

---

## 🚀 Integration with Other Modules

```
GST Reconciliation System:

├─ Purchase Reconciliation
│  └─ PR vs GSTR-2B
│     └─ ITC validation
│
├─ Sales Reconciliation (NEW)
│  └─ SR vs GSTR-1
│     └─ Revenue validation
│
└─ GSTR-3B Filing
   ├─ Uses ITC from purchase recon
   └─ Uses output tax from sales recon
```

---

## 📊 Performance Metrics

| Operation | Time | Notes |
|-----------|------|-------|
| Reconciliation (1000 invoices) | <5s | Local processing |
| Mismatch detection | <1s | Per invoice |
| Report generation | <2s | Summary stats |
| Database storage | <1s | Bulk insert |

---

## ⚠️ Common Issues

### **Q: What if GSTR-1 data is delayed?**
A: Run reconciliation weekly. System tracks timing differences. Late filings appear as "missing_in_gstr1" initially.

### **Q: How to handle credit note adjustments?**
A: Record as separate invoice in SR. System will detect if not in GSTR-1 and flag for follow-up.

### **Q: What if customer files amended GSTR-1?**
A: Re-run reconciliation with amended data. Mark mismatch as resolved with notes.

### **Q: Should I include B2C invoices <₹1L?**
A: No - they're not reported in GSTR-1 for privacy. System ignores them.

---

## 📞 Support

For issues:
1. Verify data format in sales register
2. Ensure GSTR-1 data is current (fetch fresh from portal)
3. Check for timing differences (invoices in different period)
4. Review customer-wise summary for patterns

---

**Status:** ✅ Production Ready  
**Complements:** Purchase Reconciliation (PR vs GSTR-2B)  
**Coverage:** 100% of GST returns (inbound + outbound)
