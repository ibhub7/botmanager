import re
from pyrogram import Client, filters, enums
from database import add_bot, remove_bot
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from config import Config

# --- START COMMAND ---
@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    # Apna dashboard URL yahan change karein
    dashboard_url = "https://infinity-monitor-bot-ug.koyeb.app" 

    text = (
        f"👋 <b>Hello {message.from_user.mention}!</b>\n\n"
        "Welcome to <b>Bot Monitor Pro</b>. I can track your bots' uptime "
        "and alert you if they go offline.\n\n"
        "📢 <b>Status Channel:</b> <a href='https://t.me/infinity_botzz'>Join Here</a>\n"
        "📊 <b>Live Dashboard:</b> Click the button below!"
    )

    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🌐 Open Web Dashboard", 
                web_app=WebAppInfo(url=dashboard_url)
            )
        ],
        [
            InlineKeyboardButton("📢 Channel", url="https://t.me/infinity_botzz"),
            InlineKeyboardButton("👨‍💻 Owner", user_id=Config.OWNER_ID)
        ]
    ])

    await message.reply(
        text, 
        reply_markup=reply_markup,
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )

# --- ADD BOT COMMAND ---
@Client.on_message(filters.command("addbot") & filters.private)
async def on_add(client, message):
    # Format: /addbot @username https://url.com
    args = message.text.split()
    if len(args) < 3:
        return await message.reply(
            "❌ <b>Usage:</b> <code>/addbot @BotUsername https://your-link.com</code>",
            parse_mode=enums.ParseMode.HTML
        )

    username = args[1].replace("@", "")
    url = args[2]

    try:
        # Telegram se Bot details fetch karna
        target_bot = await client.get_users(username)
        full_name = target_bot.first_name
        
        # Database mein save karna
        await add_bot(full_name, url, username) 
        
        await message.reply(
            f"✅ <b>Monitoring started!</b>\n"
            f"🤖 <b>Bot:</b> <a href='https://t.me/{username}'>{full_name}</a>\n"
            f"🔗 <b>URL:</b> <code>{url}</code>",
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True
        )
    
    except Exception as e:
        await message.reply(
            f"❌ <b>Error:</b> Username invalid hai ya bot nahi mila.\n<code>{e}</code>",
            parse_mode=enums.ParseMode.HTML
        )

# --- REMOVE BOT COMMAND ---
@Client.on_message(filters.command("removebot") & filters.private)
async def on_remove(client, message):
    # Regex for finding name inside quotes
    match = re.search(r'"([^"]+)"', message.text)
    if match:
        name = match.group(1).strip()
        await remove_bot(name)
        await message.reply(
            f"🗑 Removed <b>{name}</b> from monitoring.",
            parse_mode=enums.ParseMode.HTML
        )
    else:
        await message.reply(
            "❌ <b>Usage:</b> <code>/removebot \"Bot Name\"</code>",
            parse_mode=enums.ParseMode.HTML
        )

@Client.on_message(filters.command("list") & filters.private)
async def list_bots(client, message):
    """Database mein jitne bots hain unki list dikhane ke liye"""
    
    msg = await message.reply("⏳ <b>Fetching your bot list...</b>", parse_mode=enums.ParseMode.HTML)
    
    bot_cursor = await get_all_bots()
    bot_list = await bot_cursor.to_list(length=None) # Saare bots fetch kiye
    
    if not bot_list:
        return await msg.edit("❌ <b>No bots found in monitoring list.</b>\nUse <code>/addbot</code> to add one.")

    response = "📋 <b>Monitored Bots List</b>\n\n"
    
    for i, bot_data in enumerate(bot_list, 1):
        name = bot_data.get("name", "Unknown")
        username = bot_data.get("username", "bot")
        status = bot_data.get("status", "❌ Offline")
        url = bot_data.get("url", "#")
        
        # HTML Link Format
        response += (
            f"{i}. <b><a href='https://t.me/{username}'>{name}</a></b>\n"
            f"   └ <b>Status:</b> {status}\n"
            f"   └ <b>Endpoint:</b> <code>{url}</code>\n\n"
        )

    response += f"📊 <b>Total Bots:</b> <code>{len(bot_list)}</code>"
    
    await msg.edit(
        response, 
        parse_mode=enums.ParseMode.HTML, 
        disable_web_page_preview=True
    )

from pyrogram import Client, filters, enums

@Client.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message):
    """Bot ki saari commands aur unka use samjhane ke liye"""
    
    help_text = (
        "✨ <b>Bot Monitor Pro - Help Menu</b> ✨\n\n"
        
        "🤖 <b>Monitoring Commands:</b>\n"
        "• /addbot <code>@user https://url.com</code> - Naya bot add karein.\n"
        "• /removebot <code>\"Bot Name\"</code> - Bot ko monitoring se hatayein.\n"
        "• /list - Saare monitored bots ki live report dekhein.\n\n"
        
        "📂 <b>MongoDB Manager (Private Only):</b>\n"
        "• /check <code>MONGO_URL</code> - Connection aur Ping test karein.\n"
        "• /show <code>MONGO_URL</code> - Collections aur data count dekhein.\n"
        "• /clearmongo <code>MONGO_URL</code> - Poora DB saaf (Drop) karein.\n"
        "• /delmongocol <code>URL COL_NAME</code> - Specific table delete karein.\n"
        "• /clone <code>SOURCE_URL TARGET_URL</code> - Ek DB se doosre mein data copy karein.\n\n"
        
        "🌐 <b>Web Dashboard:</b>\n"
        "Aap /start dabakar <b>'Open Web Dashboard'</b> par click karke live status grid mein dekh sakte hain. Dashboard har 30s mein auto-refresh hota hai.\n\n"
        
        "⚠️ <b>Note:</b> Bot monitoring ke liye URL hamesha <code>https://</code> se start hona chahiye."
    )

    await message.reply(
        help_text,
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )