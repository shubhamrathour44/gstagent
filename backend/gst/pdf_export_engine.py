"""
PDF Export Engine

Converts tax forms (GSTR-3B, ITR-1, ITR-2, ITR-3) to government-ready PDFs.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime
from typing import Dict, Any, List


class GSTR3BPDFGenerator:
    """Generate PDF for GSTR-3B forms"""

    @staticmethod
    def generate_pdf(form_data: Dict[str, Any]) -> BytesIO:
        """Generate GSTR-3B PDF"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []

        # Header
        story.append(GSTR3BPDFGenerator._create_header(form_data))
        story.append(Spacer(1, 0.2*inch))

        # Metadata Section
        story.append(GSTR3BPDFGenerator._create_metadata_section(form_data))
        story.append(Spacer(1, 0.15*inch))

        # Outward Supplies
        if "outward_supplies" in form_data and form_data["outward_supplies"]:
            story.append(GSTR3BPDFGenerator._create_outward_section(form_data))
            story.append(Spacer(1, 0.15*inch))

        # Inward Supplies
        if "inward_supplies" in form_data and form_data["inward_supplies"]:
            story.append(GSTR3BPDFGenerator._create_inward_section(form_data))
            story.append(Spacer(1, 0.15*inch))

        # Tax Liability
        story.append(GSTR3BPDFGenerator._create_tax_liability_section(form_data))
        story.append(Spacer(1, 0.15*inch))

        # Footer
        story.append(GSTR3BPDFGenerator._create_footer())

        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def _create_header(form_data: Dict) -> Table:
        """Create PDF header with form info"""
        header_data = [
            ["GSTR-3B", "MONTHLY TAX SUMMARY RETURN"],
            [f"GSTIN: {form_data.get('gstin', 'N/A')}",
             f"Period: {form_data.get('period', 'N/A')}"],
            [f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}", ""]
        ]

        table = Table(header_data, colWidths=[3*inch, 3.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        return table

    @staticmethod
    def _create_metadata_section(form_data: Dict) -> Table:
        """Create metadata section"""
        data = [
            ["Field", "Value"],
            ["GSTIN", form_data.get('gstin', 'N/A')],
            ["Period", form_data.get('period', 'N/A')],
            ["Financial Year", form_data.get('financial_year', 'N/A')],
            ["Status", form_data.get('status', 'DRAFT')],
        ]

        table = Table(data, colWidths=[2*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9e8f5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ]))
        return table

    @staticmethod
    def _create_outward_section(form_data: Dict) -> Table:
        """Create outward supplies section"""
        data = [["Supply Type", "Count", "Taxable Value", "SGST", "CGST", "IGST", "CESS"]]

        outward = form_data.get('outward_supplies', {})
        for supply_type, details in outward.items():
            data.append([
                supply_type.replace('_', ' ').title(),
                str(details.get('invoice_count', 0)),
                f"₹{details.get('taxable_value', 0):,.2f}",
                f"₹{details.get('sgst', 0):,.2f}",
                f"₹{details.get('cgst', 0):,.2f}",
                f"₹{details.get('igst', 0):,.2f}",
                f"₹{details.get('cess', 0):,.2f}",
            ])

        table = Table(data, colWidths=[1.2*inch, 0.8*inch, 1.2*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9e8f5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]))
        return table

    @staticmethod
    def _create_inward_section(form_data: Dict) -> Table:
        """Create inward supplies section"""
        data = [["Supply Type", "Count", "Taxable Value", "ITC Eligible", "ITC Amount"]]

        inward = form_data.get('inward_supplies', {})
        for supply_type, details in inward.items():
            data.append([
                supply_type.replace('_', ' ').title(),
                str(details.get('invoice_count', 0)),
                f"₹{details.get('taxable_value', 0):,.2f}",
                "Yes" if details.get('itc_eligible', False) else "No",
                f"₹{details.get('itc_amount', 0):,.2f}",
            ])

        table = Table(data, colWidths=[1.5*inch, 0.9*inch, 1.5*inch, 1.3*inch, 1.3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9e8f5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]))
        return table

    @staticmethod
    def _create_tax_liability_section(form_data: Dict) -> Table:
        """Create tax liability section"""
        liability = form_data.get('tax_liability', {})

        data = [
            ["Tax Component", "Amount"],
            ["Total Output Tax (SGST+CGST+IGST+CESS)", f"₹{liability.get('total_output_tax', 0):,.2f}"],
            ["Total ITC Available", f"₹{liability.get('total_itc', 0):,.2f}"],
            ["Net Tax Payable", f"₹{liability.get('net_tax_payable', 0):,.2f}"],
        ]

        table = Table(data, colWidths=[3.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fff4e6')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]))
        return table

    @staticmethod
    def _create_footer() -> Paragraph:
        """Create footer"""
        footer_text = f"<br/><b>Generated by GST Agent Professional Suite</b><br/>Document generated on {datetime.now().strftime('%d-%m-%Y at %H:%M:%S')}<br/>This is a system-generated document."
        return Paragraph(footer_text, ParagraphStyle(
            'Footer',
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_CENTER
        ))


class ITR1PDFGenerator:
    """Generate PDF for ITR-1 (SARAL) forms"""

    @staticmethod
    def generate_pdf(form_data: Dict[str, Any]) -> BytesIO:
        """Generate ITR-1 PDF"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []

        # Header
        story.append(ITR1PDFGenerator._create_header(form_data))
        story.append(Spacer(1, 0.2*inch))

        # Personal Info
        story.append(ITR1PDFGenerator._create_personal_info(form_data))
        story.append(Spacer(1, 0.15*inch))

        # Income Details
        story.append(ITR1PDFGenerator._create_income_section(form_data))
        story.append(Spacer(1, 0.15*inch))

        # Deductions
        story.append(ITR1PDFGenerator._create_deductions_section(form_data))
        story.append(Spacer(1, 0.15*inch))

        # Tax Calculation
        story.append(ITR1PDFGenerator._create_tax_section(form_data))
        story.append(Spacer(1, 0.15*inch))

        # Footer
        story.append(ITR1PDFGenerator._create_footer())

        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def _create_header(form_data: Dict) -> Table:
        """Create PDF header"""
        header_data = [
            ["ITR-1 (SARAL)", "INCOME TAX RETURN - SALARIED INDIVIDUALS"],
            [f"PAN: {form_data.get('pan', 'N/A')}",
             f"Financial Year: {form_data.get('financial_year', 'N/A')}-{int(form_data.get('financial_year', 2026)) + 1}"],
        ]

        table = Table(header_data, colWidths=[3*inch, 3.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        return table

    @staticmethod
    def _create_personal_info(form_data: Dict) -> Table:
        """Create personal info section"""
        data = [
            ["Field", "Value"],
            ["PAN", form_data.get('pan', 'N/A')],
            ["Financial Year", f"{form_data.get('financial_year', 'N/A')}-{int(form_data.get('financial_year', 2026)) + 1}"],
            ["Assessment Year", f"{int(form_data.get('financial_year', 2026)) + 1}-{int(form_data.get('financial_year', 2026)) + 2}"],
        ]

        table = Table(data, colWidths=[2*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9e8f5')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ]))
        return table

    @staticmethod
    def _create_income_section(form_data: Dict) -> Table:
        """Create income section"""
        income = form_data.get('income_calculation', {})

        data = [
            ["Income Source", "Amount"],
            ["Salary Income", f"₹{income.get('salary_income', 0):,.2f}"],
            ["House Property Income", f"₹{income.get('house_property_income', 0):,.2f}"],
            ["Other Income", f"₹{income.get('other_income', 0):,.2f}"],
            ["Total Income", f"₹{income.get('total_income', 0):,.2f}"],
        ]

        table = Table(data, colWidths=[3.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9e8f5')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]))
        return table

    @staticmethod
    def _create_deductions_section(form_data: Dict) -> Table:
        """Create deductions section"""
        income = form_data.get('income_calculation', {})

        data = [
            ["Deduction Type", "Amount"],
            ["Section 80C", f"₹{income.get('section_80c', 0):,.2f}"],
            ["Section 80D", f"₹{income.get('section_80d', 0):,.2f}"],
            ["Total Deductions", f"₹{income.get('total_deductions', 0):,.2f}"],
            ["Taxable Income", f"₹{income.get('taxable_income', 0):,.2f}"],
        ]

        table = Table(data, colWidths=[3.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9e8f5')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]))
        return table

    @staticmethod
    def _create_tax_section(form_data: Dict) -> Table:
        """Create tax calculation section"""
        tax = form_data.get('tax_calculation', {})

        data = [
            ["Tax Component", "Amount"],
            ["Income Tax", f"₹{tax.get('income_tax', 0):,.2f}"],
            ["Surcharge", f"₹{tax.get('surcharge', 0):,.2f}"],
            ["Health & Education Cess", f"₹{tax.get('cess', 0):,.2f}"],
            ["Total Tax Liability", f"₹{tax.get('total_tax', 0):,.2f}"],
        ]

        table = Table(data, colWidths=[3.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fff4e6')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]))
        return table

    @staticmethod
    def _create_footer() -> Paragraph:
        """Create footer"""
        footer_text = f"<br/><b>Generated by GST Agent Professional Suite</b><br/>Document generated on {datetime.now().strftime('%d-%m-%Y at %H:%M:%S')}<br/>This is a system-generated document. Requires authorized person's signature."
        return Paragraph(footer_text, ParagraphStyle(
            'Footer',
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_CENTER
        ))


class ITR2PDFGenerator:
    """Generate PDF for ITR-2 forms (Capital Gains)"""

    @staticmethod
    def generate_pdf(form_data: Dict[str, Any]) -> BytesIO:
        """Generate ITR-2 PDF"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []

        story.append(ITR2PDFGenerator._create_header(form_data))
        story.append(Spacer(1, 0.2*inch))

        story.append(ITR2PDFGenerator._create_personal_info(form_data))
        story.append(Spacer(1, 0.15*inch))

        if "capital_gains" in form_data and form_data["capital_gains"]:
            story.append(ITR2PDFGenerator._create_gains_section(form_data))
            story.append(Spacer(1, 0.15*inch))

        story.append(ITR2PDFGenerator._create_income_section(form_data))
        story.append(Spacer(1, 0.15*inch))

        story.append(ITR2PDFGenerator._create_tax_section(form_data))
        story.append(Spacer(1, 0.15*inch))

        story.append(ITR2PDFGenerator._create_footer())

        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def _create_header(form_data: Dict) -> Table:
        """Create PDF header"""
        header_data = [
            ["ITR-2", "INCOME TAX RETURN - INDIVIDUALS WITH CAPITAL GAINS"],
            [f"PAN: {form_data.get('pan', 'N/A')}",
             f"Financial Year: {form_data.get('financial_year', 'N/A')}-{int(form_data.get('financial_year', 2026)) + 1}"],
        ]

        table = Table(header_data, colWidths=[3*inch, 3.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        return table

    @staticmethod
    def _create_personal_info(form_data: Dict) -> Table:
        """Create personal info section"""
        data = [
            ["Field", "Value"],
            ["PAN", form_data.get('pan', 'N/A')],
            ["Financial Year", f"{form_data.get('financial_year', 'N/A')}-{int(form_data.get('financial_year', 2026)) + 1}"],
        ]

        table = Table(data, colWidths=[2*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9e8f5')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ]))
        return table

    @staticmethod
    def _create_gains_section(form_data: Dict) -> Table:
        """Create capital gains section"""
        gains = form_data.get('capital_gains', [])
        data = [["Asset Type", "Cost", "Sale Price", "Gain", "Type"]]

        for gain in gains:
            data.append([
                gain.get('asset_type', 'N/A'),
                f"₹{gain.get('cost_of_acquisition', 0):,.2f}",
                f"₹{gain.get('selling_price', 0):,.2f}",
                f"₹{gain.get('gain', 0):,.2f}",
                gain.get('gain_type', 'N/A')
            ])

        table = Table(data, colWidths=[1.2*inch, 1.3*inch, 1.3*inch, 1.3*inch, 1.4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9e8f5')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]))
        return table

    @staticmethod
    def _create_income_section(form_data: Dict) -> Table:
        """Create income section"""
        income = form_data.get('income_calculation', {})

        data = [
            ["Income Source", "Amount"],
            ["Salary Income", f"₹{income.get('salary_income', 0):,.2f}"],
            ["House Property Income", f"₹{income.get('house_property_income', 0):,.2f}"],
            ["Short-term Capital Gains", f"₹{income.get('short_term_gains', 0):,.2f}"],
            ["Long-term Capital Gains", f"₹{income.get('long_term_gains', 0):,.2f}"],
            ["Other Income", f"₹{income.get('other_income', 0):,.2f}"],
            ["Total Income", f"₹{income.get('total_income', 0):,.2f}"],
        ]

        table = Table(data, colWidths=[3.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9e8f5')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]))
        return table

    @staticmethod
    def _create_tax_section(form_data: Dict) -> Table:
        """Create tax calculation section"""
        tax = form_data.get('tax_calculation', {})

        data = [
            ["Tax Component", "Amount"],
            ["Income Tax", f"₹{tax.get('income_tax', 0):,.2f}"],
            ["Surcharge", f"₹{tax.get('surcharge', 0):,.2f}"],
            ["Health & Education Cess", f"₹{tax.get('cess', 0):,.2f}"],
            ["Total Tax Liability", f"₹{tax.get('total_tax', 0):,.2f}"],
        ]

        table = Table(data, colWidths=[3.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fff4e6')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]))
        return table

    @staticmethod
    def _create_footer() -> Paragraph:
        """Create footer"""
        footer_text = f"<br/><b>Generated by GST Agent Professional Suite</b><br/>Document generated on {datetime.now().strftime('%d-%m-%Y at %H:%M:%S')}<br/>Capital gains computed as per Income Tax Act, 1961."
        return Paragraph(footer_text, ParagraphStyle(
            'Footer',
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_CENTER
        ))


class ITR3PDFGenerator:
    """Generate PDF for ITR-3 forms (Business Income)"""

    @staticmethod
    def generate_pdf(form_data: Dict[str, Any]) -> BytesIO:
        """Generate ITR-3 PDF"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []

        story.append(ITR3PDFGenerator._create_header(form_data))
        story.append(Spacer(1, 0.2*inch))

        story.append(ITR3PDFGenerator._create_personal_info(form_data))
        story.append(Spacer(1, 0.15*inch))

        story.append(ITR3PDFGenerator._create_business_section(form_data))
        story.append(Spacer(1, 0.15*inch))

        story.append(ITR3PDFGenerator._create_income_section(form_data))
        story.append(Spacer(1, 0.15*inch))

        story.append(ITR3PDFGenerator._create_tax_section(form_data))
        story.append(Spacer(1, 0.15*inch))

        story.append(ITR3PDFGenerator._create_footer())

        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def _create_header(form_data: Dict) -> Table:
        """Create PDF header"""
        header_data = [
            ["ITR-3", "INCOME TAX RETURN - BUSINESS/PROFESSIONALS"],
            [f"PAN: {form_data.get('pan', 'N/A')}",
             f"Financial Year: {form_data.get('financial_year', 'N/A')}-{int(form_data.get('financial_year', 2026)) + 1}"],
        ]

        table = Table(header_data, colWidths=[3*inch, 3.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        return table

    @staticmethod
    def _create_personal_info(form_data: Dict) -> Table:
        """Create personal info section"""
        data = [
            ["Field", "Value"],
            ["PAN", form_data.get('pan', 'N/A')],
            ["Financial Year", f"{form_data.get('financial_year', 'N/A')}-{int(form_data.get('financial_year', 2026)) + 1}"],
        ]

        table = Table(data, colWidths=[2*inch, 4.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9e8f5')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ]))
        return table

    @staticmethod
    def _create_business_section(form_data: Dict) -> Table:
        """Create business summary section"""
        business = form_data.get('business_summary', {})

        data = [
            ["Component", "Amount"],
            ["Gross Receipts", f"₹{business.get('gross_receipts', 0):,.2f}"],
            ["Cost of Goods Sold", f"₹{business.get('cost_of_goods_sold', 0):,.2f}"],
            ["Total Expenses", f"₹{business.get('total_expenses', 0):,.2f}"],
            ["Net Business Profit", f"₹{business.get('net_profit', 0):,.2f}"],
        ]

        table = Table(data, colWidths=[3.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9e8f5')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]))
        return table

    @staticmethod
    def _create_income_section(form_data: Dict) -> Table:
        """Create total income section"""
        income = form_data.get('income_calculation', {})

        data = [
            ["Income Source", "Amount"],
            ["Business Profit", f"₹{income.get('business_profit', 0):,.2f}"],
            ["Salary Income", f"₹{income.get('salary_income', 0):,.2f}"],
            ["House Property Income", f"₹{income.get('house_property_income', 0):,.2f}"],
            ["Other Income", f"₹{income.get('other_income', 0):,.2f}"],
            ["Total Income", f"₹{income.get('total_income', 0):,.2f}"],
        ]

        table = Table(data, colWidths=[3.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9e8f5')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]))
        return table

    @staticmethod
    def _create_tax_section(form_data: Dict) -> Table:
        """Create tax calculation section"""
        tax = form_data.get('tax_calculation', {})

        data = [
            ["Tax Component", "Amount"],
            ["Income Tax", f"₹{tax.get('income_tax', 0):,.2f}"],
            ["Surcharge", f"₹{tax.get('surcharge', 0):,.2f}"],
            ["Health & Education Cess", f"₹{tax.get('cess', 0):,.2f}"],
            ["Total Tax Liability", f"₹{tax.get('total_tax', 0):,.2f}"],
        ]

        table = Table(data, colWidths=[3.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fff4e6')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]))
        return table

    @staticmethod
    def _create_footer() -> Paragraph:
        """Create footer"""
        footer_text = f"<br/><b>Generated by GST Agent Professional Suite</b><br/>Document generated on {datetime.now().strftime('%d-%m-%Y at %H:%M:%S')}<br/>Business income computed as per Income Tax Act, 1961."
        return Paragraph(footer_text, ParagraphStyle(
            'Footer',
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_CENTER
        ))
