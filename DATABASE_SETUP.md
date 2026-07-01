# Database Setup Guide

Complete guide to configure and initialize the database for GSTAgent.

---

## 🚀 Quick Start (SQLite - Development)

### Step 1: Set Environment Variable

**Windows (PowerShell):**
```powershell
$env:DATABASE_URL = "sqlite+aiosqlite:///./gstagent.db"
```

**Linux/Mac (Bash):**
```bash
export DATABASE_URL="sqlite+aiosqlite:///./gstagent.db"
```

**Or create .env file:**
```env
DATABASE_URL=sqlite+aiosqlite:///./gstagent.db
```

### Step 2: Verify Configuration

```bash
python -c "import os; print(f'DATABASE_URL: {os.getenv(\"DATABASE_URL\")}')"
```

Expected output:
```
DATABASE_URL: sqlite+aiosqlite:///./gstagent.db
```

### Step 3: Start Server (Tables Auto-Create)

```bash
python -m uvicorn backend.main_v2:app --reload
```

The database file `gstagent.db` will be automatically created on first run.

### Step 4: Verify Database Creation

```bash
ls -lah gstagent.db
```

You should see:
```
-rw-r--r--  1 user  group  64K Jul  2 10:30 gstagent.db
```

---

## 📊 Database Options

### Option 1: SQLite (Recommended for Development)

**Pros:**
- ✅ Zero setup required
- ✅ No external dependencies
- ✅ File-based (easy backup)
- ✅ Perfect for testing
- ✅ Supports all features

**Cons:**
- ❌ Not for concurrent users (< 5 concurrent)
- ❌ Limited performance (< 10K rows)
- ❌ No remote access

**Configuration:**
```env
DATABASE_URL=sqlite+aiosqlite:///./gstagent.db
```

**Use Cases:**
- Local development
- Testing
- Small deployments
- CI/CD pipelines

---

### Option 2: PostgreSQL (Recommended for Production)

**Pros:**
- ✅ Excellent performance
- ✅ Supports many concurrent users
- ✅ Advanced features (JSONB, etc.)
- ✅ Enterprise-grade
- ✅ Easy scaling

**Cons:**
- ❌ Requires separate setup
- ❌ External dependency
- ❌ Slightly more complex

**Installation:**

#### Windows
```powershell
# Using Chocolatey
choco install postgresql

# Or download from: https://www.postgresql.org/download/windows/
```

#### macOS
```bash
brew install postgresql@15
brew services start postgresql@15
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### PostgreSQL Setup

```bash
# 1. Create database
sudo -u postgres psql
CREATE DATABASE gstagent;
CREATE USER gstagent_user WITH PASSWORD 'secure_password_here';
ALTER ROLE gstagent_user SET client_encoding TO 'utf8';
ALTER ROLE gstagent_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE gstagent_user SET default_transaction_deferrable TO on;
ALTER ROLE gstagent_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE gstagent TO gstagent_user;
\q

# 2. Set environment variable
export DATABASE_URL="postgresql+asyncpg://gstagent_user:secure_password_here@localhost:5432/gstagent"

# 3. Start server (tables auto-create)
python -m uvicorn backend.main_v2:app --reload
```

**Configuration:**
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/gstagent
```

**Cloud PostgreSQL:**

**Railway.app** (Recommended)
```bash
# 1. Create account at https://railway.app
# 2. Add PostgreSQL plugin
# 3. Get connection string from dashboard
# 4. Use in DATABASE_URL

DATABASE_URL=postgresql+asyncpg://username:password@containers-us-west-12.railway.app:5432/railway
```

**AWS RDS**
```env
DATABASE_URL=postgresql+asyncpg://admin:password@gstagent-db.xxxxx.rds.amazonaws.com:5432/gstagent
```

**Google Cloud SQL**
```env
DATABASE_URL=postgresql+asyncpg://admin:password@cloudsql-instance-connection-name/gstagent
```

**Heroku PostgreSQL**
```env
DATABASE_URL=postgresql+asyncpg://username:password@ec2-xxx-xxx-xxx-xxx.compute-1.amazonaws.com:5432/database_name
```

---

## ✅ Database Configuration

### Current Setup

**File:** `.env`
**Database Type:** SQLite
**Location:** `gstagent.db`
**Status:** ✅ Ready

### Configuration Details

```
Database URL:     sqlite+aiosqlite:///./gstagent.db
Type:            SQLite3
Driver:          aiosqlite
Pool Size:       N/A
Max Overflow:    N/A
Echo SQL:        false
```

### Environment Variables

```env
DATABASE_URL=sqlite+aiosqlite:///./gstagent.db
```

---

## 🔄 Database Initialization

### Auto-Creation

The system automatically creates all required tables on first run:

```
Tables created:
✓ users
✓ firms
✓ gstr_filings
✓ gst_payments
✓ reconciliation_results
✓ itr_documents
✓ efiling_submissions
... and more
```

### Manual Table Creation

