"""GSP connector interface and provider factory.

Important:
- This is NOT GST portal scraping.
- Production fetching must happen through a licensed GSP/ASP API contract.
- Default provider is `mock`, so the backend can be tested without credentials.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

import httpx
from fastapi import HTTPException

from .schemas import (
    FilingStatusResponse,
    GSTINVerificationResponse,
    GSTR1FetchResponse,
    GSTR2BFetchResponse,
)


class GSPProvider(ABC):
    name: str

    @abstractmethod
    async def verify_gstin(self, gstin: str) -> GSTINVerificationResponse:
        raise NotImplementedError

    @abstractmethod
    async def fetch_gstr2b(self, gstin: str, period: str) -> GSTR2BFetchResponse:
        raise NotImplementedError

    @abstractmethod
    async def fetch_gstr1(self, gstin: str, period: str) -> GSTR1FetchResponse:
        raise NotImplementedError

    @abstractmethod
    async def get_filing_status(self, gstin: str, period: str, return_type: str) -> FilingStatusResponse:
        raise NotImplementedError

    async def create_gstr3b_draft(self, gstin: str, period: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "gstin": gstin,
            "period": period,
            "source": self.name,
            "status": "draft_prepared_locally",
            "draft": payload,
            "warning": "Final filing must be reviewed and submitted by an authorised CA/taxpayer.",
        }


class MockGSPProvider(GSPProvider):
    """Safe sandbox provider for development and demos."""

    name = "mock"

    async def verify_gstin(self, gstin: str) -> GSTINVerificationResponse:
        return GSTINVerificationResponse(
            gstin=gstin,
            legal_name="Demo Taxpayer Private Limited",
            trade_name="Demo Taxpayer",
            status="Active",
            taxpayer_type="Regular",
            registration_date="01/07/2017",
            state_code=gstin[:2],
            address="Demo address from mock GSP provider",
            source=self.name,
            raw={"mock": True},
        )

    async def fetch_gstr2b(self, gstin: str, period: str) -> GSTR2BFetchResponse:
        invoices = [
            {
                "supplier_gstin": "07ABCDE1234F1Z5",
                "supplier_name": "Alpha Traders",
                "invoice_number": "A-1001",
                "invoice_date": "05/04/2026",
                "taxable_value": 100000,
                "igst": 0,
                "cgst": 9000,
                "sgst": 9000,
                "total_tax": 18000,
            },
            {
                "supplier_gstin": "27ABCDE5678G1Z2",
                "supplier_name": "Beta Services",
                "invoice_number": "B-221",
                "invoice_date": "12/04/2026",
                "taxable_value": 50000,
                "igst": 9000,
                "cgst": 0,
                "sgst": 0,
                "total_tax": 9000,
            },
        ]
        return GSTR2BFetchResponse(gstin=gstin, period=period, source=self.name, invoices=invoices, raw={"mock": True})

    async def fetch_gstr1(self, gstin: str, period: str) -> GSTR1FetchResponse:
        invoices = [
            {
                "recipient_gstin": "05PQRST1234L1Z3",
                "recipient_name": "Demo Buyer",
                "invoice_number": "S-5001",
                "invoice_date": "18/04/2026",
                "taxable_value": 125000,
                "igst": 22500,
                "cgst": 0,
                "sgst": 0,
                "total_tax": 22500,
            }
        ]
        return GSTR1FetchResponse(gstin=gstin, period=period, source=self.name, invoices=invoices, raw={"mock": True})

    async def get_filing_status(self, gstin: str, period: str, return_type: str) -> FilingStatusResponse:
        return FilingStatusResponse(gstin=gstin, period=period, return_type=return_type.upper(), status="not_filed", source=self.name, raw={"mock": True})


class HTTPGSPProvider(GSPProvider):
    """Generic HTTP adapter for real GSPs.

    Configure endpoint templates through environment variables after your GSP
    gives you sandbox/production API docs. This keeps GSTAgent provider-neutral.

    Required examples:
    MASTERGST_BASE_URL=https://api.mastergst.com
    MASTERGST_API_KEY=...
    MASTERGST_VERIFY_PATH=/public/search?gstin={gstin}
    MASTERGST_GSTR2B_PATH=/returns/gstr2b?gstin={gstin}&ret_period={period}
    """

    def __init__(self, name: str):
        self.name = name.lower()
        prefix = self.name.upper()
        self.base_url = os.getenv(f"{prefix}_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv(f"{prefix}_API_KEY", "")
        self.api_secret = os.getenv(f"{prefix}_API_SECRET", "")
        self.verify_path = os.getenv(f"{prefix}_VERIFY_PATH", "")
        self.gstr2b_path = os.getenv(f"{prefix}_GSTR2B_PATH", "")
        self.gstr1_path = os.getenv(f"{prefix}_GSTR1_PATH", "")
        self.status_path = os.getenv(f"{prefix}_FILING_STATUS_PATH", "")

    def _require_config(self, path: str, feature: str) -> str:
        if not self.base_url or not self.api_key or not path:
            raise HTTPException(
                status_code=503,
                detail=f"{self.name} {feature} API is not configured. Add {self.name.upper()}_BASE_URL, {self.name.upper()}_API_KEY and endpoint path env vars after GSP onboarding.",
            )
        return f"{self.base_url}{path}"

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.api_secret:
            headers["x-api-secret"] = self.api_secret
        return headers

    async def _get_json(self, url: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self._headers())
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail={"provider": self.name, "response": response.text[:1000]})
            return response.json()

    async def verify_gstin(self, gstin: str) -> GSTINVerificationResponse:
        path = self.verify_path.format(gstin=gstin)
        data = await self._get_json(self._require_config(path, "GSTIN verification"))
        return GSTINVerificationResponse(
            gstin=gstin,
            legal_name=data.get("legal_name") or data.get("lgnm") or data.get("legalName"),
            trade_name=data.get("trade_name") or data.get("tradeNam") or data.get("tradeName"),
            status=data.get("status") or data.get("sts") or "unknown",
            taxpayer_type=data.get("taxpayer_type") or data.get("dty"),
            registration_date=data.get("registration_date") or data.get("rgdt"),
            cancellation_date=data.get("cancellation_date") or data.get("cxdt"),
            state_code=gstin[:2],
            address=data.get("address") or data.get("pradr", {}).get("adr"),
            source=self.name,
            raw=data,
        )

    async def fetch_gstr2b(self, gstin: str, period: str) -> GSTR2BFetchResponse:
        path = self.gstr2b_path.format(gstin=gstin, period=period)
        data = await self._get_json(self._require_config(path, "GSTR-2B"))
        return GSTR2BFetchResponse(gstin=gstin, period=period, source=self.name, invoices=parse_gstr2b_invoices(data), raw=data)

    async def fetch_gstr1(self, gstin: str, period: str) -> GSTR1FetchResponse:
        path = self.gstr1_path.format(gstin=gstin, period=period)
        data = await self._get_json(self._require_config(path, "GSTR-1"))
        return GSTR1FetchResponse(gstin=gstin, period=period, source=self.name, invoices=parse_gstr1_invoices(data), raw=data)

    async def get_filing_status(self, gstin: str, period: str, return_type: str) -> FilingStatusResponse:
        path = self.status_path.format(gstin=gstin, period=period, return_type=return_type)
        data = await self._get_json(self._require_config(path, "filing status"))
        return FilingStatusResponse(
            gstin=gstin,
            period=period,
            return_type=return_type.upper(),
            status=data.get("status") or data.get("filing_status") or "unknown",
            filed_on=data.get("filed_on") or data.get("dof"),
            arn=data.get("arn"),
            source=self.name,
            raw=data,
        )


def parse_gstr2b_invoices(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalise common GSTR-2B JSON structures into engine-friendly rows."""
    records: list[dict[str, Any]] = []
    root = data.get("data", data)
    b2b_suppliers = root.get("docdata", {}).get("b2b") or root.get("b2b") or []
    for supplier in b2b_suppliers:
        supplier_gstin = supplier.get("ctin") or supplier.get("supplier_gstin") or ""
        supplier_name = supplier.get("trdnm") or supplier.get("supplier_name") or supplier.get("name") or ""
        for inv in supplier.get("inv", supplier.get("invoices", [])):
            items = inv.get("items") or inv.get("itms") or [{}]
            for item in items:
                row = item.get("itm_det", item)
                igst = float(row.get("iamt", row.get("igst", 0)) or 0)
                cgst = float(row.get("camt", row.get("cgst", 0)) or 0)
                sgst = float(row.get("samt", row.get("sgst", 0)) or 0)
                records.append({
                    "supplier_gstin": supplier_gstin,
                    "supplier_name": supplier_name,
                    "invoice_number": inv.get("inum") or inv.get("invoice_number") or "",
                    "invoice_date": inv.get("idt") or inv.get("invoice_date") or "",
                    "taxable_value": float(row.get("txval", row.get("taxable_value", 0)) or 0),
                    "igst": igst,
                    "cgst": cgst,
                    "sgst": sgst,
                    "total_tax": igst + cgst + sgst,
                    "reverse_charge": str(inv.get("rev", "N")).upper() == "Y",
                })
    if not records and isinstance(data.get("invoices"), list):
        records = data["invoices"]
    return records


