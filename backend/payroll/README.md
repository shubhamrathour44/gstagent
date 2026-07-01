# Payroll Module - GSTAgent

Complete payroll management system for Indian CA practices with statutory compliance.

## Features

✅ **Employee Management**
- Employee profiles with PAN, Aadhar, UPI, bank details
- Designation and department tracking
- Status management (active, inactive, separated)
- Joining date and employment tenure

✅ **Salary Components**
- Basic salary
- HRA (House Rent Allowance)
- Dearness Allowance (DA)
- Travel Allowance (TA)
- Medical Allowance (MA)
- Other allowances
- Proration based on attendance

✅ **Statutory Deductions**
- **PF (Provident Fund)**: 12% of basic salary (max ₹1,800/month)
- **ESI (Employee State Insurance)**: 0.75% of gross salary (if gross < ₹21,000)
- **PT (Professional Tax)**: State-wise slabs (TN, MH, KA supported)
- **Income Tax**: Based on annual salary with standard slabs

✅ **Attendance Tracking**
- Daily attendance (Present, Absent, Leave)
- Hours worked tracking
- Proration of salary based on attendance
- Monthly attendance reports

✅ **Payroll Processing**
- Automatic salary calculation with all deductions
- Monthly payroll generation
- Salary slip generation
- Batch processing for multiple employees

✅ **Reporting & Analytics**
- Monthly payroll summary
- Employee-wise salary slips
- Deduction breakdowns
- Payroll statistics by month

---

## API Endpoints

### Employee Management

#### Create Employee
```bash
POST /payroll/employees
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+919876543210",
  "pan": "ABCDE1234F",
  "aadhar": "123456789012",
  "upi_id": "john@upi",
  "bank_account": "1234567890",
  "bank_ifsc": "SBIN0001234",
  "designation": "Senior CA",
  "department": "Audit",
  "joining_date": "2023-01-15T00:00:00",
  "basic_salary": 50000.00,
  "hra": 15000.00,
  "dearness_allowance": 5000.00,
  "other_allowances": 2000.00,
  "pf_applicable": true,
  "esi_applicable": true,
  "pt_applicable": false
}
```

#### List All Employees
```bash
GET /payroll/employees?status=active&skip=0&limit=50
```

#### Get Employee Details
```bash
GET /payroll/employees/{employee_id}
```

#### Update Employee
```bash
PATCH /payroll/employees/{employee_id}
Content-Type: application/json

{
  "basic_salary": 55000.00,
  "status": "active"
}
```

---

### Attendance Management

#### Record Attendance
```bash
POST /payroll/attendance
Content-Type: application/json

{
  "employee_id": "emp-uuid",
  "attendance_date": "2026-01-15T00:00:00",
  "status": "present",
  "hours_worked": 8.0,
  "remarks": "Regular working day"
}
```

Status values: `present`, `absent`, `leave`

#### Get Employee Attendance
```bash
GET /payroll/attendance/{employee_id}?year=2026&month=1
```

---

### Salary Structure

#### Create Salary Structure
```bash
POST /payroll/salary-structures
Content-Type: application/json

{
  "employee_id": "emp-uuid",
  "effective_from": "2026-01-01T00:00:00",
  "effective_to": null,
  "basic": 50000.00,
  "hra": 15000.00,
  "dearness_allowance": 5000.00,
  "travel_allowance": 2000.00,
  "medical_allowance": 1000.00,
  "other_allowances": 2000.00,
  "pf_rate": 12.0,
  "esi_rate": 0.75,
  "pt_rate": 0.0
}
```

#### Get Active Salary Structure
```bash
GET /payroll/salary-structures/{employee_id}
```

---

### Payroll Processing

#### Process Monthly Payroll
```bash
POST /payroll/process
Content-Type: application/json

{
  "employee_id": "emp-uuid",
  "month": "2026-01",
  "working_days": 26,
  "actual_days_worked": 26,
  "income_tax": 0.0,
  "other_deductions": 0.0
}
```

**Parameters:**
- `month`: Format YYYY-MM (required)
- `working_days`: Default 26 (optional)
- `actual_days_worked`: Based on attendance (optional)
- `income_tax`: Override calculated tax (optional)
- `other_deductions`: Additional deductions (optional)

---

### Payroll Reports

#### Get Monthly Payroll Summary
```bash
GET /payroll/payroll/2026-01
```

Response includes:
- Total employees processed
- Total gross salary
- Total deductions breakdown
- Total net salary

