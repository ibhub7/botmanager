# ∞ Infinity Multi-Bot Controller

A high-performance, scalable Telegram bot system built with **Pyrofork 2.3.69**, **MongoDB**, and **FastAPI** — deployable on **Koyeb**.

---

## 🚀 Features

| Feature | Details |
|---|---|
| Force Subscribe | Multi-channel (public + private), join-request mode |
| Multi-Bot Management | Add/remove/restart child bots dynamically |
| Broadcast System | Master, selected, all bots — with pin & cancel |
| MongoDB Tools | Clone, import, reset, check URL |
| Web Dashboard | Live bot status, user counts, health check |
| Koyeb Ready | Dockerfile + koyeb.yaml included |

---

## 📁 Project Structure

```
infinity_bot/
├── main.py                  # Entry point
├── config.py                # Environment config
├── requirements.txt
├── Dockerfile
├── koyeb.yaml
├── .env.example
├── database/
│   ├── __init__.py
│   └── mongodb.py           # All DB operations
├── utils/
│   ├── __init__.py
│   ├── helpers.py           # FSub check, broadcast, etc.
│   └── logger.py            # Logging setup
├── plugins/
│   ├── user/
│   │   ├── start.py         # /start, /help
│   │   └── utils.py         # /id, /info, /stats
│   ├── fsub/
│   │   └── fsub.py          # /add_fsub, /rm_fsub, /show_dsub
│   ├── admin/
│   │   ├── bot_manager.py   # /add_bot, /removebot, /botlist, /restartbot
│   │   ├── broadcast.py     # /broadcast system
│   │   └── logs.py          # /logs
│   └── mongo/
│       └── mongo_tools.py   # /check_mongo, /import_mongo, /reset_mongo
└── web/
    └── dashboard.py         # FastAPI dashboard
```

---

## ⚙️ Setup

### 1. Clone & Configure

```bash
git clone https://github.com/yourrepo/infinity-bot
cd infinity-bot
cp .env.example .env
# Fill in your values in .env
```

### 2. Run Locally

```bash
pip install -r requirements.txt
python main.py
```

### 3. Deploy to Koyeb

1. Push your repo to GitHub
2. Go to [koyeb.com](https://koyeb.com) → New App → GitHub
3. Select your repo, set **Build method: Dockerfile**
4. Add all environment variables from `.env.example`
5. Set port to `8080`
6. Deploy!

---

## 🤖 Bot Commands

### User Commands
| Command | Description |
|---|---|
| `/start` | Start the bot (with FSub check) |
| `/help` | Show all commands |
| `/id` | Get your user/chat ID |
| `/info` | Show account info |
| `/stats` | Bot statistics |

### Admin Commands
| Command | Description |
|---|---|
| `/add_fsub <id>` | Add force subscribe channel |
| `/rm_fsub <id>` | Remove force subscribe channel |
| `/show_dsub` | List all FSub channels |
| `/logs` | Fetch last 100 log lines |

### Owner Commands
| Command | Description |
|---|---|
| `/add_bot <token>` | Add & start a child bot |
| `/removebot <id>` | Stop & remove a child bot |
| `/botlist` | List all child bots with status |
| `/restartbot <id>` | Restart a specific child bot |
| `/broadcast` | Open broadcast menu |
| `/check_mongo <url>` | Test a MongoDB connection URL |
| `/import_mongo <url> <db> <col> <bot_id>` | Import a MongoDB collection |
| `/reset_mongo [collection]` | Reset DB or specific collection |

---

## 🌐 Web Dashboard

Once deployed, visit:
```
https://your-app.koyeb.app/
```

API endpoints:
- `GET /` — Dashboard UI
- `GET /api/status` — JSON bot status
- `GET /health` — Health check for Koyeb

---

## 🛡️ Environment Variables

| Variable | Required | Description |
|---|---|---|
| `API_ID` | ✅ | Telegram API ID (my.telegram.org) |
| `API_HASH` | ✅ | Telegram API Hash |
| `BOT_TOKEN` | ✅ | Master bot token |
| `MONGO_URL` | ✅ | MongoDB connection string |
| `OWNER_ID` | ✅ | Your Telegram user ID |
| `LOG_CHANNEL` | ✅ | Channel ID for logs |
| `START_PIC` | ✅ | Photo URL for /start |
| `BOT_USERNAME` | ⚡ | Bot username (no @) |
| `KOYEB_APP_NAME` | ⚡ | Your Koyeb app name |
| `PORT` | ⚡ | Web server port (default: 8080) |

---

## 📝 Notes

- Child bots share the same `API_ID`/`API_HASH` as the master
- Each child bot's users are stored in `bot_{id}_users` collection
- Logs are written to `app.log` and streamed to console
- The system auto-restarts all child bots on master boot