```python
import asyncio
import sys
sys.path.insert(0, 'backend')

from database import create_tables

async def init_db():
    await create_tables()
    print("Database tables created successfully")

asyncio.run(init_db())
```

### Verify Tables

```bash
# SQLite
sqlite3 gstagent.db ".tables"

# PostgreSQL
psql -U gstagent_user -d gstagent -c "\dt"
```

Expected output:
```
auth_tokens              efiling_submissions    gsp_returns
bills                    firms                  itr_documents
crm_contacts             gst_payments           itr_returns
crm_interactions         gstr_filing_submissions purchase_reconciliation
gst_return_filings       reconciliation_results sales_reconciliation
```

---

## 🔐 Database Backups

### SQLite Backup

```bash
# Manual backup
cp gstagent.db gstagent_backup_$(date +%Y%m%d).db

# Automated backup (daily)
# Add to crontab:
0 2 * * * cp /path/to/gstagent.db /path/to/backups/gstagent_$(date +\%Y\%m\%d).db
```

### PostgreSQL Backup

```bash
# Full database backup
pg_dump -U gstagent_user -d gstagent > gstagent_backup_$(date +%Y%m%d).sql

# Automated backup
0 2 * * * pg_dump -U gstagent_user -d gstagent | gzip > /backups/gstagent_$(date +\%Y\%m\%d).sql.gz
```

---

## 🧪 Testing Database Connection

### Quick Test

```python
import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test_connection():
    database_url = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./gstagent.db')
    engine = create_async_engine(database_url, echo=False)
    
    async with engine.begin() as conn:
        result = await conn.execute(text('SELECT 1'))
        print(f"✓ Database connected successfully")
        print(f"  URL: {database_url}")
        
    await engine.dispose()

asyncio.run(test_connection())
```

### Run Test

```bash
python database_test.py
```

Expected output:
```
✓ Database connected successfully
  URL: sqlite+aiosqlite:///./gstagent.db
```

---

## 📊 Performance Tuning

### SQLite Optimization

```python
# In database.py, add:
engine_kwargs = {
    "connect_args": {
        "check_same_thread": False,
        "timeout": 30
    }
}
```

### PostgreSQL Optimization

```python
# Connection pooling
pool_size = 20
max_overflow = 10

# Add to engine creation:
engine = create_async_engine(
    DATABASE_URL,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_pre_ping=True
)
```

---

## 🐛 Troubleshooting

### Issue: "No such file or directory: gstagent.db"

**Solution:**
```bash
# File will be created on first run
python -m uvicorn backend.main_v2:app --reload

# Verify creation
ls -lah gstagent.db
```

### Issue: "Database connection failed"

**Solution:**
1. Check DATABASE_URL is set:
   ```bash
   echo $DATABASE_URL
   ```

2. Verify format:
   - SQLite: `sqlite+aiosqlite:///./gstagent.db`
   - PostgreSQL: `postgresql+asyncpg://user:pass@host:5432/db`

3. Test connection:
   ```bash
   python database_test.py
   ```

### Issue: "Permission denied" (PostgreSQL)

**Solution:**
```bash
# Check credentials
psql -U gstagent_user -d gstagent -c "SELECT 1"

# Reset password if needed
sudo -u postgres psql
ALTER USER gstagent_user WITH PASSWORD 'new_password';
\q
```

### Issue: "Database is locked" (SQLite)

**Solution:**
```bash
# Delete lock file
rm gstagent.db-wal
rm gstagent.db-shm

# Restart application
python -m uvicorn backend.main_v2:app --reload
```

---

## 📋 Migration Guide (SQLite → PostgreSQL)

```bash
# 1. Export SQLite data
sqlite3 gstagent.db ".dump" > sqlite_dump.sql

# 2. Create PostgreSQL database
createdb gstagent

# 3. Import data
# (May need manual adjustments for SQL dialect differences)
psql gstagent < sqlite_dump.sql

# 4. Update DATABASE_URL
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/gstagent"

# 5. Test connection
python -m uvicorn backend.main_v2:app --reload
```

---

## ✅ Verification Checklist

- [ ] DATABASE_URL environment variable set
- [ ] Database file created (SQLite) or database accessible (PostgreSQL)
- [ ] Connection test passes
- [ ] Tables created successfully
- [ ] Application starts without errors
- [ ] API endpoints respond
- [ ] Payment tracking working
- [ ] Data persists after restart

---

## 🎯 Next Steps

1. **Development:** Use SQLite (current setup)
2. **Production:** Migrate to PostgreSQL
3. **Scaling:** Use PostgreSQL with connection pooling
4. **Backup:** Configure automated backups
5. **Monitoring:** Set up database monitoring

---

## 📞 Support

For database issues:
1. Check DATABASE_URL format
2. Run connection test
3. Review logs for errors
4. Check database permissions
5. Contact: support@gstagent.co.in

---

**Database Setup Status: ✅ READY**

Current: SQLite at `./gstagent.db`  
Status: Ready for development and testing  
Production Ready: Yes (after PostgreSQL migration)
