"""
GST AI Agent Layer
Uses Claude to:
1. Explain mismatches in plain language
2. Draft vendor follow-up emails
3. Draft notice replies
4. Generate filing QA summaries
"""

import json
import os
from reconciliation_engine import ReconciliationResult, Mismatch, MismatchType


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"


async def call_claude(system_prompt: str, user_message: str, max_tokens: int = 1000) -> str:
    """
    Call Claude API. In production this uses httpx async client.
    API key is injected via environment variable ANTHROPIC_API_KEY.
    """
    import httpx

    headers = {
        "Content-Type": "application/json",
        "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "anthropic-version": "2023-06-01"
    }

    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}]
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(ANTHROPIC_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]


# ─────────────────────────────────────────────
# PROMPT 1: Mismatch Explanation
# ─────────────────────────────────────────────

MISMATCH_EXPLAINER_SYSTEM = """
You are a GST compliance expert helping Indian businesses and CA firms.
Your job is to explain GST reconciliation mismatches clearly and concisely.

Rules:
- Use plain English, not jargon
- Always mention the rupee impact
- Always state the legal consequence if unresolved
- Always give one clear next action
- Keep response under 150 words
- Never guess; only state what the data shows
"""

async def explain_mismatch(mismatch: Mismatch) -> str:
    """Generate a plain-language explanation of a mismatch."""

    prompt = f"""
Explain this GST mismatch to a business owner:

Mismatch Type: {mismatch.mismatch_type.value}
Supplier: {mismatch.supplier_name} (GSTIN: {mismatch.supplier_gstin})
Invoice Number: {mismatch.invoice_number}
Invoice Date: {mismatch.invoice_date}
Tax Impact: ₹{mismatch.tax_impact:,.2f}
PR Tax Amount: ₹{mismatch.pr_tax_amount:,.2f if mismatch.pr_tax_amount else 'N/A'}
2B Tax Amount: ₹{mismatch.b2b_tax_amount:,.2f if mismatch.b2b_tax_amount else 'N/A'}
Recommended Action: {mismatch.recommended_action.value}

Write a clear 3-sentence explanation:
1. What happened
2. What it means for ITC/tax liability
3. What to do next
"""
    return await call_claude(MISMATCH_EXPLAINER_SYSTEM, prompt)


# ─────────────────────────────────────────────
# PROMPT 2: Vendor Follow-up Email
# ─────────────────────────────────────────────

VENDOR_EMAIL_SYSTEM = """
You are a GST compliance professional drafting vendor follow-up emails for Indian businesses.

Rules:
- Professional but firm tone
- Reference specific invoice numbers and GST periods
- Clearly state what action the vendor needs to take
- Mention the legal timeline (GSTR-1 amendment possible up to specific period)
- Do NOT threaten legal action unless instructed
- Keep under 200 words
- Format as a proper business email with Subject, Body, and closing
"""

async def draft_vendor_email(
    mismatch: Mismatch,
    sender_company: str,
    sender_gstin: str,
    period: str
) -> str:
    """Draft a vendor follow-up email for a missing/mismatched invoice."""

    period_formatted = f"{period[2:]}/{period[:2]}"  # 032025 -> 03/2025

    prompt = f"""
Draft a vendor follow-up email for this GST mismatch:

Our Company: {sender_company}
Our GSTIN: {sender_gstin}
Tax Period: {period_formatted}

Vendor: {mismatch.supplier_name}
Vendor GSTIN: {mismatch.supplier_gstin}
Invoice Number: {mismatch.invoice_number}
Invoice Date: {mismatch.invoice_date}
Issue: {mismatch.mismatch_type.value}
ITC at Risk: ₹{abs(mismatch.tax_impact):,.2f}

The vendor needs to: {mismatch.recommended_action.value}

Draft the email now.
"""
    return await call_claude(VENDOR_EMAIL_SYSTEM, prompt)


# ─────────────────────────────────────────────
# PROMPT 3: Notice Reply Draft
# ─────────────────────────────────────────────

NOTICE_REPLY_SYSTEM = """
You are a senior GST consultant drafting replies to GST notices on behalf of taxpayers.

Rules:
- Reference the exact notice number and date
- Cite the relevant GST rule or section for every point
- Attach only facts from the supplied data — never invent supporting details
- Use formal legal language appropriate for tax authority correspondence
- Structure as: Reference to Notice → Summary of our Position → Point-by-point response → Supporting documents list → Closing
- Add [REVIEW REQUIRED] wherever human CA review is essential before sending
- Never state a position is correct unless backed by supplied evidence
"""

