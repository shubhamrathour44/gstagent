# Database Optimization Guide

## Current State Analysis

### Database Configuration
- **Driver:** SQLAlchemy async + asyncpg (Postgres) or aiosqlite (SQLite)
- **Pool Config:** Default (not optimized)
- **Indexes:** Only on foreign keys and unique fields
- **Query Patterns:** N+1 issues in reconciliation matching

### Performance Baseline (Production)
```
Typical Reconciliation Upload:
- 5,000 invoices: ~8-12 seconds
- 25,000 invoices: ~45-60 seconds
- 100,000 invoices: >5 minutes (unacceptable)

Bottlenecks:
1. Sequential line-by-line matching (O(n²))
2. Missing database indexes on common queries
3. No connection pooling for concurrent requests
4. N+1 query problem in relationship loading
```

---

## Optimization Strategy

### Phase 1: Quick Wins (1-2 days, +30% performance)

#### 1.1: Add Strategic Indexes

```python
# backend/database.py - Add to model definitions

class Reconciliation(Base):
    __tablename__ = "reconciliations"
    __table_args__ = (
        Index('idx_reconciliations_firm_period', 'firm_id', 'period', postgresql_desc('created_at')),
        Index('idx_reconciliations_firm_created', 'firm_id', postgresql_desc('created_at')),
    )
    # ... columns ...

class Mismatch(Base):
    __tablename__ = "mismatches"
    __table_args__ = (
        Index('idx_mismatches_status', 'firm_id', 'status'),
        Index('idx_mismatches_severity', 'firm_id', 'severity'),
    )
    # ... columns ...

class GSTClient(Base):
    __tablename__ = "gst_clients"
    __table_args__ = (
        Index('idx_gst_clients_firm_active', 'firm_id', 'is_active'),
    )
    # ... columns ...
```

**Impact:** 20-30% faster list queries
**SQL Migration (if Postgres):**
```sql
CREATE INDEX idx_reconciliations_firm_period ON reconciliations(firm_id, period DESC, created_at DESC);
CREATE INDEX idx_reconciliations_firm_created ON reconciliations(firm_id, created_at DESC);
CREATE INDEX idx_mismatches_status ON mismatches(firm_id, status);
CREATE INDEX idx_mismatches_severity ON mismatches(firm_id, severity);
CREATE INDEX idx_gst_clients_firm_active ON gst_clients(firm_id, is_active);
```

#### 1.2: Enable Connection Pooling

```python
# backend/database.py

from sqlalchemy.pool import QueuePool, NullPool, StaticPool

def _get_engine_kwargs():
    """Get database engine configuration with pooling."""
    kwargs = {
        "echo": os.getenv("SQL_ECHO", "0") == "1",
        "pool_pre_ping": True,  # Test connection before use
    }
    
    if DATABASE_URL.startswith("sqlite"):
        # SQLite: Use StaticPool for in-memory, NullPool otherwise
        kwargs["poolclass"] = StaticPool if ":memory:" in DATABASE_URL else NullPool
    else:
        # Postgres: Use QueuePool for connection reuse
        kwargs["poolclass"] = QueuePool
        kwargs["pool_size"] = 20  # Maintain up to 20 open connections
        kwargs["max_overflow"] = 10  # Allow up to 10 overflow connections
        kwargs["pool_recycle"] = 3600  # Recycle connections every hour
        kwargs["pool_timeout"] = 30  # Wait 30s for a connection before timeout
    
    return kwargs

engine = create_async_engine(DATABASE_URL, **_get_engine_kwargs())
```

**Impact:** Eliminates connection setup overhead, supports concurrent requests
**Testing:**
```bash
# Load test with 10 concurrent requests
ab -c 10 -n 100 http://localhost:8000/reconciliations
```

#### 1.3: Optimize Query Selection (selectinload vs joinedload)

