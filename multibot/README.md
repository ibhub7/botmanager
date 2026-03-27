# 🤖 MultiBot System v2

A production-ready **multi-bot Telegram broadcast system** built with:

- **[Pyrofork](https://github.com/kavehkn/pyrofork) 2.3.69** — Pyrogram fork with active maintenance
- **Motor + MongoDB** — async database, no Redis needed
- **FastAPI** — web dashboard with session auth
- **Python 3.12+**

---

## 📁 Project Structure

```
multibot/
├── .env                        ← your config (copy from .env.example)
├── .env.example                ← template with all variables
├── .python-version             ← 3.12
├── requirements.txt
├── config.py                   ← loads all env vars
├── main.py                     ← entry point, starts everything
├── bot_manager.py              ← dynamic Pyrogram client pool
│
├── database/
│   ├── __init__.py
│   ├── db.py                   ← shared Motor client
│   ├── bots.py                 ← bot registry CRUD
│   ├── users.py                ← user management + analytics
│   └── broadcasts.py           ← broadcast logs, templates, schedules
│
├── handlers/
│   ├── __init__.py
│   ├── admin.py                ← all master bot commands
│   └── start.py                ← /start handler for child bots
│
├── utils/
│   ├── __init__.py
│   ├── antiban.py              ← token bucket + FloodWait handler
│   ├── broadcaster.py          ← concurrent multi-bot broadcast engine
│   ├── importer.py             ← external MongoDB importer
│   └── scheduler.py            ← MongoDB-based scheduled broadcast loop
│
├── web/
│   ├── __init__.py
│   └── app.py                  ← FastAPI dashboard + REST API
│
└── sessions/                   ← auto-created, stores Pyrogram session files
```

---

## ⚡ Quick Start

### 1. Install dependencies

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
nano .env   # fill in API_ID, API_HASH, MASTER_TOKEN, MONGO_URI, ADMINS
```

### 3. Start MongoDB

```bash
# Local
mongod --dbpath /data/db

# Or Docker
docker run -d -p 27017:27017 --name mongo mongo:7
```

### 4. Run

```bash
python main.py
```

The web dashboard will be at `http://localhost:8080`.

---

## 🔧 Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `API_ID` | ✅ | — | From https://my.telegram.org |
| `API_HASH` | ✅ | — | From https://my.telegram.org |
| `MASTER_TOKEN` | ✅ | — | Master bot token from @BotFather |
| `MONGO_URI` | ✅ | `mongodb://localhost:27017` | MongoDB connection string |
| `DB_NAME` | | `multibot_system` | Database name |
| `ADMINS` | ✅ | — | Space-separated Telegram user IDs |
| `BATCH_SIZE` | | `80` | Users per broadcast batch |
| `CONCURRENCY` | | `15` | Max concurrent sends |
| `MIN_DELAY` | | `0.05` | Min jitter between sends (seconds) |
| `MAX_DELAY` | | `0.15` | Max jitter between sends (seconds) |
| `RETRY_DELAY` | | `0.3` | Delay before retry on temp error |
| `BOT_RATE_LIMIT` | | `25` | Max msgs/sec per bot (token bucket) |
| `SESSIONS_DIR` | | `sessions` | Folder for Pyrogram session files |
| `WEB_HOST` | | `0.0.0.0` | Dashboard bind host |
| `WEB_PORT` | | `8080` | Dashboard port |
| `DASHBOARD_TOKEN` | ✅ | `changeme123` | Login token for web dashboard |
| `LOG_CHANNEL` | | `0` | Telegram channel ID for system logs (0 = off) |

---

## 📋 All Bot Commands

### Bot Management

| Command | Description |
|---|---|
| `/bots` | List all registered bots with status and user counts |
| `/addbot <token>` | Add and start a new child bot |
| `/removebot <bot_id>` | Stop and remove a bot |
| `/restartbot <bot_id>` | Restart a specific bot |

### User Management

| Command | Description |
|---|---|
| `/stats` | Global stats across all bots |
| `/stats <bot_id>` | Per-bot stats (total, active, eligible, blocked, imported) |
| `/close_bot_users <bot_id>` | Mark all users of a bot as "closed" (excluded from broadcasts) |
| `/open_bot_users <bot_id>` | Re-open all closed users of a bot |
| `/userinfo <user_id>` | Look up a user's status across all bots |
| `/searchuser <query>` | Search users by username or first name |
| `/unblock <user_id> <bot_id>` | Manually unblock a wrongly-flagged user |

### Broadcast

| Command | How to use | Description |
|---|---|---|
| `/broadcast <bot_id>` | Reply to a message | Broadcast to all eligible users of one bot |
| `/broadcast all` | Reply to a message | Broadcast to all bots' users (deduplicated) |
| `/pin_broadcast <bot_id>` | Reply to a message | Broadcast + pin the message |
| `/allbroadcast` | Reply to a message | Alias for broadcast to all bots |
| `/cancel <broadcast_id>` | — | Cancel a running broadcast |
| `/retry <broadcast_id>` | — | Re-send to all failed users from a broadcast |
| `/resume` | — | List and resume crash-saved (mid-flight) broadcasts |
| `/history` | — | Show last 10 broadcasts with stats |

### Scheduler

| Command | Description |
|---|---|
| `/schedule <bot_id\|all> <YYYY-MM-DD> <HH:MM>` | Schedule a broadcast (reply to message). Time is UTC. |
| `/schedules` | List all pending scheduled broadcasts |
| `/cancelschedule <schedule_id>` | Cancel a pending scheduled broadcast |

### Templates

| Command | Description |
|---|---|
| `/savetemplate <name>` | Save the replied-to message as a named template |
| `/templates` | List all saved templates |
| `/deltemplate <template_id>` | Delete a saved template |

### Import

| Command | Description |
|---|---|
| `/import_mongo <url> <db> <collection> <bot_id>` | Import users from an external MongoDB (DM only — message is auto-deleted for security) |

### System

| Command | Description |
|---|---|
| `/help` | Show this command list |

---

## 🌐 Web Dashboard

Access at `http://your-server:8080`. Login with your `DASHBOARD_TOKEN`.

### Pages

| Page | Features |
|---|---|
| **Overview** | Global stats cards, per-bot table, auto-refreshes every 30s |
| **Bots** | Add/remove bots, close/open users, see online status |
| **Broadcast** | Send text broadcast directly from browser, view progress |
| **Logs** | Full broadcast history with success/fail counts, cancel button |
| **Analytics** | User growth chart (last 14 days), filterable by bot |
| **Schedules** | View pending scheduled broadcasts |
| **Import** | Import users from external MongoDB |

### REST API

All endpoints require session cookie (login first via `/login`).

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | MongoDB + bot status health check |
| `GET` | `/api/stats` | Global user stats |
| `GET` | `/api/bots` | All bots with stats |
| `POST` | `/api/bots` | Add bot `{ "token": "..." }` |
| `DELETE` | `/api/bots/{bot_id}` | Remove bot |
| `POST` | `/api/bots/{bot_id}/close` | Close all users of bot |
| `POST` | `/api/bots/{bot_id}/open` | Open all users of bot |
| `POST` | `/api/bots/{bot_id}/restart` | Restart bot client |
| `GET` | `/api/broadcasts` | Recent broadcasts |
| `POST` | `/api/broadcasts/cancel/{bc_id}` | Cancel broadcast |
| `GET` | `/api/analytics` | User growth data (`?bot_id=` optional) |
| `POST` | `/api/import` | Import from external MongoDB |
| `GET` | `/api/templates` | List templates |
| `GET` | `/api/schedules` | Pending schedules |
| `GET` | `/api/users/search?q=...` | Search users by name/username |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                   main.py                        │
│  asyncio event loop (single process)             │
│                                                  │
│  ┌──────────────┐   ┌──────────────┐            │
│  │  Master Bot   │   │  Child Bots  │            │
│  │  (admin cmds) │   │  (start/track│            │
│  │               │   │   users)     │            │
│  └──────┬────────┘   └──────┬───────┘            │
│         │                   │                    │
│  ┌──────▼───────────────────▼───────────────┐   │
│  │           BotManager                      │   │
│  │  - Dynamic client pool                    │   │
│  │  - Heartbeat monitor + auto-reconnect     │   │
│  │  - File-based sessions (survive restart)  │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────┐   ┌──────────────┐            │
│  │  Broadcaster  │   │  Scheduler   │            │
│  │  (concurrent  │   │  (MongoDB    │            │
│  │   engine)     │   │   cron loop) │            │
│  └──────────────┘   └──────────────┘            │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │        FastAPI Web Dashboard              │   │
│  │        (uvicorn, port 8080)               │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │       MongoDB        │
              │  - bots              │
              │  - users             │
              │  - broadcasts        │
              │  - broadcast_failures│
              │  - broadcast_templates│
              │  - scheduled_broadcasts│
              └─────────────────────┘
```

---

## 🛡️ Anti-ban Features

- **Token bucket** per bot — enforces `BOT_RATE_LIMIT` msgs/sec
- **Random jitter** between sends (`MIN_DELAY`–`MAX_DELAY`)
- **FloodWait handler** — releases semaphore before sleeping so other users don't block
- **Smart block** — users only permanently blocked after **3 consecutive failures** (not on FloodWait)
- **Per-bot failover** — if one bot fails a batch, another takes over automatically

---

## 🔄 Broadcast Engine

1. Fetches eligible users (active, not blocked, not closed)
2. Splits them into batches across all online bots
3. Each bot sends concurrently up to `CONCURRENCY` sends at a time
4. Progress checkpointed to MongoDB every 500 users
5. Failed users saved — retryable via `/retry`
6. Broadcasts can be **cancelled** mid-flight
7. Crash-saved broadcasts can be **resumed**
8. Completion notification sent to `LOG_CHANNEL`

---

## 🐛 Bugs Fixed vs Original Code

| # | File | Bug | Fix |
|---|---|---|---|
| 1 | `config.py` | `.env` file never loaded | Added `load_dotenv()` |
| 2 | `bot_manager.py` | Circular imports at module level | Lazy imports inside methods |
| 3 | `admin.py` | Broadcast blocked web dashboard | `asyncio.create_task()` |
| 4 | `bot_manager.py` | `in_memory` sessions lost on restart | File-based sessions in `SESSIONS_DIR` |
| 5 | `broadcaster.py` | Crash lost all progress | MongoDB checkpoint every 500 users |
| 6 | `admin.py` | MongoDB credentials leaked in group chats | `/import_mongo` DM-only + auto-delete |
| 7 | `web/app.py` | Insecure `prompt()` login | Proper form + session cookie |
| 8 | `admin.py` | No retry mechanism | `/retry <broadcast_id>` command |
| 9 | `antiban.py` | Semaphore held during FloodWait sleep | Release before sleep, re-acquire after |
| 10 | `scheduler.py` | No scheduler existed | MongoDB-based 60s poll loop |
| 11 | `admin.py` | No template system | `/savetemplate`, `/templates`, `/deltemplate` |
| 12 | `users.py` | No growth analytics | `daily_growth()` aggregation pipeline |
| 13 | `users.py` | FloodWait wrongly blocked users | `fail_count` — block only after 3 failures |
| 14 | `database/` | Missing `__init__.py` files | Added all `__init__.py` |
| 15 | `broadcaster.py` | `type(Exception).__name__` always returned `"type"` | Fixed to `type(e).__name__` |

---

## 🚀 Deployment (Docker)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

```bash
docker build -t multibot .
docker run -d \
  --env-file .env \
  -p 8080:8080 \
  -v $(pwd)/sessions:/app/sessions \
  --name multibot \
  multibot
```

---

## 📝 Notes

- The **master bot** handles all admin commands. Child bots only handle `/start` and user tracking.
- Add child bots with `/addbot <token>` — no restart needed.
- `DASHBOARD_TOKEN` should be a long random string in production.
- `LOG_CHANNEL` should be a channel/group where your master bot is an admin.
- Sessions are stored as files in `sessions/` — back this folder up to avoid re-authentication.
