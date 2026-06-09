"""
GST Reconciliation Engine
Compares GSTR-2B vs Purchase Register and GSTR-1 vs Sales Register
Classifies mismatches and estimates tax impact
"""

import json
import pandas as pd
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum
from datetime import datetime


class MismatchType(str, Enum):
    INVOICE_NOT_IN_2B = "Invoice in purchase register but missing in GSTR-2B"
    INVOICE_NOT_IN_PR = "Invoice in GSTR-2B but missing in purchase register"
    TAXABLE_VALUE_DIFF = "Taxable value mismatch"
    TAX_AMOUNT_DIFF = "Tax amount mismatch"
    GSTIN_MISMATCH = "Supplier GSTIN mismatch"
    INVOICE_DATE_DIFF = "Invoice date mismatch"
    REVERSE_CHARGE_DIFF = "Reverse charge flag mismatch"


class MismatchSeverity(str, Enum):
    HIGH = "high"        # Tax impact > ₹10,000
    MEDIUM = "medium"    # Tax impact ₹1,000 - ₹10,000
    LOW = "low"          # Tax impact < ₹1,000


class MismatchAction(str, Enum):
    CHASE_VENDOR = "Chase vendor to file/amend return"
    VERIFY_INTERNALLY = "Verify invoice details internally"
    DEFER_ITC = "Defer ITC claim until resolved"
    REVERSE_ITC = "Reverse ITC if unresolved beyond time limit"
    RECONCILE_BOOKS = "Reconcile books of accounts"
    NO_ACTION = "No action required"


@dataclass
class InvoiceRecord:
    invoice_number: str
    invoice_date: str
    supplier_gstin: str
    supplier_name: str
    taxable_value: float
    igst: float
    cgst: float
    sgst: float
    total_tax: float
    reverse_charge: bool = False
    source: str = ""  # "2B" or "PR" (purchase register)

    @property
    def total_value(self):
        return self.taxable_value + self.total_tax


@dataclass
class Mismatch:
    mismatch_id: str
    mismatch_type: MismatchType
    severity: MismatchSeverity
    supplier_gstin: str
    supplier_name: str
    invoice_number: str
    invoice_date: str
    pr_taxable_value: Optional[float]
    b2b_taxable_value: Optional[float]
    pr_tax_amount: Optional[float]
    b2b_tax_amount: Optional[float]
    tax_impact: float  # Rupee impact on ITC
    recommended_action: MismatchAction
    action_deadline: Optional[str]
    notes: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class ReconciliationResult:
    gstin: str
    period: str  # e.g. "032025" for March 2025
    reconciled_at: str
    total_pr_invoices: int
    total_2b_invoices: int
    matched_invoices: int
    mismatched_invoices: int
    missing_in_2b: int
    missing_in_pr: int
    total_itc_as_per_2b: float
    total_itc_as_per_pr: float
    itc_difference: float
    high_severity_count: int
    medium_severity_count: int
    low_severity_count: int
    mismatches: list[Mismatch] = field(default_factory=list)
    summary_stats: dict = field(default_factory=dict)

    def to_dict(self):
        result = asdict(self)
        return result


