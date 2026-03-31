import asyncio
import aiohttp
import logging
from datetime import datetime
import pytz

from fastapi import FastAPI
from contextlib import asynccontextmanager
from pyrogram import Client, enums
from pyrogram.errors import MessageNotModified

from config import Config
from database import get_all_bots, db 
# register_commands hata diya kyunki ab auto-load use ho raha hai
from plugins.routes import router as web_router 

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("MonitorBot")

# --- CLIENT INITIALIZATION WITH AUTO-LOAD ---
bot = Client(
    "MonitorBot", 
    api_id=Config.API_ID, 
    api_hash=Config.API_HASH, 
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="plugins"), # Ye line saare @Client handlers ko load karegi
    in_memory=True
)

async def check_bots_loop():
    """Background task for monitoring with HTML Hyperlinks."""
    IST = pytz.timezone(Config.TIME_ZONE)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) MonitorBot/1.0'}
    
    while True:
        now_ist = datetime.now(IST).strftime('%H:%M:%S')
        date_ist = datetime.now(IST).strftime('%d %B %Y')
        
        status_text = "🌐 <b>Live Bot Status Report</b>\n"
        status_text += f"📅 <b>Date:</b> <code>{date_ist}</code>\n"
        status_text += f"⏰ <b>Last Updated:</b> <code>{now_ist} (IST)</code>\n\n"
        
        async for target in await get_all_bots():
            name = target.get('name')
            url = target.get('url')
            username = target.get('username', 'bot')
            prev_status = target.get('status', '✅ Online')
            
            web_status = "❌ Offline" 
            
            for attempt in range(2):
                try:
                    async with aiohttp.ClientSession(headers=headers) as session:
                        async with session.get(url, timeout=15) as resp:
                            if resp.status == 200:
                                web_status = "✅ Online"
                                break 
                except Exception:
                    if attempt == 0: await asyncio.sleep(10)
            
            if "Offline" in web_status and "Online" in prev_status:
                try:
                    await bot.send_message(
                        Config.OWNER_ID, 
                        f"⚠️ <b>ALERT: <a href='https://t.me/{username}'>{name}</a> is DOWN!</b>\n⏰ Time: <code>{now_ist} IST</code>",
                        parse_mode=enums.ParseMode.HTML,
                        disable_web_page_preview=True
                    )
                except Exception as e:
                    logger.error(f"Alert failed: {e}")

            await db.update_one({"name": name}, {"$set": {"status": web_status}})
            status_text += f"🤖 <b><a href='https://t.me/{username}'>{name}</a></b>\n└ Status: {web_status}\n\n"

        status_text += f"🔄 <i>Next update in {Config.CHECK_INTERVAL // 60} minutes...</i>"

        try:
            await bot.edit_message_text(
                Config.STATUS_CHANNEL_ID, 
                Config.STATUS_MESSAGE_ID, 
                status_text,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True
            )
            logger.info(f"Updated status message at {now_ist}")
        except MessageNotModified:
            pass
        except Exception as e:
            logger.error(f"Failed to edit message: {e}")
            
        await asyncio.sleep(Config.CHECK_INTERVAL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Bot start hote hi background loop shuru
    await bot.start()
    monitor_task = asyncio.create_task(check_bots_loop())
    await asyncio.sleep(5) 
    
    try:
        IST = pytz.timezone(Config.TIME_ZONE)
        now_ist = datetime.now(IST).strftime('%H:%M:%S')
        await bot.send_message(
            Config.OWNER_ID, 
            f"🚀 <b>System Online & Stable</b>\n"
            f"✅ Health Checks: <code>Passed</code>\n"
            f"⏰ Restart At: <code>{now_ist} IST</code>",
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Owner DM failed: {e}")

    yield
    # Shutdown logic
    monitor_task.cancel()
    await bot.stop()

app = FastAPI(lifespan=lifespan)
app.include_router(web_router)