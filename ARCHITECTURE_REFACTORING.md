# GSTAgent – Architecture Refactoring Roadmap

## Overview

This document outlines a step-by-step plan to modularize and reorganize the backend for better maintainability, testability, and scalability.

---

## Current State Assessment

### Strengths ✓
- Database models well-organized with repository pattern
- Clear separation of concerns for modularized services (gsp/, reconciliation/, etc.)
- Multi-tenant architecture with firm_id isolation
- Proper use of async/await with SQLAlchemy
- JWT-based authentication

### Pain Points ✗
1. **Flat file structure** – Multiple .py files at root level mixing concerns
2. **Inconsistent patterns** – Some modules have routers only; others have business logic in routers
3. **Code duplication** – Invoice handling, reconciliation queries spread across files
4. **Missing layer separation** – No clear service/domain logic layer
5. **Incomplete modules** – Tally/Zoho integrations are basic stubs
6. **No shared utilities** – Validators, formatters, error handlers duplicated
7. **Testing impossible** – No dependency injection for business logic, tightly coupled to FastAPI

---

## Target Architecture

### Recommended 3-Layer Pattern

```
FastAPI Router Layer (request/response)
        ↓
Service/Domain Layer (business logic)
        ↓
Repository Layer (data access)
```

### Target Directory Structure

```
backend/
├── core/                          # NEW: Shared utilities
│   ├── __init__.py
│   ├── config.py                  # Environment, constants
│   ├── exceptions.py              # Custom exceptions
│   ├── schemas.py                 # Common Pydantic models
│   ├── validators.py              # Reusable validators
│   └── logger.py                  # Centralized logging
│
├── auth/                          # REFACTORED: Extract from auth.py
│   ├── __init__.py
│   ├── models.py                  # (if new models needed)
│   ├── schemas.py
│   ├── service.py                 # Business logic
│   ├── dependencies.py            # Dependency injection (current_user, etc.)
│   └── router.py
│
├── clients/                       # REFACTORED: Extract from crm
│   ├── __init__.py
│   ├── schemas.py
│   ├── service.py                 # Client CRUD logic
│   └── router.py
│
├── invoices/                      # REFACTORED: Move invoices.py here
│   ├── __init__.py
│   ├── schemas.py
│   ├── service.py                 # Invoice CRUD
│   └── router.py
│
├── reconciliation/                # REFACTORED: Expand existing
│   ├── __init__.py
│   ├── engine.py                  # Move from reconciliation_engine.py
│   ├── schemas.py
│   ├── service.py                 # NEW: Orchestrate matching
│   ├── saved_queries.py           # Move from reconcile_saved.py
│   └── router.py
│
├── gsp/                           # KEEP: Already well-structured
│   ├── __init__.py
│   ├── client.py
│   ├── schemas.py
│   └── router.py
│
├── integrations/                  # REFACTORED: Merge tally/zoho
│   ├── __init__.py
│   ├── tally/
│   │   ├── __init__.py
│   │   ├── service.py
│   │   └── mapper.py              # CSV→Invoice mapping
│   ├── zoho/
│   │   ├── __init__.py
│   │   ├── service.py
│   │   └── mapper.py
│   └── router.py                  # Unified integration endpoint
│
├── reporting/                     # REFACTORED: Extract from excel_export
│   ├── __init__.py
│   ├── exporters/
│   │   ├── __init__.py
│   │   ├── excel.py               # Move from excel_export.py
│   │   └── pdf.py                 # Future
│   ├── schemas.py
│   └── router.py
│
├── ai/                            # REFACTORED: Rename from ai_agent
│   ├── __init__.py
│   ├── service.py                 # Move from ai_agent.py
│   ├── prompts.py                 # NEW: Centralize LLM prompts
│   └── router.py
│
├── tax/                           # KEEP: Already organized
│   ├── __init__.py
│   ├── analyzer.py
│   ├── schemas.py
│   └── router.py
│
├── billing/                       # KEEP: Already organized
│   ├── __init__.py
│   ├── schemas.py
│   ├── service.py                 # NEW: Extract from billing.py
│   └── router.py
│
├── compliance/                    # KEEP
│   ├── __init__.py
│   ├── router.py
│   └── schemas.py
│
├── notices/                       # KEEP
│   ├── __init__.py
│   ├── router.py
│   └── schemas.py
│
├── documents/                     # KEEP
│   ├── __init__.py
│   ├── router.py
│   └── schemas.py
│
├── tasks/                         # KEEP
│   ├── __init__.py
│   ├── router.py
│   └── schemas.py
│
├── itr/                           # KEEP
│   ├── __init__.py
│   ├── router.py
│   └── schemas.py
│
├── bill_reader/                   # KEEP
│   ├── __init__.py
│   ├── router.py
│   └── schemas.py
│
├── database.py                    # Keep as-is (models + repos)
├── main_v2.py                     # Refactor: import from submodules
├── conftest.py                    # NEW: Pytest fixtures & setup
└── tests/                         # NEW: Test suite
    ├── __init__.py
    ├── conftest.py
    ├── test_auth.py
    ├── test_reconciliation.py
    ├── test_gsp.py
    └── ...
```

