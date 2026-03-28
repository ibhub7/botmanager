from pyrogram import Client, filters
from pyrogram.types import Message
from database import db
from config import Config
import platform, sys


def owner_only(func):
    async def wrapper(client, message):
        if message.from_user.id != Config.OWNER_ID:
            return await message.reply("❌ Owner only command.")
        return await func(client, message)
    wrapper.__name__ = func.__name__
    return wrapper


@Client.on_message(filters.command("id"))
async def id_handler(client: Client, message: Message):
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        text = f"👤 **User ID:** `{user.id}`\n📛 Name: {user.mention}"
    else:
        user = message.from_user
        chat = message.chat
        text = (
            f"👤 **Your ID:** `{user.id}`\n"
            f"💬 **Chat ID:** `{chat.id}`\n"
            f"📛 Name: {user.mention}"
        )
    await message.reply(text)


@Client.on_message(filters.command("info"))
async def info_handler(client: Client, message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    text = (
        f"👤 **User Info**\n"
        f"• **Name:** {target.first_name} {target.last_name or ''}\n"
        f"• **ID:** `{target.id}`\n"
        f"• **Username:** @{target.username or 'N/A'}\n"
        f"• **Language:** {target.language_code or 'N/A'}\n"
        f"• **Bot:** {'Yes' if target.is_bot else 'No'}\n"
        f"• **DC:** {target.dc_id or 'N/A'}"
    )
    await message.reply(text)


@Client.on_message(filters.command("stats"))
async def stats_handler(client: Client, message: Message):
    total_users = await db.total_users()
    total_bots = await db.total_bots()
    bot_info = await client.get_me()
    text = (
        f"📊 **Bot Statistics**\n\n"
        f"🤖 Bot: @{bot_info.username}\n"
        f"👥 Total Users: `{total_users}`\n"
        f"🤖 Child Bots: `{total_bots}`\n"
        f"🐍 Python: `{sys.version.split()[0]}`\n"
        f"💻 Platform: `{platform.system()} {platform.release()}`"
    )
    await message.reply(text)


@Client.on_callback_query(filters.regex("^stats$"))
async def stats_callback(client, cb):
    total_users = await db.total_users()
    total_bots = await db.total_bots()
    await cb.message.edit_text(
        f"📊 **Statistics**\n\n"
        f"👥 Users: `{total_users}`\n"
        f"🤖 Child Bots: `{total_bots}`"
    )