async def draft_notice_reply(
    notice_number: str,
    notice_date: str,
    notice_type: str,
    notice_content: str,
    taxpayer_gstin: str,
    taxpayer_name: str,
    supporting_facts: str
) -> str:
    """Draft a reply to a GST notice."""

    prompt = f"""
Draft a formal reply to this GST notice:

NOTICE DETAILS:
Notice Number: {notice_number}
Notice Date: {notice_date}
Notice Type: {notice_type}
Notice Content Summary: {notice_content}

TAXPAYER DETAILS:
GSTIN: {taxpayer_gstin}
Name: {taxpayer_name}

SUPPORTING FACTS AND EVIDENCE:
{supporting_facts}

Draft a complete formal notice reply. Mark any section needing CA review with [REVIEW REQUIRED].
"""
    return await call_claude(NOTICE_REPLY_SYSTEM, prompt, max_tokens=1500)


# ─────────────────────────────────────────────
# PROMPT 4: Full Reconciliation Summary
# ─────────────────────────────────────────────

SUMMARY_SYSTEM = """
You are a GST compliance analyst preparing reconciliation summary reports for CA firms and CFOs.

Rules:
- Lead with the most critical finding
- Quantify everything in rupees
- Group issues by urgency: file before due date, chase vendor, internal review
- Keep total summary under 300 words
- Use bullet points for action items
- Never say "everything is fine" if unresolved high-severity mismatches exist
"""

async def generate_reconciliation_summary(result: ReconciliationResult, company_name: str) -> str:
    """Generate an executive summary of the full reconciliation."""

    high_mismatches = [m for m in result.mismatches if m.severity.value == "high"]
    vendor_chase = [
        m for m in result.mismatches
        if m.mismatch_type == MismatchType.INVOICE_NOT_IN_2B
    ]

    prompt = f"""
Generate a reconciliation summary report for:

Company: {company_name}
GSTIN: {result.gstin}
Period: {result.period}

KEY NUMBERS:
- Total PR Invoices: {result.total_pr_invoices}
- Total 2B Invoices: {result.total_2b_invoices}
- Matched: {result.matched_invoices}
- Mismatches: {result.mismatched_invoices}
- Match Rate: {result.summary_stats.get('match_rate', 0)}%
- ITC as per 2B: ₹{result.total_itc_as_per_2b:,.2f}
- ITC as per PR: ₹{result.total_itc_as_per_pr:,.2f}
- ITC Difference: ₹{result.itc_difference:,.2f}

SEVERITY BREAKDOWN:
- HIGH: {result.high_severity_count}
- MEDIUM: {result.medium_severity_count}
- LOW: {result.low_severity_count}

HIGH-SEVERITY MISMATCHES:
{json.dumps([m.to_dict() for m in high_mismatches], indent=2, default=str)}

VENDORS TO CHASE ({len(vendor_chase)} vendors):
{', '.join(set(m.supplier_name for m in vendor_chase))}

Write the summary report now with clear action priorities.
"""
    return await call_claude(SUMMARY_SYSTEM, prompt, max_tokens=1200)


# ─────────────────────────────────────────────
# PROMPT 5: Filing QA Check
# ─────────────────────────────────────────────

FILING_QA_SYSTEM = """
You are a GST filing quality assurance agent reviewing returns before submission.

Rules:
- Check for common filing errors: wrong tax period, GSTIN errors, HSN mismatches, wrong tax heads
- Flag any item that could trigger a notice
- Rate overall filing readiness: READY / NEEDS REVIEW / DO NOT FILE
- List every issue with the specific line or field
- Never approve filing if HIGH-severity unresolved mismatches exist
"""

async def filing_qa_check(
    result: ReconciliationResult,
    return_type: str,
    draft_return_summary: dict
) -> str:
    """QA check a draft GST return before filing."""

    prompt = f"""
Perform a filing QA check on this draft {return_type}:

RECONCILIATION STATUS:
- Unresolved mismatches: {result.mismatched_invoices}
- High severity: {result.high_severity_count}
- ITC difference: ₹{result.itc_difference:,.2f}

DRAFT RETURN SUMMARY:
{json.dumps(draft_return_summary, indent=2)}

Provide filing QA result:
1. FILING STATUS: READY / NEEDS REVIEW / DO NOT FILE
2. Issues found (if any)
3. Items to verify before filing
4. Estimated risk if filed as-is
"""
    return await call_claude(FILING_QA_SYSTEM, prompt)