```python
# BAD: N+1 query problem
reconciliations = await db.execute(select(Reconciliation).where(...))
for recon in reconciliations:
    mismatches = recon.mismatches  # Triggers 1 query per reconciliation

# GOOD: Single query with join
from sqlalchemy.orm import selectinload

reconciliations = await db.execute(
    select(Reconciliation)
    .where(...)
    .options(selectinload(Reconciliation.mismatches))
)
```

**Where to apply:**
- `ReconciliationRepo.get()` – Include mismatches
- `ReconciliationRepo.list_for_firm()` – Include client summary only
- `GSTClient` fetches – Include active reconciliations

**Impact:** 70-90% fewer queries for reconciliation detail views

#### 1.4: Add Query Logging & Monitoring

```python
# backend/core/logger.py

import logging
import time

class SQLAlchemyLogger:
    @staticmethod
    def setup():
        """Enable SQLAlchemy query logging."""
        # Slow query logger
        logging.basicConfig(level=logging.INFO)
        sql_logger = logging.getLogger('sqlalchemy.engine')
        sql_logger.setLevel(logging.INFO)
        
        # Add handler to log queries > 1 second
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - SLOW QUERY (%(duration)s ms): %(message)s'
        ))
        sql_logger.addHandler(handler)

# Usage in main_v2.py
from core.logger import SQLAlchemyLogger
SQLAlchemyLogger.setup()
```

**Identify slow queries:**
```bash
# Watch logs for "SLOW QUERY" messages
tail -f logs/app.log | grep "SLOW QUERY"
```

---

### Phase 2: Batch Processing & Caching (3-5 days, +200% performance)

#### 2.1: Batch Invoice Insertion

```python
# backend/reconciliation/service.py

class ReconciliationService:
    async def batch_insert_invoices(
        self, 
        db: AsyncSession, 
        invoices: list[InvoiceData],
        batch_size: int = 1000
    ) -> list[Invoice]:
        """Insert invoices in batches to reduce query overhead."""
        all_inserted = []
        
        for i in range(0, len(invoices), batch_size):
            batch = invoices[i:i + batch_size]
            
            # Convert to ORM objects
            orm_objects = [Invoice(**inv) for inv in batch]
            db.add_all(orm_objects)
            await db.flush()
            all_inserted.extend(orm_objects)
        
        await db.commit()
        return all_inserted
    
    async def batch_matching(
        self,
        db: AsyncSession,
        pr_invoices: list[Invoice],
        gstr2b_invoices: list[Invoice],
        batch_size: int = 500
    ) -> list[MatchResult]:
        """Match invoices in chunks using indexes."""
        results = []
        
        for i in range(0, len(pr_invoices), batch_size):
            batch = pr_invoices[i:i + batch_size]
            
            # Query GSTR-2B invoices matching batch criteria
            # Uses index: (supplier_gstin, invoice_number, invoice_date)
            matched = await self._match_batch(db, batch, gstr2b_invoices)
            results.extend(matched)
        
        return results
```

**Impact:** 10x faster for 100k+ invoices
**Effort:** 8-10 hours

#### 2.2: Query Result Caching

```python
# backend/core/cache.py

from functools import wraps
from datetime import datetime, timedelta
from typing import Any, Callable

class QueryCache:
    _cache = {}
    _ttl = {}
    
    @classmethod
    async def get(cls, key: str) -> Any:
        """Get cached value if not expired."""
        if key not in cls._cache:
            return None
        
        if datetime.now() > cls._ttl.get(key, datetime.now()):
            del cls._cache[key]
            return None
        
        return cls._cache[key]
    
    @classmethod
    def set(cls, key: str, value: Any, ttl_seconds: int = 300):
        """Cache a value."""
        cls._cache[key] = value
        cls._ttl[key] = datetime.now() + timedelta(seconds=ttl_seconds)
    
    @classmethod
    def cache_result(cls, ttl_seconds: int = 300):
        """Decorator to cache async function results."""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Create cache key from function name + args
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                
                cached = await cls.get(cache_key)
                if cached is not None:
                    return cached
                
                result = await func(*args, **kwargs)
                cls.set(cache_key, result, ttl_seconds)
                return result
            
            return wrapper
        return decorator

# Usage
from core.cache import QueryCache

@QueryCache.cache_result(ttl_seconds=600)
async def get_gstr2b_data(db, gstin, period):
    """Cache GSTR-2B fetches for 10 minutes."""
    return await gsp_client.fetch_gstr2b(gstin, period)
```

