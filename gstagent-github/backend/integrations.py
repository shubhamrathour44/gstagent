"""
GSTAgent — Tally ODBC Connector
Pulls purchase register data directly from Tally Prime / Tally ERP 9.

How it works:
    Tally exposes an XML/HTTP API on localhost:9000 by default.
    We send TDL (Tally Definition Language) XML requests and parse responses.
    No ODBC driver needed — works over HTTP.

Requirements:
    - Tally must be running on the same machine or accessible on LAN
    - Tally Gateway Server must be enabled (F12 > Advanced Config > Client/Server > Enable ODBC Server)
    - pip install httpx lxml

Setup for customer:
    1. Open Tally
    2. Press F12 > Advanced Configuration
    3. Enable "Act as ODBC Server"
    4. Note the port (default 9000)
    5. Enter company name and port in GSTAgent settings
"""

import httpx
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, date
import re


# ─── DATA CLASSES ─────────────────────────────────────────────────────────────

@dataclass
class TallyInvoice:
    voucher_number: str
    voucher_date: str
    party_name: str
    party_gstin: str
    ledger_name: str
    taxable_value: float
    igst: float = 0.0
    cgst: float = 0.0
    sgst: float = 0.0
    cess: float = 0.0
    reverse_charge: bool = False
    voucher_type: str = "Purchase"

    @property
    def total_tax(self):
        return self.igst + self.cgst + self.sgst + self.cess

    def to_dict(self) -> dict:
        return {
            "invoice_number": self.voucher_number,
            "invoice_date": self.voucher_date,
            "supplier_name": self.party_name,
            "supplier_gstin": self.party_gstin,
            "taxable_value": self.taxable_value,
            "igst": self.igst,
            "cgst": self.cgst,
            "sgst": self.sgst,
            "reverse_charge": self.reverse_charge,
            "source": "tally"
        }


@dataclass
class TallyConfig:
    host: str = "localhost"
    port: int = 9000
    company_name: str = ""   # Exact Tally company name
    timeout: float = 30.0


# ─── TALLY XML REQUESTS ───────────────────────────────────────────────────────

def _build_purchase_register_request(company: str, from_date: str, to_date: str) -> str:
    """
    Build TDL XML request to pull purchase vouchers with GST details.
    Dates format: YYYYMMDD
    """
    return f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Voucher Register</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <SVFROMDATE>{from_date}</SVFROMDATE>
          <SVTODATE>{to_date}</SVTODATE>
          <SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY>
          <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


def _build_ledger_gstin_request(company: str, ledger_name: str) -> str:
    """Fetch GSTIN for a specific ledger (supplier)."""
    return f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>List of Accounts</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY>
        </STATICVARIABLES>
      </REQUESTDESC>
      <REQUESTDATA>
        <TALLYMESSAGE>
          <LEDGER NAME="{ledger_name}" FETCH="GSTREGISTRATIONDETAILS.GSTIN"/>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


def _build_gst_purchase_report_request(company: str, from_date: str, to_date: str) -> str:
    """
    Direct GST Purchase Register report from Tally.
    This is the preferred method as it includes pre-parsed GST amounts.
    """
    return f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>GSTR2</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <SVFROMDATE>{from_date}</SVFROMDATE>
          <SVTODATE>{to_date}</SVTODATE>
          <SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


# ─── TALLY CONNECTOR ──────────────────────────────────────────────────────────

