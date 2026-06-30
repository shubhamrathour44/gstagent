# GSTAgent – Architecture & Developer Guide

## Project Overview

**GSTAgent** is a CA Practice Management Platform for GST reconciliation and compliance in India. It enables Chartered Accountants to match purchase/sales registers against GST returns (GSTR-2B/GSTR-1), identify mismatches, and manage GST compliance workflows.

- **Backend:** FastAPI (Python 3.9+)
- **Database:** PostgreSQL (Railway) / SQLite (local)
- **Frontend:** Vanilla HTML/JavaScript SPA
- **Deployment:** Railway (backend) + Vercel (frontend)
- **Version:** 2.1.0

---

## Architecture Overview

### Backend Structure

```
backend/
├── main_v2.py              # FastAPI app entry point, router mounting
├── database.py             # SQLAlchemy ORM, models, repository pattern
├── auth.py                 # JWT authentication, user/firm management
│
├── Modularized Services (subdirectories):
│   ├── gsp/                # GST Portal integration (GSTR-2B/1 fetch)
│   ├── reconciliation/     # Core reconciliation engine & routes
│   ├── tax/                # Tax analysis and compliance rules
│   ├── crm/                # Client management
│   ├── billing/            # Invoice and payment tracking
│   ├── compliance/         # Regulatory tracking and notices
│   ├── documents/          # Document storage and retrieval
│   ├── notices/            # GST notice management
│   ├── tasks/              # Task workflow
│   ├── itr/                # Income Tax Return handling
│   ├── bill_reader/        # Invoice scanning/OCR
│   ├── tally_import/       # Tally integration
│   └── zoho_import/        # Zoho Books integration
│
├── Flat Services (to be modularized):
│   ├── reconcile_saved.py  # Saved reconciliation queries
│   ├── invoices.py         # Invoice CRUD operations
│   ├── excel_export.py     # Excel report generation
│   ├── ai_agent.py         # AI-powered recommendations
│   ├── password_reset.py   # Password recovery flow
│   └── integrations.py     # Third-party API connectors
│
└── Utilities:
    ├── init_db.py          # Database initialization
    ├── form26as.py         # Form 26AS parsing
    └── tds.py              # TDS handling
```

---

## Core Data Model

### Entity Relationships

```
CAFirm (1) ──── (n) User
        └────────────────(n) GSTClient
                              └──── (n) Reconciliation
                                    └──── (n) Mismatch
```

### Key Entities

| Table | Purpose | Tenant Scoping |
|-------|---------|---|
| `ca_firms` | CA practice entity | Root tenant |
| `users` | Team members within a firm | `firm_id` |
| `gst_clients` | Businesses managed by the firm | `firm_id` |
| `reconciliations` | Match results for a period | `firm_id`, `client_id`, `period` |
| `mismatches` | Individual discrepancies (MM0001, etc) | `firm_id`, `reconciliation_id` |
| `audit_logs` | Action trail for compliance | `firm_id` |

**Tenant Isolation:** All data queries filter by `firm_id` to ensure multi-tenant security. This is enforced in repository pattern and auth middleware.

---

## Key Flows

### 1. User Authentication
```
Client Login → verify_token() → JWT payload extracted → Dependency: current_user → Route handler
```
- Tokens created in `create_access_token()`
- Verified via `HTTPBearer` security scheme
- User/firm tied via `User.firm_id`

### 2. Reconciliation Workflow
```
CSV Upload → parse_register() → Reconciliation Engine → Match vs GSTR-2B → Create Mismatches → Store in DB
```
- **Input:** Purchase/Sales register (CSV/Excel)
- **Processing:** `reconciliation_engine.py` classifies differences
- **Output:** Reconciliation record + Mismatch items
- **Impact:** Slow for large files (see optimizations below)

### 3. GSP Integration
```
POST /gsp/gstr2b/fetch → GSP Client (mock or live) → Parse response → Return JSON
```
- **Mock Mode:** Returns synthetic data (default, dev-friendly)
- **Live Mode:** Calls external GSP provider (MasterGST, WhiteBooks, etc)
- **Config:** See `.env.gsp.example` for environment variables

---

## Database Layer – Repository Pattern

All data access goes through repositories in `database.py`. This centralizes queries and ensures consistency:

```python
# Example: Get a client for a firm
client = await ClientRepo.get_by_gstin(db, gstin="05ABCDE1234F1Z5", firm_id=firm_id)

# Example: Create a reconciliation
recon = await ReconciliationRepo.create(
    db,
    firm_id=firm_id,
    client_id=client_id,
    company_name="XYZ Ltd",
    source="file_upload",
    result_json={...},
    created_by=user_id
)
```

