"""
Sales Register Reconciliation Engine

Compares Sales Register (SR) vs GSTR-1 data.
Detects mismatches and calculates financial impact.

Complements purchase reconciliation (PR vs GSTR-2B).
"""

import json
import pandas as pd
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum
from datetime import datetime


class SalesMismatchType(str, Enum):
    """Types of sales mismatches."""
    INVOICE_NOT_IN_GSTR1 = "Invoice in SR but missing in GSTR-1"
    INVOICE_NOT_IN_SR = "Invoice in GSTR-1 but missing in SR"
    CUSTOMER_GSTIN_MISMATCH = "Customer GSTIN mismatch"
    TAXABLE_VALUE_DIFF = "Taxable value mismatch"
    TAX_AMOUNT_DIFF = "Tax amount mismatch"
    INVOICE_DATE_DIFF = "Invoice date mismatch"
    SUPPLY_TYPE_DIFF = "Supply type mismatch (B2B/B2C/Export)"


class SalesMismatchSeverity(str, Enum):
    """Severity classification based on tax impact."""
    HIGH = "high"        # Tax impact > ₹10,000 or revenue mismatch > ₹100,000
    MEDIUM = "medium"    # Tax impact ₹1,000 - ₹10,000 or revenue ₹10,000 - ₹100,000
    LOW = "low"          # Tax impact < ₹1,000


class SalesMismatchAction(str, Enum):
    """Recommended actions."""
    VERIFY_INVOICE = "Verify invoice in SR and correct"
    CHASE_CUSTOMER = "Chase customer to file/amend GSTR-1"
    REVERSE_SALE = "Reverse sale if unintended"
    RECONCILE_BOOKS = "Reconcile in books of accounts"
    CHECK_GSTR1 = "Check if invoice included in GSTR-1 return"
    NO_ACTION = "No action required"


@dataclass
class SalesInvoiceRecord:
    """Sales invoice record."""
    invoice_number: str
    invoice_date: str
    customer_gstin: str
    customer_name: str
    taxable_value: float
    cgst: float = 0.0
    sgst: float = 0.0
    igst: float = 0.0
    cess: float = 0.0
    supply_type: str = "B2B"  # B2B, B2C, Export
    reverse_charge: bool = False
    source: str = ""  # "SR" or "GSTR1"

    @property
    def total_tax(self):
        return self.cgst + self.sgst + self.igst + self.cess

    @property
    def total_value(self):
        return self.taxable_value + self.total_tax


@dataclass
class SalesMismatch:
    """Detected sales mismatch."""
    mismatch_id: str
    mismatch_type: SalesMismatchType
    severity: SalesMismatchSeverity
    customer_gstin: str
    customer_name: str
    invoice_number: str
    invoice_date: str
    sr_taxable_value: Optional[float]
    gstr1_taxable_value: Optional[float]
    sr_tax_amount: Optional[float]
    gstr1_tax_amount: Optional[float]
    financial_impact: float  # Revenue impact (positive = SR has more, negative = GSTR1 has more)
    tax_impact: float  # Tax impact
    recommended_action: SalesMismatchAction
    notes: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class SalesReconciliationResult:
    """Sales reconciliation result."""
    gstin: str
    period: str
    reconciled_at: str
    total_sr_invoices: int
    total_gstr1_invoices: int
    matched_invoices: int
    mismatched_invoices: int
    missing_in_gstr1: int
    missing_in_sr: int
    total_sr_revenue: float
    total_gstr1_revenue: float
    revenue_difference: float
    total_sr_tax: float
    total_gstr1_tax: float
    tax_difference: float
    high_severity_count: int
    medium_severity_count: int
    low_severity_count: int
    mismatches: list[SalesMismatch] = field(default_factory=list)
    summary_stats: dict = field(default_factory=dict)

    def to_dict(self):
        result = asdict(self)
        result["mismatches"] = [m.to_dict() for m in self.mismatches]
        return result


