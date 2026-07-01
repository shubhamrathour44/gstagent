"""
GSTR-1 & GSTR-3B XML Generator

Generates official XML for GST returns per Income Tax department schema.

Supports:
- GSTR-1 (Sales/Outward Supplies)
- GSTR-3B (Summary Return with ITC reconciliation)
- Regular & Composite taxpayers
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from typing import Dict, List, Any, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class GSTR1XMLGenerator:
    """Generate GSTR-1 (Sales Return) XML."""

    NAMESPACE = "http://www.incometaxindia.gov.in"

    @staticmethod
    def generate(
        gstin: str,
        period: str,
        company_name: str,
        sales_invoices: List[Dict[str, Any]],
        amendments: bool = False
    ) -> str:
        """
        Generate GSTR-1 XML from sales data.

        Args:
            gstin: 15-digit GSTIN
            period: MMYYYY format (e.g., 032026)
            company_name: Legal name of supplier
            sales_invoices: List of invoice dictionaries
            amendments: True if amended return

        Returns:
            XML string for e-filing
        """
        root = ET.Element("GSTR1")
        root.set("xmlns", GSTR1XMLGenerator.NAMESPACE)
        root.set("gstin", gstin)
        root.set("ret_period", period)
        root.set("version", "2.0")

        # Header
        header = ET.SubElement(root, "Header")
        ET.SubElement(header, "GSTIN").text = gstin
        ET.SubElement(header, "Period").text = period
        ET.SubElement(header, "CompanyName").text = company_name
        ET.SubElement(header, "Status").text = "A" if amendments else "N"  # A=Amended, N=Normal
        ET.SubElement(header, "FilingDate").text = datetime.utcnow().strftime("%d/%m/%Y")

        # B2B (Business to Business) Invoices - HSN-wise
        b2b_element = ET.SubElement(root, "B2B")
        _add_b2b_invoices(b2b_element, sales_invoices)

        # B2C (Business to Consumer) - Over 1L
        b2c_element = ET.SubElement(root, "B2C_Large")
        _add_b2c_invoices(b2c_element, sales_invoices)

        # Exports
        export_element = ET.SubElement(root, "Exports")
        _add_export_invoices(export_element, sales_invoices)

        # HSN Summary (aggregated by HSN)
        hsn_element = ET.SubElement(root, "HSNSummary")
        _add_hsn_summary(hsn_element, sales_invoices)

        # NIL Supplies
        nil_element = ET.SubElement(root, "NilSupplies")
        ET.SubElement(nil_element, "TaxableAmount").text = "0.00"
        ET.SubElement(nil_element, "ExemptAmount").text = "0.00"
        ET.SubElement(nil_element, "NonGSTAmount").text = "0.00"

        # Amendments (if any)
        if amendments:
            amend_element = ET.SubElement(root, "Amendments")
            ET.SubElement(amend_element, "AmendmentCount").text = "1"

        return _prettify_xml(root)


class GSTR3BXMLGenerator:
    """Generate GSTR-3B (Summary Return with ITC) XML."""

    NAMESPACE = "http://www.incometaxindia.gov.in"

    @staticmethod
    def generate(
        gstin: str,
        period: str,
        company_name: str,
        gstr1_data: Dict[str, Any],
        gstr2b_data: Dict[str, Any],
        itc_data: Dict[str, Any],
        payment_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate GSTR-3B XML (Summary Return).

        Args:
            gstin: 15-digit GSTIN
            period: MMYYYY format
            company_name: Company legal name
            gstr1_data: GSTR-1 summary data (supplies)
            gstr2b_data: GSTR-2B data (purchases, reconciled)
            itc_data: ITC eligibility details
            payment_data: Tax payment details

        Returns:
            XML string for e-filing
        """
        root = ET.Element("GSTR3B")
        root.set("xmlns", GSTR3BXMLGenerator.NAMESPACE)
        root.set("gstin", gstin)
        root.set("ret_period", period)
        root.set("version", "2.0")

        # Header
        header = ET.SubElement(root, "Header")
        ET.SubElement(header, "GSTIN").text = gstin
        ET.SubElement(header, "Period").text = period
        ET.SubElement(header, "CompanyName").text = company_name
        ET.SubElement(header, "FilingDate").text = datetime.utcnow().strftime("%d/%m/%Y")

        # Part A: Outward Supplies (from GSTR-1)
        outward = ET.SubElement(root, "OutwardSupplies")
        _add_outward_supplies(outward, gstr1_data)

        # Part B: ITC (from GSTR-2B)
        itc = ET.SubElement(root, "ITCClaim")
        _add_itc_details(itc, gstr2b_data, itc_data)

        # Part C: Tax Computation
        tax = ET.SubElement(root, "TaxComputation")
        _add_tax_computation(tax, gstr1_data, gstr2b_data, itc_data)

        # Part D: Tax Payment
        if payment_data:
            payment = ET.SubElement(root, "Payment")
            _add_payment_details(payment, payment_data)

        # Declarations
        declaration = ET.SubElement(root, "Declaration")
        ET.SubElement(declaration, "Declarant").text = "Legal Representative"
        ET.SubElement(declaration, "DeclarationDate").text = datetime.utcnow().strftime("%d/%m/%Y")

        return _prettify_xml(root)


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _add_b2b_invoices(parent: ET.Element, invoices: List[Dict[str, Any]]) -> None:
    """Add B2B (HSN-wise) invoices to GSTR-1."""
    # Group by HSN
    hsn_groups: Dict[str, List[Dict]] = {}
    for inv in invoices:
        if inv.get("invoice_type") == "B2B":
            hsn = inv.get("hsn_code", "999999")
            if hsn not in hsn_groups:
                hsn_groups[hsn] = []
            hsn_groups[hsn].append(inv)

    # Add grouped invoices
    for hsn, group_invoices in hsn_groups.items():
        hsn_elem = ET.SubElement(parent, "HSNWise")
        ET.SubElement(hsn_elem, "HSNCode").text = hsn

        for inv in group_invoices:
            inv_elem = ET.SubElement(hsn_elem, "Invoice")
            ET.SubElement(inv_elem, "InvoiceNo").text = str(inv.get("invoice_number", ""))
            ET.SubElement(inv_elem, "InvoiceDate").text = str(inv.get("invoice_date", ""))
            ET.SubElement(inv_elem, "RecipientGSTIN").text = inv.get("recipient_gstin", "")
            ET.SubElement(inv_elem, "RecipientName").text = inv.get("recipient_name", "")
            ET.SubElement(inv_elem, "InvoiceValue").text = f"{float(inv.get('total_value', 0)):.2f}"
            ET.SubElement(inv_elem, "PlaceOfSupply").text = inv.get("place_of_supply", "")
            ET.SubElement(inv_elem, "TaxableValue").text = f"{float(inv.get('taxable_value', 0)):.2f}"
            ET.SubElement(inv_elem, "CGST").text = f"{float(inv.get('cgst', 0)):.2f}"
            ET.SubElement(inv_elem, "SGST").text = f"{float(inv.get('sgst', 0)):.2f}"
            ET.SubElement(inv_elem, "IGST").text = f"{float(inv.get('igst', 0)):.2f}"
            ET.SubElement(inv_elem, "CESS").text = f"{float(inv.get('cess', 0)):.2f}"


