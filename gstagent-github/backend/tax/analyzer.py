from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from .schemas import TaxAnalyzeRequest, TaxDocumentRecord, TaxProfile


AMOUNT_KEYS = [
    "amount", "gross_amount", "income", "taxable_amount", "paid_amount", "value",
    "transaction_amount", "total_amount", "salary", "interest", "dividend",
]
TDS_KEYS = ["tds", "tax_deducted", "tds_amount", "tax", "tax_amount", "amount_deducted"]
DESCRIPTION_KEYS = ["description", "nature", "income_type", "transaction_type", "particulars", "remarks"]
PAYER_NAME_KEYS = ["payer_name", "deductor_name", "employer_name", "name", "tan_name"]
PAYER_PAN_KEYS = ["payer_pan", "deductor_pan", "pan", "tan", "employer_pan"]
SECTION_KEYS = ["section", "tds_section", "section_code"]
DATE_KEYS = ["date", "transaction_date", "payment_date", "credit_date"]


NEW_REGIME_SLABS_AY_2026_27 = [
    (400000, 0.00),
    (800000, 0.05),
    (1200000, 0.10),
    (1600000, 0.15),
    (2000000, 0.20),
    (2400000, 0.25),
    (float("inf"), 0.30),
]

OLD_REGIME_SLABS_BELOW_60 = [
    (250000, 0.00),
    (500000, 0.05),
    (1000000, 0.20),
    (float("inf"), 0.30),
]

OLD_REGIME_SLABS_60_TO_79 = [
    (300000, 0.00),
    (500000, 0.05),
    (1000000, 0.20),
    (float("inf"), 0.30),
]

OLD_REGIME_SLABS_80_PLUS = [
    (500000, 0.00),
    (1000000, 0.20),
    (float("inf"), 0.30),
]


def _first_value(row: dict[str, Any], keys: list[str], default: Any = "") -> Any:
    lower_map = {str(k).lower().strip().replace(" ", "_"): v for k, v in row.items()}
    for key in keys:
        if key in lower_map and lower_map[key] not in (None, ""):
            return lower_map[key]
    return default


