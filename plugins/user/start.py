from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database import db
from utils import check_fsub, get_invite_links
import logging

logger = logging.getLogger(__name__)

START_TEXT = """
✨ **Hello {name}!**

Welcome to **∞ Infinity Bot** — your all-in-one Telegram management system.

[🌐 Open Dashboard]({web_link})

Use /help to see all available commands.
"""

HELP_TEXT = """
📖 **Commands Guide**

**👤 User Commands**
/start — Start the bot
/help — Show this message
/id — Get your user/chat ID
/info — Show your account info
/stats — Bot statistics

**🔐 Force Subscribe (Admin)**
/add\\_fsub `<channel_id>` — Add FSub channel
/rm\\_fsub `<channel_id>` — Remove FSub channel
/show\\_dsub — List FSub channels

**🤖 Multi-Bot Management (Owner)**
/add\\_bot `<token>` — Add a child bot
/removebot `<bot_id>` — Remove a child bot
/botlist — List all bots
/restartbot `<bot_id>` — Restart a child bot

**📡 Broadcast (Owner)**
/broadcast — Interactive broadcast menu

**🗄️ MongoDB Tools (Owner)**
/check\\_mongo `<url>` — Verify MongoDB URL
/import\\_mongo `<url> <db> <col> <bot_id>` — Import collection
/reset\\_mongo `[collection]` — Reset DB or collection

**🔧 Admin Only**
/logs — Fetch last 100 log lines
"""


@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user = message.from_user
    # Save user to DB
    await db.add_user(user.id, {
        "name": user.first_name,
        "username": user.username,
        "lang": user.language_code,
    })
    # Log to channel
    try:
        await client.send_message(
            Config.LOG_CHANNEL,
            f"✅ **New User**\n"
            f"• Name: {user.mention}\n"
            f"• ID: `{user.id}`\n"
            f"• Username: @{user.username or 'N/A'}",
        )
    except Exception:
        pass

    # Force subscribe check
    not_joined = await check_fsub(client, user.id)
    if not_joined:
        links = await get_invite_links(client, not_joined)
        buttons = [[InlineKeyboardButton(f"➕ Join {l['name']}", url=l["link"])] for l in links]
        buttons.append([InlineKeyboardButton("✅ I've Joined", callback_data="check_fsub")])
        await message.reply_photo(
            Config.START_PIC,
            caption="⚠️ **Please join the required channels to use this bot.**",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    web_link = f"https://{Config.KOYEB_APP_NAME}.koyeb.app" if Config.KOYEB_APP_NAME else "https://t.me"
    caption = START_TEXT.format(name=user.first_name, web_link=web_link)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📖 Help", callback_data="help"),
            InlineKeyboardButton("📊 Stats", callback_data="stats"),
        ],
        [InlineKeyboardButton("🌐 Dashboard", url=web_link)],
    ])

    await message.reply_photo(
        Config.START_PIC,
        caption=caption,
        reply_markup=keyboard,
    )


@Client.on_message(filters.command("help"))
async def help_handler(client: Client, message: Message):
    await message.reply_text(HELP_TEXT, disable_web_page_preview=True)


@Client.on_callback_query(filters.regex("^help$"))
async def help_callback(client, callback_query):
    await callback_query.message.edit_text(HELP_TEXT, disable_web_page_preview=True)


@Client.on_callback_query(filters.regex("^check_fsub$"))
async def recheck_fsub(client: Client, callback_query):
    user = callback_query.from_user
    not_joined = await check_fsub(client, user.id)
    if not_joined:
        await callback_query.answer("❌ You haven't joined all channels yet!", show_alert=True)
    else:
        await callback_query.message.delete()
        # Resend start
        web_link = f"https://{Config.KOYEB_APP_NAME}.koyeb.app" if Config.KOYEB_APP_NAME else "https://t.me"
        caption = START_TEXT.format(name=user.first_name, web_link=web_link)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📖 Help", callback_data="help"),
                InlineKeyboardButton("📊 Stats", callback_data="stats"),
            ],
        ])
        await client.send_photo(
            user.id,
            Config.START_PIC,
            caption=caption,
            reply_markup=keyboard,
        )
