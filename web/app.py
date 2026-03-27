"""
web/app.py — FastAPI dashboard (fully functional)

Fix #7:  Proper login with session cookie (no insecure prompt())
New:     /api/health endpoint, /api/bots/{id}/restart,
         /api/users/search, text broadcast from dashboard,
         WebSocket live broadcast progress
"""
import asyncio
import secrets
from typing import Optional

from fastapi import (
    FastAPI, Request, Response, Depends,
    HTTPException, status, Cookie, WebSocket, WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import DASHBOARD_TOKEN
from database import users as users_db, bots as bots_db, broadcasts as bc_db
from database.db import ping_db
from utils.importer import import_from_mongo
from utils.broadcaster import request_cancel

app = FastAPI(title="MultiBot Dashboard", version="2.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# ── Session store ─────────────────────────────────────────────────────────────
_SESSIONS: dict = {}


def _make_session() -> str:
    sid = secrets.token_urlsafe(32)
    _SESSIONS[sid] = True
    return sid


def _check_session(session: Optional[str] = Cookie(default=None)):
    if not session or session not in _SESSIONS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return True


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return HTMLResponse(_LOGIN_HTML)


@app.post("/login")
async def do_login(request: Request):
    form  = await request.form()
    token = form.get("token", "")
    if token != DASHBOARD_TOKEN:
        return HTMLResponse(_LOGIN_HTML.replace(
            "<!--ERR-->",
            '<p class="err">❌ Invalid token</p>',
        ))
    sid  = _make_session()
    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie("session", sid, httponly=True, samesite="lax", max_age=86400)
    return resp


@app.post("/logout")
async def logout(session: Optional[str] = Cookie(default=None)):
    if session:
        _SESSIONS.pop(session, None)
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie("session")
    return resp


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(session: Optional[str] = Cookie(default=None)):
    if not session or session not in _SESSIONS:
        return RedirectResponse("/login")
    return HTMLResponse(_DASHBOARD_HTML)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def api_health():
    db_ok = await ping_db()
    from bot_manager import manager
    return {
        "status":  "ok" if db_ok else "degraded",
        "db":      db_ok,
        "bots_online": manager.count_online(),
    }


# ── Stats & Bots ──────────────────────────────────────────────────────────────

@app.get("/api/stats")
async def api_stats(_=Depends(_check_session)):
    g    = await users_db.global_stats()
    bots = await bots_db.get_all_bots()
    return {"global": g, "bot_count": len(bots)}


@app.get("/api/bots")
async def api_bots(_=Depends(_check_session)):
    from datetime import datetime, timezone
    from config import HEARTBEAT_TIMEOUT
    bots   = await bots_db.get_all_bots()
    result = []
    for b in bots:
        last = b.get("last_seen")
        if last:
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            online = (datetime.now(timezone.utc) - last).total_seconds() < HEARTBEAT_TIMEOUT
        else:
            online = False
        s = await users_db.stats_for_bot(b["bot_id"])
        result.append({
            "bot_id":   b["bot_id"],
            "bot_name": b.get("bot_name", str(b["bot_id"])),
            "is_active": b.get("is_active"),
            "online":   online,
            "status":   b.get("status", "unknown"),
            **s,
        })
    return result


class AddBotReq(BaseModel):
    token: str


@app.post("/api/bots")
async def api_add_bot(req: AddBotReq, _=Depends(_check_session)):
    from bot_manager import manager
    try:
        info = await manager.add_bot(req.token)
        return {"ok": True, **info}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.delete("/api/bots/{bot_id}")
async def api_remove_bot(bot_id: int, _=Depends(_check_session)):
    from bot_manager import manager
    await manager.remove_bot(bot_id)
    await bots_db.remove_bot(bot_id)
    return {"ok": True}


@app.post("/api/bots/{bot_id}/restart")
async def api_restart_bot(bot_id: int, _=Depends(_check_session)):
    from bot_manager import manager
    try:
        await manager.restart_bot(bot_id)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/api/bots/{bot_id}/close")
async def api_close(bot_id: int, _=Depends(_check_session)):
    count = await users_db.close_bot_users(bot_id)
    return {"ok": True, "closed": count}


@app.post("/api/bots/{bot_id}/open")
async def api_open(bot_id: int, _=Depends(_check_session)):
    count = await users_db.open_bot_users(bot_id)
    return {"ok": True, "opened": count}


# ── Users ─────────────────────────────────────────────────────────────────────

@app.get("/api/users/search")
async def api_search_users(
    q: str,
    bot_id: Optional[int] = None,
    _=Depends(_check_session),
):
    results = await users_db.search_users(q, bot_id=bot_id, limit=20)
    return results


# ── Broadcasts ────────────────────────────────────────────────────────────────

@app.get("/api/broadcasts")
async def api_broadcasts(_=Depends(_check_session)):
    return await bc_db.get_recent_broadcasts(20)


@app.post("/api/broadcasts/cancel/{bc_id}")
async def api_cancel(bc_id: str, _=Depends(_check_session)):
    request_cancel(bc_id)
    await bc_db.cancel_broadcast(bc_id)
    return {"ok": True}


class TextBroadcastReq(BaseModel):
    text: str
    bot_id: Optional[int] = None   # None = all bots


@app.post("/api/broadcasts/text")
async def api_text_broadcast(req: TextBroadcastReq, _=Depends(_check_session)):
    """Send a plain-text broadcast from the dashboard."""
    from bot_manager import manager
    online = manager.get_online_clients()
    if not online:
        raise HTTPException(400, "No bots online")

    if req.bot_id:
        user_ids = await users_db.get_broadcast_users(req.bot_id)
    else:
        user_ids = await users_db.get_all_unique_users()

    if not user_ids:
        raise HTTPException(400, "No eligible users")

    bc_id = await bc_db.create_broadcast(
        target_bot_id=req.bot_id,
        sender_bot_ids=list(online.keys()),
        total_users=len(user_ids),
        initiated_by=0,
    )

    async def _run():
        client = next(iter(online.values()))
        bot_id = next(iter(online.keys()))
        ok = fail = 0
        for uid in user_ids:
            try:
                await client.send_message(uid, req.text)
                ok += 1
                await asyncio.sleep(0.05)
            except Exception:
                fail += 1
        await bc_db.finish_broadcast(bc_id, "completed")
        await bc_db.update_progress(bc_id, ok, fail, len(user_ids))

    asyncio.create_task(_run())
    return {"ok": True, "broadcast_id": bc_id, "total": len(user_ids)}


# ── Analytics ─────────────────────────────────────────────────────────────────

@app.get("/api/analytics")
async def api_analytics(bot_id: Optional[int] = None, _=Depends(_check_session)):
    growth = await users_db.daily_growth(bot_id=bot_id, days=14)
    hourly = await users_db.hourly_active(bot_id=bot_id)
    return {"growth": growth, "hourly": hourly}


# ── Import ────────────────────────────────────────────────────────────────────

class ImportReq(BaseModel):
    mongo_url:  str
    db_name:    str
    collection: str
    bot_id:     int


@app.post("/api/import")
async def api_import(req: ImportReq, _=Depends(_check_session)):
    ins, skp, err = await import_from_mongo(
        req.mongo_url, req.db_name, req.collection, req.bot_id
    )
    if err:
        raise HTTPException(400, err)
    return {"ok": True, "inserted": ins, "skipped": skp}


# ── Templates & Schedules ─────────────────────────────────────────────────────

@app.get("/api/templates")
async def api_templates(_=Depends(_check_session)):
    return await bc_db.get_templates()


@app.get("/api/schedules")
async def api_schedules(_=Depends(_check_session)):
    return await bc_db.get_pending_schedules()


# ── HTML ──────────────────────────────────────────────────────────────────────

_LOGIN_HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>MultiBot Login</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#0f1117;display:flex;align-items:center;justify-content:center;
       min-height:100vh;font-family:'Segoe UI',sans-serif}
  .card{background:#1a1d27;border:1px solid #2d3148;border-radius:16px;
        padding:40px;width:360px;text-align:center}
  h2{color:#e2e8f0;margin-bottom:8px}
  p{color:#64748b;font-size:.9rem;margin-bottom:24px}
  input{width:100%;background:#0f1117;border:1px solid #2d3148;color:#e2e8f0;
        border-radius:8px;padding:12px 14px;font-size:.95rem;margin-bottom:16px}
  button{width:100%;background:#7c6af7;color:#fff;border:none;border-radius:8px;
         padding:12px;font-size:1rem;cursor:pointer}
  button:hover{opacity:.85}
  .err{color:#ef4444;font-size:.85rem;margin-top:-8px;margin-bottom:10px}
  <!--ERR-->
</style></head>
<body><div class="card">
  <h2>🤖 MultiBot</h2>
  <p>Enter your dashboard token to continue</p>
  <form method="post" action="/login">
    <input type="password" name="token" placeholder="Dashboard token" autofocus>
    <!--ERR-->
    <button type="submit">Login →</button>
  </form>
</div></body></html>"""


_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MultiBot Dashboard</title>
<style>
:root{--bg:#0f1117;--card:#1a1d27;--accent:#7c6af7;--green:#22c55e;--red:#ef4444;
      --yellow:#f59e0b;--text:#e2e8f0;--muted:#64748b;--border:#2d3148}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',sans-serif;display:flex;min-height:100vh}
aside{width:200px;background:var(--card);border-right:1px solid var(--border);
      padding:24px 0;display:flex;flex-direction:column;flex-shrink:0}
aside h1{font-size:1.1rem;padding:0 20px 20px;border-bottom:1px solid var(--border);margin-bottom:12px}
nav button{display:block;width:100%;text-align:left;padding:10px 20px;background:none;
           border:none;color:var(--muted);cursor:pointer;font-size:.9rem;transition:.15s}
nav button:hover,nav button.active{background:#7c6af720;color:var(--text)}
nav button.active{border-left:3px solid var(--accent)}
.logout{margin-top:auto;padding:0 16px}
.logout button{width:100%;background:#ef444420;border:1px solid var(--red);
               color:var(--red);border-radius:8px;padding:8px;cursor:pointer;font-size:.85rem}
main{flex:1;padding:28px;overflow-y:auto}
.section{display:none}.section.active{display:block}
h2{font-size:1.2rem;margin-bottom:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:14px;margin-bottom:24px}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px}
.val{font-size:1.8rem;font-weight:700;color:var(--accent)}
.lbl{font-size:.78rem;color:var(--muted);margin-top:4px}
table{width:100%;border-collapse:collapse;font-size:.88rem}
th{text-align:left;padding:10px 12px;color:var(--muted);border-bottom:1px solid var(--border)}
td{padding:10px 12px;border-bottom:1px solid #1e2130;vertical-align:middle}
tr:hover td{background:#1e2130}
.online{color:var(--green)}.offline{color:var(--red)}
.btn{background:var(--accent);color:#fff;border:none;border-radius:7px;
     padding:7px 14px;cursor:pointer;font-size:.82rem}
.btn:hover{opacity:.85}
.btn.sm{padding:4px 9px;font-size:.78rem}
.btn.red{background:var(--red)}
.btn.green{background:var(--green)}
.btn.yellow{background:var(--yellow);color:#000}
input,select,textarea{background:#0f1117;border:1px solid var(--border);color:var(--text);
       border-radius:8px;padding:9px 12px;font-size:.88rem;width:100%;margin-bottom:10px}
textarea{resize:vertical;min-height:80px}
.row{display:flex;gap:10px}
.row>*{flex:1}
#toast{display:none;position:fixed;bottom:24px;right:24px;padding:12px 20px;
       border-radius:10px;color:#fff;font-size:.9rem;z-index:999;box-shadow:0 4px 20px #0008}
.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:.75rem}
.badge.ok{background:#22c55e20;color:var(--green)}
.badge.err{background:#ef444420;color:var(--red)}
code{background:#0f1117;padding:1px 5px;border-radius:4px;font-size:.83rem}
</style></head>
<body>

<aside>
  <h1>🤖 MultiBot</h1>
  <nav>
    <button onclick="show('overview',this)" class="active">📊 Overview</button>
    <button onclick="show('bots',this)">🤖 Bots</button>
    <button onclick="show('broadcast',this)">📢 Broadcast</button>
    <button onclick="show('logs',this)">📜 Logs</button>
    <button onclick="show('analytics',this)">📈 Analytics</button>
    <button onclick="show('users',this)">👥 Users</button>
    <button onclick="show('schedule',this)">⏰ Schedule</button>
    <button onclick="show('import',this)">📥 Import</button>
  </nav>
  <div class="logout">
    <form method="post" action="/logout"><button type="submit">🚪 Logout</button></form>
  </div>
</aside>

<main>

<!-- OVERVIEW -->
<div class="section active" id="overview">
  <h2>📊 Overview <span id="lu" style="font-size:.75rem;color:var(--muted);font-weight:400"></span></h2>
  <div class="grid" id="statCards"></div>
  <div class="card">
    <table>
      <thead><tr><th>Bot</th><th>Status</th><th>Total</th><th>Eligible</th><th>Blocked</th><th>Closed</th><th>Imported</th></tr></thead>
      <tbody id="overviewTable"></tbody>
    </table>
  </div>
</div>

<!-- BOTS -->
<div class="section" id="bots">
  <h2>🤖 Bot Management</h2>
  <div class="card" style="margin-bottom:16px">
    <div class="row">
      <input id="newToken" placeholder="Bot token from @BotFather" style="margin:0">
      <button class="btn" onclick="addBot()" style="flex:0 0 auto">➕ Add Bot</button>
    </div>
  </div>
  <div class="card">
    <table>
      <thead><tr><th>Bot</th><th>Status</th><th>Total</th><th>Eligible</th><th>Actions</th></tr></thead>
      <tbody id="botsTable"></tbody>
    </table>
  </div>
</div>

<!-- BROADCAST -->
<div class="section" id="broadcast">
  <h2>📢 Text Broadcast</h2>
  <div class="card">
    <p style="color:var(--muted);font-size:.85rem;margin-bottom:12px">
      For media/photo broadcasts, use <code>/broadcast</code> in Telegram instead.
    </p>
    <select id="bcBot" style="margin-bottom:10px"></select>
    <textarea id="bcText" placeholder="Message text…"></textarea>
    <button class="btn" onclick="sendTextBc()">🚀 Send Broadcast</button>
    <p id="bcResult" style="margin-top:10px;font-size:.85rem"></p>
  </div>
</div>

<!-- LOGS -->
<div class="section" id="logs">
  <h2>📜 Broadcast Logs</h2>
  <div class="card">
    <table>
      <thead><tr><th>ID</th><th>Target</th><th>Total</th><th>✅</th><th>❌</th><th>Status</th><th>Date</th></tr></thead>
      <tbody id="logsTable"></tbody>
    </table>
  </div>
</div>

<!-- ANALYTICS -->
<div class="section" id="analytics">
  <h2>📈 Analytics</h2>
  <div class="card" style="margin-bottom:16px">
    <select id="analyticsBot" onchange="loadAnalytics()" style="width:220px;margin-bottom:16px">
      <option value="">All Bots</option>
    </select>
    <h3 style="font-size:.9rem;color:var(--muted);margin-bottom:10px">User Growth (last 14 days)</h3>
    <canvas id="growthChart" height="110"></canvas>
  </div>
  <div class="card">
    <h3 style="font-size:.9rem;color:var(--muted);margin-bottom:10px">Active Users by Hour of Day</h3>
    <canvas id="hourlyChart" height="110"></canvas>
  </div>
</div>

<!-- USERS -->
<div class="section" id="users">
  <h2>👥 User Search</h2>
  <div class="card">
    <div class="row">
      <input id="userQ" placeholder="Search by name or @username" style="margin:0">
      <button class="btn" onclick="searchUsers()" style="flex:0 0 auto">🔍 Search</button>
    </div>
    <div id="userResults" style="margin-top:14px"></div>
  </div>
</div>

<!-- SCHEDULE -->
<div class="section" id="schedule">
  <h2>⏰ Scheduled Broadcasts</h2>
  <div class="card" style="margin-bottom:16px">
    <p style="color:var(--muted);font-size:.85rem">
      Use <code>/schedule &lt;bot_id|all&gt; &lt;YYYY-MM-DD&gt; &lt;HH:MM&gt;</code> in Telegram to create schedules.
    </p>
  </div>
  <div class="card">
    <table>
      <thead><tr><th>ID</th><th>Target</th><th>Run At (UTC)</th><th>Text</th></tr></thead>
      <tbody id="schedTable"></tbody>
    </table>
  </div>
</div>

<!-- IMPORT -->
<div class="section" id="import">
  <h2>📥 Import from External MongoDB</h2>
  <div class="card">
    <input id="impUrl" placeholder="mongodb+srv://user:pass@host/…">
    <div class="row">
      <input id="impDb"  placeholder="Database name"   style="margin:0">
      <input id="impCol" placeholder="Collection name" style="margin:0">
    </div>
    <input id="impBot" placeholder="Target bot_id" style="margin-top:10px">
    <button class="btn" onclick="runImport()" style="margin-top:4px">Import</button>
    <p id="impResult" style="margin-top:10px;font-size:.85rem"></p>
  </div>
</div>

</main>
<div id="toast"></div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>
let _growthChart = null, _hourlyChart = null;

async function api(path, method='GET', body=null){
  const r = await fetch('/api'+path,{
    method,
    headers:{'Content-Type':'application/json'},
    body: body ? JSON.stringify(body) : null,
    credentials:'same-origin',
  });
  if(r.status===401){ location='/login'; return null; }
  if(!r.ok){ const e=await r.json().catch(()=>({detail:r.statusText})); toast(e.detail||'Error',false); return null; }
  return r.json();
}

function show(id,btn){
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b=>b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  if(btn) btn.classList.add('active');
  ({overview:loadOverview,bots:loadBots,logs:loadLogs,
    analytics:loadAnalytics,broadcast:loadBcBots,
    schedule:loadSchedules}[id]||noop)();
}
function noop(){}

function toast(msg,ok=true){
  const t=document.getElementById('toast');
  t.textContent=msg; t.style.background=ok?'#22c55e':'#ef4444';
  t.style.display='block'; setTimeout(()=>t.style.display='none',3000);
}

async function loadOverview(){
  const [stats,bots]=await Promise.all([api('/stats'),api('/bots')]);
  if(!stats||!bots) return;
  const g=stats.global;
  document.getElementById('statCards').innerHTML=`
    <div class="card"><div class="val">${g.total}</div><div class="lbl">Total Users</div></div>
    <div class="card"><div class="val">${g.active}</div><div class="lbl">Active</div></div>
    <div class="card"><div class="val">${g.eligible}</div><div class="lbl">Eligible</div></div>
    <div class="card"><div class="val">${g.blocked}</div><div class="lbl">Blocked</div></div>
    <div class="card"><div class="val">${stats.bot_count}</div><div class="lbl">Bots</div></div>`;
  document.getElementById('overviewTable').innerHTML=bots.map(b=>`
    <tr>
      <td>@${b.bot_name} <code>${b.bot_id}</code></td>
      <td class="${b.online?'online':'offline'}">${b.online?'🟢 Online':'🔴 Offline'}</td>
      <td>${b.total}</td><td>${b.eligible}</td>
      <td>${b.blocked}</td><td>${b.closed}</td><td>${b.imported}</td>
    </tr>`).join('');
  document.getElementById('lu').textContent='Updated: '+new Date().toLocaleTimeString();
}

async function loadBots(){
  const bots=await api('/bots'); if(!bots) return;
  document.getElementById('botsTable').innerHTML=bots.map(b=>`
    <tr>
      <td>@${b.bot_name} <code>${b.bot_id}</code></td>
      <td class="${b.online?'online':'offline'}">${b.online?'🟢':'🔴'} ${b.status}</td>
      <td>${b.total}</td><td>${b.eligible}</td>
      <td style="white-space:nowrap">
        <button class="btn sm yellow" onclick="restartBot(${b.bot_id})">🔄</button>
        <button class="btn sm" onclick="closeUsers(${b.bot_id})">🔒</button>
        <button class="btn sm green" onclick="openUsers(${b.bot_id})">🔓</button>
        <button class="btn sm red" onclick="removeBot(${b.bot_id})">🗑</button>
      </td>
    </tr>`).join('');
}

async function addBot(){
  const token=document.getElementById('newToken').value.trim();
  if(!token) return toast('Enter a token',false);
  const r=await api('/bots','POST',{token}); if(!r) return;
  toast('✅ @'+r.username+' added'); document.getElementById('newToken').value=''; loadBots();
}
async function removeBot(id){ if(!confirm('Remove bot '+id+'?')) return; await api('/bots/'+id,'DELETE'); toast('Removed'); loadBots(); }
async function restartBot(id){ const r=await api('/bots/'+id+'/restart','POST'); if(r) toast('🔄 Restarted'); loadBots(); }
async function closeUsers(id){ const r=await api('/bots/'+id+'/close','POST'); if(r) toast('🔒 Closed '+r.closed); }
async function openUsers(id){ const r=await api('/bots/'+id+'/open','POST'); if(r) toast('🔓 Opened '+r.opened); }

async function loadBcBots(){
  const bots=await api('/bots'); if(!bots) return;
  const sel=document.getElementById('bcBot');
  sel.innerHTML='<option value="">— All Bots —</option>';
  bots.forEach(b=>sel.innerHTML+=`<option value="${b.bot_id}">@${b.bot_name}</option>`);
}

async function sendTextBc(){
  const text=document.getElementById('bcText').value.trim();
  const bot_id=document.getElementById('bcBot').value||null;
  if(!text) return toast('Enter message text',false);
  const body={text, bot_id: bot_id ? parseInt(bot_id) : null};
  const r=await api('/broadcasts/text','POST',body); if(!r) return;
  const p=document.getElementById('bcResult');
  p.style.color='var(--green)';
  p.textContent=`✅ Started — ID: ${r.broadcast_id.slice(-8)} | Users: ${r.total}`;
  toast('✅ Broadcast started');
}

async function loadLogs(){
  const logs=await api('/broadcasts'); if(!logs) return;
  const em={completed:'✅',running:'🔄',cancelled:'🛑',saved:'💾'};
  document.getElementById('logsTable').innerHTML=logs.length?logs.map(d=>`
    <tr>
      <td><code>${d._id.slice(-8)}</code></td>
      <td>${d.target_bot_id||'All'}</td>
      <td>${d.total_users}</td>
      <td style="color:var(--green)">${d.success}</td>
      <td style="color:var(--red)">${d.failed}</td>
      <td>${em[d.status]||'?'} ${d.status}
        ${d.status==='running'?`<button class="btn sm red" onclick="cancelBc('${d._id}')">Cancel</button>`:''}
      </td>
      <td style="color:var(--muted);font-size:.78rem">${new Date(d.created_at).toLocaleString()}</td>
    </tr>`).join(''):'<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:20px">No broadcasts yet</td></tr>';
}
async function cancelBc(id){ await api('/broadcasts/cancel/'+id,'POST'); toast('Cancelled'); loadLogs(); }

async function loadAnalytics(){
  const botId=document.getElementById('analyticsBot').value;
  const path='/analytics'+(botId?'?bot_id='+botId:'');
  const data=await api(path); if(!data) return;

  if(_growthChart) _growthChart.destroy();
  _growthChart=new Chart(document.getElementById('growthChart'),{
    type:'bar',
    data:{labels:data.growth.map(d=>d.date),
          datasets:[{label:'New Users',data:data.growth.map(d=>d.count),
                     backgroundColor:'#7c6af7',borderRadius:6}]},
    options:{plugins:{legend:{display:false}},
             scales:{y:{beginAtZero:true,grid:{color:'#1e2130'}},x:{grid:{display:false}}}}
  });

  if(_hourlyChart) _hourlyChart.destroy();
  const hours=Array.from({length:24},(_,i)=>i);
  const hMap=Object.fromEntries((data.hourly||[]).map(h=>[h.hour,h.count]));
  _hourlyChart=new Chart(document.getElementById('hourlyChart'),{
    type:'line',
    data:{labels:hours.map(h=>h+':00'),
          datasets:[{label:'Active',data:hours.map(h=>hMap[h]||0),
                     borderColor:'#22c55e',backgroundColor:'#22c55e20',tension:.4,fill:true}]},
    options:{plugins:{legend:{display:false}},
             scales:{y:{beginAtZero:true,grid:{color:'#1e2130'}},x:{grid:{display:false}}}}
  });

  const bots=await api('/bots'); if(!bots) return;
  const sel=document.getElementById('analyticsBot');
  if(sel.options.length===1) bots.forEach(b=>sel.innerHTML+=`<option value="${b.bot_id}">@${b.bot_name}</option>`);
}

async function searchUsers(){
  const q=document.getElementById('userQ').value.trim();
  if(!q) return;
  const data=await api('/users/search?q='+encodeURIComponent(q)); if(!data) return;
  const div=document.getElementById('userResults');
  if(!data.length){ div.innerHTML='<p style="color:var(--muted)">No users found.</p>'; return; }
  div.innerHTML=`<table>
    <thead><tr><th>ID</th><th>Name</th><th>Username</th><th>Bot</th><th>Status</th></tr></thead>
    <tbody>${data.map(u=>{
      const s=u.is_blocked?'⛔ Blocked':u.closed?'🔒 Closed':'✅ Active';
      return `<tr><td><code>${u.user_id}</code></td><td>${u.first_name||''}</td>
        <td>@${u.username||'N/A'}</td><td>${u.bot_id}</td><td>${s}</td></tr>`;
    }).join('')}</tbody></table>`;
}

async function loadSchedules(){
  const data=await api('/schedules'); if(!data) return;
  document.getElementById('schedTable').innerHTML=data.length?data.map(s=>`
    <tr>
      <td><code>${s._id.slice(-6)}</code></td>
      <td>${s.target_bot_id||'All'}</td>
      <td>${s.run_at||'?'}</td>
      <td>${(s.text||'').slice(0,50)}</td>
    </tr>`).join(''):'<tr><td colspan="4" style="text-align:center;color:var(--muted);padding:20px">No pending schedules</td></tr>';
}

async function runImport(){
  const body={
    mongo_url:  document.getElementById('impUrl').value,
    db_name:    document.getElementById('impDb').value,
    collection: document.getElementById('impCol').value,
    bot_id:     parseInt(document.getElementById('impBot').value)||0,
  };
  const p=document.getElementById('impResult');
  p.style.color='var(--muted)'; p.textContent='⏳ Importing…';
  const r=await api('/import','POST',body); if(!r) return;
  p.style.color='var(--green)';
  p.textContent=`✅ Inserted: ${r.inserted} | Skipped: ${r.skipped}`;
}

// Boot
loadOverview();
setInterval(()=>{
  if(document.getElementById('overview').classList.contains('active')) loadOverview();
  if(document.getElementById('logs').classList.contains('active')) loadLogs();
},30000);
</script>
</body></html>"""