**Apply to:**
- GSP data fetches (GSTR-2B, GSTR-1)
- Tax rates lookups
- Firm subscription status

**Impact:** 80-90% reduction in GSP API calls
**Effort:** 4-5 hours

#### 2.3: Read Replica for Reporting

```python
# backend/database.py

class ReadOnlySession(AsyncSession):
    """Use read replica for reports."""
    pass

def get_reporting_db() -> AsyncGenerator[AsyncSession, None]:
    """Route reporting queries to read replica."""
    replica_url = os.getenv("DATABASE_READ_REPLICA_URL")
    if replica_url:
        # Use read replica for read-heavy operations
        engine = create_async_engine(replica_url, **_get_engine_kwargs())
    else:
        # Fall back to primary if no replica
        engine = AsyncSessionLocal
    
    async with engine() as session:
        yield session

# Usage in router
@router.get("/reports/summary")
async def get_summary(db: AsyncSession = Depends(get_reporting_db)):
    # Heavy aggregation query routed to replica
    pass
```

**When to implement:** After hitting production scale (~1k+ concurrent users)
**Effort:** 3-4 hours

---

### Phase 3: Advanced Optimization (2+ weeks, +500% performance)

#### 3.1: Elasticsearch for Full-Text Search

```python
# backend/integrations/elasticsearch.py

from elasticsearch import Elasticsearch

class InvoiceSearch:
    def __init__(self):
        self.es = Elasticsearch([os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")])
    
    async def index_invoice(self, invoice: Invoice):
        """Index invoice for full-text search."""
        await self.es.index(
            index="invoices",
            id=invoice.id,
            body={
                "invoice_number": invoice.invoice_number,
                "supplier_name": invoice.supplier_name,
                "gstin": invoice.supplier_gstin,
                "amount": invoice.taxable_value,
                "firm_id": invoice.firm_id,  # Tenant isolation
            }
        )
    
    async def search(self, firm_id: str, query: str) -> list[dict]:
        """Full-text search invoices."""
        results = await self.es.search(
            index="invoices",
            body={
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"supplier_name": query}},
                            {"term": {"firm_id": firm_id}},
                        ]
                    }
                }
            }
        )
        return results['hits']['hits']
```

**Impact:** Sub-100ms search across 1M+ invoices
**Effort:** 15-20 hours (includes infrastructure setup)

#### 3.2: Background Job Queue

```python
# backend/core/jobs.py

from celery import Celery
import redis

redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost"))
celery_app = Celery('gstagent', broker=os.getenv("CELERY_BROKER", "redis://localhost"))

@celery_app.task
async def reconcile_large_register(firm_id: str, client_id: str, csv_path: str):
    """Process large reconciliation asynchronously."""
    # Progress tracking
    job_id = reconcile_large_register.request.id
    
    db = AsyncSessionLocal()
    try:
        # Step 1: Parse CSV (with progress)
        invoices = await parse_csv_in_chunks(csv_path)
        update_job_progress(job_id, 25, "Parsing complete")
        
        # Step 2: Fetch GSTR-2B
        gstr2b = await fetch_gstr2b_data(client_id)
        update_job_progress(job_id, 50, "GSTR-2B fetched")
        
        # Step 3: Match invoices
        results = await batch_matching(invoices, gstr2b)
        update_job_progress(job_id, 75, "Matching complete")
        
        # Step 4: Store results
        await ReconciliationRepo.create(db, results)
        update_job_progress(job_id, 100, "Complete")
        
    finally:
        await db.close()

# Usage in router
@router.post("/reconciliation/upload-async")
async def upload_async(firm_id: str, file: UploadFile):
    """Submit large reconciliation to background queue."""
    csv_path = await save_upload(file)
    
    task = reconcile_large_register.delay(firm_id, client_id, csv_path)
    
    return {
        "job_id": task.id,
        "status": "queued",
        "progress_url": f"/reconciliation/jobs/{task.id}"
    }

@router.get("/reconciliation/jobs/{job_id}")
async def get_job_progress(job_id: str):
    """Check job progress."""
    return {
        "job_id": job_id,
        "progress": redis_client.get(f"job:{job_id}:progress"),
        "message": redis_client.get(f"job:{job_id}:message")
    }
```

