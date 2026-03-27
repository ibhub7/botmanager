"""
main.py — Entry point
Starts everything in one asyncio event loop:
  1. DB indexes
  2. All child bot clients (BotManager)
  3. Start handlers on each child bot
  4. Master bot (admin commands)
  5. MongoDB-based scheduler loop
  6. FastAPI web dashboard
  7. Graceful SIGTERM/SIGINT shutdown
"""
import asyncio
import os
import signal

import uvicorn
from pyrogram import Client

from config import API_ID, API_HASH, MASTER_TOKEN, WEB_HOST, WEB_PORT, SESSIONS_DIR, LOG_CHANNEL
from database import users as users_db, bots as bots_db, broadcasts as bc_db
from database.db import ping_db
from bot_manager import manager
from handlers.admin import register_admin_handlers
from handlers.start import register_start_handler
from web.app import app as web_app


async def init_db():
    ok = await ping_db()
    if not ok:
        raise RuntimeError("❌ Cannot reach MongoDB — check MONGO_URI in .env")
    await users_db.ensure_indexes()
    await bots_db.ensure_indexes()
    await bc_db.ensure_indexes()
    print("[main] ✅ DB indexes ready")


async def start_master_bot() -> Client:
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    master = Client(
        name=os.path.join(SESSIONS_DIR, "master_bot"),
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=MASTER_TOKEN,
    )
    register_admin_handlers(master)
    await master.start()
    me = await master.get_me()
    print(f"[main] ✅ Master bot: @{me.username}")
    return master


async def attach_child_handlers():
    for bot_id, client in manager.get_all_clients().items():
        register_start_handler(client, bot_id)
    print(f"[main] ✅ Handlers on {len(manager.get_all_clients())} child bot(s)")


async def run_web():
    config = uvicorn.Config(web_app, host=WEB_HOST, port=WEB_PORT, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()


async def notify_log_channel(master: Client, text: str):
    if LOG_CHANNEL:
        try:
            await master.send_message(LOG_CHANNEL, text)
        except Exception:
            pass


async def main():
    print("━" * 52)
    print("  🤖  MultiBot System  v2  Starting...")
    print("━" * 52)

    await init_db()
    await manager.start_all()
    await attach_child_handlers()
    master = await start_master_bot()

    await notify_log_channel(master,
        f"🟢 **MultiBot started**\n"
        f"🤖 Bots online: `{manager.count_online()}`"
    )

    # MongoDB-based scheduler
    from utils.scheduler import scheduler_loop
    scheduler_task = asyncio.create_task(
        scheduler_loop(manager.get_online_clients, master),
        name="scheduler",
    )

    print(f"[main] 🌐 Dashboard → http://{WEB_HOST}:{WEB_PORT}")
    print(f"[main] 🔐 Login with your DASHBOARD_TOKEN")
    print("━" * 52)

    # Graceful shutdown on SIGTERM (Docker) or SIGINT (Ctrl-C)
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _handle_signal():
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    web_task = asyncio.create_task(run_web())

    await stop_event.wait()

    print("\n[main] Shutting down gracefully…")
    web_task.cancel()
    scheduler_task.cancel()

    await notify_log_channel(master,
        f"🔴 **MultiBot stopped**\n"
        f"🤖 Bots were online: `{manager.count_online()}`"
    )

    await master.stop()
    await manager.stop_all()
    print("[main] ✅ Clean shutdown")


if __name__ == "__main__":
    asyncio.run(main())
