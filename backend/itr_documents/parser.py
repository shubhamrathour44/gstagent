"""Document parsing and data extraction for AIS, 26AS, and Form 16."""

import re
from typing import Dict, Any, List, Tuple, Optional


class DocumentParser:
    """Base parser for tax documents."""

    @staticmethod
    def extract_pan(text: str) -> Optional[str]:
        """Extract PAN from document text."""
        pan_pattern = r'[A-Z]{5}[0-9]{4}[A-Z]{1}'
        match = re.search(pan_pattern, text)
        return match.group(0) if match else None

    @staticmethod
    def extract_assessment_year(text: str) -> Optional[str]:
        """Extract assessment year from document."""
        ay_patterns = [
            r'(\d{4})-?(\d{2})',  # 2024-25 or 202425
            r'AY\s+(\d{4})-(\d{2})',  # AY 2024-25
            r'Assessment Year.*?(\d{4})-(\d{2})',
        ]

        for pattern in ay_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    return f"{match.group(1)}-{match.group(2)}"
                return match.group(0)

        return None

    @staticmethod
    def extract_number(text: str, pattern: str) -> Optional[float]:
        """Extract a number matching a pattern."""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                # Find the last number-like string in the match
                numbers = re.findall(r'[\d,]+(?:\.\d+)?', match.group(0))
                if numbers:
                    return float(numbers[-1].replace(',', ''))
            except (ValueError, AttributeError):
                pass
        return None


class AISParser(DocumentParser):
    """Parse AIS (Annual Information Statement) documents."""

    @staticmethod
    def parse(text: str) -> Dict[str, Any]:
        """Parse AIS document and extract key fields."""

        extraction = {
            "document_type": "AIS",
            "pan": DocumentParser.extract_pan(text),
            "assessment_year": DocumentParser.extract_assessment_year(text),
            "salary_income": None,
            "hra_received": None,
            "other_income": None,
            "tds_salary": None,
            "tds_interest": None,
            "tds_other": None,
            "total_tds": None,
            "extracted_fields": {}
        }

        # Extract salary income
        salary_patterns = [
            r'(?:Salary\s+Income|Gross\s+Salary|Income.*?Salary).*?([\d,]+(?:\.\d+)?)',
            r'(?:Income\s+under\s+the\s+head\s+)?Salaries.*?([\d,]+(?:\.\d+)?)',
        ]
        for pattern in salary_patterns:
            salary = DocumentParser.extract_number(text, pattern)
            if salary:
                extraction["salary_income"] = salary
                extraction["extracted_fields"]["salary_income"] = pattern
                break

        # Extract HRA
        hra_patterns = [
            r'(?:HRA|House\s+Rent\s+Allowance).*?([\d,]+(?:\.\d+)?)',
            r'(?:Allowances|Perquisites).*?HRA.*?([\d,]+(?:\.\d+)?)',
        ]
        for pattern in hra_patterns:
            hra = DocumentParser.extract_number(text, pattern)
            if hra:
                extraction["hra_received"] = hra
                extraction["extracted_fields"]["hra_received"] = pattern
                break

        # Extract TDS
        tds_patterns = [
            (r'(?:TDS|Tax\s+Deducted).*?Salary.*?([\d,]+(?:\.\d+)?)', "tds_salary"),
            (r'(?:TDS|Tax\s+Deducted).*?Interest.*?([\d,]+(?:\.\d+)?)', "tds_interest"),
            (r'Total\s+TDS.*?([\d,]+(?:\.\d+)?)', "total_tds"),
        ]
        for pattern, field in tds_patterns:
            tds = DocumentParser.extract_number(text, pattern)
            if tds:
                extraction[field] = tds
                extraction["extracted_fields"][field] = pattern

        # Calculate total TDS if not found
        if extraction["total_tds"] is None:
            tds_sum = sum(v for k, v in extraction.items()
                         if k.startswith('tds_') and v is not None and k != 'tds_salary')
            if tds_sum > 0:
                extraction["total_tds"] = tds_sum

        return extraction


