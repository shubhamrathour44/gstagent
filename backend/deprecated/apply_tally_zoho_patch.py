
from pathlib import Path

APP = Path("frontend/app.html")
MAIN = Path("backend/main_v2.py")

app = APP.read_text(encoding="utf-8", errors="ignore")
main = MAIN.read_text(encoding="utf-8", errors="ignore")

menu = """\n    <button class="ni" onclick="nav('accountingIntegrations',this)"><span class="ni-icon">📚</span>Accounting Integrations</button>\n"""

if "pg-accountingIntegrations" not in app:
    if "Invoice Register" in app:
        # Add after first Invoice Register menu text occurrence
        pos = app.find("Invoice Register")
        line_start = app.rfind("<button", 0, pos)
        line_end = app.find("</button>", pos)
        if line_start != -1 and line_end != -1:
            line_end += len("</button>")
            app = app[:line_end] + menu + app[line_end:]
    elif '<div class="ns">Income Tax</div>' in app:
        app = app.replace('<div class="ns">Income Tax</div>', menu + '\n    <div class="ns">Income Tax</div>')

    page = """
    <!-- ACCOUNTING INTEGRATIONS -->
    <div class="page" id="pg-accountingIntegrations">
      <div class="card">
        <div class="ch">📚 Accounting Integrations — Tally + Zoho Books</div>
        <div class="info-box">Upload Tally or Zoho Books Excel/CSV export → import invoices → view in Invoice Register → reconcile with GSTR-2B.</div>
        <div class="stats">
          <div class="stat stat-b"><div class="sv" id="acc-tally-count" style="color:var(--blue3)">0</div><div class="sl">Tally Imported</div></div>
          <div class="stat stat-g"><div class="sv" id="acc-zoho-count" style="color:var(--green)">0</div><div class="sl">Zoho Imported</div></div>
          <div class="stat stat-a"><div class="sv" id="acc-master-count" style="color:var(--amb)">0</div><div class="sl">Masters Parsed</div></div>
          <div class="stat stat-r"><div class="sv" style="color:var(--red)">Demo</div><div class="sl">Status</div></div>
        </div>
      </div>

      <div class="card">
        <div class="ch">📘 Tally Import</div>
        <div class="g3">
          <div class="fg"><label>Client</label><select id="tally-client"></select></div>
          <div class="fg"><label>Register Type</label><select id="tally-type"><option value="purchase">Purchase Register</option><option value="sales">Sales Register</option></select></div>
          <div class="fg"><label>Tally Excel/CSV</label><input type="file" id="tally-file" accept=".xlsx,.xls,.csv"></div>
        </div>
        <button class="btn btn-p" onclick="importTallyInvoices()">📥 Import Tally Invoices</button>
        <button class="btn btn-s" onclick="importTallyMasters()">📚 Import Tally Masters</button>
        <div id="tally-msg" style="margin-top:10px"></div>
      </div>

      <div class="card">
        <div class="ch">🚀 Zoho Books Import</div>
        <div class="g3">
          <div class="fg"><label>Client</label><select id="zoho-client"></select></div>
          <div class="fg"><label>Register Type</label><select id="zoho-type"><option value="sales">Sales Invoices</option><option value="purchase">Purchase Bills</option></select></div>
          <div class="fg"><label>Zoho Excel/CSV</label><input type="file" id="zoho-file" accept=".xlsx,.xls,.csv"></div>
        </div>
        <button class="btn btn-p" onclick="importZohoInvoices()">📥 Import Zoho Invoices</button>
        <button class="btn btn-s" onclick="importZohoContacts()">👥 Import Zoho Contacts</button>
        <div id="zoho-msg" style="margin-top:10px"></div>
      </div>
    </div>
"""
    if "<!-- AI AGENT -->" in app:
        app = app.replace("<!-- AI AGENT -->", page + "\n\n    <!-- AI AGENT -->")
    else:
        app = app.replace("</div>\n</div>\n\n<script>", page + "\n  </div>\n</div>\n\n<script>")

if "accountingIntegrations" not in app.split("const titles", 1)[-1].split("};", 1)[0]:
    app = app.replace("aiagent:'🤖 AI Agent'", "aiagent:'🤖 AI Agent',accountingIntegrations:'📚 Accounting Integrations'")
    app = app.replace('aiagent:"🤖 AI Agent"', 'aiagent:"🤖 AI Agent",accountingIntegrations:"📚 Accounting Integrations"')

