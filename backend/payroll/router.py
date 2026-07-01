from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from auth import CurrentUser, get_current_user
from database import get_db, Employee, Attendance, SalaryStructure, Payroll
from .schemas import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    AttendanceCreate,
    AttendanceResponse,
    SalaryStructureCreate,
    SalaryStructureResponse,
    PayrollCreate,
    PayrollResponse,
    PayrollDetailResponse,
    SalarySlip,
    PayrollStats,
)
from .calculator import PayrollProcessor, SalaryCalculator

payroll_router = APIRouter(prefix="/payroll", tags=["Payroll"])


@payroll_router.get("/status")
async def payroll_status(current_user: CurrentUser = Depends(get_current_user)):
    return {
        "status": "ok",
        "module": "payroll_management",
        "version": "1.0.0",
        "features": [
            "Employee management",
            "Attendance tracking",
            "Salary structure",
            "Payroll processing",
            "Salary slip generation",
            "Statutory deductions (PF, ESI, PT)",
            "Income tax calculation",
            "Payroll reports",
        ],
    }


@payroll_router.post("/employees")
async def create_employee(
    employee: EmployeeCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    emp = Employee(
        firm_id=current_user.firm_id,
        created_by=current_user.id,
        **employee.model_dump(),
    )
    db.add(emp)
    await db.flush()
    return EmployeeResponse.model_validate(emp)


@payroll_router.get("/employees")
async def list_employees(
    status: str = Query("active", description="Filter by status: active, inactive, all"),
    skip: int = Query(0),
    limit: int = Query(50),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Employee).where(Employee.firm_id == current_user.firm_id)

    if status != "all":
        query = query.where(Employee.status == status)

    result = await db.execute(query.order_by(desc(Employee.created_at)).offset(skip).limit(limit))
    employees = result.scalars().all()

    return {
        "count": len(employees),
        "employees": [EmployeeResponse.model_validate(e) for e in employees],
    }


@payroll_router.get("/employees/{employee_id}")
async def get_employee(
    employee_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Employee).where(
            and_(Employee.id == employee_id, Employee.firm_id == current_user.firm_id)
        )
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return EmployeeResponse.model_validate(emp)


@payroll_router.patch("/employees/{employee_id}")
async def update_employee(
    employee_id: str,
    update_data: EmployeeUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Employee).where(
            and_(Employee.id == employee_id, Employee.firm_id == current_user.firm_id)
        )
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(emp, key, value)

    await db.flush()
    return EmployeeResponse.model_validate(emp)


@payroll_router.post("/attendance")
async def record_attendance(
    attendance: AttendanceCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    emp_check = await db.execute(
        select(Employee).where(
            and_(Employee.id == attendance.employee_id, Employee.firm_id == current_user.firm_id)
        )
    )
    if not emp_check.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Employee not found")

    att = Attendance(
        firm_id=current_user.firm_id,
        **attendance.model_dump(),
    )
    db.add(att)
    await db.flush()
    return AttendanceResponse.model_validate(att)


@payroll_router.get("/attendance/{employee_id}")
async def get_employee_attendance(
    employee_id: str,
    year: int = Query(...),
    month: int = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Attendance).where(
            and_(
                Attendance.employee_id == employee_id,
                Attendance.firm_id == current_user.firm_id,
                Attendance.attendance_date.year == year,
                Attendance.attendance_date.month == month,
            )
        )
    )
    attendances = result.scalars().all()

    present = sum(1 for a in attendances if a.status == "present")
    absent = sum(1 for a in attendances if a.status == "absent")
    leave = sum(1 for a in attendances if a.status == "leave")

    return {
        "employee_id": employee_id,
        "year": year,
        "month": month,
        "total_records": len(attendances),
        "present": present,
        "absent": absent,
        "leave": leave,
        "attendance": [AttendanceResponse.model_validate(a) for a in attendances],
    }


@payroll_router.post("/salary-structures")
async def create_salary_structure(
    structure: SalaryStructureCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    emp_check = await db.execute(
        select(Employee).where(
            and_(Employee.id == structure.employee_id, Employee.firm_id == current_user.firm_id)
        )
    )
    if not emp_check.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Employee not found")

    sal_struct = SalaryStructure(
        firm_id=current_user.firm_id,
        created_by=current_user.id,
        **structure.model_dump(),
    )
    db.add(sal_struct)
    await db.flush()
    return SalaryStructureResponse.model_validate(sal_struct)


@payroll_router.get("/salary-structures/{employee_id}")
async def get_salary_structure(
    employee_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SalaryStructure).where(
            and_(
                SalaryStructure.employee_id == employee_id,
                SalaryStructure.firm_id == current_user.firm_id,
                SalaryStructure.effective_to == None,
            )
        )
    )
    structure = result.scalar_one_or_none()
    if not structure:
        raise HTTPException(status_code=404, detail="No active salary structure found")
    return SalaryStructureResponse.model_validate(structure)


@payroll_router.post("/process")
async def process_payroll(
    payroll: PayrollCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    emp_check = await db.execute(
        select(Employee).where(
            and_(Employee.id == payroll.employee_id, Employee.firm_id == current_user.firm_id)
        )
    )
    if not emp_check.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Employee not found")

    try:
        payroll_data = await PayrollProcessor.process_employee_payroll(
            db,
            payroll.employee_id,
            payroll.month,
            None,
            payroll.other_deductions,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    existing = await db.execute(
        select(Payroll).where(
            and_(
                Payroll.employee_id == payroll.employee_id,
                Payroll.month == payroll.month,
                Payroll.firm_id == current_user.firm_id,
            )
        )
    )
    existing_payroll = existing.scalar_one_or_none()

    if existing_payroll:
        for key, value in payroll_data.items():
            if key not in ["employee_id", "month"]:
                setattr(existing_payroll, key, value)
        payroll_obj = existing_payroll
    else:
        payroll_obj = Payroll(
            firm_id=current_user.firm_id,
            created_by=current_user.id,
            **payroll_data,
        )
        db.add(payroll_obj)

    await db.flush()
    return PayrollDetailResponse.model_validate(payroll_obj)


@payroll_router.get("/payroll/{month}")
async def get_monthly_payroll(
    month: str = Query(..., description="Format: YYYY-MM"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Payroll).where(
            and_(Payroll.month == month, Payroll.firm_id == current_user.firm_id)
        )
    )
    payrolls = result.scalars().all()

    total_gross = sum(p.gross_salary for p in payrolls)
    total_deductions = sum(p.total_deductions for p in payrolls)
    total_net = sum(p.net_salary for p in payrolls)

    return {
        "month": month,
        "count": len(payrolls),
        "total_gross_salary": round(total_gross, 2),
        "total_deductions": round(total_deductions, 2),
        "total_net_salary": round(total_net, 2),
        "payrolls": [PayrollDetailResponse.model_validate(p) for p in payrolls],
    }


@payroll_router.get("/salary-slip/{employee_id}/{month}")
async def get_salary_slip(
    employee_id: str,
    month: str = Query(..., description="Format: YYYY-MM"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    emp_result = await db.execute(
        select(Employee).where(
            and_(Employee.id == employee_id, Employee.firm_id == current_user.firm_id)
        )
    )
    emp = emp_result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    payroll_result = await db.execute(
        select(Payroll).where(
            and_(
                Payroll.employee_id == employee_id,
                Payroll.month == month,
                Payroll.firm_id == current_user.firm_id,
            )
        )
    )
    payroll = payroll_result.scalar_one_or_none()
    if not payroll:
        raise HTTPException(status_code=404, detail="Payroll not found for this period")

    return SalarySlip(
        employee_name=emp.name,
        employee_id=emp.id,
        month=payroll.month,
        designation=emp.designation,
        joining_date=emp.joining_date,
        basic_salary=payroll.basic_salary,
        hra=payroll.hra,
        dearness_allowance=payroll.dearness_allowance,
        travel_allowance=payroll.travel_allowance,
        medical_allowance=payroll.medical_allowance,
        other_allowances=payroll.other_allowances,
        gross_salary=payroll.gross_salary,
        pf_deduction=payroll.pf_deduction,
        esi_deduction=payroll.esi_deduction,
        pt_deduction=payroll.pt_deduction,
        income_tax=payroll.income_tax,
        other_deductions=payroll.other_deductions,
        total_deductions=payroll.total_deductions,
        net_salary=payroll.net_salary,
        working_days=payroll.working_days,
        actual_days_worked=payroll.actual_days_worked,
        payment_method=payroll.payment_method,
        payment_date=payroll.payment_date,
    )


@payroll_router.get("/stats/{month}")
async def get_payroll_stats(
    month: str = Query(..., description="Format: YYYY-MM"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    employees_result = await db.execute(
        select(func.count(Employee.id)).where(
            and_(Employee.firm_id == current_user.firm_id, Employee.status == "active")
        )
    )
    active_emp_count = employees_result.scalar() or 0

    total_emp_result = await db.execute(
        select(func.count(Employee.id)).where(Employee.firm_id == current_user.firm_id)
    )
    total_emp_count = total_emp_result.scalar() or 0

    payroll_result = await db.execute(
        select(Payroll).where(
            and_(Payroll.month == month, Payroll.firm_id == current_user.firm_id)
        )
    )
    payrolls = payroll_result.scalars().all()

    total_gross = sum(p.gross_salary for p in payrolls)
    total_deductions = sum(p.total_deductions for p in payrolls)
    total_net = sum(p.net_salary for p in payrolls)

    return PayrollStats(
        total_employees=total_emp_count,
        active_employees=active_emp_count,
        total_gross_salary=round(total_gross, 2),
        total_deductions=round(total_deductions, 2),
        total_net_salary=round(total_net, 2),
        processing_month=month,
    )
