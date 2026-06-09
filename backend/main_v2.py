import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import existing routers
from auth import router as auth_router
from integrations import tally_router, zoho_router
from gsp.router import router as gsp_router
from tax.router import router as tax_router
from crm.router import crm_router

# FIX: Added missing compliance router import
from compliance.router import compliance_router

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gstagent-backend")

app = FastAPI(
    title="GSTAgent API",
    description="Backend API engine for GSTAgent CA Practice Management Platform",
    version="2.0.0"
)

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "https://gstagent.co.in",
    "https://www.gstagent.co.in",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Temporarily allow all origins to bypass preflight bugs completely
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Welcome to GSTAgent Core API Engine",
        "status": "healthy",
        "version": "2.0.0"
    }

# Include App Routers
app.include_router(auth_router)
app.include_router(tally_router)
app.include_router(zoho_router)
app.include_router(gsp_router)
app.include_router(tax_router)
app.include_router(crm_router)

# Include New Compliance Tracker Router
app.include_router(compliance_router)

# Optional Billing Router Safeguard
try:
    from billing import router as billing_router
    app.include_router(billing_router)
    logger.info("Billing router integrated successfully.")
except ImportError:
    logger.warning("Billing module not found. Skipping billing router initialization.")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main_v2.py:app", host="0.0.0.0", port=port, reload=True)