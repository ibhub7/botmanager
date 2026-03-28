import asyncio
import logging
import uvicorn
from pyrogram import Client
from config import Config
from database import db
from utils.logger import get_logger
from web.dashboard import app as web_app
from plugins.admin.bot_manager import start_all_child_bots

logger = get_logger(__name__)


def create_master_bot() -> Client:
    return Client(
        "master_bot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN,
        plugins=dict(root="plugins"),
    )


async def notify_owner(client: Client):
    try:
        await client.send_message(
            Config.OWNER_ID,
            "🚀 **Infinity Bot is Online!**\n"
            "Master bot has started successfully.\n"
            f"Dashboard: https://{Config.KOYEB_APP_NAME}.koyeb.app" if Config.KOYEB_APP_NAME else "🚀 **Infinity Bot is Online!**",
        )
    except Exception as e:
        logger.warning(f"Could not DM owner: {e}")


async def run_web():
    config = uvicorn.Config(web_app, host="0.0.0.0", port=Config.WEB_PORT, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()


async def run_bot(bot: Client):
    await bot.start()
    logger.info("✅ Master bot started.")
    await notify_owner(bot)
    await start_all_child_bots()
    logger.info("✅ All child bots initialized.")
    await asyncio.Event().wait()  # Run forever


async def main():
    logger.info("Starting Infinity Bot System...")
    master = create_master_bot()
    await asyncio.gather(
        run_bot(master),
        run_web(),
    )


if __name__ == "__main__":
    asyncio.run(main())
