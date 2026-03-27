# 🤖 MultiBot System v2

A production-grade **multi-bot Telegram broadcast system** built with:
- **Pyrofork 2.3.69** (Pyrogram fork)
- **Python 3.12+**
- **MongoDB** (Motor async driver)
- **FastAPI** web dashboard

Manage multiple Telegram bots from a single master bot. Broadcast messages to thousands of users concurrently with anti-ban protection, crash-safe checkpointing, and a live web dashboard.

---

## 📁 Project Structure

```
multibot/
├── .env                    ← your config (copy from .env.example)
├── .python-version         ← 3.12
├── requirements.txt
├── config.py               ← central settings (reads .env)
├── main.py                 ← entry point
├── bot_manager.py          ← dynamic Pyrogram client pool
├── database/
│   ├── __init__.py
│   ├── db.py               ← Motor client singleton
│   ├── bots.py             ← bot registry CRUD
│   ├── users.py            ← user CRUD + stats + import
│   └── broadcasts.py       ← broadcast logs + queue + templates + schedules
├── handlers/
│   ├── __init__.py
│   ├── admin.py            ← all master-bot admin commands
│   └── start.py            ← /start + passive user tracking (child bots)
├── utils/
│   ├── __init__.py
│   ├── antiban.py          ← token bucket rate limiter + FloodWait handler
│   ├── broadcaster.py      ← concurrent multi-bot broadcast engine
│   ├── importer.py         ← import users from external MongoDB
│   └── scheduler.py        ← MongoDB-based scheduled broadcast loop
└── web/
    ├── __init__.py
    └── app.py              ← FastAPI dashboard + REST API
```

---

## ⚙️ Setup

### 1. Requirements

- Python 3.12+
- MongoDB (local or Atlas)
- Telegram API credentials from https://my.telegram.org

### 2. Install

```bash
git clone <your-repo>
cd multibot
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
nano .env   # fill in your values
```

Key values in `.env`:

| Variable | Description |
|---|---|
| `API_ID` | From https://my.telegram.org |
| `API_HASH` | From https://my.telegram.org |
| `MASTER_TOKEN` | Your master bot token from @BotFather |
| `MONGO_URI` | MongoDB connection string |
| `ADMINS` | Space-separated Telegram user IDs |
| `DASHBOARD_TOKEN` | Web dashboard password |
| `LOG_CHANNEL` | Telegram channel ID for notifications (0 = off) |

### 4. Run

```bash
python main.py
```

The web dashboard starts at `http://localhost:8080`.

---

## 🖥️ Web Dashboard

Open `http://your-server:8080` and log in with your `DASHBOARD_TOKEN`.

### Dashboard Pages

| Page | Features |
|---|---|
| **Overview** | Global stats, per-bot user counts, online status |
| **Bots** | Add / remove / restart bots, close/open users |
| **Broadcast** | Send plain-text broadcasts from the browser |
| **Logs** | Recent broadcast history, cancel running broadcasts |
| **Analytics** | Daily growth chart + hourly activity chart |
| **Users** | Search users by name or username |
| **Schedule** | View pending scheduled broadcasts |
| **Import** | Import users from external MongoDB collections |

### REST API

All endpoints require session cookie (login at `/login` first).

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check (DB + bot status) |
| GET | `/api/stats` | Global user stats |
| GET | `/api/bots` | List all bots with stats |
| POST | `/api/bots` | Add bot `{token}` |
| DELETE | `/api/bots/{id}` | Remove bot |
| POST | `/api/bots/{id}/restart` | Restart bot |
| POST | `/api/bots/{id}/close` | Pause users for bot |
| POST | `/api/bots/{id}/open` | Resume users for bot |
| GET | `/api/users/search?q=` | Search users |
| GET | `/api/broadcasts` | Recent broadcasts |
| POST | `/api/broadcasts/text` | Start text broadcast |
| POST | `/api/broadcasts/cancel/{id}` | Cancel broadcast |
| GET | `/api/analytics` | Growth + hourly data |
| GET | `/api/templates` | List templates |
| GET | `/api/schedules` | Pending schedules |
| POST | `/api/import` | Import from MongoDB |

---

## 📟 Telegram Commands

All commands are sent to the **master bot** and require you to be in `ADMINS`.

### Bot Management

| Command | Description |
|---|---|
| `/bots` | List all registered bots with stats |
| `/addbot <token>` | Add and start a new child bot |
| `/removebot <bot_id>` | Stop and remove a bot |
| `/restartbot <bot_id>` | Restart a bot client |

### User Control

| Command | Description |
|---|---|
| `/stats` | Global user statistics |
| `/stats <bot_id>` | Per-bot user statistics |
| `/close_bot_users <bot_id>` | Exclude bot's users from broadcasts |
| `/open_bot_users <bot_id>` | Re-include bot's users in broadcasts |
| `/unblock <user_id> <bot_id>` | Manually unblock a user |
| `/userinfo <user_id>` | User status across all bots |
| `/searchuser <query>` | Search by name or username |

### Broadcast

> ℹ️ All broadcast commands must be sent as a **reply** to the message you want to broadcast.

