import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from database import db
from config import Config

logger = logging.getLogger(__name__)

# Registry of running child bots
child_bots: dict[int, Client] = {}


def owner_only(func):
    async def wrapper(client: Client, message: Message):
        if message.from_user.id != Config.OWNER_ID:
            return await message.reply("❌ Owner only command.")
        return await func(client, message)
    wrapper.__name__ = func.__name__
    return wrapper


async def start_child_bot(token: str, bot_id: int) -> Client | None:
    """Start a child bot client."""
    try:
        child = Client(
            f"child_{bot_id}",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=token,
            plugins=dict(root="plugins"),
            in_memory=True,
        )
        await child.start()
        child_bots[bot_id] = child
        logger.info(f"Child bot {bot_id} started.")
        return child
    except Exception as e:
        logger.error(f"Failed to start child bot {bot_id}: {e}")
        return None


async def stop_child_bot(bot_id: int):
    """Stop a running child bot."""
    if bot_id in child_bots:
        try:
            await child_bots[bot_id].stop()
            del child_bots[bot_id]
        except Exception as e:
            logger.error(f"Error stopping child bot {bot_id}: {e}")


async def start_all_child_bots():
    """Start all child bots from DB at boot."""
    bots = await db.get_all_bots()
    for bot in bots:
        if bot.get("active"):
            asyncio.create_task(
                start_child_bot(bot["token"], bot["_id"])
            )


@Client.on_message(filters.command("add_bot"))
@owner_only
async def add_bot_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: `/add_bot <BOT_TOKEN>`")
    token = message.command[1]
    try:
        temp = Client("temp_verify", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=token, in_memory=True)
        await temp.start()
        me = await temp.get_me()
        await temp.stop()
        added = await db.add_bot(me.id, token, me.username, message.from_user.id)
        if not added:
            return await message.reply("⚠️ Bot already registered.")
        asyncio.create_task(start_child_bot(token, me.id))
        await message.reply(
            f"✅ **Bot Added & Started**\n"
            f"• Name: {me.first_name}\n"
            f"• ID: `{me.id}`\n"
            f"• Username: @{me.username}"
        )
    except Exception as e:
        await message.reply(f"❌ Failed to verify bot: `{e}`")


@Client.on_message(filters.command("removebot"))
@owner_only
async def remove_bot_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: `/removebot <bot_id>`")
    try:
        bot_id = int(message.command[1])
        await stop_child_bot(bot_id)
        removed = await db.remove_bot(bot_id)
        if removed:
            await message.reply(f"✅ Bot `{bot_id}` removed and stopped.")
        else:
            await message.reply("❌ Bot not found in database.")
    except ValueError:
        await message.reply("❌ Invalid bot ID.")


@Client.on_message(filters.command("botlist"))
@owner_only
async def botlist_handler(client: Client, message: Message):
    bots = await db.get_all_bots()
    if not bots:
        return await message.reply("📭 No child bots registered.")
    lines = ["🤖 **Child Bot List:**\n"]
    for bot in bots:
        status = "🟢 Running" if bot["_id"] in child_bots else "🔴 Stopped"
        lines.append(f"• @{bot['username']} (`{bot['_id']}`) — {status}")
    await message.reply("\n".join(lines))


@Client.on_message(filters.command("restartbot"))
@owner_only
async def restart_bot_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: `/restartbot <bot_id>`")
    try:
        bot_id = int(message.command[1])
        bot_doc = await db.get_bot(bot_id)
        if not bot_doc:
            return await message.reply("❌ Bot not found.")
        await stop_child_bot(bot_id)
        await asyncio.sleep(1)
        started = await start_child_bot(bot_doc["token"], bot_id)
        if started:
            await message.reply(f"✅ Bot `{bot_id}` restarted successfully.")
        else:
            await message.reply(f"❌ Failed to restart bot `{bot_id}`.")
    except ValueError:
        await message.reply("❌ Invalid bot ID.")
