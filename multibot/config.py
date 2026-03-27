"""
config.py — Central configuration (loads .env automatically)
"""
import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

# ── Telegram API ──────────────────────────────────────────────────────────────
API_ID: int   = int(os.getenv("API_ID", "0"))
API_HASH: str = os.getenv("API_HASH", "")

# ── Master bot token ──────────────────────────────────────────────────────────
MASTER_TOKEN: str = os.getenv("MASTER_TOKEN", "")

# ── MongoDB ───────────────────────────────────────────────────────────────────
MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME: str   = os.getenv("DB_NAME", "multibot_system")

# ── Admins ────────────────────────────────────────────────────────────────────
ADMINS: List[int] = list(map(int, filter(None, os.getenv("ADMINS", "0").split())))

# ── Broadcast performance ─────────────────────────────────────────────────────
BATCH_SIZE:   int   = int(os.getenv("BATCH_SIZE",   "80"))
CONCURRENCY:  int   = int(os.getenv("CONCURRENCY",  "15"))
MIN_DELAY:    float = float(os.getenv("MIN_DELAY",   "0.05"))
MAX_DELAY:    float = float(os.getenv("MAX_DELAY",   "0.15"))
RETRY_DELAY:  float = float(os.getenv("RETRY_DELAY", "0.3"))

# ── Anti-ban ──────────────────────────────────────────────────────────────────
BOT_RATE_LIMIT: int = int(os.getenv("BOT_RATE_LIMIT", "25"))  # msgs/sec per bot

# ── Heartbeat ─────────────────────────────────────────────────────────────────
HEARTBEAT_INTERVAL: int = 60   # seconds between pings
HEARTBEAT_TIMEOUT:  int = 90   # seconds before marking bot offline

# ── Sessions directory ────────────────────────────────────────────────────────
SESSIONS_DIR: str = os.getenv("SESSIONS_DIR", "sessions")

# ── Web dashboard ─────────────────────────────────────────────────────────────
WEB_HOST:        str = os.getenv("WEB_HOST",        "0.0.0.0")
WEB_PORT:        int = int(os.getenv("WEB_PORT",    "8080"))
DASHBOARD_TOKEN: str = os.getenv("DASHBOARD_TOKEN", "changeme123")

# ── Log channel ───────────────────────────────────────────────────────────────
LOG_CHANNEL: int = int(os.getenv("LOG_CHANNEL", "0"))