| Command | Description |
|---|---|
| `/broadcast <bot_id>` | Broadcast to one bot's users |
| `/pin_broadcast <bot_id>` | Broadcast + pin the message |
| `/allbroadcast` | Broadcast to all bots' users (deduplicated) |
| `/retry <broadcast_id>` | Retry failed users from a broadcast |
| `/resume` | List crash-saved broadcasts |
| `/resume <broadcast_id>` | Resume a specific saved broadcast |
| `/cancel <broadcast_id>` | Cancel a running broadcast |
| `/history` | Last 10 broadcasts |

### Scheduler

> ℹ️ `/schedule` must be sent as a **reply** to the message you want to schedule.

| Command | Description |
|---|---|
| `/schedule <bot_id\|all> <YYYY-MM-DD> <HH:MM>` | Schedule a broadcast (UTC) |
| `/schedules` | List all pending schedules |
| `/cancelschedule <schedule_id>` | Cancel a pending schedule |

### Templates

> ℹ️ `/savetemplate` must be sent as a **reply** to the message to save.

| Command | Description |
|---|---|
| `/savetemplate <name>` | Save a message as a template |
| `/templates` | List all saved templates |
| `/deltemplate <id>` | Delete a template |

### Import

> ⚠️ DM only — message is auto-deleted after reading to protect credentials.

| Command | Description |
|---|---|
| `/import_mongo <url> <db> <collection> <bot_id>` | Import users from external MongoDB |

### Help

| Command | Description |
|---|---|
| `/help` | Show command reference |

---

## 🏗️ Architecture

### How broadcasts work

1. Admin sends `/broadcast <bot_id>` replying to a message
2. System fetches eligible users (active + not blocked + not closed)
3. `run_broadcast()` divides users across all online bots
4. Each bot sends concurrently, limited by `CONCURRENCY` semaphore
5. `TokenBucket` enforces per-bot rate limits
6. FloodWait → semaphore released so other bots keep sending
7. Checkpoint saved every 500 users (crash-safe resume)
8. Failed users saved to DB for `/retry`
9. LOG_CHANNEL notified on completion

### Anti-ban system

- **Token bucket**: max `BOT_RATE_LIMIT` msgs/sec per bot
- **Jitter**: random delay between `MIN_DELAY` and `MAX_DELAY`
- **FloodWait handling**: semaphore released before sleeping so other bots fill the gap
- **Smart blocking**: users only permanently blocked after 3 consecutive failures (not on FloodWait)
- **Per-bot failover**: if a bot fails a batch, another bot retries it

### Session persistence

All bot sessions are stored as files in `SESSIONS_DIR/` (default: `sessions/`). Bots survive restarts without re-authentication.

---

## 🔧 Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `BATCH_SIZE` | 80 | Users per batch |
| `CONCURRENCY` | 15 | Max concurrent sends |
| `MIN_DELAY` | 0.05s | Min jitter between sends |
| `MAX_DELAY` | 0.15s | Max jitter between sends |
| `RETRY_DELAY` | 0.3s | Delay before retry on error |
| `BOT_RATE_LIMIT` | 25 | Max msgs/sec per bot |
| `HEARTBEAT_INTERVAL` | 60s | How often bots ping MongoDB |
| `HEARTBEAT_TIMEOUT` | 90s | Seconds before marking offline |
| `SESSIONS_DIR` | sessions/ | Where session files are stored |
| `WEB_PORT` | 8080 | Dashboard port |

---

## 🐛 Bugs Fixed (from original)

| # | Bug | Fix |
|---|---|---|
| 2 | Circular imports at module load | Lazy imports inside methods |
| 3 | Broadcast blocked web dashboard | `asyncio.create_task()` |
| 4 | In-memory sessions lost on restart | File-based sessions in SESSIONS_DIR |
| 5 | Crash lost all broadcast progress | MongoDB checkpoint every 500 users |
| 6 | `/import_mongo` leaked credentials in group | DM-only + auto-delete |
| 7 | Dashboard used insecure browser `prompt()` | Login page + session cookie |
| 8 | No way to retry failed users | `/retry` + failed users stored in DB |
| 9 | Semaphore held during FloodWait sleep | Released before sleep, re-acquired after |
| 10 | No scheduled broadcasts | MongoDB-based scheduler loop |
| 11 | No broadcast templates | Template CRUD in MongoDB |
| 13 | FloodWait wrongly blocked users | fail_count — block only after 3 fails |
| 15 | No completion notification | LOG_CHANNEL notification on finish |
| — | `type(Exception).__name__` always "type" | Fixed to `type(e).__name__` |
| — | Missing `database/__init__.py` | Added |
| — | Missing `handlers/__init__.py` | Added |
| — | Missing `web/__init__.py` | Added |
| — | No graceful shutdown | SIGTERM/SIGINT handler in main.py |

---

## 📦 Dependencies

```
pyrofork==2.3.69    ← Pyrogram fork (Python 3.12 compatible)
tgcrypto            ← Fast crypto for Pyrogram
motor>=3.3.0        ← Async MongoDB driver
pymongo>=4.6.0      ← MongoDB driver
fastapi>=0.111.0    ← Web framework
uvicorn[standard]   ← ASGI server
python-dotenv       ← .env loader
aiohttp             ← Async HTTP
pydantic>=2.0.0     ← Data validation
```
