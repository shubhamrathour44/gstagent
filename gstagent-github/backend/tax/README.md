# Income Tax Assistant Module

This module adds file-upload based Income Tax workflows to GSTAgent.

## Routes

- `GET /tax/status`
- `GET /tax/templates/sample`
- `POST /tax/analyze`
- `POST /tax/analyze/upload`
- `POST /tax/itr-suggest`
- `POST /tax/tax-summary`
- `POST /tax/export/xlsx`

## Supported v1 uploads

- AIS export: `.xlsx`, `.csv`, `.json`
- TIS export: `.xlsx`, `.csv`, `.json`
- Form 26AS export: `.xlsx`, `.csv`, `.json`
- Form 16 structured Excel/CSV/JSON
- Books records Excel/CSV/JSON

PDF parsing is intentionally disabled in v1 to keep deployment lightweight. Add `pypdf` later for PDF text extraction.

## Production note

This module provides CA-review assistance only. Do not file returns directly from AI output without human review.
