import asyncio
import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from database import db
from config import Config
from plugins.admin.bot_manager import child_bots

app = FastAPI(title="Infinity Bot Dashboard")

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>∞ Infinity Bot Dashboard</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');
  :root {
    --bg: #0a0a0f;
    --surface: #12121a;
    --border: #1e1e2e;
    --accent: #7c3aed;
    --accent2: #06b6d4;
    --text: #e2e8f0;
    --muted: #64748b;
    --green: #22c55e;
    --red: #ef4444;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: 'Syne', sans-serif; min-height: 100vh; }
  header {
    padding: 2rem 3rem;
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 1rem;
    background: linear-gradient(135deg, #0a0a0f 60%, #12062a);
  }
  header h1 { font-size: 2rem; font-weight: 800; background: linear-gradient(90deg, var(--accent), var(--accent2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  header span { font-size: 2rem; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1.5rem; padding: 2rem 3rem; }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.5rem;
    transition: border-color 0.2s;
  }
  .card:hover { border-color: var(--accent); }
  .card .label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); margin-bottom: 0.5rem; }
  .card .value { font-size: 2.5rem; font-weight: 800; font-family: 'JetBrains Mono', monospace; }
  .card .value.purple { color: var(--accent); }
  .card .value.cyan { color: var(--accent2); }
  .card .value.green { color: var(--green); }
  section { padding: 0 3rem 2rem; }
  section h2 { font-size: 1.2rem; font-weight: 700; margin-bottom: 1rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
  table { width: 100%; border-collapse: collapse; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; }
  th { text-align: left; padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); color: var(--muted); font-size: 0.7rem; text-transform: uppercase; }
  td { padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); }
  .badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.7rem; font-weight: 700; }
  .badge.alive { background: rgba(34,197,94,0.15); color: var(--green); }
  .badge.dead { background: rgba(239,68,68,0.15); color: var(--red); }
  .refresh { display: inline-block; margin: 0 3rem 1rem; padding: 0.5rem 1.5rem; background: var(--accent); color: white; border: none; border-radius: 8px; cursor: pointer; font-family: 'Syne', sans-serif; font-weight: 700; font-size: 0.9rem; }
  .refresh:hover { opacity: 0.85; }
</style>
</head>
<body>
<header>
  <span>∞</span>
  <div>
    <h1>Infinity Bot Dashboard</h1>
    <p style="color:var(--muted);font-size:0.85rem;">Multi-bot management system</p>
  </div>
</header>

<div class="grid">
  <div class="card">
    <div class="label">Total Users</div>
    <div class="value purple" id="total-users">—</div>
  </div>
  <div class="card">
    <div class="label">Child Bots</div>
    <div class="value cyan" id="total-bots">—</div>
  </div>
  <div class="card">
    <div class="label">Active Now</div>
    <div class="value green" id="active-bots">—</div>
  </div>
</div>

<button class="refresh" onclick="loadData()">↻ Refresh</button>

<section>
  <h2>Bot Status</h2>
  <table>
    <thead>
      <tr><th>Username</th><th>Bot ID</th><th>Status</th></tr>
    </thead>
    <tbody id="bot-table">
      <tr><td colspan="3" style="color:var(--muted)">Loading...</td></tr>
    </tbody>
  </table>
</section>

<script>
async function loadData() {
  const res = await fetch('/api/status');
  const data = await res.json();
  document.getElementById('total-users').textContent = data.total_users;
  document.getElementById('total-bots').textContent = data.total_bots;
  document.getElementById('active-bots').textContent = data.active_bots;
  const tbody = document.getElementById('bot-table');
  if (!data.bots.length) {
    tbody.innerHTML = '<tr><td colspan="3" style="color:var(--muted)">No bots registered.</td></tr>';
    return;
  }
  tbody.innerHTML = data.bots.map(b => `
    <tr>
      <td>@${b.username}</td>
      <td>${b.id}</td>
      <td><span class="badge ${b.alive ? 'alive' : 'dead'}">${b.alive ? '🟢 Alive' : '🔴 Dead'}</span></td>
    </tr>
  `).join('');
}
loadData();
setInterval(loadData, 30000);
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML


@app.get("/api/status")
async def status():
    bots = await db.get_all_bots()
    total_users = await db.total_users()
    bot_statuses = []
    for bot in bots:
        bot_id = bot["_id"]
        alive = bot_id in child_bots
        bot_statuses.append({
            "id": bot_id,
            "username": bot.get("username", "unknown"),
            "alive": alive,
        })
    return {
        "total_users": total_users,
        "total_bots": len(bots),
        "active_bots": len(child_bots),
        "bots": bot_statuses,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