def parse_gstr1_invoices(data: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    root = data.get("data", data)
    b2b = root.get("b2b") or []
    for receiver in b2b:
        recipient_gstin = receiver.get("ctin") or receiver.get("recipient_gstin") or ""
        for inv in receiver.get("inv", receiver.get("invoices", [])):
            taxable = 0.0
            tax = 0.0
            for item in inv.get("itms", inv.get("items", [])):
                row = item.get("itm_det", item)
                taxable += float(row.get("txval", 0) or 0)
                tax += float(row.get("iamt", 0) or 0) + float(row.get("camt", 0) or 0) + float(row.get("samt", 0) or 0)
            records.append({
                "recipient_gstin": recipient_gstin,
                "invoice_number": inv.get("inum", ""),
                "invoice_date": inv.get("idt", ""),
                "taxable_value": taxable,
                "total_tax": tax,
            })
    if not records and isinstance(data.get("invoices"), list):
        records = data["invoices"]
    return records


def get_provider(provider_name: str | None = None) -> GSPProvider:
    name = (provider_name or os.getenv("GSP_PROVIDER", "mock")).lower().strip()
    if name in {"mock", "sandbox", "demo"}:
        return MockGSPProvider()
    if name in {"mastergst", "whitebooks", "gsthero", "iris"}:
        return HTTPGSPProvider(name)
    raise HTTPException(status_code=400, detail=f"Unsupported GSP provider: {name}")


def provider_status() -> dict[str, Any]:
    configured = []
    for name in ["mastergst", "whitebooks", "gsthero", "iris"]:
        prefix = name.upper()
        configured.append({
            "provider": name,
            "base_url_configured": bool(os.getenv(f"{prefix}_BASE_URL")),
            "api_key_configured": bool(os.getenv(f"{prefix}_API_KEY")),
            "gstr2b_path_configured": bool(os.getenv(f"{prefix}_GSTR2B_PATH")),
            "gstr1_path_configured": bool(os.getenv(f"{prefix}_GSTR1_PATH")),
            "status_path_configured": bool(os.getenv(f"{prefix}_FILING_STATUS_PATH")),
        })
    return {
        "active_provider": os.getenv("GSP_PROVIDER", "mock"),
        "mode": "production_gsp" if os.getenv("GSP_PROVIDER", "mock").lower() != "mock" else "mock_sandbox",
        "providers": configured,
        "note": "Use mock for demos. For live GST portal data, complete ASP/GSP onboarding and add provider credentials/endpoints.",
    }
