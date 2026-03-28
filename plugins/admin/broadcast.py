import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from config import Config
from utils import broadcast_message
from plugins.admin.bot_manager import child_bots

logger = logging.getLogger(__name__)

# Track active broadcasts: {user_id: task}
active_broadcasts: dict[int, asyncio.Task] = {}


def owner_only(func):
    async def wrapper(client: Client, message: Message):
        if message.from_user.id != Config.OWNER_ID:
            return await message.reply("❌ Owner only command.")
        return await func(client, message)
    wrapper.__name__ = func.__name__
    return wrapper


@Client.on_message(filters.command("broadcast"))
@owner_only
async def broadcast_menu(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📡 Master Bot Only", callback_data="bc_master")],
        [InlineKeyboardButton("🤖 All Bots (incl. Master)", callback_data="bc_all_incl")],
        [InlineKeyboardButton("🤖 All Bots (excl. Master)", callback_data="bc_all_excl")],
        [InlineKeyboardButton("📌 Pin Broadcast", callback_data="bc_pin")],
        [InlineKeyboardButton("❌ Cancel", callback_data="bc_cancel")],
    ])
    await message.reply("📡 **Broadcast Menu**\nSelect target:", reply_markup=keyboard)


@Client.on_callback_query(filters.regex(r"^bc_"))
async def broadcast_callback(client: Client, callback_query):
    if callback_query.from_user.id != Config.OWNER_ID:
        return await callback_query.answer("❌ Owner only.", show_alert=True)

    data = callback_query.data
    uid = callback_query.from_user.id

    if data == "bc_cancel":
        task = active_broadcasts.pop(uid, None)
        if task:
            task.cancel()
            await callback_query.message.edit_text("✅ Broadcast cancelled.")
        else:
            await callback_query.message.edit_text("⚠️ No active broadcast to cancel.")
        return

    pin = data == "bc_pin"
    await callback_query.message.edit_text("📩 **Reply with the message to broadcast:**")

    # Store pending action
    client._broadcast_pending = {uid: {"mode": data, "pin": pin}}


@Client.on_message(filters.private & ~filters.command([]))
async def handle_broadcast_message(client: Client, message: Message):
    uid = message.from_user.id
    pending = getattr(client, "_broadcast_pending", {})
    if uid not in pending:
        return

    action = pending.pop(uid)
    mode = action["mode"]
    pin = action["pin"]

    status_msg = await message.reply("⏳ Broadcasting...")

    async def do_broadcast():
        try:
            users = await db.get_all_users()
            success, failed = await broadcast_message(client, users, message, pin=pin)

            if mode in ("bc_all_incl", "bc_all_excl"):
                for bot_id, child_client in child_bots.items():
                    if mode == "bc_all_excl":
                        child_users = await db.db[f"bot_{bot_id}_users"].find({}).to_list(length=None)
                        s2, f2 = await broadcast_message(child_client, child_users, message, pin=pin)
                        success += s2
                        failed += f2

            await status_msg.edit_text(
                f"✅ **Broadcast Complete**\n"
                f"• Success: `{success}`\n"
                f"• Failed: `{failed}`"
            )
        except asyncio.CancelledError:
            await status_msg.edit_text("❌ Broadcast was cancelled.")
        except Exception as e:
            await status_msg.edit_text(f"❌ Error: `{e}`")

    task = asyncio.create_task(do_broadcast())
    active_broadcasts[uid] = task
