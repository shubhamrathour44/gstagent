# Payroll Module - Quick Start Guide

## 5-Minute Setup

### 1. Create an Employee
```bash
curl -X POST http://localhost:8000/payroll/employees \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Rajesh Kumar",
    "email": "rajesh@firm.com",
    "phone": "+919876543210",
    "pan": "ABCDE1234F",
    "designation": "Senior CA",
    "joining_date": "2023-06-01T00:00:00",
    "basic_salary": 60000,
    "hra": 20000,
    "dearness_allowance": 6000,
    "pf_applicable": true,
    "esi_applicable": true
  }'
```

**Response:**
```json
{
  "id": "emp-uuid-123",
  "name": "Rajesh Kumar",
  "designation": "Senior CA",
  "basic_salary": 60000,
  "status": "active"
}
```

### 2. Create Salary Structure
```bash
curl -X POST http://localhost:8000/payroll/salary-structures \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "emp-uuid-123",
    "effective_from": "2026-01-01T00:00:00",
    "basic": 60000,
    "hra": 20000,
    "dearness_allowance": 6000,
    "travel_allowance": 2000,
    "medical_allowance": 1000,
    "pf_rate": 12,
    "esi_rate": 0.75
  }'
```

### 3. Record Daily Attendance
```bash
curl -X POST http://localhost:8000/payroll/attendance \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "emp-uuid-123",
    "attendance_date": "2026-01-15T00:00:00",
    "status": "present",
    "hours_worked": 8
  }'
```

### 4. Process Monthly Payroll
```bash
curl -X POST http://localhost:8000/payroll/process \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "emp-uuid-123",
    "month": "2026-01",
    "working_days": 26,
    "actual_days_worked": 26
  }'
```

**Response:**
```json
{
  "employee_id": "emp-uuid-123",
  "month": "2026-01",
  "basic_salary": 60000,
  "gross_salary": 89000,
  "pf_deduction": 1800,
  "esi_deduction": 667.50,
  "income_tax": 1234.56,
  "total_deductions": 3701.50,
  "net_salary": 85298.50
}
```

### 5. Get Salary Slip
```bash
curl -X GET "http://localhost:8000/payroll/salary-slip/emp-uuid-123/2026-01" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 6. View Monthly Report
```bash
curl -X GET "http://localhost:8000/payroll/payroll/2026-01" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Common Tasks

### List All Employees
```bash
GET /payroll/employees?status=active
```

### Get Employee Details
```bash
GET /payroll/employees/{employee_id}
```

### Update Employee Salary
```bash
PATCH /payroll/employees/{employee_id}
{
  "basic_salary": 70000,
  "hra": 25000
}
```

### Record Leave
```bash
POST /payroll/attendance
{
  "employee_id": "emp-uuid-123",
  "attendance_date": "2026-01-20T00:00:00",
  "status": "leave"
}
```

### Get Attendance Report
```bash
GET /payroll/attendance/{employee_id}?year=2026&month=1
```

### Get Payroll Statistics
```bash
GET /payroll/stats/2026-01
```

---

## Salary Calculation Example

**Employee: Rajesh Kumar**

```
Month: January 2026
Working Days: 26
Actual Days Worked: 26

EARNINGS:
  Basic Salary:        ₹60,000.00
  HRA:                 ₹20,000.00
  Dearness Allowance:  ₹6,000.00
  Travel Allowance:    ₹2,000.00
  Medical Allowance:   ₹1,000.00
  ─────────────────────────────────
  GROSS SALARY:        ₹89,000.00

DEDUCTIONS:
  PF (12% capped):     ₹1,800.00  [min(89,000 × 12%, 1,800)]
  ESI (0.75%):         ₹667.50    [89,000 × 0.75%]
  PT (TN):             ₹0.00      [Below slab]
  Income Tax:          ₹1,234.56  [Based on annual ₹10,68,000]
  ─────────────────────────────────
  TOTAL DEDUCTIONS:    ₹3,702.06

NET SALARY (Take-Home): ₹85,297.94
```

---

## Database Tables Created

1. **employees** - Employee profiles and basic info
2. **attendance** - Daily attendance records
3. **salary_structures** - Salary components and rates
4. **payrolls** - Monthly salary calculations

All data is firm-scoped and multi-tenant safe.

---

## Key Features

✅ Automatic salary calculation
✅ Statutory deductions (PF, ESI, PT, IT)
✅ Attendance-based proration
✅ Salary slip generation
✅ Monthly reports
✅ Indian tax compliance
✅ Multi-tenant (firm-scoped)

---

## Troubleshooting

**Issue: Employee not found**
- Ensure employee_id is correct
- Verify employee belongs to your firm

**Issue: Salary structure missing**
- Create salary structure before processing payroll
- Check effective_from date

**Issue: PF calculation capped at ₹1,800**
- This is per statutory rules (max ₹1,800/month)
- Cannot be overridden

---

## Next Steps

1. Integrate with frontend dashboard
2. Add salary slip PDF generation
3. Add bank file export (NEFT/RTGS)
4. Add employee self-service portal
5. Add compliance report generation