def _add_b2c_invoices(parent: ET.Element, invoices: List[Dict[str, Any]]) -> None:
    """Add B2C (over 1L) invoices to GSTR-1."""
    b2c_invoices = [inv for inv in invoices if inv.get("invoice_type") == "B2C" and float(inv.get("total_value", 0)) > 100000]

    total_taxable = sum(float(inv.get("taxable_value", 0)) for inv in b2c_invoices)
    total_cgst = sum(float(inv.get("cgst", 0)) for inv in b2c_invoices)
    total_sgst = sum(float(inv.get("sgst", 0)) for inv in b2c_invoices)
    total_igst = sum(float(inv.get("igst", 0)) for inv in b2c_invoices)

    ET.SubElement(parent, "TaxableAmount").text = f"{total_taxable:.2f}"
    ET.SubElement(parent, "CGST").text = f"{total_cgst:.2f}"
    ET.SubElement(parent, "SGST").text = f"{total_sgst:.2f}"
    ET.SubElement(parent, "IGST").text = f"{total_igst:.2f}"


def _add_export_invoices(parent: ET.Element, invoices: List[Dict[str, Any]]) -> None:
    """Add export invoices to GSTR-1."""
    export_invoices = [inv for inv in invoices if inv.get("invoice_type") == "Export"]

    total_value = sum(float(inv.get("total_value", 0)) for inv in export_invoices)
    ET.SubElement(parent, "TotalExportValue").text = f"{total_value:.2f}"
    ET.SubElement(parent, "SGSTFlag").text = "Y" if total_value > 0 else "N"


def _add_hsn_summary(parent: ET.Element, invoices: List[Dict[str, Any]]) -> None:
    """Add HSN-wise summary (aggregated)."""
    hsn_summary: Dict[str, Dict[str, float]] = {}

    for inv in invoices:
        if inv.get("invoice_type") in ["B2B", "B2C", "Export"]:
            hsn = inv.get("hsn_code", "999999")
            if hsn not in hsn_summary:
                hsn_summary[hsn] = {
                    "quantity": 0,
                    "taxable": 0,
                    "cgst": 0,
                    "sgst": 0,
                    "igst": 0
                }
            hsn_summary[hsn]["quantity"] += float(inv.get("quantity", 0))
            hsn_summary[hsn]["taxable"] += float(inv.get("taxable_value", 0))
            hsn_summary[hsn]["cgst"] += float(inv.get("cgst", 0))
            hsn_summary[hsn]["sgst"] += float(inv.get("sgst", 0))
            hsn_summary[hsn]["igst"] += float(inv.get("igst", 0))

    for hsn, data in hsn_summary.items():
        hsn_elem = ET.SubElement(parent, "HSNEntry")
        ET.SubElement(hsn_elem, "HSNCode").text = hsn
        ET.SubElement(hsn_elem, "Quantity").text = f"{data['quantity']:.0f}"
        ET.SubElement(hsn_elem, "TaxableAmount").text = f"{data['taxable']:.2f}"
        ET.SubElement(hsn_elem, "CGST").text = f"{data['cgst']:.2f}"
        ET.SubElement(hsn_elem, "SGST").text = f"{data['sgst']:.2f}"
        ET.SubElement(hsn_elem, "IGST").text = f"{data['igst']:.2f}"