class GSTReconciliationEngine:
    """
    Core reconciliation engine.
    Compares Purchase Register (PR) with GSTR-2B data.
    """

    TOLERANCE = 1.0  # ₹1 tolerance for floating point differences

    def reconcile(
        self,
        gstin: str,
        period: str,
        purchase_register: list[dict],
        gstr_2b: list[dict]
    ) -> ReconciliationResult:
        """
        Main reconciliation function.
        Returns a ReconciliationResult with all mismatches.
        """

        pr_invoices = self._parse_records(purchase_register, source="PR")
        b2b_invoices = self._parse_records(gstr_2b, source="2B")

        # Build lookup maps
        pr_map = self._build_invoice_map(pr_invoices)
        b2b_map = self._build_invoice_map(b2b_invoices)

        mismatches = []
        matched = 0
        mismatch_counter = 0

        # Check PR invoices against 2B
        for key, pr_inv in pr_map.items():
            if key not in b2b_map:
                mismatch_counter += 1
                m = self._create_mismatch(
                    mismatch_id=f"MM{mismatch_counter:04d}",
                    mismatch_type=MismatchType.INVOICE_NOT_IN_2B,
                    pr_inv=pr_inv,
                    b2b_inv=None
                )
                mismatches.append(m)
            else:
                b2b_inv = b2b_map[key]
                field_mismatches = self._compare_invoices(pr_inv, b2b_inv)
                if field_mismatches:
                    for mt in field_mismatches:
                        mismatch_counter += 1
                        m = self._create_mismatch(
                            mismatch_id=f"MM{mismatch_counter:04d}",
                            mismatch_type=mt,
                            pr_inv=pr_inv,
                            b2b_inv=b2b_inv
                        )
                        mismatches.append(m)
                else:
                    matched += 1

        # Check 2B invoices missing in PR
        for key, b2b_inv in b2b_map.items():
            if key not in pr_map:
                mismatch_counter += 1
                m = self._create_mismatch(
                    mismatch_id=f"MM{mismatch_counter:04d}",
                    mismatch_type=MismatchType.INVOICE_NOT_IN_PR,
                    pr_inv=None,
                    b2b_inv=b2b_inv
                )
                mismatches.append(m)

        # Compute totals
        total_itc_2b = sum(inv.total_tax for inv in b2b_invoices)
        total_itc_pr = sum(inv.total_tax for inv in pr_invoices)

        high = sum(1 for m in mismatches if m.severity == MismatchSeverity.HIGH)
        medium = sum(1 for m in mismatches if m.severity == MismatchSeverity.MEDIUM)
        low = sum(1 for m in mismatches if m.severity == MismatchSeverity.LOW)

        missing_in_2b = sum(
            1 for m in mismatches
            if m.mismatch_type == MismatchType.INVOICE_NOT_IN_2B
        )
        missing_in_pr = sum(
            1 for m in mismatches
            if m.mismatch_type == MismatchType.INVOICE_NOT_IN_PR
        )

        # Vendor-wise summary
        vendor_summary = {}
        for m in mismatches:
            gstin_key = m.supplier_gstin
            if gstin_key not in vendor_summary:
                vendor_summary[gstin_key] = {
                    "name": m.supplier_name,
                    "gstin": gstin_key,
                    "mismatch_count": 0,
                    "total_tax_impact": 0.0
                }
            vendor_summary[gstin_key]["mismatch_count"] += 1
            vendor_summary[gstin_key]["total_tax_impact"] += abs(m.tax_impact)

        return ReconciliationResult(
            gstin=gstin,
            period=period,
            reconciled_at=datetime.now().isoformat(),
            total_pr_invoices=len(pr_invoices),
            total_2b_invoices=len(b2b_invoices),
            matched_invoices=matched,
            mismatched_invoices=len(mismatches),
            missing_in_2b=missing_in_2b,
            missing_in_pr=missing_in_pr,
            total_itc_as_per_2b=round(total_itc_2b, 2),
            total_itc_as_per_pr=round(total_itc_pr, 2),
            itc_difference=round(total_itc_pr - total_itc_2b, 2),
            high_severity_count=high,
            medium_severity_count=medium,
            low_severity_count=low,
            mismatches=mismatches,
            summary_stats={
                "vendor_wise": list(vendor_summary.values()),
                "match_rate": round(matched / max(len(pr_invoices), 1) * 100, 1)
            }
        )

    def _parse_records(self, records: list[dict], source: str) -> list[InvoiceRecord]:
        parsed = []
        for r in records:
            try:
                igst = float(r.get("igst", 0) or 0)
                cgst = float(r.get("cgst", 0) or 0)
                sgst = float(r.get("sgst", 0) or 0)
                total_tax = igst + cgst + sgst

                inv = InvoiceRecord(
                    invoice_number=str(r.get("invoice_number", "")).strip().upper(),
                    invoice_date=str(r.get("invoice_date", "")).strip(),
                    supplier_gstin=str(r.get("supplier_gstin", "")).strip().upper(),
                    supplier_name=str(r.get("supplier_name", "Unknown")).strip(),
                    taxable_value=float(r.get("taxable_value", 0) or 0),
                    igst=igst,
                    cgst=cgst,
                    sgst=sgst,
                    total_tax=total_tax,
                    reverse_charge=bool(r.get("reverse_charge", False)),
                    source=source
                )
                parsed.append(inv)
            except Exception as e:
                print(f"Warning: Could not parse record {r}: {e}")
        return parsed

    def _build_invoice_map(self, invoices: list[InvoiceRecord]) -> dict:
        """Key: (supplier_gstin, invoice_number)"""
        return {
            (inv.supplier_gstin, inv.invoice_number): inv
            for inv in invoices
        }

    def _compare_invoices(
        self,
        pr: InvoiceRecord,
        b2b: InvoiceRecord
    ) -> list[MismatchType]:
        mismatches = []

        if abs(pr.taxable_value - b2b.taxable_value) > self.TOLERANCE:
            mismatches.append(MismatchType.TAXABLE_VALUE_DIFF)

        if abs(pr.total_tax - b2b.total_tax) > self.TOLERANCE:
            mismatches.append(MismatchType.TAX_AMOUNT_DIFF)

        if pr.reverse_charge != b2b.reverse_charge:
            mismatches.append(MismatchType.REVERSE_CHARGE_DIFF)

        return mismatches

    def _create_mismatch(
        self,
        mismatch_id: str,
        mismatch_type: MismatchType,
        pr_inv: Optional[InvoiceRecord],
        b2b_inv: Optional[InvoiceRecord]
    ) -> Mismatch:
        ref = pr_inv or b2b_inv

        pr_taxable = pr_inv.taxable_value if pr_inv else None
        b2b_taxable = b2b_inv.taxable_value if b2b_inv else None
        pr_tax = pr_inv.total_tax if pr_inv else None
        b2b_tax = b2b_inv.total_tax if b2b_inv else None

        # Tax impact = ITC at risk
        if mismatch_type == MismatchType.INVOICE_NOT_IN_2B:
            tax_impact = -(pr_inv.total_tax)  # ITC cannot be claimed
            action = MismatchAction.CHASE_VENDOR
        elif mismatch_type == MismatchType.INVOICE_NOT_IN_PR:
            tax_impact = b2b_inv.total_tax  # Unclaimed ITC opportunity
            action = MismatchAction.VERIFY_INTERNALLY
        elif mismatch_type == MismatchType.TAX_AMOUNT_DIFF:
            diff = (pr_inv.total_tax if pr_inv else 0) - (b2b_inv.total_tax if b2b_inv else 0)
            tax_impact = diff
            action = MismatchAction.CHASE_VENDOR if diff < 0 else MismatchAction.RECONCILE_BOOKS
        elif mismatch_type == MismatchType.TAXABLE_VALUE_DIFF:
            diff = (pr_inv.taxable_value if pr_inv else 0) - (b2b_inv.taxable_value if b2b_inv else 0)
            tax_impact = diff * 0.18  # Approximate 18% GST impact
            action = MismatchAction.VERIFY_INTERNALLY
        else:
            tax_impact = 0.0
            action = MismatchAction.VERIFY_INTERNALLY

        # Severity based on tax impact
        abs_impact = abs(tax_impact)
        if abs_impact >= 10000:
            severity = MismatchSeverity.HIGH
        elif abs_impact >= 1000:
            severity = MismatchSeverity.MEDIUM
        else:
            severity = MismatchSeverity.LOW

        return Mismatch(
            mismatch_id=mismatch_id,
            mismatch_type=mismatch_type,
            severity=severity,
            supplier_gstin=ref.supplier_gstin,
            supplier_name=ref.supplier_name,
            invoice_number=ref.invoice_number,
            invoice_date=ref.invoice_date,
            pr_taxable_value=pr_taxable,
            b2b_taxable_value=b2b_taxable,
            pr_tax_amount=pr_tax,
            b2b_tax_amount=b2b_tax,
            tax_impact=round(tax_impact, 2),
            recommended_action=action,
            action_deadline=None,
            notes=self._generate_notes(mismatch_type, pr_inv, b2b_inv)
        )

    def _generate_notes(
        self,
        mismatch_type: MismatchType,
        pr_inv: Optional[InvoiceRecord],
        b2b_inv: Optional[InvoiceRecord]
    ) -> str:
        if mismatch_type == MismatchType.INVOICE_NOT_IN_2B:
            return (
                f"Invoice {pr_inv.invoice_number} booked in purchase register "
                f"but supplier {pr_inv.supplier_name} ({pr_inv.supplier_gstin}) "
                f"has not reported it in GSTR-1. ITC of ₹{pr_inv.total_tax:,.2f} at risk."
            )
        elif mismatch_type == MismatchType.INVOICE_NOT_IN_PR:
            return (
                f"Invoice {b2b_inv.invoice_number} from {b2b_inv.supplier_name} "
                f"appears in GSTR-2B but not in purchase register. "
                f"Verify if invoice was received. Potential unclaimed ITC: ₹{b2b_inv.total_tax:,.2f}."
            )
        elif mismatch_type == MismatchType.TAX_AMOUNT_DIFF:
            diff = (pr_inv.total_tax if pr_inv else 0) - (b2b_inv.total_tax if b2b_inv else 0)
            return (
                f"Tax amount differs by ₹{abs(diff):,.2f}. "
                f"PR shows ₹{pr_inv.total_tax:,.2f}, 2B shows ₹{b2b_inv.total_tax:,.2f}. "
                f"Verify with original invoice."
            )
        elif mismatch_type == MismatchType.TAXABLE_VALUE_DIFF:
            diff = (pr_inv.taxable_value if pr_inv else 0) - (b2b_inv.taxable_value if b2b_inv else 0)
            return (
                f"Taxable value differs by ₹{abs(diff):,.2f}. "
                f"PR: ₹{pr_inv.taxable_value:,.2f} vs 2B: ₹{b2b_inv.taxable_value:,.2f}."
            )
        return ""