class TallyConnector:
    """
    Connects to Tally via HTTP XML API.
    Works with Tally Prime and Tally ERP 9.
    """

    def __init__(self, config: TallyConfig):
        self.config = config
        self.base_url = f"http://{config.host}:{config.port}"

    async def test_connection(self) -> dict:
        """Test if Tally is running and accessible."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Send a minimal request to check if Tally responds
                xml = f"""<ENVELOPE>
  <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>List of Companies</REPORTNAME>
        <STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""
                resp = await client.post(self.base_url, content=xml, headers={"Content-Type": "text/xml"})
                if resp.status_code == 200:
                    companies = self._parse_company_list(resp.text)
                    return {"status": "connected", "companies": companies}
                return {"status": "error", "message": f"HTTP {resp.status_code}"}
        except httpx.ConnectError:
            return {
                "status": "unreachable",
                "message": f"Cannot connect to Tally at {self.base_url}. Is Tally running with ODBC server enabled?",
                "fix": "In Tally: F12 > Advanced Configuration > Enable 'Act as ODBC Server'"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_purchase_register(
        self,
        period: str   # MMYYYY e.g. 032025
    ) -> list[dict]:
        """
        Fetch purchase register from Tally for a given period.
        Returns list of invoice dicts ready for reconciliation engine.
        """
        month = period[:2]
        year = period[2:]
        from_date = f"{year}{month}01"

        # Last day of month
        import calendar
        last_day = calendar.monthrange(int(year), int(month))[1]
        to_date = f"{year}{month}{last_day:02d}"

        xml_request = _build_gst_purchase_report_request(
            self.config.company_name, from_date, to_date
        )

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                resp = await client.post(
                    self.base_url,
                    content=xml_request,
                    headers={"Content-Type": "text/xml"}
                )
                resp.raise_for_status()
                return self._parse_purchase_register(resp.text)
        except httpx.ConnectError:
            raise ConnectionError(
                f"Tally not accessible at {self.base_url}. "
                "Check that Tally is open and ODBC server is enabled."
            )

    def _parse_purchase_register(self, xml_text: str) -> list[dict]:
        """Parse Tally XML response into invoice dicts."""
        invoices = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        # Tally XML structure varies by version — handle both GSTR2 and Voucher Register
        for voucher in root.iter("VOUCHER"):
            try:
                inv = self._parse_voucher(voucher)
                if inv:
                    invoices.append(inv.to_dict())
            except Exception:
                continue

        # Also try GSTR2 report format
        if not invoices:
            for entry in root.iter("GSTR2DETAILS"):
                try:
                    inv = self._parse_gstr2_entry(entry)
                    if inv:
                        invoices.append(inv.to_dict())
                except Exception:
                    continue

        return invoices

    def _parse_voucher(self, voucher_elem: ET.Element) -> Optional[TallyInvoice]:
        """Parse a single VOUCHER element."""
        def get(tag, default=""):
            el = voucher_elem.find(f".//{tag}")
            return el.text.strip() if el is not None and el.text else default

        voucher_type = get("VOUCHERTYPENAME")
        if "purchase" not in voucher_type.lower():
            return None

        # Extract GST amounts from ledger entries
        igst = cgst = sgst = 0.0
        taxable_value = 0.0

        for ledger in voucher_elem.iter("LEDGERENTRIES.LIST"):
            ledger_name = get_child_text(ledger, "LEDGERNAME", "").lower()
            amount = abs(float(get_child_text(ledger, "AMOUNT", "0") or 0))

            if "igst" in ledger_name:
                igst = amount
            elif "cgst" in ledger_name:
                cgst = amount
            elif "sgst" in ledger_name or "utgst" in ledger_name:
                sgst = amount
            elif any(x in ledger_name for x in ["purchase", "stock", "expense", "asset"]):
                taxable_value += amount

        # Try to get GSTIN from party GSTIN field
        gstin = get("PARTYGSTIN") or get("GSTREGISTRATIONDETAILS.GSTIN") or ""

        # Clean GSTIN
        gstin = re.sub(r'[^A-Z0-9]', '', gstin.upper())

        voucher_date = get("DATE") or get("VOUCHERDATE") or ""
        if len(voucher_date) == 8:
            voucher_date = f"{voucher_date[6:]}-{voucher_date[4:6]}-{voucher_date[:4]}"

        return TallyInvoice(
            voucher_number=get("VOUCHERNUMBER") or get("REFERENCENO"),
            voucher_date=voucher_date,
            party_name=get("PARTYLEDGERNAME"),
            party_gstin=gstin,
            ledger_name=get("PARTYLEDGERNAME"),
            taxable_value=taxable_value,
            igst=igst,
            cgst=cgst,
            sgst=sgst,
            reverse_charge=get("ISREVERSECHARGE", "No").upper() == "YES",
        )

    def _parse_gstr2_entry(self, entry: ET.Element) -> Optional[TallyInvoice]:
        """Parse a GSTR2DETAILS entry from Tally's built-in GSTR2 report."""
        def get(tag, default=""):
            el = entry.find(f".//{tag}")
            return el.text.strip() if el is not None and el.text else default

        gstin = re.sub(r'[^A-Z0-9]', '', get("GSTIN").upper())
        if not gstin:
            return None

        return TallyInvoice(
            voucher_number=get("INVOICENUMBER") or get("BILLNO"),
            voucher_date=get("INVOICEDATE") or get("DATE"),
            party_name=get("PARTYNAME") or get("SUPPLIERNAME"),
            party_gstin=gstin,
            ledger_name=get("PARTYNAME"),
            taxable_value=abs(float(get("TAXABLEAMOUNT", "0") or 0)),
            igst=abs(float(get("IGSTAMOUNT", "0") or 0)),
            cgst=abs(float(get("CGSTAMOUNT", "0") or 0)),
            sgst=abs(float(get("SGSTAMOUNT", "0") or 0)),
            reverse_charge=get("ISREVERSECHARGE", "No").upper() == "YES",
        )

    def _parse_company_list(self, xml_text: str) -> list[str]:
        """Parse list of companies from Tally."""
        companies = []
        try:
            root = ET.fromstring(xml_text)
            for company in root.iter("COMPANY"):
                name = company.find("NAME")
                if name is not None and name.text:
                    companies.append(name.text.strip())
        except Exception:
            pass
        return companies


def get_child_text(element: ET.Element, tag: str, default: str = "") -> str:
    el = element.find(tag)
    return el.text.strip() if el is not None and el.text else default


# ─── FASTAPI ROUTES ───────────────────────────────────────────────────────────

from fastapi import APIRouter

tally_router = APIRouter(prefix="/tally", tags=["Tally Integration"])


@tally_router.post("/test-connection")
async def test_tally_connection(host: str = "localhost", port: int = 9000, company: str = ""):
    """Test if Tally is accessible from the server."""
    config = TallyConfig(host=host, port=port, company_name=company)
    connector = TallyConnector(config)
    result = await connector.test_connection()
    return result


@tally_router.post("/fetch-purchase-register")
async def fetch_from_tally(
    host: str = "localhost",
    port: int = 9000,
    company: str = "",
    period: str = "032025"
):
    """
    Fetch purchase register from Tally for a given period.
    Returns data ready for reconciliation.
    """
    config = TallyConfig(host=host, port=port, company_name=company)
    connector = TallyConnector(config)

    try:
        invoices = await connector.get_purchase_register(period)
        return {
            "source": "tally",
            "company": company,
            "period": period,
            "invoice_count": len(invoices),
            "invoices": invoices
        }
    except ConnectionError as e:
        return {
            "error": str(e),
            "fix": "Ensure Tally is open and HTTP server is enabled on the correct port."
        }


# ─── ZOHO BOOKS CONNECTOR ─────────────────────────────────────────────────────

class ZohoConnector:
    """
    Zoho Books API connector.
    Uses OAuth2 with refresh token flow.
    
    Setup:
    1. Create app at https://api-console.zoho.in/
    2. Add redirect URI: https://yourapp.com/zoho/callback
    3. Get client_id and client_secret
    4. User authorises → exchange code for refresh_token
    5. Store refresh_token encrypted in DB
    """

    AUTH_URL = "https://accounts.zoho.in/oauth/v2/token"
    API_BASE = "https://books.zoho.in/api/v3"

    def __init__(self, client_id: str, client_secret: str, refresh_token: str, org_id: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.org_id = org_id
        self._access_token: Optional[str] = None

    async def _get_access_token(self) -> str:
        """Exchange refresh token for access token."""
        if self._access_token:
            return self._access_token

        async with httpx.AsyncClient() as client:
            resp = await client.post(self.AUTH_URL, data={
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token
            })
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            return self._access_token

    async def get_purchase_register(self, period: str) -> list[dict]:
        """
        Fetch bills from Zoho Books for a period.
        Maps to purchase register format.
        """
        token = await self._get_access_token()
        month = period[:2]
        year = period[2:]

        import calendar
        last_day = calendar.monthrange(int(year), int(month))[1]
        from_date = f"{year}-{month}-01"
        to_date = f"{year}-{month}-{last_day:02d}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.API_BASE}/bills",
                headers={"Authorization": f"Zoho-oauthtoken {token}"},
                params={
                    "organization_id": self.org_id,
                    "date_start": from_date,
                    "date_end": to_date,
                    "per_page": 200,
                    "page": 1
                }
            )
            resp.raise_for_status()
            data = resp.json()

        invoices = []
        for bill in data.get("bills", []):
            # Get full bill details for tax breakdown
            bill_detail = await self._get_bill_detail(token, bill["bill_id"])
            if bill_detail:
                inv = self._map_bill_to_invoice(bill_detail)
                if inv:
                    invoices.append(inv)

        return invoices

    async def _get_bill_detail(self, token: str, bill_id: str) -> Optional[dict]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.API_BASE}/bills/{bill_id}",
                headers={"Authorization": f"Zoho-oauthtoken {token}"},
                params={"organization_id": self.org_id}
            )
            if resp.status_code == 200:
                return resp.json().get("bill")
        return None

    def _map_bill_to_invoice(self, bill: dict) -> Optional[dict]:
        """Map Zoho bill to reconciliation engine format."""
        gstin = bill.get("vendor_gst_no", "").strip().upper()
        if not gstin:
            return None   # Skip bills without GSTIN

        # Extract IGST, CGST, SGST from taxes
        igst = cgst = sgst = 0.0
        for tax in bill.get("taxes", []):
            tax_name = tax.get("tax_name", "").lower()
            amount = float(tax.get("tax_amount", 0))
            if "igst" in tax_name:
                igst = amount
            elif "cgst" in tax_name:
                cgst = amount
            elif "sgst" in tax_name or "utgst" in tax_name:
                sgst = amount

        return {
            "invoice_number": bill.get("bill_number", ""),
            "invoice_date": bill.get("date", ""),
            "supplier_name": bill.get("vendor_name", ""),
            "supplier_gstin": gstin,
            "taxable_value": float(bill.get("sub_total", 0)),
            "igst": igst,
            "cgst": cgst,
            "sgst": sgst,
            "reverse_charge": bill.get("is_reverse_charge_applicable", False),
            "source": "zoho"
        }


zoho_router = APIRouter(prefix="/zoho", tags=["Zoho Integration"])


@zoho_router.get("/auth-url")
async def get_zoho_auth_url(client_id: str, redirect_uri: str):
    """Step 1: Get Zoho OAuth URL to redirect user to."""
    return {
        "url": f"https://accounts.zoho.in/oauth/v2/auth?scope=ZohoBooks.bills.READ&client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&access_type=offline"
    }


@zoho_router.post("/exchange-code")
async def exchange_zoho_code(code: str, client_id: str, client_secret: str, redirect_uri: str):
    """Step 2: Exchange auth code for refresh token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://accounts.zoho.in/oauth/v2/token",
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "code": code
            }
        )
        data = resp.json()
        return {
            "refresh_token": data.get("refresh_token"),
            "note": "Store this refresh_token encrypted in your database"
        }