**Repositories:**
- `FirmRepo` – Create/fetch CA firms
- `UserRepo` – User CRUD
- `ClientRepo` – Client management
- `ReconciliationRepo` – Reconciliation create/fetch/list
- `MismatchRepo` – Mismatch updates and resolutions
- `AuditRepo` – Audit trail logging

---

## Module Responsibilities

### `gsp/` – GST Portal Connector
- **File:** `client.py`, `router.py`, `schemas.py`
- **Purpose:** Fetch GSTR-2B, GSTR-1, verify GSTIN via authorized GSP
- **Endpoints:**
  - `GET /gsp/gstin/{gstin}/verify` – Verify GSTIN
  - `POST /gsp/gstr2b/fetch` – Fetch purchase invoice register
  - `POST /gsp/gstr1/fetch` – Fetch sales invoice register
  - `GET /gsp/filing-status` – Check return filing status
- **Modes:** Mock (test) | MasterGST | WhiteBooks | Custom (IRIS, GSTHero)
- **Config:** `GSP_PROVIDER`, `GSP_*` env vars

### `reconciliation/` – Core Matching Engine
- **File:** `router.py` + imports from `reconciliation_engine.py`
- **Purpose:** Accept register uploads, perform line-by-line matching
- **Endpoints:**
  - `POST /reconciliation/upload` – Upload purchase/sales register
  - `GET /reconciliation/{rec_id}` – Fetch reconciliation result
  - `POST /reconciliation/{rec_id}/mismatches` – List mismatches with filters
- **Performance Note:** Currently processes invoices sequentially. See "Optimizations" section.

### `tax/` – Tax Compliance
- **File:** `analyzer.py`, `router.py`, `schemas.py`
- **Purpose:** Tax calculations, filing deadline tracking, compliance rules
- **Key Logic:** ITR cross-checks, TDS reconciliation, advance tax planning

### `billing/` – Billing & Subscriptions
- **File:** `billing.py`
- **Purpose:** Manage CA firm subscription plans, invoice clients, track usage
- **Plans:** Starter, Professional, Enterprise (configurable)
- **Model:** SaaS billing with per-firm metering

### `crm/` – Client Management
- **File:** `router.py`, `schemas.py`
- **Purpose:** CRUD for `GSTClient` records, track Tally/Zoho integrations
- **Scoping:** Always filtered by `current_firm_id`

### `tally_import/` & `zoho_import/`
- **Purpose:** Sync with Tally.ERP9 and Zoho Books
- **Status:** Basic import scaffolding; see "Feature Gaps" for improvements

### `ai_agent/` – AI-Powered Assistance
- **File:** `ai_agent.py`, `ai_agent_router.py`
- **Purpose:** Generate mismatch explanations, vendor contact drafts, filing recommendations
- **Backend:** Calls LLM (Claude/OpenAI) to interpret reconciliation results

### Flat Modules (To Be Refactored)
- `invoices.py` – Invoice CRUD (should move to `billing/` or new `invoices/`)
- `reconcile_saved.py` – Saved reconciliation queries (move to `reconciliation/`)
- `excel_export.py` – Report generation (extract to shared utility)
- `password_reset.py` – Auth flow (should move to `auth/` as submodule)

---

## Database Indexing Strategy

**Current Indexes:**
- `email` (unique) on `users` and `ca_firms`
- `firm_id` on all tenant-scoped tables
- `gstin` on `gst_clients`
- `period` on `reconciliations`
- `severity`, `status` on `mismatches`

**Missing Indexes (add for performance):**
- `reconciliation_id` on `mismatches` (already foreign key, but add explicit non-unique index)
- `(firm_id, created_at DESC)` on `reconciliations` for fast recent queries
- `(firm_id, status)` on `mismatches` for filtered lookups

---

## Development Workflow

### Setup (First Time)

```bash
# Clone and navigate
git clone <repo>
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Initialize database
python database.py  # Creates tables in local SQLite

# Create .env (or .env.local)
cat > .env << EOF
DATABASE_URL=sqlite:///./gstagent.db
JWT_SECRET_KEY=your-random-256-bit-key-here
GSP_PROVIDER=mock
EOF

# Run server
python main_v2.py
# API docs: http://localhost:8000/docs
```

### Local Development

```bash
# With auto-reload
python main_v2.py

# Or with uvicorn directly
uvicorn main_v2:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `DATABASE_URL` | Postgres or SQLite | `sqlite:///./gstagent.db` |
| `JWT_SECRET_KEY` | Signing key for tokens | (change in prod!) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token TTL | `480` (8 hours) |
| `GSP_PROVIDER` | mock, mastergst, whitebooks | `mock` |
| `GSP_*` | Provider-specific credentials | (see `.env.gsp.example`) |
| `SQL_ECHO` | SQLAlchemy query logging | `0` |