def load_from_excel(filepath: str, source: str) -> list[dict]:
    """Load invoice data from Excel file."""
    df = pd.read_excel(filepath)
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    return df.to_dict(orient="records")


def load_from_gstr2b_json(filepath: str) -> list[dict]:
    """Parse GSTR-2B JSON format from GST portal."""
    with open(filepath) as f:
        data = json.load(f)

    records = []
    # GSTR-2B structure: data -> docdata -> b2b -> invoices
    b2b_data = (
        data.get("data", {})
            .get("docdata", {})
            .get("b2b", [])
    )

    for supplier in b2b_data:
        supplier_gstin = supplier.get("ctin", "")
        supplier_name = supplier.get("trdnm", "")
        for inv in supplier.get("inv", []):
            for item in inv.get("items", [{}]):
                records.append({
                    "supplier_gstin": supplier_gstin,
                    "supplier_name": supplier_name,
                    "invoice_number": inv.get("inum", ""),
                    "invoice_date": inv.get("idt", ""),
                    "taxable_value": item.get("txval", 0),
                    "igst": item.get("igst", 0),
                    "cgst": item.get("cgst", 0),
                    "sgst": item.get("sgst", 0),
                    "reverse_charge": inv.get("rev", "N") == "Y"
                })

    return records


# ─────────────────────────────────────────────
# Quick test with sample data
# ─────────────────────────────────────────────
if __name__ == "__main__":
    purchase_register = [
        {
            "invoice_number": "INV001",
            "invoice_date": "2025-03-05",
            "supplier_gstin": "27AABCS1429B1Z3",
            "supplier_name": "Sharma Traders",
            "taxable_value": 100000,
            "igst": 18000, "cgst": 0, "sgst": 0,
            "reverse_charge": False
        },
        {
            "invoice_number": "INV002",
            "invoice_date": "2025-03-10",
            "supplier_gstin": "29AABCT1332L1ZV",
            "supplier_name": "Tech Supplies Pvt Ltd",
            "taxable_value": 50000,
            "igst": 0, "cgst": 4500, "sgst": 4500,
            "reverse_charge": False
        },
        {
            "invoice_number": "INV003",
            "invoice_date": "2025-03-15",
            "supplier_gstin": "06AABCU9603R1ZP",
            "supplier_name": "Delhi Distributors",
            "taxable_value": 75000,
            "igst": 13500, "cgst": 0, "sgst": 0,
            "reverse_charge": False
        },
    ]

    gstr_2b = [
        {
            "invoice_number": "INV001",
            "invoice_date": "2025-03-05",
            "supplier_gstin": "27AABCS1429B1Z3",
            "supplier_name": "Sharma Traders",
            "taxable_value": 100000,
            "igst": 18000, "cgst": 0, "sgst": 0,
            "reverse_charge": False
        },
        {
            "invoice_number": "INV002",
            "invoice_date": "2025-03-10",
            "supplier_gstin": "29AABCT1332L1ZV",
            "supplier_name": "Tech Supplies Pvt Ltd",
            "taxable_value": 50000,
            "igst": 0, "cgst": 3500,  # MISMATCH: 3500 vs 4500
            "sgst": 3500,
            "reverse_charge": False
        },
        # INV003 is missing from 2B — vendor hasn't filed
        {
            "invoice_number": "INV004",  # In 2B but not in PR
            "invoice_date": "2025-03-20",
            "supplier_gstin": "09AABCV3530J1Z1",
            "supplier_name": "UP Enterprises",
            "taxable_value": 30000,
            "igst": 5400, "cgst": 0, "sgst": 0,
            "reverse_charge": False
        },
    ]

    engine = GSTReconciliationEngine()
    result = engine.reconcile(
        gstin="27XXXXX1234X1Z5",
        period="032025",
        purchase_register=purchase_register,
        gstr_2b=gstr_2b
    )

    print(f"\n{'='*60}")
    print(f"GST RECONCILIATION RESULT")
    print(f"{'='*60}")
    print(f"Period: {result.period} | GSTIN: {result.gstin}")
    print(f"PR Invoices: {result.total_pr_invoices} | 2B Invoices: {result.total_2b_invoices}")
    print(f"Matched: {result.matched_invoices} | Mismatches: {result.mismatched_invoices}")
    print(f"ITC as per 2B: ₹{result.total_itc_as_per_2b:,.2f}")
    print(f"ITC as per PR: ₹{result.total_itc_as_per_pr:,.2f}")
    print(f"ITC Difference: ₹{result.itc_difference:,.2f}")
    print(f"\nSeverity: HIGH={result.high_severity_count} | MEDIUM={result.medium_severity_count} | LOW={result.low_severity_count}")
    print(f"\nMISMATCHES:")
    for m in result.mismatches:
        print(f"\n  [{m.severity.upper()}] {m.mismatch_id} - {m.mismatch_type.value}")
        print(f"  Supplier: {m.supplier_name} ({m.supplier_gstin})")
        print(f"  Invoice: {m.invoice_number} | Tax Impact: ₹{m.tax_impact:,.2f}")
        print(f"  Action: {m.recommended_action.value}")
        print(f"  Notes: {m.notes}")
