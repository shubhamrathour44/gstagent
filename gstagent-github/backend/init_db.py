"""
Runs once on startup to create all database tables.
Called by railway.toml start command before uvicorn.
"""
import asyncio
import os
import sys

async def init():
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        print("WARNING: DATABASE_URL not set. Skipping DB init.")
        return
    try:
        from database import create_tables
        await create_tables()
        print("Database tables ready.")
    except Exception as e:
        print(f"DB init error (non-fatal): {e}")

if __name__ == "__main__":
    asyncio.run(init())
