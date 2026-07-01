import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_tables
from auth import auth_router
from integrations import tally_router, zoho_router
from gsp.router import gsp_router
from tax.router import tax_router
from crm.router import crm_router
from compliance.router import compliance_router
from billing import router as billing_router
from documents.router import router as documents_router
from notices.router import router as notices_router
from tasks.router import router as tasks_router
from reconciliation.router import router as reconciliation_router
from bill_reader.router import router as bill_reader_router
from itr.router import router as itr_router
from password_reset import router as password_reset_router
from ai_agent_router import router as ai_agent_router
from invoices import router as invoices_router
from reconcile_saved import router as reconcile_saved_router
from tally_import import router as tally_import_router
from zoho_import import router as zoho_import_router
from payroll.router import payroll_router
from accounting.router import accounting_router
from itr_documents.router import router as itr_documents_router


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gstagent-backend")

app = FastAPI(
    title="GSTAgent API",
    description="Backend API engine for GSTAgent CA Practice Management Platform",
    version="2.1.0"
)

origins = [
    "http://localhost:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "https://gstagent.co.in",
    "https://www.gstagent.co.in",
    "https://gstagent.vercel.app",
    "https://www.gstagent.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_create_tables():
    try:
        await create_tables()
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.exception(f"Database startup failed: {e}")

@app.get("/")
async def root():
    return {
        "message": "Welcome to GSTAgent Core API Engine",
        "status": "healthy",
        "version": "2.1.0"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "gstagent-backend"
    }

@app.get("/modules")
async def modules():
    return {
        "modules": [
            "auth",
            "billing",
            "crm",
            "tax",
            "gsp",
            "compliance",
            "documents",
            "notices",
            "tasks",
            "tally",
            "zoho",
            "payroll",
            "accounting",
            "itr_documents"
        ]
    }

app.include_router(auth_router)
app.include_router(gsp_router)
app.include_router(tax_router)
app.include_router(crm_router)
app.include_router(compliance_router)
app.include_router(billing_router)
app.include_router(documents_router)
app.include_router(notices_router)
app.include_router(tasks_router)
app.include_router(reconciliation_router)
app.include_router(bill_reader_router)
app.include_router(itr_router)
app.include_router(password_reset_router)
app.include_router(ai_agent_router)
app.include_router(invoices_router)
app.include_router(reconcile_saved_router)
app.include_router(tally_import_router)
app.include_router(zoho_import_router)
app.include_router(payroll_router)
app.include_router(accounting_router)
app.include_router(itr_documents_router)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main_v2:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