class Form26ASParser(DocumentParser):
    """Parse Form 26AS (Tax Collected at Source) documents."""

    @staticmethod
    def parse(text: str) -> Dict[str, Any]:
        """Parse Form 26AS and extract TDS entries."""

        extraction = {
            "document_type": "Form 26AS",
            "pan": DocumentParser.extract_pan(text),
            "assessment_year": DocumentParser.extract_assessment_year(text),
            "gross_total_income": None,
            "tds_entries": [],
            "total_tds": None,
            "deposit_entries": [],
            "extracted_fields": {}
        }

        # Extract GTI (Gross Total Income)
        gti_patterns = [
            r'(?:Gross\s+Total\s+Income|GTI).*?([\d,]+(?:\.\d+)?)',
            r'Income.*?computed.*?([\d,]+(?:\.\d+)?)',
        ]
        for pattern in gti_patterns:
            gti = DocumentParser.extract_number(text, pattern)
            if gti:
                extraction["gross_total_income"] = gti
                extraction["extracted_fields"]["gti"] = pattern
                break

        # Extract TDS entries (look for Section-wise entries)
        tds_section_pattern = r'Section\s+(\d+[A-Z]*)\s+[A-Za-z\s]*?([\d,]+(?:\.\d+)?)'
        matches = re.finditer(tds_section_pattern, text, re.IGNORECASE)

        total_tds = 0
        for match in matches:
            section = match.group(1)
            amount = float(match.group(2).replace(',', ''))
            extraction["tds_entries"].append({
                "section": f"Section {section}",
                "amount": amount
            })
            total_tds += amount

        if total_tds > 0:
            extraction["total_tds"] = total_tds

        # Extract deposit entries (cash deposits)
        deposit_pattern = r'(?:Deposit|Advance\s+Tax).*?(?:Date|Amount).*?([\d,]+(?:\.\d+)?)'
        deposits = re.findall(deposit_pattern, text, re.IGNORECASE)
        extraction["deposit_entries"] = [
            {"amount": float(d.replace(',', ''))} for d in deposits
        ]

        return extraction


class Form16Parser(DocumentParser):
    """Parse Form 16 (TDS Certificate for Salary) documents."""

    @staticmethod
    def parse(text: str) -> Dict[str, Any]:
        """Parse Form 16 and extract salary/TDS details."""

        extraction = {
            "document_type": "Form 16",
            "pan": DocumentParser.extract_pan(text),
            "employee_pan": DocumentParser.extract_pan(text),
            "assessment_year": DocumentParser.extract_assessment_year(text),
            "salary_paid": None,
            "salary_credited": None,
            "hra_paid": None,
            "hra_exemption": None,
            "standard_deduction": None,
            "gross_total_income": None,
            "tds_deducted": None,
            "tds_deposited": None,
            "employee_name": None,
            "employer_name": None,
            "extracted_fields": {}
        }

        # Extract employee name
        name_pattern = r'(?:Employee|Name)\s*:?\s*([A-Z][A-Za-z\s]+)'
        name_match = re.search(name_pattern, text)
        if name_match:
            extraction["employee_name"] = name_match.group(1).strip()
            extraction["extracted_fields"]["employee_name"] = name_pattern

        # Extract employer name
        employer_pattern = r'(?:Employer|Company)\s*:?\s*([A-Z][A-Za-z\s,\.]+)'
        employer_match = re.search(employer_pattern, text)
        if employer_match:
            extraction["employer_name"] = employer_match.group(1).strip()
            extraction["extracted_fields"]["employer_name"] = employer_pattern

        # Extract salary components
        salary_patterns = [
            (r'(?:Salary\s+Paid|Amount\s+Paid).*?([\d,]+(?:\.\d+)?)', "salary_paid"),
            (r'(?:Salary\s+Credited|Credited).*?([\d,]+(?:\.\d+)?)', "salary_credited"),
            (r'(?:HRA\s+Paid|House\s+Rent).*?([\d,]+(?:\.\d+)?)', "hra_paid"),
            (r'(?:HRA\s+Exemption|Exemption).*?([\d,]+(?:\.\d+)?)', "hra_exemption"),
            (r'(?:Standard\s+Deduction).*?([\d,]+(?:\.\d+)?)', "standard_deduction"),
            (r'(?:Gross\s+Total\s+Income|GTI).*?([\d,]+(?:\.\d+)?)', "gross_total_income"),
            (r'(?:TDS\s+Deducted|Deducted).*?([\d,]+(?:\.\d+)?)', "tds_deducted"),
            (r'(?:TDS\s+Deposited|Deposited).*?([\d,]+(?:\.\d+)?)', "tds_deposited"),
        ]

        for pattern, field in salary_patterns:
            value = DocumentParser.extract_number(text, pattern)
            if value:
                extraction[field] = value
                extraction["extracted_fields"][field] = pattern

        return extraction


class DocumentParserFactory:
    """Factory to get appropriate parser for document type."""

    PARSERS = {
        "AIS": AISParser,
        "26AS": Form26ASParser,
        "Form 26AS": Form26ASParser,
        "Form 16": Form16Parser,
        "Form16": Form16Parser,
    }

    @staticmethod
    def get_parser(document_type: str):
        """Get parser for document type."""
        parser = DocumentParserFactory.PARSERS.get(document_type.strip())
        if not parser:
            raise ValueError(f"Unsupported document type: {document_type}")
        return parser

    @staticmethod
    def parse(document_type: str, text: str) -> Dict[str, Any]:
        """Parse document and extract data."""
        parser = DocumentParserFactory.get_parser(document_type)
        return parser.parse(text)
