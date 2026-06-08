# GSTAgent GSP Connector Module

This update adds a provider-neutral GSP connector under `gsp/`.

## What is included

- `gsp/client.py` — provider interface, mock sandbox provider, generic HTTP provider for MasterGST/WhiteBooks/GSTHero/IRIS style APIs.
- `gsp/schemas.py` — request/response schemas.
- `gsp/router.py` — FastAPI routes mounted at `/gsp`.
- `.env.gsp.example` — environment variables for switching from mock to real GSP credentials.

## New API endpoints

All endpoints require Bearer auth.

```text
GET  /gsp/status
GET  /gsp/gstin/{gstin}/verify
POST /gsp/gstr2b/fetch
POST /gsp/gstr1/fetch
GET  /gsp/filing-status?gstin=...&period=042026&return_type=GSTR3B
POST /gsp/gstr3b/draft
POST /gsp/reconcile/gstr2b
```

## Default mode

By default the connector runs in mock mode:

```env
GSP_PROVIDER=mock
```

This lets you test your frontend and backend without live GST portal access.

## Production mode

After you complete ASP/GSP onboarding, your GSP will provide:

- Sandbox base URL
- Production base URL
- API key / client ID
- Secret / token flow
- Exact endpoint paths
- Headers and authentication rules

Then set environment variables such as:

```env
GSP_PROVIDER=mastergst
MASTERGST_BASE_URL=https://api.your-gsp.com
MASTERGST_API_KEY=your_key
MASTERGST_API_SECRET=your_secret
MASTERGST_VERIFY_PATH=/gstin/verify/{gstin}
MASTERGST_GSTR2B_PATH=/returns/gstr2b?gstin={gstin}&ret_period={period}
MASTERGST_GSTR1_PATH=/returns/gstr1?gstin={gstin}&ret_period={period}
MASTERGST_FILING_STATUS_PATH=/returns/status?gstin={gstin}&ret_period={period}&return_type={return_type}
```

## Test flow

1. Register/login and copy the JWT token.
2. Call `GET /gsp/status`.
3. Call `GET /gsp/gstin/05ABCDE1234F1Z5/verify`.
4. Call `POST /gsp/gstr2b/fetch` with:

```json
{
  "gstin": "05ABCDE1234F1Z5",
  "period": "042026"
}
```

5. Call `POST /gsp/reconcile/gstr2b` with purchase register rows to create a saved reconciliation from GSP-fetched GSTR-2B.

## Important compliance note

This module does not scrape the GST portal. Live GST data must be accessed only through an authorised GSP/ASP route with taxpayer consent and your GSP contract.
