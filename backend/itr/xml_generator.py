"""
ITR XML Generator - Generate XML for income tax e-filing portal.

Supports: ITR-1, ITR-2, ITR-3, ITR-4, ITR-7
Format: As per Income Tax Department XML schema
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class ITRXMLGenerator:
    """Generate ITR XML for e-filing submission."""

    NAMESPACE = "http://www.incometaxindia.gov.in"

    @staticmethod
    def generate_itr1(
        pan: str,
        name: str,
        dob: str,
        ay: str,
        income_data: Dict[str, Any],
        signature_value: str = ""
    ) -> str:
        """
        Generate ITR-1 XML.

        Args:
            pan: PAN (10 chars)
            name: Taxpayer name
            dob: Date of birth (DDMMYYYY)
            ay: Assessment year (e.g., 2023-24)
            income_data: Income details dict
            signature_value: Digital signature (if verified)

        Returns:
            XML string ready for e-filing
        """
        root = ET.Element("ITRDocument")
        root.set("xmlns", ITRXMLGenerator.NAMESPACE)
        root.set("DocumentType", "ITR1")

        # Taxable Entity Details
        entity = ET.SubElement(root, "TaxableEntity")
        ET.SubElement(entity, "PAN").text = pan
        ET.SubElement(entity, "Name").text = name
        ET.SubElement(entity, "DOB").text = dob

        # ITR Form
        form = ET.SubElement(root, "ITRForm")
        form.set("FormName", "ITR-1")
        form.set("AY", ay)

        # Income Details
        income_elem = ET.SubElement(form, "IncomeDetails")
        _add_income_element(income_elem, "SalaryIncome", income_data.get("salary_income", 0))
        _add_income_element(income_elem, "HRAExemption", income_data.get("hra_exemption", 0))
        _add_income_element(income_elem, "StandardDeduction", income_data.get("standard_deduction", 50000))
        _add_income_element(income_elem, "IncomeFromHouseProperty", income_data.get("income_from_house_property", 0))
        _add_income_element(income_elem, "InterestIncome", income_data.get("interest_income", 0))
        _add_income_element(income_elem, "OtherIncome", income_data.get("other_income", 0))

        gross_income = (
            income_data.get("salary_income", 0) - income_data.get("hra_exemption", 0) +
            income_data.get("income_from_house_property", 0) +
            income_data.get("interest_income", 0) +
            income_data.get("other_income", 0)
        )
        _add_income_element(income_elem, "GrossTotalIncome", gross_income)

        # Deductions
        deduction_elem = ET.SubElement(form, "Deductions")
        _add_income_element(deduction_elem, "Section80C", income_data.get("sec_80c", 0))
        _add_income_element(deduction_elem, "Section80D", income_data.get("sec_80d", 0))
        _add_income_element(deduction_elem, "Section80E", income_data.get("sec_80e", 0))
        _add_income_element(deduction_elem, "Section80G", income_data.get("sec_80g", 0))
        _add_income_element(deduction_elem, "Section80TTA", income_data.get("sec_80tta", 0))

        total_deductions = (
            income_data.get("sec_80c", 0) +
            income_data.get("sec_80d", 0) +
            income_data.get("sec_80e", 0) +
            income_data.get("sec_80g", 0) +
            income_data.get("sec_80tta", 0)
        )
        _add_income_element(deduction_elem, "TotalDeductions", total_deductions)

        # Tax Computation
        tax_elem = ET.SubElement(form, "TaxComputation")
        _add_income_element(tax_elem, "TaxableIncome", gross_income - total_deductions)
        _add_income_element(tax_elem, "IncomeTax", income_data.get("income_tax", 0))
        _add_income_element(tax_elem, "Surcharge", income_data.get("surcharge", 0))
        _add_income_element(tax_elem, "Cess", income_data.get("cess", 0))

        total_tax = (
            income_data.get("income_tax", 0) +
            income_data.get("surcharge", 0) +
            income_data.get("cess", 0)
        )
        _add_income_element(tax_elem, "TotalTax", total_tax)

        # Tax Paid
        paid_elem = ET.SubElement(form, "TaxPaid")
        _add_income_element(paid_elem, "TDSEmployer", income_data.get("tds_employer", 0))
        _add_income_element(paid_elem, "TDSBank", income_data.get("tds_bank", 0))
        _add_income_element(paid_elem, "TDSOther", income_data.get("tds_other", 0))
        _add_income_element(paid_elem, "AdvanceTax", income_data.get("advance_tax", 0))

        total_paid = (
            income_data.get("tds_employer", 0) +
            income_data.get("tds_bank", 0) +
            income_data.get("tds_other", 0) +
            income_data.get("advance_tax", 0)
        )
        _add_income_element(paid_elem, "TotalTaxPaid", total_paid)

        # Refund/Payable
        refund_payable = total_paid - total_tax
        if refund_payable > 0:
            _add_income_element(form, "RefundAmount", refund_payable)
        else:
            _add_income_element(form, "TaxPayable", abs(refund_payable))

        # Verification (if signature provided)
        if signature_value:
            verification = ET.SubElement(form, "Verification")
            ET.SubElement(verification, "DigitalSignature").text = signature_value
            ET.SubElement(verification, "SignatureDate").text = datetime.utcnow().strftime("%d/%m/%Y")

        return _prettify_xml(root)

    @staticmethod
    def generate_itr2(
        pan: str,
        name: str,
        dob: str,
        age: int,
        ay: str,
        income_data: Dict[str, Any],
        signature_value: str = ""
    ) -> str:
        """Generate ITR-2 XML (Salary + Investments + Capital Gains)."""
        root = ET.Element("ITRDocument")
        root.set("xmlns", ITRXMLGenerator.NAMESPACE)
        root.set("DocumentType", "ITR2")

        # Taxable Entity
        entity = ET.SubElement(root, "TaxableEntity")
        ET.SubElement(entity, "PAN").text = pan
        ET.SubElement(entity, "Name").text = name
        ET.SubElement(entity, "DOB").text = dob
        ET.SubElement(entity, "Age").text = str(age)

        # ITR Form
        form = ET.SubElement(root, "ITRForm")
        form.set("FormName", "ITR-2")
        form.set("AY", ay)

        # Income Details
        income_elem = ET.SubElement(form, "IncomeDetails")

        # Salary
        salary = ET.SubElement(income_elem, "Salary")
        _add_income_element(salary, "SalaryIncome", income_data.get("salary_income", 0))
        _add_income_element(salary, "HRAExemption", income_data.get("hra_exemption", 0))
        _add_income_element(salary, "StandardDeduction", income_data.get("standard_deduction", 50000))

        # House Property
        house = ET.SubElement(income_elem, "HouseProperty")
        _add_income_element(house, "AnnualRentalValue", income_data.get("annual_rental_value", 0))
        _add_income_element(house, "LoanInterest", income_data.get("self_occupied_loan_interest", 0))
        _add_income_element(house, "IncomeFromHouseProperty", income_data.get("house_property_income", 0))

        # Capital Gains
        gains = ET.SubElement(income_elem, "CapitalGains")
        _add_income_element(gains, "STCG111A", income_data.get("stcg_111a", 0))
        _add_income_element(gains, "STCGOther", income_data.get("stcg_other", 0))
        _add_income_element(gains, "LTCG112A", income_data.get("ltcg_112a", 0))
        _add_income_element(gains, "LTCGOther", income_data.get("ltcg_other", 0))

        # Other Income
        other = ET.SubElement(income_elem, "OtherIncome")
        _add_income_element(other, "InterestIncome", income_data.get("interest_income", 0))
        _add_income_element(other, "DividendIncome", income_data.get("dividend_income", 0))
        _add_income_element(other, "OtherIncome", income_data.get("other_income", 0))

        # Gross Total Income
        gross_income = (
            income_data.get("salary_income", 0) - income_data.get("hra_exemption", 0) +
            income_data.get("house_property_income", 0) +
            income_data.get("stcg_111a", 0) + income_data.get("stcg_other", 0) +
            income_data.get("ltcg_112a", 0) + income_data.get("ltcg_other", 0) +
            income_data.get("interest_income", 0) + income_data.get("dividend_income", 0) +
            income_data.get("other_income", 0)
        )
        _add_income_element(income_elem, "GrossTotalIncome", gross_income)

        # Deductions
        deduction_elem = ET.SubElement(form, "Deductions")
        _add_income_element(deduction_elem, "Section80C", income_data.get("sec_80c", 0))
        _add_income_element(deduction_elem, "Section80D", income_data.get("sec_80d", 0))
        _add_income_element(deduction_elem, "Section80E", income_data.get("sec_80e", 0))
        _add_income_element(deduction_elem, "Section80G", income_data.get("sec_80g", 0))
        _add_income_element(deduction_elem, "Section80TTA", income_data.get("sec_80tta", 0))
        _add_income_element(deduction_elem, "Section80TTB", income_data.get("sec_80ttb", 0))

        total_deductions = (
            income_data.get("sec_80c", 0) + income_data.get("sec_80d", 0) +
            income_data.get("sec_80e", 0) + income_data.get("sec_80g", 0) +
            income_data.get("sec_80tta", 0) + income_data.get("sec_80ttb", 0)
        )
        _add_income_element(deduction_elem, "TotalDeductions", total_deductions)

        # Tax Computation
        tax_elem = ET.SubElement(form, "TaxComputation")
        taxable_income = gross_income - total_deductions
        _add_income_element(tax_elem, "TaxableIncome", taxable_income)
        _add_income_element(tax_elem, "IncomeTax", income_data.get("income_tax", 0))
        _add_income_element(tax_elem, "Surcharge", income_data.get("surcharge", 0))
        _add_income_element(tax_elem, "Cess", income_data.get("cess", 0))

        total_tax = (
            income_data.get("income_tax", 0) +
            income_data.get("surcharge", 0) +
            income_data.get("cess", 0)
        )
        _add_income_element(tax_elem, "TotalTax", total_tax)

        # Tax Paid
        paid_elem = ET.SubElement(form, "TaxPaid")
        _add_income_element(paid_elem, "TDSSalary", income_data.get("tds_salary", 0))
        _add_income_element(paid_elem, "TDSOther", income_data.get("tds_other", 0))
        _add_income_element(paid_elem, "AdvanceTax", income_data.get("advance_tax", 0))

        total_paid = (
            income_data.get("tds_salary", 0) +
            income_data.get("tds_other", 0) +
            income_data.get("advance_tax", 0)
        )
        _add_income_element(paid_elem, "TotalTaxPaid", total_paid)

        # Refund/Payable
        refund_payable = total_paid - total_tax
        if refund_payable > 0:
            _add_income_element(form, "RefundAmount", refund_payable)
        else:
            _add_income_element(form, "TaxPayable", abs(refund_payable))

        # Verification
        if signature_value:
            verification = ET.SubElement(form, "Verification")
            ET.SubElement(verification, "DigitalSignature").text = signature_value
            ET.SubElement(verification, "SignatureDate").text = datetime.utcnow().strftime("%d/%m/%Y")

        return _prettify_xml(root)

    @staticmethod
    def generate_itr3(
        pan: str,
        name: str,
        ay: str,
        income_data: Dict[str, Any],
        signature_value: str = ""
    ) -> str:
        """Generate ITR-3 XML (Business/Profession)."""
        root = ET.Element("ITRDocument")
        root.set("xmlns", ITRXMLGenerator.NAMESPACE)
        root.set("DocumentType", "ITR3")

        entity = ET.SubElement(root, "TaxableEntity")
        ET.SubElement(entity, "PAN").text = pan
        ET.SubElement(entity, "Name").text = name

        form = ET.SubElement(root, "ITRForm")
        form.set("FormName", "ITR-3")
        form.set("AY", ay)

        income_elem = ET.SubElement(form, "IncomeDetails")
        _add_income_element(income_elem, "BusinessIncome", income_data.get("business_income", 0))
        _add_income_element(income_elem, "ProfessionIncome", income_data.get("profession_income", 0))
        _add_income_element(income_elem, "SpeculativeIncome", income_data.get("speculative_income", 0))
        _add_income_element(income_elem, "CapitalGainSTCG", income_data.get("capital_gains_stcg", 0))
        _add_income_element(income_elem, "CapitalGainLTCG", income_data.get("capital_gains_ltcg", 0))
        _add_income_element(income_elem, "OtherIncome", income_data.get("other_income", 0))

        gross_income = (
            income_data.get("business_income", 0) +
            income_data.get("profession_income", 0) +
            income_data.get("speculative_income", 0) +
            income_data.get("capital_gains_stcg", 0) +
            income_data.get("capital_gains_ltcg", 0) +
            income_data.get("other_income", 0)
        )
        _add_income_element(income_elem, "GrossTotalIncome", gross_income)

        deduction_elem = ET.SubElement(form, "Deductions")
        _add_income_element(deduction_elem, "Section80C", income_data.get("sec_80c", 0))
        _add_income_element(deduction_elem, "Section80D", income_data.get("sec_80d", 0))
        _add_income_element(deduction_elem, "Section80G", income_data.get("sec_80g", 0))

        total_deductions = (
            income_data.get("sec_80c", 0) +
            income_data.get("sec_80d", 0) +
            income_data.get("sec_80g", 0)
        )
        _add_income_element(deduction_elem, "TotalDeductions", total_deductions)

        tax_elem = ET.SubElement(form, "TaxComputation")
        taxable_income = gross_income - total_deductions
        _add_income_element(tax_elem, "TaxableIncome", taxable_income)
        _add_income_element(tax_elem, "IncomeTax", income_data.get("income_tax", 0))
        _add_income_element(tax_elem, "Surcharge", income_data.get("surcharge", 0))
        _add_income_element(tax_elem, "Cess", income_data.get("cess", 0))

        total_tax = (
            income_data.get("income_tax", 0) +
            income_data.get("surcharge", 0) +
            income_data.get("cess", 0)
        )
        _add_income_element(tax_elem, "TotalTax", total_tax)

        paid_elem = ET.SubElement(form, "TaxPaid")
        _add_income_element(paid_elem, "TDSTotal", income_data.get("tds_total", 0))
        _add_income_element(paid_elem, "AdvanceTax", income_data.get("advance_tax", 0))

        total_paid = income_data.get("tds_total", 0) + income_data.get("advance_tax", 0)
        _add_income_element(paid_elem, "TotalTaxPaid", total_paid)

        refund_payable = total_paid - total_tax
        if refund_payable > 0:
            _add_income_element(form, "RefundAmount", refund_payable)
        else:
            _add_income_element(form, "TaxPayable", abs(refund_payable))

        if signature_value:
            verification = ET.SubElement(form, "Verification")
            ET.SubElement(verification, "DigitalSignature").text = signature_value

        return _prettify_xml(root)

    @staticmethod
    def generate_itr4(
        pan: str,
        name: str,
        ay: str,
        income_data: Dict[str, Any],
        signature_value: str = ""
    ) -> str:
        """Generate ITR-4 XML (Section 44AD/44ADA Presumptive Scheme)."""
        root = ET.Element("ITRDocument")
        root.set("xmlns", ITRXMLGenerator.NAMESPACE)
        root.set("DocumentType", "ITR4")

        entity = ET.SubElement(root, "TaxableEntity")
        ET.SubElement(entity, "PAN").text = pan
        ET.SubElement(entity, "Name").text = name

        form = ET.SubElement(root, "ITRForm")
        form.set("FormName", "ITR-4")
        form.set("AY", ay)

        income_elem = ET.SubElement(form, "IncomeDetails")
        ET.SubElement(income_elem, "Section").text = income_data.get("section", "44AD")
        _add_income_element(income_elem, "GrossTurnover", income_data.get("gross_turnover", 0))
        _add_income_element(income_elem, "PresumptiveIncome", income_data.get("presumptive_income", 0))
        _add_income_element(income_elem, "OtherIncome", income_data.get("other_income", 0))

        gross_income = (
            income_data.get("presumptive_income", 0) +
            income_data.get("other_income", 0)
        )
        _add_income_element(income_elem, "GrossTotalIncome", gross_income)

        deduction_elem = ET.SubElement(form, "Deductions")
        _add_income_element(deduction_elem, "Section80C", income_data.get("sec_80c", 0))
        _add_income_element(deduction_elem, "Section80D", income_data.get("sec_80d", 0))

        total_deductions = income_data.get("sec_80c", 0) + income_data.get("sec_80d", 0)
        _add_income_element(deduction_elem, "TotalDeductions", total_deductions)

        tax_elem = ET.SubElement(form, "TaxComputation")
        taxable_income = gross_income - total_deductions
        _add_income_element(tax_elem, "TaxableIncome", taxable_income)
        _add_income_element(tax_elem, "IncomeTax", income_data.get("income_tax", 0))
        _add_income_element(tax_elem, "Surcharge", income_data.get("surcharge", 0))

        total_tax = income_data.get("income_tax", 0) + income_data.get("surcharge", 0)
        _add_income_element(tax_elem, "TotalTax", total_tax)

        paid_elem = ET.SubElement(form, "TaxPaid")
        _add_income_element(paid_elem, "TDSTotal", income_data.get("tds_total", 0))
        _add_income_element(paid_elem, "AdvanceTax", income_data.get("advance_tax", 0))

        total_paid = income_data.get("tds_total", 0) + income_data.get("advance_tax", 0)
        _add_income_element(paid_elem, "TotalTaxPaid", total_paid)

        refund_payable = total_paid - total_tax
        if refund_payable > 0:
            _add_income_element(form, "RefundAmount", refund_payable)
        else:
            _add_income_element(form, "TaxPayable", abs(refund_payable))

        if signature_value:
            verification = ET.SubElement(form, "Verification")
            ET.SubElement(verification, "DigitalSignature").text = signature_value

        return _prettify_xml(root)

    @staticmethod
    def generate_itr7(
        pan: str,
        entity_name: str,
        ay: str,
        income_data: Dict[str, Any],
        signature_value: str = ""
    ) -> str:
        """Generate ITR-7 XML (Trust/Section 139(4A))."""
        root = ET.Element("ITRDocument")
        root.set("xmlns", ITRXMLGenerator.NAMESPACE)
        root.set("DocumentType", "ITR7")

        entity = ET.SubElement(root, "TaxableEntity")
        ET.SubElement(entity, "PAN").text = pan
        ET.SubElement(entity, "EntityType").text = income_data.get("entity_type", "trust")
        ET.SubElement(entity, "Name").text = entity_name

        form = ET.SubElement(root, "ITRForm")
        form.set("FormName", "ITR-7")
        form.set("AY", ay)

        income_elem = ET.SubElement(form, "IncomeDetails")
        _add_income_element(income_elem, "GrossReceipts", income_data.get("gross_receipts", 0))
        _add_income_element(income_elem, "VoluntaryContributions", income_data.get("voluntary_contributions", 0))
        _add_income_element(income_elem, "CorpusDonations", income_data.get("corpus_donations", 0))
        _add_income_element(income_elem, "AnonymousDonations", income_data.get("anonymous_donations", 0))
        _add_income_element(income_elem, "BusinessIncome", income_data.get("business_income", 0))
        _add_income_element(income_elem, "InvestmentIncome", income_data.get("investment_income", 0))

        gross_income = (
            income_data.get("business_income", 0) +
            income_data.get("investment_income", 0) +
            income_data.get("gross_receipts", 0)
        )
        _add_income_element(income_elem, "GrossTotalIncome", gross_income)

        tax_elem = ET.SubElement(form, "TaxComputation")
        _add_income_element(tax_elem, "TaxableIncome", gross_income)
        _add_income_element(tax_elem, "IncomeTax", income_data.get("income_tax", 0))
        _add_income_element(tax_elem, "Surcharge", income_data.get("surcharge", 0))

        total_tax = income_data.get("income_tax", 0) + income_data.get("surcharge", 0)
        _add_income_element(tax_elem, "TotalTax", total_tax)

        paid_elem = ET.SubElement(form, "TaxPaid")
        _add_income_element(paid_elem, "TDSTotal", income_data.get("tds_total", 0))
        _add_income_element(paid_elem, "AdvanceTax", income_data.get("advance_tax", 0))

        total_paid = income_data.get("tds_total", 0) + income_data.get("advance_tax", 0)
        _add_income_element(paid_elem, "TotalTaxPaid", total_paid)

        refund_payable = total_paid - total_tax
        if refund_payable > 0:
            _add_income_element(form, "RefundAmount", refund_payable)
        else:
            _add_income_element(form, "TaxPayable", abs(refund_payable))

        if signature_value:
            verification = ET.SubElement(form, "Verification")
            ET.SubElement(verification, "DigitalSignature").text = signature_value

        return _prettify_xml(root)


def _add_income_element(parent: ET.Element, tag: str, value: float) -> None:
    """Add income element with proper formatting."""
    elem = ET.SubElement(parent, tag)
    elem.text = f"{value:.2f}"


def _prettify_xml(elem: ET.Element) -> str:
    """Return prettified XML string."""
    rough_string = ET.tostring(elem, encoding='utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")
