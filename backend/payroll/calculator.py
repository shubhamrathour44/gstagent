"""Salary and payroll calculation logic for Indian tax compliance."""

from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import Employee, SalaryStructure, Attendance


class SalaryCalculator:
    """Calculates salary components based on Indian tax rules."""

    @staticmethod
    async def get_active_salary_structure(
        db: AsyncSession, employee_id: str, effective_date: datetime
    ) -> Optional[SalaryStructure]:
        """Get the active salary structure for an employee on a given date."""
        result = await db.execute(
            select(SalaryStructure).where(
                (SalaryStructure.employee_id == employee_id)
                & (SalaryStructure.effective_from <= effective_date)
                & (
                    (SalaryStructure.effective_to == None)
                    | (SalaryStructure.effective_to > effective_date)
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_attendance_days(
        db: AsyncSession, employee_id: str, year: int, month: int
    ) -> Tuple[int, int]:
        """Get working days and actual days worked for a month."""
        result = await db.execute(
            select(Attendance).where(
                (Attendance.employee_id == employee_id)
                & (Attendance.attendance_date.year == year)
                & (Attendance.attendance_date.month == month)
            )
        )
        attendances = result.scalars().all()

        working_days = 26
        present_days = sum(1 for a in attendances if a.status == "present")

        return working_days, present_days

    @staticmethod
    def calculate_basic_salary(basic: float, days_worked: int, working_days: int = 26) -> float:
        """Calculate basic salary based on days worked."""
        if working_days == 0:
            return 0.0
        return (basic / working_days) * days_worked

    @staticmethod
    def calculate_allowances(
        hra: float,
        da: float,
        ta: float,
        ma: float,
        others: float,
        days_worked: int,
        working_days: int = 26,
    ) -> Tuple[float, float, float, float, float]:
        """Calculate all allowances for the month based on days worked."""
        if working_days == 0:
            return 0.0, 0.0, 0.0, 0.0, 0.0

        factor = days_worked / working_days

        return (
            hra * factor,
            da * factor,
            ta * factor,
            ma * factor,
            others * factor,
        )

    @staticmethod
    def calculate_gross_salary(
        basic: float, hra: float, da: float, ta: float, ma: float, others: float
    ) -> float:
        """Calculate gross salary (sum of all earnings)."""
        return basic + hra + da + ta + ma + others

    @staticmethod
    def calculate_pf(gross_salary: float, pf_rate: float = 12.0) -> float:
        """Calculate Employee PF (max ₹1,800/month as per statutory limit)."""
        pf = (gross_salary * pf_rate) / 100
        return min(pf, 1800.0)

    @staticmethod
    def calculate_esi(gross_salary: float, esi_rate: float = 0.75) -> float:
        """Calculate ESI (applicable if gross salary < ₹21,000/month)."""
        if gross_salary > 21000:
            return 0.0
        return (gross_salary * esi_rate) / 100

    @staticmethod
    def calculate_pt(gross_salary: float, state: str = "TN", pt_rate: float = 0.0) -> float:
        """Calculate Professional Tax (varies by state)."""
        if pt_rate == 0:
            return 0.0

        pt_slabs = {
            "TN": {
                0: 0,
                15000: 0,
                25000: 100,
                50000: 150,
                100000: 200,
                150000: 300,
            },
            "MH": {0: 0, 10000: 0, 12500: 100, 20000: 150, 30000: 200},
            "KA": {0: 0, 15000: 0, 25000: 100, 50000: 150},
        }

        slab = pt_slabs.get(state, {0: 0})
        pt = 0.0
        for limit, tax in sorted(slab.items()):
            if gross_salary >= limit:
                pt = tax

        return pt

    @staticmethod
    def calculate_income_tax(gross_salary: float, annual_salary: Optional[float] = None) -> float:
        """Calculate income tax based on annual salary (simplified)."""
        if annual_salary is None:
            annual_salary = gross_salary * 12

        if annual_salary <= 250000:
            return 0.0
        elif annual_salary <= 500000:
            return (annual_salary - 250000) * 0.05 / 12
        elif annual_salary <= 1000000:
            return (annual_salary - 500000) * 0.20 / 12 + 12500 / 12
        else:
            return (annual_salary - 1000000) * 0.30 / 12 + 112500 / 12

    @staticmethod
    def calculate_total_deductions(
        pf: float, esi: float, pt: float, income_tax: float, other: float = 0.0
    ) -> float:
        """Calculate total deductions."""
        return pf + esi + pt + income_tax + other

    @staticmethod
    def calculate_net_salary(gross_salary: float, total_deductions: float) -> float:
        """Calculate net salary (take-home)."""
        return max(gross_salary - total_deductions, 0.0)


class PayrollProcessor:
    """Process and generate payroll for employees."""

    @staticmethod
    async def process_employee_payroll(
        db: AsyncSession,
        employee_id: str,
        month_str: str,
        income_tax_override: Optional[float] = None,
        other_deductions: float = 0.0,
    ) -> dict:
        """Process payroll for a single employee for a given month."""
        year, month = map(int, month_str.split("-"))

        employee = await db.execute(select(Employee).where(Employee.id == employee_id))
        employee = employee.scalar_one_or_none()
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")

        salary_structure = await SalaryCalculator.get_active_salary_structure(
            db, employee_id, datetime(year, month, 1)
        )
        if not salary_structure:
            raise ValueError(f"No salary structure found for employee {employee_id}")

        working_days, actual_days = await SalaryCalculator.get_attendance_days(
            db, employee_id, year, month
        )

        basic = SalaryCalculator.calculate_basic_salary(
            salary_structure.basic, actual_days, working_days
        )
        hra, da, ta, ma, others = SalaryCalculator.calculate_allowances(
            salary_structure.hra,
            salary_structure.dearness_allowance,
            salary_structure.travel_allowance,
            salary_structure.medical_allowance,
            salary_structure.other_allowances,
            actual_days,
            working_days,
        )

        gross_salary = SalaryCalculator.calculate_gross_salary(basic, hra, da, ta, ma, others)

        pf = (
            SalaryCalculator.calculate_pf(gross_salary, salary_structure.pf_rate)
            if employee.pf_applicable
            else 0.0
        )
        esi = (
            SalaryCalculator.calculate_esi(gross_salary, salary_structure.esi_rate)
            if employee.esi_applicable
            else 0.0
        )
        pt = (
            SalaryCalculator.calculate_pt(gross_salary, pt_rate=salary_structure.pt_rate)
            if employee.pt_applicable
            else 0.0
        )
        income_tax = (
            income_tax_override
            if income_tax_override is not None
            else SalaryCalculator.calculate_income_tax(gross_salary)
        )

        total_deductions = SalaryCalculator.calculate_total_deductions(
            pf, esi, pt, income_tax, other_deductions
        )
        net_salary = SalaryCalculator.calculate_net_salary(gross_salary, total_deductions)

        return {
            "employee_id": employee_id,
            "month": month_str,
            "working_days": working_days,
            "actual_days_worked": actual_days,
            "basic_salary": round(basic, 2),
            "hra": round(hra, 2),
            "dearness_allowance": round(da, 2),
            "travel_allowance": round(ta, 2),
            "medical_allowance": round(ma, 2),
            "other_allowances": round(others, 2),
            "gross_salary": round(gross_salary, 2),
            "pf_deduction": round(pf, 2),
            "esi_deduction": round(esi, 2),
            "pt_deduction": round(pt, 2),
            "income_tax": round(income_tax, 2),
            "other_deductions": round(other_deductions, 2),
            "total_deductions": round(total_deductions, 2),
            "net_salary": round(net_salary, 2),
        }