def _to_float(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").replace("₹", "").strip()
    try:
        return float(text)
    except Exception:
        return 0.0


def classify_category(row: dict[str, Any]) -> str:
    text = " ".join(str(_first_value(row, DESCRIPTION_KEYS + SECTION_KEYS + PAYER_NAME_KEYS, "")).lower().split())
    section = str(_first_value(row, SECTION_KEYS, "")).lower()
    if any(word in text for word in ["salary", "form 16", "employer"]) or section in {"192", "192a"}:
        return "salary"
    if any(word in text for word in ["interest", "savings", "deposit", "fd", "bank"]) or section in {"194a", "194n"}:
        return "interest"
    if "dividend" in text or section == "194":
        return "dividend"
    if any(word in text for word in ["capital", "securities", "mutual fund", "share", "stcg", "ltcg"]):
        return "capital_gains"
    if any(word in text for word in ["business", "profession", "contract", "commission", "fees"]):
        return "business_profession"
    if any(word in text for word in ["house property", "rent received", "rental"]):
        return "house_property"
    if any(word in text for word in ["rent", "194i"]):
        return "rent"
    if any(word in text for word in ["crypto", "vda", "virtual digital asset"]):
        return "capital_gains"
    return "other_sources"


def normalize_record(source: str, row: dict[str, Any]) -> TaxDocumentRecord:
    category = classify_category(row)
    amount = _to_float(_first_value(row, AMOUNT_KEYS, 0))
    tds = _to_float(_first_value(row, TDS_KEYS, 0))
    return TaxDocumentRecord(
        source=source,
        description=str(_first_value(row, DESCRIPTION_KEYS, "")),
        payer_name=str(_first_value(row, PAYER_NAME_KEYS, "")),
        payer_pan=str(_first_value(row, PAYER_PAN_KEYS, "")),
        section=str(_first_value(row, SECTION_KEYS, "")),
        category=category,
        amount=amount,
        tds=tds,
        transaction_date=str(_first_value(row, DATE_KEYS, "")) or None,
        raw=row,
    )


def normalize_records(source: str, rows: list[dict[str, Any]]) -> list[TaxDocumentRecord]:
    return [normalize_record(source, r) for r in rows if isinstance(r, dict)]


def summarize_income(records: list[TaxDocumentRecord]) -> dict[str, float]:
    summary = defaultdict(float)
    tds_summary = defaultdict(float)
    for r in records:
        summary[r.category] += r.amount
        tds_summary[f"{r.category}_tds"] += r.tds
    summary["gross_total_income"] = sum(v for k, v in summary.items() if not k.endswith("_tds"))
    summary["total_tds"] = sum(r.tds for r in records)
    summary.update(tds_summary)
    return {k: round(v, 2) for k, v in summary.items()}


def compare_tds(ais: list[TaxDocumentRecord], form26as: list[TaxDocumentRecord]) -> list[dict[str, Any]]:
    def key(r: TaxDocumentRecord) -> str:
        return "|".join([r.payer_pan.upper().strip(), r.section.strip(), r.category])

    ais_map = defaultdict(float)
    form_map = defaultdict(float)
    label = {}
    for r in ais:
        k = key(r)
        ais_map[k] += r.tds
        label[k] = {"payer": r.payer_name, "payer_pan": r.payer_pan, "section": r.section, "category": r.category}
    for r in form26as:
        k = key(r)
        form_map[k] += r.tds
        label[k] = {"payer": r.payer_name, "payer_pan": r.payer_pan, "section": r.section, "category": r.category}

    mismatches = []
    for k in sorted(set(ais_map) | set(form_map)):
        diff = round(ais_map[k] - form_map[k], 2)
        if abs(diff) >= 1:
            mismatches.append({
                **label.get(k, {}),
                "ais_tds": round(ais_map[k], 2),
                "form26as_tds": round(form_map[k], 2),
                "difference": diff,
                "severity": "high" if abs(diff) >= 10000 else "medium" if abs(diff) >= 1000 else "low",
                "suggested_action": "Verify AIS/Form 26AS source record and confirm whether TDS credit is missing or duplicated.",
            })
    return mismatches


def suggest_itr_form(profile: TaxProfile, income_summary: dict[str, float]) -> dict[str, Any]:
    total_income = income_summary.get("gross_total_income", 0.0)
    reasons = []

    has_business = profile.has_business_income or income_summary.get("business_profession", 0) > 0
    has_capital = profile.has_capital_gains or income_summary.get("capital_gains", 0) > 0

    if profile.taxpayer_type in {"firm_llp"}:
        return {"suggested_itr": "ITR-5", "confidence": "medium", "reasons": ["Partnership firm / LLP profile selected."]}
    if profile.taxpayer_type == "company":
        return {"suggested_itr": "ITR-6", "confidence": "medium", "reasons": ["Company profile selected."]}
    if has_business:
        if profile.presumptive_income and not has_capital and not profile.has_foreign_assets:
            return {"suggested_itr": "ITR-4", "confidence": "medium", "reasons": ["Presumptive business/profession income selected."]}
        return {"suggested_itr": "ITR-3", "confidence": "medium", "reasons": ["Business/profession income detected."]}
    if has_capital or profile.has_foreign_assets or profile.has_crypto_income or profile.has_more_than_one_house:
        if has_capital:
            reasons.append("Capital gains detected.")
        if profile.has_foreign_assets:
            reasons.append("Foreign assets flag selected.")
        if profile.has_crypto_income:
            reasons.append("VDA/crypto income flag selected.")
        if profile.has_more_than_one_house:
            reasons.append("More than one house property flag selected.")
        return {"suggested_itr": "ITR-2", "confidence": "medium", "reasons": reasons}
    if total_income <= 5000000 and income_summary.get("salary", 0) >= 0:
        return {"suggested_itr": "ITR-1", "confidence": "medium", "reasons": ["Simple individual return: salary/interest/dividend/other sources and income within ₹50 lakh."]}
    return {"suggested_itr": "ITR-2", "confidence": "low", "reasons": ["Income profile is not simple enough for ITR-1."]}


def compute_slab_tax(income: float, slabs: list[tuple[float, float]]) -> float:
    tax = 0.0
    prev = 0.0
    for limit, rate in slabs:
        if income > prev:
            taxable = min(income, limit) - prev
            tax += taxable * rate
        if income <= limit:
            break
        prev = limit
    return round(tax, 2)


def old_regime_slabs_for_age(age: int) -> list[tuple[float, float]]:
    if age >= 80:
        return OLD_REGIME_SLABS_80_PLUS
    if age >= 60:
        return OLD_REGIME_SLABS_60_TO_79
    return OLD_REGIME_SLABS_BELOW_60


def compute_tax_summary(profile: TaxProfile, income_summary: dict[str, float]) -> dict[str, Any]:
    gross = float(income_summary.get("gross_total_income", 0.0))
    total_tds = float(income_summary.get("total_tds", 0.0))

    new_tax_before_cess = compute_slab_tax(gross, NEW_REGIME_SLABS_AY_2026_27)
    old_taxable = max(0.0, gross - float(profile.deductions_old_regime or 0))
    old_tax_before_cess = compute_slab_tax(old_taxable, old_regime_slabs_for_age(profile.age))

    new_tax = round(new_tax_before_cess * 1.04, 2)
    old_tax = round(old_tax_before_cess * 1.04, 2)

    paid = total_tds + float(profile.advance_tax_paid or 0) + float(profile.self_assessment_tax_paid or 0)
    recommended_regime = "new" if new_tax <= old_tax else "old"
    recommended_tax = min(new_tax, old_tax)

    return {
        "assessment_year": profile.assessment_year,
        "gross_total_income": round(gross, 2),
        "old_regime_taxable_income_after_declared_deductions": round(old_taxable, 2),
        "new_regime_tax_before_cess": new_tax_before_cess,
        "new_regime_tax_after_4_percent_cess": new_tax,
        "old_regime_tax_before_cess": old_tax_before_cess,
        "old_regime_tax_after_4_percent_cess": old_tax,
        "tax_paid_tds_advance_self_assessment": round(paid, 2),
        "recommended_regime_preliminary": recommended_regime,
        "estimated_payable_or_refund_preliminary": round(recommended_tax - paid, 2),
        "important_note": "Preliminary calculator only. CA must verify deductions, exemptions, surcharge, rebate, special-rate income and latest law before filing.",
    }


def build_checklist(profile: TaxProfile, income_summary: dict[str, float], mismatches: list[dict[str, Any]]) -> list[dict[str, str]]:
    items = [
        {"task": "Verify PAN and assessment year", "status": "required"},
        {"task": "Reconcile AIS/TIS with Form 26AS", "status": "required"},
        {"task": "Verify bank account and refund details", "status": "required"},
        {"task": "Review old vs new regime comparison", "status": "required"},
    ]
    if income_summary.get("salary", 0) > 0:
        items.append({"task": "Match salary income with Form 16 and AIS", "status": "required"})
    if income_summary.get("interest", 0) > 0:
        items.append({"task": "Confirm savings/FD interest with bank statements", "status": "required"})
    if income_summary.get("dividend", 0) > 0:
        items.append({"task": "Verify dividend income and TDS section", "status": "required"})
    if income_summary.get("capital_gains", 0) > 0 or profile.has_capital_gains:
        items.append({"task": "Upload broker capital gains statement and verify STCG/LTCG classification", "status": "required"})
    if profile.has_foreign_assets:
        items.append({"task": "Complete foreign asset schedule review", "status": "high_risk"})
    if mismatches:
        items.append({"task": f"Resolve {len(mismatches)} AIS/Form 26AS TDS mismatch(es)", "status": "high_priority"})
    return items


def analyze_tax(request: TaxAnalyzeRequest) -> dict[str, Any]:
    ais = normalize_records("AIS", request.ais_records)
    tis = normalize_records("TIS", request.tis_records)
    form26as = normalize_records("Form 26AS", request.form26as_records)
    form16 = normalize_records("Form 16", request.form16_records)
    books = normalize_records("Books", request.books_records)

    all_records = ais + tis + form26as + form16 + books
    income_summary = summarize_income(all_records)
    tds_mismatches = compare_tds(ais, form26as)
    itr = suggest_itr_form(request.profile, income_summary)
    tax_summary = compute_tax_summary(request.profile, income_summary)
    checklist = build_checklist(request.profile, income_summary, tds_mismatches)

    risk_flags = []
    if tds_mismatches:
        risk_flags.append({"risk": "TDS mismatch", "severity": "high", "count": len(tds_mismatches)})
    if income_summary.get("capital_gains", 0) > 0 and not request.profile.has_capital_gains:
        risk_flags.append({"risk": "Capital gains detected but profile flag not selected", "severity": "medium"})
    if income_summary.get("business_profession", 0) > 0 and not request.profile.has_business_income:
        risk_flags.append({"risk": "Business/profession income detected but profile flag not selected", "severity": "medium"})

    return {
        "analysis_id": f"tax-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "profile": request.profile.model_dump(),
        "income_summary": income_summary,
        "tax_summary": tax_summary,
        "itr_suggestion": itr,
        "tds_mismatches": tds_mismatches,
        "risk_flags": risk_flags,
        "filing_checklist": checklist,
        "records_count": {
            "ais": len(ais),
            "tis": len(tis),
            "form26as": len(form26as),
            "form16": len(form16),
            "books": len(books),
            "total": len(all_records),
        },
        "disclaimer": "This is an assistant output for CA review. It is not final tax filing advice and should not be filed without professional verification.",
    }