---

## Refactoring Tasks (Prioritized)

### Phase 1A: Foundation (Week 1)

#### Task 1.1: Create Core Utilities Module
**File:** `backend/core/`
- **What:** Centralized config, exceptions, validators
- **Action:**
  ```python
  # core/exceptions.py
  class TenantError(Exception): pass
  class ValidationError(Exception): pass
  class GSTError(Exception): pass
  
  # core/validators.py
  def validate_gstin(gstin: str) -> None: ...
  def validate_email(email: str) -> None: ...
  
  # core/config.py
  JWT_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
  ```
- **Impact:** Reduce duplication, centralize constants
- **Effort:** 2-3 hours

#### Task 1.2: Extract Auth to Module
**File:** `backend/auth/` → move from `auth.py`
- **What:** Separate router, dependencies, service logic
- **Structure:**
  ```
  auth/
  ├── dependencies.py  # current_user, verify_token
  ├── service.py       # register_user, login, etc.
  ├── schemas.py       # LoginRequest, UserResponse, etc.
  └── router.py        # @router endpoints
  ```
- **Impact:** Make auth testable, reusable
- **Effort:** 4-5 hours

#### Task 1.3: Extract Password Reset to Auth
**File:** Move `password_reset.py` → `auth/reset.py`
- **What:** Consolidate auth flows
- **Impact:** Cleaner auth module
- **Effort:** 1-2 hours

#### Task 1.4: Create Clients Module
**File:** `backend/clients/` (extract from `crm/`)
- **What:** Move client CRUD logic to service layer
- **Service Layer:**
  ```python
  # clients/service.py
  class ClientService:
      async def create(self, db, firm_id, data) -> GSTClient: ...
      async def list(self, db, firm_id) -> list[GSTClient]: ...
      async def get(self, db, firm_id, client_id) -> GSTClient: ...
      async def update(self, db, firm_id, client_id, data) -> GSTClient: ...
  ```
- **Router:** Use the service, handle HTTP layer
- **Impact:** Business logic testable without FastAPI
- **Effort:** 3-4 hours

#### Task 1.5: Create Invoices Module
**File:** `backend/invoices/` (move `invoices.py`)
- **What:** Refactor to 3-layer pattern
- **Current State:** `invoices.py` has all logic mixed
- **Target State:**
  ```
  invoices/
  ├── schemas.py         # CreateInvoiceRequest, etc.
  ├── service.py         # InvoiceService with CRUD + matching logic
  └── router.py          # HTTP endpoints (thin layer)
  ```
- **Effort:** 5-6 hours

#### Task 1.6: Refactor Reconciliation Module
**File:** `backend/reconciliation/`
- **What:** Consolidate scattered logic
  - Move `reconciliation_engine.py` → `reconciliation/engine.py`
  - Move `reconcile_saved.py` → `reconciliation/saved.py`
  - Create `reconciliation/service.py` (orchestration)
- **New Service Layer:**
  ```python
  class ReconciliationService:
      async def upload_register(self, db, firm_id, csv_data) -> Reconciliation: ...
      async def get_with_mismatches(self, db, firm_id, rec_id) -> dict: ...
      async def resolve_mismatch(self, db, firm_id, mm_id, notes) -> Mismatch: ...
  ```
- **Impact:** Single entry point for all reconciliation operations
- **Effort:** 6-8 hours

### Phase 1B: Integrations & Reporting (Week 2)

#### Task 1.7: Create Integrations Module
**File:** `backend/integrations/`
- **What:** Unify Tally/Zoho under one roof
- **Structure:**
  ```
  integrations/
  ├── tally/
  │   ├── client.py      # Tally API wrapper
  │   ├── mapper.py      # CSV → Invoice conversion
  │   └── service.py     # TallyService(sync, import, etc.)
  ├── zoho/
  │   ├── client.py
  │   ├── mapper.py
  │   └── service.py
  └── router.py          # /integrations/sync endpoints
  ```
- **Impact:** Clear contract for new integrations
- **Effort:** 7-8 hours

#### Task 1.8: Extract Reporting Module
**File:** `backend/reporting/`
- **What:** Move `excel_export.py` to structured module
- **Structure:**
  ```
  reporting/
  ├── exporters/
  │   ├── excel.py       # ExcelExporter
  │   └── pdf.py         # PDFExporter (future)
  ├── schemas.py         # ReportRequest, etc.
  └── router.py          # /reporting/export
  ```
- **Impact:** Extensible reporting, easy to add formats
- **Effort:** 3-4 hours