def _add_outward_supplies(parent: ET.Element, gstr1_data: Dict[str, Any]) -> None:
    """Add outward supplies from GSTR-1 to GSTR-3B."""
    supplies = ET.SubElement(parent, "Supplies")

    # Taxable supplies
    taxable = ET.SubElement(supplies, "Taxable")
    ET.SubElement(taxable, "CGST").text = f"{float(gstr1_data.get('total_cgst', 0)):.2f}"
    ET.SubElement(taxable, "SGST").text = f"{float(gstr1_data.get('total_sgst', 0)):.2f}"
    ET.SubElement(taxable, "IGST").text = f"{float(gstr1_data.get('total_igst', 0)):.2f}"

    # Exempt supplies
    exempt = ET.SubElement(supplies, "Exempt")
    ET.SubElement(exempt, "Value").text = f"{float(gstr1_data.get('exempt_value', 0)):.2f}"

    # Nil-rated supplies
    nil = ET.SubElement(supplies, "Nil")
    ET.SubElement(nil, "Value").text = f"{float(gstr1_data.get('nil_value', 0)):.2f}"


def _add_itc_details(parent: ET.Element, gstr2b_data: Dict[str, Any], itc_data: Dict[str, Any]) -> None:
    """Add ITC claim details from GSTR-2B."""
    itc_claim = ET.SubElement(parent, "Claim")

    # ITC on inputs
    inputs = ET.SubElement(itc_claim, "Inputs")
    ET.SubElement(inputs, "CGST").text = f"{float(gstr2b_data.get('total_cgst', 0)):.2f}"
    ET.SubElement(inputs, "SGST").text = f"{float(gstr2b_data.get('total_sgst', 0)):.2f}"
    ET.SubElement(inputs, "IGST").text = f"{float(gstr2b_data.get('total_igst', 0)):.2f}"

    # Ineligible ITC (reverse charges, personal consumption, etc.)
    ineligible = ET.SubElement(itc_claim, "Ineligible")
    ET.SubElement(ineligible, "ReverseCharge").text = f"{float(itc_data.get('reverse_charge_itc', 0)):.2f}"
    ET.SubElement(ineligible, "NonGST").text = f"{float(itc_data.get('non_gst_itc', 0)):.2f}"
    ET.SubElement(ineligible, "Blocked").text = f"{float(itc_data.get('blocked_itc', 0)):.2f}"


def _add_tax_computation(parent: ET.Element, gstr1_data: Dict[str, Any], gstr2b_data: Dict[str, Any], itc_data: Dict[str, Any]) -> None:
    """Add tax computation (tax payable/refund)."""
    output_tax = (
        float(gstr1_data.get("total_cgst", 0)) +
        float(gstr1_data.get("total_sgst", 0)) +
        float(gstr1_data.get("total_igst", 0))
    )

    input_tax = (
        float(gstr2b_data.get("total_cgst", 0)) +
        float(gstr2b_data.get("total_sgst", 0)) +
        float(gstr2b_data.get("total_igst", 0)) -
        float(itc_data.get("ineligible_itc", 0))
    )

    tax_payable = max(0, output_tax - input_tax)
    refund = max(0, input_tax - output_tax)

    ET.SubElement(parent, "OutputTax").text = f"{output_tax:.2f}"
    ET.SubElement(parent, "ITCClaimed").text = f"{input_tax:.2f}"
    ET.SubElement(parent, "TaxPayable").text = f"{tax_payable:.2f}"
    ET.SubElement(parent, "Refund").text = f"{refund:.2f}"


def _add_payment_details(parent: ET.Element, payment_data: Dict[str, Any]) -> None:
    """Add tax payment details."""
    payment_method = ET.SubElement(parent, "Method")
    ET.SubElement(payment_method, "ChallanNo").text = payment_data.get("challan_no", "")
    ET.SubElement(payment_method, "ChallanDate").text = payment_data.get("challan_date", "")
    ET.SubElement(payment_method, "Amount").text = f"{float(payment_data.get('amount', 0)):.2f}"


def _prettify_xml(elem: ET.Element) -> str:
    """Return prettified XML string."""
    rough_string = ET.tostring(elem, encoding='utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")