**Impact:** Non-blocking reconciliation, progress tracking for UX
**Effort:** 20-25 hours (includes Redis/Celery setup)

---

## Implementation Roadmap

| Phase | Tasks | Timeline | Expected Improvement |
|-------|-------|----------|----------------------|
| **Phase 1** | Indexes + Connection Pooling + Selectinload | 1-2 days | +30% |
| **Phase 2** | Batch Processing + Caching | 1 week | +200% total |
| **Phase 3A** | Elasticsearch | 1-2 weeks | +500% search performance |
| **Phase 3B** | Background Jobs + Progress Tracking | 1 week | Better UX, no timeouts |

---

## Benchmarking Script

```python
# backend/tests/benchmark_reconciliation.py

import asyncio
import time
from sqlalchemy import select
from database import AsyncSessionLocal, Reconciliation

async def benchmark_queries():
    """Measure query performance before/after optimization."""
    db = AsyncSessionLocal()
    
    # Test 1: List reconciliations (should use index)
    start = time.time()
    for _ in range(100):
        result = await db.execute(
            select(Reconciliation)
            .where(Reconciliation.firm_id == "test-firm")
            .limit(50)
        )
        list(result.scalars())
    elapsed = time.time() - start
    print(f"List query (100x): {elapsed:.2f}s avg: {elapsed/100:.3f}s")
    
    # Test 2: Get with relationships (should use selectinload)
    start = time.time()
    for _ in range(10):
        result = await db.execute(
            select(Reconciliation)
            .where(Reconciliation.firm_id == "test-firm")
            .options(selectinload(Reconciliation.mismatches))
        )
        list(result.scalars())
    elapsed = time.time() - start
    print(f"Get with mismatches (10x): {elapsed:.2f}s avg: {elapsed/10:.3f}s")
    
    await db.close()

# Run with: python -m pytest tests/benchmark_reconciliation.py -v -s
if __name__ == "__main__":
    asyncio.run(benchmark_queries())
```

---

## Monitoring & Alerting

### Key Metrics to Track

```python
# backend/core/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Counters
db_queries = Counter('db_queries_total', 'Total database queries', ['operation'])
cache_hits = Counter('cache_hits_total', 'Cache hit count')

# Histograms
query_duration = Histogram('db_query_duration_seconds', 'Query execution time', buckets=(0.01, 0.1, 0.5, 1.0, 5.0))
reconciliation_time = Histogram('reconciliation_duration_seconds', 'Reconciliation processing time')

# Gauges
active_connections = Gauge('db_active_connections', 'Active database connections')
cache_size = Gauge('cache_size_bytes', 'Cache size in bytes')
```

### Alert Thresholds

- Query > 5 seconds ⚠️
- Cache hit rate < 60% ⚠️
- Connection pool exhausted ⚠️
- GSP API errors > 5% ⚠️

---

## Deployment Checklist

- [ ] Run index creation migration (no downtime)
- [ ] Update `database.py` with pooling config
- [ ] Deploy code with selectinload optimizations
- [ ] Run benchmarks before/after
- [ ] Monitor query logs for 24 hours
- [ ] Scale database resources if needed
- [ ] Document any configuration changes