if "loadAccountingIntegrations" not in app:
    js = """
function fillIntegrationClientDropdowns(){
  const source = document.querySelector('#smart-client, #smartClientSelect, #recon-client, #recon-client-select, #invoice-client-filter');
  ['tally-client','zoho-client'].forEach(id=>{
    const el=$(id); if(!el) return;
    if(source && source.options && source.options.length){ el.innerHTML=source.innerHTML; }
    else { el.innerHTML='<option value="">Select Client</option>'; }
  });
}
function loadAccountingIntegrations(){ fillIntegrationClientDropdowns(); }
async function importTallyInvoices(){
  const client=$('tally-client')?.value, file=$('tally-file')?.files?.[0];
  if(!client||!file){ $('tally-msg').innerHTML='<div class="err-box">Select client and upload Tally Excel/CSV</div>'; return; }
  const fd=new FormData(); fd.append('client_id',client); fd.append('invoice_type',$('tally-type').value); fd.append('file',file);
  try{ const r=await fetch(API+'/tally-import/invoices',{method:'POST',headers:{Authorization:'Bearer '+token},body:fd}); const d=await r.json(); if(!r.ok) throw new Error(d.detail||'Import failed'); $('acc-tally-count').textContent=d.imported||0; $('tally-msg').innerHTML=`<div class="ok-box">✅ Imported ${d.imported||0} Tally invoices</div>`; if(typeof loadInvoiceRegister==='function') loadInvoiceRegister(); }
  catch(e){ $('tally-msg').innerHTML='<div class="err-box">Tally import failed: '+e.message+'</div>'; }
}
async function importTallyMasters(){
  const file=$('tally-file')?.files?.[0]; if(!file){ $('tally-msg').innerHTML='<div class="err-box">Upload Tally Excel/CSV first</div>'; return; }
  const fd=new FormData(); fd.append('file',file);
  try{ const r=await fetch(API+'/tally-import/masters',{method:'POST',headers:{Authorization:'Bearer '+token},body:fd}); const d=await r.json(); if(!r.ok) throw new Error(d.detail||'Import failed'); $('acc-master-count').textContent=d.masters_found||0; $('tally-msg').innerHTML=`<div class="ok-box">✅ Parsed ${d.masters_found||0} Tally masters</div>`; }
  catch(e){ $('tally-msg').innerHTML='<div class="err-box">Tally masters failed: '+e.message+'</div>'; }
}
async function importZohoInvoices(){
  const client=$('zoho-client')?.value, file=$('zoho-file')?.files?.[0];
  if(!client||!file){ $('zoho-msg').innerHTML='<div class="err-box">Select client and upload Zoho Excel/CSV</div>'; return; }
  const fd=new FormData(); fd.append('client_id',client); fd.append('invoice_type',$('zoho-type').value); fd.append('file',file);
  try{ const r=await fetch(API+'/zoho-import/invoices',{method:'POST',headers:{Authorization:'Bearer '+token},body:fd}); const d=await r.json(); if(!r.ok) throw new Error(d.detail||'Import failed'); $('acc-zoho-count').textContent=d.imported||0; $('zoho-msg').innerHTML=`<div class="ok-box">✅ Imported ${d.imported||0} Zoho invoices</div>`; if(typeof loadInvoiceRegister==='function') loadInvoiceRegister(); }
  catch(e){ $('zoho-msg').innerHTML='<div class="err-box">Zoho import failed: '+e.message+'</div>'; }
}
async function importZohoContacts(){
  const file=$('zoho-file')?.files?.[0]; if(!file){ $('zoho-msg').innerHTML='<div class="err-box">Upload Zoho Excel/CSV first</div>'; return; }
  const fd=new FormData(); fd.append('file',file);
  try{ const r=await fetch(API+'/zoho-import/masters',{method:'POST',headers:{Authorization:'Bearer '+token},body:fd}); const d=await r.json(); if(!r.ok) throw new Error(d.detail||'Import failed'); $('acc-master-count').textContent=d.masters_found||0; $('zoho-msg').innerHTML=`<div class="ok-box">✅ Parsed ${d.masters_found||0} Zoho contacts</div>`; }
  catch(e){ $('zoho-msg').innerHTML='<div class="err-box">Zoho contacts failed: '+e.message+'</div>'; }
}
"""
    app = app.replace("\ninit();", "\n" + js + "\ninit();")
if "'accountingIntegrations':loadAccountingIntegrations" not in app:
    app = app.replace("const m={clients:loadClients", "const m={'accountingIntegrations':loadAccountingIntegrations,clients:loadClients")
    app = app.replace("const m = {clients:loadClients", "const m = {'accountingIntegrations':loadAccountingIntegrations,clients:loadClients")

APP.write_text(app, encoding="utf-8")

if "tally_import" not in main:
    main = main.replace("from fastapi.middleware.cors import CORSMiddleware", "from fastapi.middleware.cors import CORSMiddleware\nfrom tally_import import router as tally_import_router\nfrom zoho_import import router as zoho_import_router")
if "tally_import_router" not in main or "zoho_import_router" not in main:
    if "engine =" in main:
        main = main.replace("engine =", "app.include_router(tally_import_router)\napp.include_router(zoho_import_router)\n\nengine =")
    else:
        main += "\napp.include_router(tally_import_router)\napp.include_router(zoho_import_router)\n"
MAIN.write_text(main, encoding="utf-8")
print("Tally + Zoho patch applied successfully.")