#### Task 1.9: Refactor AI Module
**File:** `backend/ai/` (rename from `ai_agent/`)
- **What:** Better prompt management, service layer
- **Structure:**
  ```
  ai/
  ├── prompts.py         # NEW: Centralize all LLM prompts
  ├── service.py         # Move from ai_agent.py
  └── router.py
  ```
- **Impact:** Easier to test, update prompts, swap LLM providers
- **Effort:** 3-4 hours

### Phase 1C: Testing & Polish (Week 2-3)

#### Task 1.10: Add Pytest Infrastructure
**File:** `backend/conftest.py`, `backend/tests/`
- **What:** Fixtures, database setup, mocks
- **Create:**
  ```python
  # conftest.py
  @pytest.fixture
  async def db():
      # In-memory SQLite for tests
      # Yield session, cleanup
      
  @pytest.fixture
  async def auth_client(db):
      # Create test firm, user, return token
  ```
- **Impact:** Enable unit and integration tests
- **Effort:** 4-5 hours

#### Task 1.11: Write Service Layer Tests
**Files:** `tests/test_clients.py`, `tests/test_reconciliation.py`, etc.
- **What:** Test business logic in isolation
- **Example:**
  ```python
  async def test_create_client():
      service = ClientService()
      client = await service.create(db, firm_id, data)
      assert client.gstin == "05ABCDE1234F1Z5"
  ```
- **Impact:** Confidence in refactoring, catch regressions
- **Effort:** 8-10 hours

#### Task 1.12: Update main_v2.py
**File:** `backend/main_v2.py`
- **What:** Clean up imports, mount new modules
- **Before:**
  ```python
  from auth import auth_router
  from gsp.router import gsp_router
  from reconciliation.router import reconciliation_router
  ...  # 20+ imports
  ```
- **After:**
  ```python
  from core.app import create_app
  
  app = create_app()
  # Routers auto-discovered or explicitly mounted
  ```
- **Effort:** 2-3 hours

---

## Database Optimization (Parallel to Refactoring)

### Task 2.1: Add Missing Indexes

```sql
-- Add indexes for common queries
CREATE INDEX idx_mismatches_reconciliation_id ON mismatches(reconciliation_id);
CREATE INDEX idx_reconciliations_firm_period ON reconciliations(firm_id, period DESC);
CREATE INDEX idx_mismatches_status ON mismatches(firm_id, status);
CREATE INDEX idx_reconciliations_created_at ON reconciliations(firm_id, created_at DESC);
```

### Task 2.2: Connection Pooling

```python
# database.py - Update engine creation
engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool if SQLite else QueuePool,  # Use QueuePool for Postgres
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    echo=SQL_ECHO
)
```

### Task 2.3: Query Analysis

Add monitoring to identify N+1 queries:

```python
# core/logger.py
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

---

## Migration Path (No Downtime)

### Week 1-2: Build in Parallel
- Refactoring happens on feature branch
- Production continues with old code
- New tests ensure compatibility

### Week 3: Cutover
- Deploy refactored code
- Keep old files (as fallback)
- Monitor for issues

### Week 4: Cleanup
- Remove old files after validation
- Update CI/CD
- Documentation update

---

## Success Metrics

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Module cyclomatic complexity | High | < 10 per function | 2 weeks |
| Test coverage | 0% | > 70% | 3 weeks |
| Setup time for new dev | 2 hours | < 30 min | 2 weeks |
| Time to add a new endpoint | 1 hour | < 15 min | 2 weeks |
| Duplicate lines of code | 15% | < 5% | 3 weeks |

---

## Implementation Strategy

### Git Workflow
```bash
# Create feature branch
git checkout -b refactor/phase1-foundation

# Commit frequently (one task per commit)
git commit -m "feat(core): add shared utilities module"
git commit -m "refactor(auth): extract to module with service layer"
...

# Create PR for review
# Merge to main after tests pass
```

### Code Review Checklist
- [ ] All tests passing (new + existing)
- [ ] No new dependencies
- [ ] No breaking API changes (backwards compatible)
- [ ] Documentation updated (CLAUDE.md)
- [ ] No duplicate logic introduced

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Break existing API | Keep old endpoints, test compatibility |
| Database migration issues | Test with production data snapshot |
| Performance regression | Benchmark before/after queries |
| Import circular dependencies | Use TYPE_CHECKING for hints |
| Incomplete refactoring | Strict code review, run full test suite |

---

## Next Steps

1. **This Week:** Start Tasks 1.1 → 1.4 (core utilities, auth, clients)
2. **Next Week:** Tasks 1.5 → 1.8 (invoices, reconciliation, integrations)
3. **Week 3:** Tasks 1.9 → 1.12 (AI, testing, cleanup)
4. **Week 4:** Deploy, monitor, document final state

Estimated total effort: **60-80 engineer-hours** over 3 weeks.