class SalesReconciliationEngine:
    """
    Core sales reconciliation engine.
    Compares Sales Register (SR) with GSTR-1 data.
    """

    TOLERANCE = 1.0  # ₹1 tolerance for floating point differences

    def reconcile(
        self,
        gstin: str,
        period: str,
        sales_register: list[dict],
        gstr1_invoices: list[dict]
    ) -> SalesReconciliationResult:
        """
        Main reconciliation function.
        Returns a SalesReconciliationResult with all mismatches.
        """
        sr_invoices = self._parse_records(sales_register, source="SR")
        gstr1_inv_list = self._parse_records(gstr1_invoices, source="GSTR1")

        # Build lookup maps
        sr_map = self._build_invoice_map(sr_invoices)
        gstr1_map = self._build_invoice_map(gstr1_inv_list)

        mismatches = []
        matched = 0
        mismatch_counter = 0

        # Check SR invoices against GSTR-1
        for key, sr_inv in sr_map.items():
            if key not in gstr1_map:
                mismatch_counter += 1
                m = self._create_mismatch(
                    mismatch_id=f"SM{mismatch_counter:04d}",
                    mismatch_type=SalesMismatchType.INVOICE_NOT_IN_GSTR1,
                    sr_inv=sr_inv,
                    gstr1_inv=None
                )
                mismatches.append(m)
            else:
                gstr1_inv = gstr1_map[key]
                field_mismatches = self._compare_invoices(sr_inv, gstr1_inv)
                if field_mismatches:
                    for mt in field_mismatches:
                        mismatch_counter += 1
                        m = self._create_mismatch(
                            mismatch_id=f"SM{mismatch_counter:04d}",
                            mismatch_type=mt,
                            sr_inv=sr_inv,
                            gstr1_inv=gstr1_inv
                        )
                        mismatches.append(m)
                else:
                    matched += 1

        # Check GSTR-1 invoices missing in SR
        for key, gstr1_inv in gstr1_map.items():
            if key not in sr_map:
                mismatch_counter += 1
                m = self._create_mismatch(
                    mismatch_id=f"SM{mismatch_counter:04d}",
                    mismatch_type=SalesMismatchType.INVOICE_NOT_IN_SR,
                    sr_inv=None,
                    gstr1_inv=gstr1_inv
                )
                mismatches.append(m)

        # Compute totals
        total_sr_revenue = sum(inv.total_value for inv in sr_invoices)
        total_gstr1_revenue = sum(inv.total_value for inv in gstr1_inv_list)
        total_sr_tax = sum(inv.total_tax for inv in sr_invoices)
        total_gstr1_tax = sum(inv.total_tax for inv in gstr1_inv_list)

        high = sum(1 for m in mismatches if m.severity == SalesMismatchSeverity.HIGH)
        medium = sum(1 for m in mismatches if m.severity == SalesMismatchSeverity.MEDIUM)
        low = sum(1 for m in mismatches if m.severity == SalesMismatchSeverity.LOW)

        missing_in_gstr1 = sum(
            1 for m in mismatches
            if m.mismatch_type == SalesMismatchType.INVOICE_NOT_IN_GSTR1
        )
        missing_in_sr = sum(
            1 for m in mismatches
            if m.mismatch_type == SalesMismatchType.INVOICE_NOT_IN_SR
        )

        # Customer-wise summary
        customer_summary = {}
        for m in mismatches:
            gstin_key = m.customer_gstin
            if gstin_key not in customer_summary:
                customer_summary[gstin_key] = {
                    "name": m.customer_name,
                    "gstin": gstin_key,
                    "mismatch_count": 0,
                    "financial_impact": 0.0,
                    "tax_impact": 0.0
                }
            customer_summary[gstin_key]["mismatch_count"] += 1
            customer_summary[gstin_key]["financial_impact"] += abs(m.financial_impact)
            customer_summary[gstin_key]["tax_impact"] += abs(m.tax_impact)

        return SalesReconciliationResult(
            gstin=gstin,
            period=period,
            reconciled_at=datetime.now().isoformat(),
            total_sr_invoices=len(sr_invoices),
            total_gstr1_invoices=len(gstr1_inv_list),
            matched_invoices=matched,
            mismatched_invoices=len(mismatches),
            missing_in_gstr1=missing_in_gstr1,
            missing_in_sr=missing_in_sr,
            total_sr_revenue=round(total_sr_revenue, 2),
            total_gstr1_revenue=round(total_gstr1_revenue, 2),
            revenue_difference=round(total_sr_revenue - total_gstr1_revenue, 2),
            total_sr_tax=round(total_sr_tax, 2),
            total_gstr1_tax=round(total_gstr1_tax, 2),
            tax_difference=round(total_sr_tax - total_gstr1_tax, 2),
            high_severity_count=high,
            medium_severity_count=medium,
            low_severity_count=low,
            mismatches=mismatches,
            summary_stats={
                "customer_wise": list(customer_summary.values()),
                "match_rate": round(matched / max(len(sr_invoices), 1) * 100, 1)
            }
        )

    def _parse_records(self, records: list[dict], source: str) -> list[SalesInvoiceRecord]:
        """Parse records into SalesInvoiceRecord objects."""
        parsed = []
        for r in records:
            try:
                cgst = float(r.get("cgst", 0) or 0)
                sgst = float(r.get("sgst", 0) or 0)
                igst = float(r.get("igst", 0) or 0)
                cess = float(r.get("cess", 0) or 0)

                inv = SalesInvoiceRecord(
                    invoice_number=str(r.get("invoice_number", "")).strip().upper(),
                    invoice_date=str(r.get("invoice_date", "")).strip(),
                    customer_gstin=str(r.get("customer_gstin", "")).strip().upper(),
                    customer_name=str(r.get("customer_name", "Unknown")).strip(),
                    taxable_value=float(r.get("taxable_value", 0) or 0),
                    cgst=cgst,
                    sgst=sgst,
                    igst=igst,
                    cess=cess,
                    supply_type=str(r.get("supply_type", "B2B")).strip(),
                    reverse_charge=bool(r.get("reverse_charge", False)),
                    source=source
                )
                parsed.append(inv)
            except Exception as e:
                print(f"Warning: Could not parse record {r}: {e}")
        return parsed

    def _build_invoice_map(self, invoices: list[SalesInvoiceRecord]) -> dict:
        """Key: (customer_gstin, invoice_number)"""
        return {
            (inv.customer_gstin, inv.invoice_number): inv
            for inv in invoices
        }

    def _compare_invoices(
        self,
        sr: SalesInvoiceRecord,
        gstr1: SalesInvoiceRecord
    ) -> list[SalesMismatchType]:
        """Compare two invoices and return list of mismatches."""
        mismatches = []

        if abs(sr.taxable_value - gstr1.taxable_value) > self.TOLERANCE:
            mismatches.append(SalesMismatchType.TAXABLE_VALUE_DIFF)

        if abs(sr.total_tax - gstr1.total_tax) > self.TOLERANCE:
            mismatches.append(SalesMismatchType.TAX_AMOUNT_DIFF)

        if sr.supply_type != gstr1.supply_type:
            mismatches.append(SalesMismatchType.SUPPLY_TYPE_DIFF)

        return mismatches

    def _create_mismatch(
        self,
        mismatch_id: str,
        mismatch_type: SalesMismatchType,
        sr_inv: Optional[SalesInvoiceRecord],
        gstr1_inv: Optional[SalesInvoiceRecord]
    ) -> SalesMismatch:
        """Create a mismatch record."""
        ref = sr_inv or gstr1_inv

        sr_taxable = sr_inv.taxable_value if sr_inv else None
        gstr1_taxable = gstr1_inv.taxable_value if gstr1_inv else None
        sr_tax = sr_inv.total_tax if sr_inv else None
        gstr1_tax = gstr1_inv.total_tax if gstr1_inv else None

        # Financial impact = Revenue difference (SR value - GSTR1 value)
        if mismatch_type == SalesMismatchType.INVOICE_NOT_IN_GSTR1:
            financial_impact = sr_inv.total_value if sr_inv else 0
            tax_impact = sr_inv.total_tax if sr_inv else 0
            action = SalesMismatchAction.CHASE_CUSTOMER
        elif mismatch_type == SalesMismatchType.INVOICE_NOT_IN_SR:
            financial_impact = -(gstr1_inv.total_value if gstr1_inv else 0)
            tax_impact = gstr1_inv.total_tax if gstr1_inv else 0
            action = SalesMismatchAction.VERIFY_INVOICE
        elif mismatch_type == SalesMismatchType.TAXABLE_VALUE_DIFF:
            diff = (sr_inv.taxable_value if sr_inv else 0) - (gstr1_inv.taxable_value if gstr1_inv else 0)
            financial_impact = diff
            tax_impact = diff * 0.18  # Approximate tax impact
            action = SalesMismatchAction.RECONCILE_BOOKS
        elif mismatch_type == SalesMismatchType.TAX_AMOUNT_DIFF:
            diff = (sr_inv.total_tax if sr_inv else 0) - (gstr1_inv.total_tax if gstr1_inv else 0)
            financial_impact = diff
            tax_impact = diff
            action = SalesMismatchAction.CHECK_GSTR1
        else:
            financial_impact = 0.0
            tax_impact = 0.0
            action = SalesMismatchAction.VERIFY_INVOICE

        # Severity based on financial/tax impact
        abs_fin_impact = abs(financial_impact)
        abs_tax_impact = abs(tax_impact)

        if abs_fin_impact > 100000 or abs_tax_impact >= 10000:
            severity = SalesMismatchSeverity.HIGH
        elif abs_fin_impact > 10000 or abs_tax_impact >= 1000:
            severity = SalesMismatchSeverity.MEDIUM
        else:
            severity = SalesMismatchSeverity.LOW

        return SalesMismatch(
            mismatch_id=mismatch_id,
            mismatch_type=mismatch_type,
            severity=severity,
            customer_gstin=ref.customer_gstin,
            customer_name=ref.customer_name,
            invoice_number=ref.invoice_number,
            invoice_date=ref.invoice_date,
            sr_taxable_value=sr_taxable,
            gstr1_taxable_value=gstr1_taxable,
            sr_tax_amount=sr_tax,
            gstr1_tax_amount=gstr1_tax,
            financial_impact=round(financial_impact, 2),
            tax_impact=round(tax_impact, 2),
            recommended_action=action,
            notes=self._generate_notes(mismatch_type, sr_inv, gstr1_inv)
        )

    def _generate_notes(
        self,
        mismatch_type: SalesMismatchType,
        sr_inv: Optional[SalesInvoiceRecord],
        gstr1_inv: Optional[SalesInvoiceRecord]
    ) -> str:
        """Generate explanation for mismatch."""
        if mismatch_type == SalesMismatchType.INVOICE_NOT_IN_GSTR1:
            return "Invoice recorded in SR but not found in GSTR-1. Customer may not have reported sale or filed amended return."
        elif mismatch_type == SalesMismatchType.INVOICE_NOT_IN_SR:
            return "Invoice reported in GSTR-1 but not found in SR. May be entry error or invoice recorded in different period."
        elif mismatch_type == SalesMismatchType.TAXABLE_VALUE_DIFF:
            sr_val = sr_inv.taxable_value if sr_inv else 0
            g1_val = gstr1_inv.taxable_value if gstr1_inv else 0
            return f"Revenue mismatch: SR={sr_val:.2f}, GSTR-1={g1_val:.2f}. Likely billing/discount discrepancy."
        elif mismatch_type == SalesMismatchType.TAX_AMOUNT_DIFF:
            sr_tax = sr_inv.total_tax if sr_inv else 0
            g1_tax = gstr1_inv.total_tax if gstr1_inv else 0
            return f"Tax mismatch: SR={sr_tax:.2f}, GSTR-1={g1_tax:.2f}. Check tax rate application."
        elif mismatch_type == SalesMismatchType.SUPPLY_TYPE_DIFF:
            sr_type = sr_inv.supply_type if sr_inv else "N/A"
            g1_type = gstr1_inv.supply_type if gstr1_inv else "N/A"
            return f"Supply type differs: SR={sr_type}, GSTR-1={g1_type}. Verify correct classification."
        return "Mismatch detected between SR and GSTR-1."
