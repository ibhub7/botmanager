from pyrogram import Client, filters
from pyrogram.types import Message
from database import db
from config import Config


def admin_only(func):
    async def wrapper(client: Client, message: Message):
        if message.from_user.id != Config.OWNER_ID:
            chat = message.chat
            member = await client.get_chat_member(chat.id, message.from_user.id)
            if member.status.value not in ("administrator", "creator"):
                return await message.reply("❌ Admin only command.")
        return await func(client, message)
    wrapper.__name__ = func.__name__
    return wrapper


@Client.on_message(filters.command("add_fsub"))
@admin_only
async def add_fsub(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: `/add_fsub <channel_id>`")
    try:
        ch_id = int(message.command[1])
        added = await db.add_fsub_channel(ch_id)
        if added:
            chat = await client.get_chat(ch_id)
            await message.reply(f"✅ Added **{chat.title}** (`{ch_id}`) to FSub list.")
        else:
            await message.reply("⚠️ Channel already in FSub list.")
    except ValueError:
        await message.reply("❌ Invalid channel ID. Must be a number.")
    except Exception as e:
        await message.reply(f"❌ Error: `{e}`")


@Client.on_message(filters.command("rm_fsub"))
@admin_only
async def rm_fsub(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: `/rm_fsub <channel_id>`")
    try:
        ch_id = int(message.command[1])
        removed = await db.remove_fsub_channel(ch_id)
        if removed:
            await message.reply(f"✅ Removed `{ch_id}` from FSub list.")
        else:
            await message.reply("⚠️ Channel not found in FSub list.")
    except ValueError:
        await message.reply("❌ Invalid channel ID.")
    except Exception as e:
        await message.reply(f"❌ Error: `{e}`")


@Client.on_message(filters.command("show_dsub"))
async def show_fsub(client: Client, message: Message):
    channels = await db.get_fsub_channels()
    if not channels:
        return await message.reply("📭 No FSub channels configured.")

    lines = ["📋 **Force Subscribe Channels:**\n"]
    for ch_id in channels:
        try:
            chat = await client.get_chat(ch_id)
            link = f"https://t.me/{chat.username}" if chat.username else "Private"
            lines.append(f"• [{chat.title}]({link}) — `{ch_id}`")
        except Exception:
            lines.append(f"• `{ch_id}` (unknown)")

    await message.reply("\n".join(lines), disable_web_page_preview=True)
