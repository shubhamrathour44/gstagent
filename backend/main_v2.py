"""
GSTAgent — Production FastAPI App
Domain: gstagent.co.in
GitHub: shubhamrathour44/gstagent
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from typing import Optional
import json, uuid, io, os
import pandas as pd
from datetime import datetime

# ── APP SETUP ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="GSTAgent API",
    description="AI-powered GST Reconciliation for Indian CA Firms",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://gstagent.co.in",
        "https://www.gstagent.co.in",
        "https://app.gstagent.co.in",
        "http://localhost:3000",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── IN-MEMORY STORE (works without DB for demo) ────────────────────────────────
_store: dict = {}
_users: dict = {}  # email → user data

# ── RECONCILIATION ENGINE ──────────────────────────────────────────────────────
def reconcile_data(gstin, period, pr, b2b):
    def tax(r): return (r.get("igst",0) or 0)+(r.get("cgst",0) or 0)+(r.get("sgst",0) or 0)
    prMap, b2bMap = {}, {}
    for r in pr: prMap[f"{r.get('supplier_gstin','')}||{r.get('invoice_number','')}"] = r
    for r in b2b: b2bMap[f"{r.get('supplier_gstin','')}||{r.get('invoice_number','')}"] = r

    mismatches, matched, n = [], 0, 0
    TOLERANCE = 1.0

    for k, p in prMap.items():
        if k not in b2bMap:
            n += 1; t = tax(p)
            mismatches.append({"mismatch_id":f"MM{n:04d}","mismatch_type":"Invoice in purchase register but missing in GSTR-2B","severity":"high" if t>=10000 else "medium" if t>=1000 else "low","supplier_name":p.get("supplier_name",""),"supplier_gstin":p.get("supplier_gstin",""),"invoice_number":p.get("invoice_number",""),"invoice_date":p.get("invoice_date",""),"pr_tax_amount":t,"b2b_tax_amount":None,"tax_impact":-t,"recommended_action":"Chase vendor to file/amend GSTR-1","notes":f"ITC of ₹{t:,.0f} at risk"})
        else:
            b = b2bMap[k]; pt = tax(p); bt = tax(b)
            if abs(pt - bt) > TOLERANCE:
                n += 1; diff = pt - bt
                mismatches.append({"mismatch_id":f"MM{n:04d}","mismatch_type":"Tax amount mismatch","severity":"high" if abs(diff)>=10000 else "medium" if abs(diff)>=1000 else "low","supplier_name":p.get("supplier_name",""),"supplier_gstin":p.get("supplier_gstin",""),"invoice_number":p.get("invoice_number",""),"invoice_date":p.get("invoice_date",""),"pr_tax_amount":pt,"b2b_tax_amount":bt,"tax_impact":diff,"recommended_action":"Verify invoice and reconcile books","notes":f"Difference of ₹{abs(diff):,.0f}"})
            else:
                matched += 1

    for k, b in b2bMap.items():
        if k not in prMap:
            n += 1; t = tax(b)
            mismatches.append({"mismatch_id":f"MM{n:04d}","mismatch_type":"Invoice in GSTR-2B but missing in purchase register","severity":"high" if t>=10000 else "medium" if t>=1000 else "low","supplier_name":b.get("supplier_name",""),"supplier_gstin":b.get("supplier_gstin",""),"invoice_number":b.get("invoice_number",""),"invoice_date":b.get("invoice_date",""),"pr_tax_amount":None,"b2b_tax_amount":t,"tax_impact":t,"recommended_action":"Verify if invoice was received","notes":f"Potential unclaimed ITC: ₹{t:,.0f}"})

    itc2b = sum(tax(r) for r in b2b)
    itcpr = sum(tax(r) for r in pr)
    match_rate = round(matched / max(len(pr), 1) * 100, 1)

    return {
        "gstin": gstin, "period": period,
        "reconciled_at": datetime.now().isoformat(),
        "total_pr_invoices": len(pr),
        "total_2b_invoices": len(b2b),
        "matched_invoices": matched,
        "mismatched_invoices": len(mismatches),
        "missing_in_2b": sum(1 for m in mismatches if "missing in GSTR-2B" in m["mismatch_type"]),
        "missing_in_pr": sum(1 for m in mismatches if "missing in purchase register" in m["mismatch_type"]),
        "total_itc_as_per_2b": round(itc2b, 2),
        "total_itc_as_per_pr": round(itcpr, 2),
        "itc_difference": round(itcpr - itc2b, 2),
        "high_severity_count": sum(1 for m in mismatches if m["severity"]=="high"),
        "medium_severity_count": sum(1 for m in mismatches if m["severity"]=="medium"),
        "low_severity_count": sum(1 for m in mismatches if m["severity"]=="low"),
        "summary_stats": {"match_rate": match_rate, "vendor_wise": []},
        "mismatches": mismatches
    }

# ── CLAUDE AI CALL ─────────────────────────────────────────────────────────────
async def call_claude(system: str, user: str, max_tokens: int = 1000) -> str:
    import httpx
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        return "AI features require ANTHROPIC_API_KEY to be configured."
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"Content-Type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01"},
                json={"model":"claude-sonnet-4-20250514","max_tokens":max_tokens,"system":system,"messages":[{"role":"user","content":user}]}
            )
            res.raise_for_status()
            return res.json()["content"][0]["text"]
    except Exception as e:
        return f"AI error: {str(e)}"

# ── SCHEMAS ────────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: str
    password: str
    firm_name: str
    admin_name: str
    phone: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class ReconcileRequest(BaseModel):
    gstin: str
    period: str
    company_name: str
    purchase_register: list[dict]
    gstr_2b: list[dict]

class NoticeReplyRequest(BaseModel):
    notice_number: str
    notice_date: str
    notice_type: str
    notice_content: str
    taxpayer_gstin: str
    taxpayer_name: str
    supporting_facts: str

class WaitlistRequest(BaseModel):
    email: str
    name: Optional[str] = None

# ── AUTH ROUTES ────────────────────────────────────────────────────────────────
import hashlib, hmac as _hmac, base64, time, json as _json

def _hash_pw(pw: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 100000)
    return base64.b64encode(salt + key).decode()

def _verify_pw(pw: str, h: str) -> bool:
    try:
        d = base64.b64decode(h); salt, stored = d[:32], d[32:]
        return _hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 100000), stored)
    except: return False

def _make_token(data: dict) -> str:
    secret = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
    payload = {**data, "exp": time.time() + 8*3600, "iat": time.time()}
    h = base64.urlsafe_b64encode(_json.dumps({"alg":"HS256"}).encode()).rstrip(b"=").decode()
    b = base64.urlsafe_b64encode(_json.dumps(payload).encode()).rstrip(b"=").decode()
    sig = _hmac.new(secret.encode(), f"{h}.{b}".encode(), hashlib.sha256).digest()
    return f"{h}.{b}.{base64.urlsafe_b64encode(sig).rstrip(b'=').decode()}"

def _verify_token(token: str) -> dict:
    secret = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
    try:
        h, b, sig = token.split(".")
        exp_sig = _hmac.new(secret.encode(), f"{h}.{b}".encode(), hashlib.sha256).digest()
        if not _hmac.compare_digest(base64.urlsafe_b64decode(sig+"=="), exp_sig): raise ValueError("bad sig")
        payload = _json.loads(base64.urlsafe_b64decode(b+"=="))
        if payload.get("exp", 0) < time.time(): raise ValueError("expired")
        return payload
    except Exception as e: raise HTTPException(401, f"Invalid token: {e}")

def get_user(authorization: str = None):
    from fastapi import Header
    return authorization

@app.post("/auth/register")
async def register(req: RegisterRequest):
    if req.email in _users:
        raise HTTPException(400, "Email already registered")
    user_id = str(uuid.uuid4())
    firm_id = str(uuid.uuid4())
    _users[req.email] = {
        "user_id": user_id, "firm_id": firm_id,
        "email": req.email, "hashed_password": _hash_pw(req.password),
        "firm_name": req.firm_name, "admin_name": req.admin_name,
        "phone": req.phone, "role": "ca_admin",
        "created_at": datetime.now().isoformat()
    }
    token = _make_token({"sub": user_id, "firm_id": firm_id, "firm_name": req.firm_name, "email": req.email, "name": req.admin_name, "role": "ca_admin"})
    return {"access_token": token, "token_type": "bearer", "firm_id": firm_id, "firm_name": req.firm_name, "user_id": user_id, "user_name": req.admin_name, "role": "ca_admin"}

@app.post("/auth/login")
async def login(req: LoginRequest):
    user = _users.get(req.email)
    if not user or not _verify_pw(req.password, user["hashed_password"]):
        raise HTTPException(401, "Invalid email or password")
    token = _make_token({"sub": user["user_id"], "firm_id": user["firm_id"], "firm_name": user["firm_name"], "email": user["email"], "name": user["admin_name"], "role": user["role"]})
    return {"access_token": token, "token_type": "bearer", "firm_id": user["firm_id"], "firm_name": user["firm_name"], "user_id": user["user_id"], "user_name": user["admin_name"], "role": user["role"]}

@app.get("/auth/me")
async def me(authorization: Optional[str] = None):
    if not authorization: raise HTTPException(401, "No token")
    token = authorization.replace("Bearer ", "")
    return _verify_token(token)

@app.post("/auth/waitlist")
async def waitlist(req: WaitlistRequest):
    """Capture email from landing page before signup."""
    _store[f"waitlist:{req.email}"] = {"email": req.email, "name": req.name, "joined_at": datetime.now().isoformat()}
    return {"status": "ok", "message": "You're on the list! We'll be in touch shortly."}

# ── HEALTH ─────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0", "domain": "gstagent.co.in", "timestamp": datetime.now().isoformat()}

# ── CLIENTS ────────────────────────────────────────────────────────────────────
@app.get("/clients")
async def list_clients(authorization: Optional[str] = None):
    if not authorization: raise HTTPException(401, "No token")
    payload = _verify_token(authorization.replace("Bearer ", ""))
    key = f"clients:{payload['firm_id']}"
    return {"clients": _store.get(key, [])}

@app.post("/clients")
async def create_client(client: dict, authorization: Optional[str] = None):
    if not authorization: raise HTTPException(401, "No token")
    payload = _verify_token(authorization.replace("Bearer ", ""))
    key = f"clients:{payload['firm_id']}"
    new_client = {**client, "id": str(uuid.uuid4()), "firm_id": payload["firm_id"], "created_at": datetime.now().isoformat()}
    if key not in _store: _store[key] = []
    _store[key].append(new_client)
    return {"client": new_client}

# ── RECONCILIATION ─────────────────────────────────────────────────────────────
@app.post("/reconcile")
async def reconcile(req: ReconcileRequest):
    result = reconcile_data(req.gstin, req.period, req.purchase_register, req.gstr_2b)
    rec_id = str(uuid.uuid4())
    _store[rec_id] = {"result": result, "company_name": req.company_name, "created_at": datetime.now().isoformat()}
    return {"reconciliation_id": rec_id, "result": result}

@app.post("/reconcile/upload")
async def reconcile_upload(
    gstin: str, period: str, company_name: str,
    purchase_register_file: UploadFile = File(...),
    gstr_2b_file: UploadFile = File(...)
):
    try:
        pr_bytes = await purchase_register_file.read()
        pr_df = pd.read_excel(io.BytesIO(pr_bytes))
        pr_df.columns = [c.lower().strip().replace(" ","_") for c in pr_df.columns]
        purchase_register = pr_df.to_dict(orient="records")

        b2b_bytes = await gstr_2b_file.read()
        if gstr_2b_file.filename.endswith(".json"):
            raw = json.loads(b2b_bytes)
            gstr_2b = raw if isinstance(raw, list) else _parse_2b_portal(raw)
        else:
            b2b_df = pd.read_excel(io.BytesIO(b2b_bytes))
            b2b_df.columns = [c.lower().strip().replace(" ","_") for c in b2b_df.columns]
            gstr_2b = b2b_df.to_dict(orient="records")

        result = reconcile_data(gstin, period, purchase_register, gstr_2b)
        rec_id = str(uuid.uuid4())
        _store[rec_id] = {"result": result, "company_name": company_name, "created_at": datetime.now().isoformat()}
        return {"reconciliation_id": rec_id, "result": result}
    except Exception as e:
        raise HTTPException(400, f"File error: {str(e)}")

@app.get("/reconcile/{rec_id}")
def get_reconciliation(rec_id: str):
    if rec_id not in _store: raise HTTPException(404, "Not found")
    return _store[rec_id]

# ── AI FEATURES ────────────────────────────────────────────────────────────────
@app.post("/ai/explain-mismatch")
async def explain_mismatch(reconciliation_id: str, mismatch_id: str):
    stored = _store.get(reconciliation_id)
    if not stored: raise HTTPException(404, "Reconciliation not found")
    m = next((x for x in stored["result"]["mismatches"] if x["mismatch_id"]==mismatch_id), None)
    if not m: raise HTTPException(404, "Mismatch not found")
    text = await call_claude(
        "You are a GST compliance expert. Explain mismatches in 3 clear sentences: what happened, the tax consequence, and the exact next step. Be specific with rupee amounts. Plain English.",
        f"Mismatch: {m['mismatch_type']}. Supplier: {m['supplier_name']} ({m['supplier_gstin']}). Invoice: {m['invoice_number']}. Tax impact: ₹{abs(m['tax_impact']):,.0f}. PR tax: {m.get('pr_tax_amount')}. 2B tax: {m.get('b2b_tax_amount')}."
    )
    return {"mismatch_id": mismatch_id, "explanation": text}

@app.post("/ai/vendor-email")
async def vendor_email(reconciliation_id: str, mismatch_id: str, sender_company: str, sender_gstin: str):
    stored = _store.get(reconciliation_id)
    if not stored: raise HTTPException(404, "Not found")
    m = next((x for x in stored["result"]["mismatches"] if x["mismatch_id"]==mismatch_id), None)
    if not m: raise HTTPException(404, "Mismatch not found")
    period = stored["result"]["period"]
    period_fmt = f"{period[:2]}/{period[2:]}"
    text = await call_claude(
        "You are a GST compliance professional drafting vendor follow-up emails. Professional but firm tone. Reference exact invoice numbers. State required action clearly. Include Subject: line. Under 180 words.",
        f"From: {sender_company} ({sender_gstin}). To: {m['supplier_name']} ({m['supplier_gstin']}). Invoice: {m['invoice_number']}. Period: {period_fmt}. Issue: {m['mismatch_type']}. ITC at risk: ₹{abs(m['tax_impact']):,.0f}. Required: {m['recommended_action']}."
    )
    return {"mismatch_id": mismatch_id, "email_draft": text}

@app.post("/ai/summary")
async def ai_summary(reconciliation_id: str):
    stored = _store.get(reconciliation_id)
    if not stored: raise HTTPException(404, "Not found")
    r = stored["result"]
    text = await call_claude(
        "You are a GST compliance analyst. Write a concise executive summary for a CA firm. Lead with critical findings. Quantify in rupees. Use bullet points. Under 250 words.",
        f"Company: {stored['company_name']}. Period: {r['period']}. PR: {r['total_pr_invoices']} invoices. 2B: {r['total_2b_invoices']}. Matched: {r['matched_invoices']}. Mismatches: {r['mismatched_invoices']}. ITC diff: ₹{r['itc_difference']:,.0f}. HIGH: {r['high_severity_count']}. MEDIUM: {r['medium_severity_count']}. Match rate: {r['summary_stats']['match_rate']}%.",
        max_tokens=800
    )
    return {"reconciliation_id": reconciliation_id, "summary": text}

@app.post("/ai/notice-reply")
async def notice_reply(req: NoticeReplyRequest):
    text = await call_claude(
        "You are a senior GST consultant drafting formal notice replies. Use exact notice numbers and dates. Cite relevant GST rules. Mark [REVIEW REQUIRED] where CA must verify before submitting. Structure: Reference → Position → Point-by-point response → Documents list → Closing. Formal legal language.",
        f"Notice: {req.notice_number} dated {req.notice_date}. Type: {req.notice_type}. Content: {req.notice_content}. Taxpayer: {req.taxpayer_name} ({req.taxpayer_gstin}). Supporting facts: {req.supporting_facts}.",
        max_tokens=1500
    )
    return {"notice_number": req.notice_number, "draft_reply": text, "disclaimer": "Review by qualified CA required before submission."}

# ── EXPORT ─────────────────────────────────────────────────────────────────────
@app.get("/export/{rec_id}/xlsx")
async def export_excel(rec_id: str):
    stored = _store.get(rec_id)
    if not stored: raise HTTPException(404, "Not found")
    try:
        from excel_export import generate_to_bytes
        xlsx = generate_to_bytes(stored["result"], stored["company_name"])
        period = stored["result"].get("period","")
        name = f"GST_Recon_{stored['company_name'][:20]}_{period}.xlsx".replace(" ","_")
        return Response(content=xlsx, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition":f"attachment; filename={name}"})
    except Exception as e:
        raise HTTPException(500, f"Export error: {str(e)}")

# ── BILLING ────────────────────────────────────────────────────────────────────
@app.get("/billing/plans")
async def billing_plans():
    return {"plans":[
        {"id":"starter","name":"Starter","price_monthly":1500,"price_yearly":14990,"max_gstins":5,"features":["5 GSTINs","20 reconciliations/mo","AI explanations","Excel export"],"popular":False},
        {"id":"growth","name":"Growth","price_monthly":4000,"price_yearly":39900,"max_gstins":25,"features":["25 GSTINs","100 reconciliations/mo","Notice replies","Tally connector","Priority support"],"popular":True},
        {"id":"enterprise","name":"Enterprise","price_monthly":9999,"price_yearly":99990,"max_gstins":-1,"features":["Unlimited GSTINs","GSP integration","Multi-user","Audit logs","SLA support"],"popular":False},
    ],"currency":"INR","note":"Launch pricing — 50% off for first 20 firms"}

@app.post("/billing/create-order")
async def create_order(plan_id: str, billing: str = "monthly"):
    rzp_key = os.getenv("RAZORPAY_KEY_ID","")
    prices = {"starter":{"monthly":150000,"yearly":1499000},"growth":{"monthly":400000,"yearly":3990000},"enterprise":{"monthly":999900,"yearly":9999000}}
    if plan_id not in prices: raise HTTPException(400, "Unknown plan")
    amount = prices[plan_id].get(billing, prices[plan_id]["monthly"])
    if not rzp_key:
        return {"order_id":"demo_order_"+str(uuid.uuid4())[:8],"amount":amount,"currency":"INR","plan_id":plan_id,"razorpay_key":"","demo":True,"message":"Add RAZORPAY_KEY_ID to enable real payments"}
    try:
        import razorpay
        rzp = razorpay.Client(auth=(rzp_key, os.getenv("RAZORPAY_KEY_SECRET","")))
        order = rzp.order.create({"amount":amount,"currency":"INR","receipt":f"gstagent_{plan_id}_{uuid.uuid4().hex[:8]}","notes":{"plan":plan_id,"billing":billing}})
        return {"order_id":order["id"],"amount":amount,"currency":"INR","plan_id":plan_id,"razorpay_key":rzp_key}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/billing/status")
async def billing_status():
    return {"plan":"trial","plan_name":"Free Trial","status":"active","days_remaining":14,"reconciliations_used":0,"reconciliations_limit":5}

# ── HELPERS ────────────────────────────────────────────────────────────────────
def _parse_2b_portal(data: dict) -> list[dict]:
    records = []
    for supplier in data.get("data",{}).get("docdata",{}).get("b2b",[]):
        for inv in supplier.get("inv",[]):
            for item in inv.get("items",[{}]):
                records.append({"supplier_gstin":supplier.get("ctin",""),"supplier_name":supplier.get("trdnm",""),"invoice_number":inv.get("inum",""),"invoice_date":inv.get("idt",""),"taxable_value":item.get("txval",0),"igst":item.get("igst",0),"cgst":item.get("cgst",0),"sgst":item.get("sgst",0),"reverse_charge":inv.get("rev","N")=="Y"})
    return records

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