---

## Code Patterns & Conventions

### 1. Dependency Injection (FastAPI)
```python
@router.get("/items")
async def list_items(db: AsyncSession = Depends(get_db), current_user: User = Depends(current_user)):
    # db and current_user are injected
    pass
```

### 2. Repository Pattern (Data Access)
```python
# DON'T do raw queries in routes
# DO use repositories
client = await ClientRepo.get_by_gstin(db, gstin, firm_id)
```

### 3. Pydantic Schemas (Request/Response)
```python
# Request
class CreateClientRequest(BaseModel):
    name: str
    gstin: str
    
# Response
class ClientResponse(BaseModel):
    id: str
    name: str
    gstin: str
    created_at: datetime
```

### 4. Tenant Isolation
```python
# ALWAYS filter by firm_id
result = await db.execute(
    select(GSTClient)
    .where(and_(GSTClient.firm_id == firm_id, GSTClient.gstin == gstin))
)
# Don't trust current_user.firm_id alone; also validate in the query
```

### 5. Error Handling
```python
from fastapi import HTTPException, status

if not resource:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
if not permission:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
```

### 6. Async/Await
```python
# All DB operations are async
recon = await ReconciliationRepo.create(db, ...)
clients = await ClientRepo.list_for_firm(db, firm_id)
```

---

## Known Issues & Tech Debt

1. **Reconciliation Performance**
   - Invoice matching is O(n²) for large files (>10k rows)
   - Blocking operation; no progress tracking
   - No batch processing or chunking

2. **Frontend is Outdated**
   - Vanilla HTML/JS (no framework)
   - No real-time updates (WebSocket)
   - Poor mobile responsiveness
   - Scattered components across many .html files

3. **Module Organization**
   - `invoices.py`, `reconcile_saved.py`, etc. should be in subdirectories
   - No clear separation between router, service, and schema layers
   - Missing shared utilities (logging, error handling, validators)

4. **Database**
   - No connection pooling config for high concurrency
   - Missing indexes for common queries
   - Audit log doesn't capture all mutations

5. **Integration Gaps**
   - Tally/Zoho sync is basic (one-time import only)
   - No real-time webhook support
   - GSP mock data is synthetic, not representative

6. **Testing**
   - No unit or integration tests
   - No test fixtures or factories
   - Manual testing only

---

## Optimization Opportunities

### Phase 2: Performance Enhancements (Coming)
- Batch invoice processing with pagination
- Async GSP fetches with caching
- Database connection pooling
- Elasticsearch for full-text search on invoices
- Background job queue (Celery/RQ) for heavy operations

### Phase 3: UI/UX Modernization (Coming)
- Migrate to React or Vue.js
- Add real-time WebSocket support
- Responsive mobile design
- Component library for consistency

---

## Key Files to Know

| File | Purpose |
|------|---------|
| `main_v2.py` | FastAPI app, router mounting |
| `database.py` | ORM models, repositories |
| `auth.py` | JWT, user auth |
| `reconciliation_engine.py` | Core matching logic |
| `gsp/client.py` | GSP provider interface |
| `billing.py` | Subscription & usage tracking |
| `ai_agent.py` | LLM integration for recommendations |

---

## Contributing

### Adding a New Module
1. Create a directory under `backend/MODULE_NAME/`
2. Inside, create: `__init__.py`, `router.py`, `schemas.py` (if needed)
3. Import the router in `main_v2.py` and mount it
4. Add to `/modules` endpoint list
5. Follow existing patterns (dependency injection, tenant isolation, error handling)

### Modifying Database Schema
1. Update model class in `database.py`
2. Drop existing SQLite/use Alembic migration for Postgres
3. Run `python database.py` to create tables

### Adding an Endpoint
1. Create a route function in the module's `router.py`
2. Use `Depends(get_db)` and `Depends(current_user)` for auth
3. Always validate `current_user.firm_id` in queries
4. Return `BaseModel` response (Pydantic schema)

---

## Support & Questions

- **Setup Issues:** Check `.env` and `DATABASE_URL`
- **Auth Errors:** Verify JWT_SECRET_KEY is set, token not expired
- **Database Errors:** Ensure PostgreSQL is running (production) or SQLite file writable
- **GSP Integration:** Use mock mode for testing; configure credentials for live

For more info, see inline code comments and test flows in module README files.