#### Get Salary Slip
```bash
GET /payroll/salary-slip/{employee_id}/2026-01
```

Returns complete salary slip with:
- All earnings components
- All deductions (PF, ESI, PT, IT)
- Net salary
- Working days and actual days worked

#### Get Payroll Statistics
```bash
GET /payroll/stats/2026-01
```

Returns:
- Total employees count
- Active employees count
- Total gross, deductions, net salary for the month

---

## Salary Calculation Logic

### 1. Basic Salary
```
Prorated Basic = (Basic / Working Days) × Actual Days Worked
```

### 2. Allowances
All allowances are prorated based on attendance:
```
Prorated Allowance = (Allowance / Working Days) × Actual Days Worked
```

### 3. Gross Salary
```
Gross = Basic + HRA + DA + TA + MA + Other Allowances
```

### 4. Deductions

**PF (Provident Fund)**
```
PF = min((Gross × 12%) / 100, ₹1,800)
```

**ESI (Employee State Insurance)**
```
ESI = (Gross × 0.75%) / 100  [Only if Gross < ₹21,000]
```

**PT (Professional Tax)** - State-wise slabs
```
Tamil Nadu: ₹0-15K (₹0), ₹15-25K (₹100), ₹25-50K (₹150), etc.
```

**Income Tax** - Annual calculation (simplified)
```
Annual Income < ₹2.5L: ₹0
₹2.5L - ₹5L: 5% of excess
₹5L - ₹10L: 20% of excess + ₹12,500
> ₹10L: 30% of excess + ₹1,12,500
```

### 5. Net Salary
```
Net = Gross - (PF + ESI + PT + Income Tax + Other Deductions)
```

---

## Database Schema

### employees
```
id (UUID)
firm_id → ca_firms
name, email, phone
pan, aadhar, upi_id, bank_account, bank_ifsc
designation, department
joining_date, status
basic_salary, hra, dearness_allowance, other_allowances
pf_applicable, esi_applicable, pt_applicable
created_by, created_at, updated_at
```

### attendance
```
id (UUID)
firm_id, employee_id → employees
attendance_date, status (present/absent/leave)
hours_worked, remarks
created_at
```

### salary_structures
```
id (UUID)
firm_id, employee_id → employees
effective_from, effective_to
basic, hra, da, ta, ma, other_allowances
pf_rate, esi_rate, pt_rate
created_by, created_at
```

### payrolls
```
id (UUID)
firm_id, employee_id → employees
month (YYYY-MM), status (draft/finalized/paid)
working_days, actual_days_worked
Earnings: basic, hra, da, ta, ma, other_allowances, gross
Deductions: pf, esi, pt, income_tax, other, total
net_salary, payment_method, payment_date
created_by, created_at, updated_at
```

---

## Example Workflow

### 1. Create Employee
```bash
POST /payroll/employees
→ Returns: employee_id
```

### 2. Mark Attendance (Daily)
```bash
POST /payroll/attendance
→ Record for each working day
```

### 3. Create Salary Structure (Once per employee)
```bash
POST /payroll/salary-structures
→ Define salary components and rates
```

### 4. Process Monthly Payroll
```bash
POST /payroll/process
→ Automatically calculates all components and deductions
```

### 5. Generate Salary Slip
```bash
GET /payroll/salary-slip/{employee_id}/2026-01
→ Share with employee
```

### 6. View Reports
```bash
GET /payroll/payroll/2026-01
GET /payroll/stats/2026-01
```

---

## Compliance Notes

✅ **India Tax Compliance**
- PF capped at ₹1,800/month per statutory rules
- ESI only applicable for gross < ₹21,000
- PT calculation follows state-wise slabs
- Income tax based on annual salary brackets

✅ **Statutory Deductions**
- Supports all major statutory deductions
- Employer and employee contributions tracked
- Compliance reports for payroll audit

✅ **Flexibility**
- Override income tax if paid through advance tax
- Add custom deductions per employee
- Proration based on actual attendance

---

## Future Enhancements

- [ ] Employer's PF/ESI contributions
- [ ] Gratuity and bonus management
- [ ] Leave accrual and management
- [ ] Payroll approval workflow
- [ ] Bank file generation (NEFT/RTGS)
- [ ] Compliance report generation
- [ ] Integration with TDS filing
- [ ] Mobile app for salary slip access

---

## Status

✅ Production Ready for MVP
- Core payroll processing complete
- All statutory deductions implemented
- Salary slip generation working
- Monthly reporting functional

