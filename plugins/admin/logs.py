from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
import os


def owner_only(func):
    async def wrapper(client: Client, message: Message):
        if message.from_user.id != Config.OWNER_ID:
            return await message.reply("❌ Owner only command.")
        return await func(client, message)
    wrapper.__name__ = func.__name__
    return wrapper


@Client.on_message(filters.command("logs"))
@owner_only
async def logs_handler(client: Client, message: Message):
    log_file = "app.log"
    if not os.path.exists(log_file):
        return await message.reply("📭 No log file found.")
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
        last_100 = "".join(lines[-100:])
        if len(last_100) > 4096:
            # Send as file
            await message.reply_document(log_file, caption="📋 Last 100 log lines")
        else:
            await message.reply(f"```\n{last_100}\n```")
    except Exception as e:
        await message.reply(f"❌ Error reading logs: `{e}`")
