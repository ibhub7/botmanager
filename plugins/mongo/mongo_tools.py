from pyrogram import Client, filters
from pyrogram.types import Message
from database import db
from config import Config


def owner_only(func):
    async def wrapper(client: Client, message: Message):
        if message.from_user.id != Config.OWNER_ID:
            return await message.reply("❌ Owner only command.")
        return await func(client, message)
    wrapper.__name__ = func.__name__
    return wrapper


@Client.on_message(filters.command("check_mongo"))
@owner_only
async def check_mongo(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: `/check_mongo <mongodb_url>`")
    url = message.command[1]
    msg = await message.reply("⏳ Checking MongoDB connection...")
    alive = await db.check_url(url)
    if alive:
        await msg.edit_text("✅ **MongoDB URL is valid and reachable.**")
    else:
        await msg.edit_text("❌ **MongoDB URL is invalid or unreachable.**")


@Client.on_message(filters.command("import_mongo"))
@owner_only
async def import_mongo(client: Client, message: Message):
    """
    Usage: /import_mongo <url> <db_name> <collection> <bot_id>
    """
    args = message.command[1:]
    if len(args) < 4:
        return await message.reply(
            "Usage: `/import_mongo <url> <db_name> <collection> <bot_id>`"
        )
    url, db_name, collection, bot_id_str = args[0], args[1], args[2], args[3]
    try:
        bot_id = int(bot_id_str)
    except ValueError:
        return await message.reply("❌ bot_id must be a number.")

    msg = await message.reply("⏳ Importing collection...")
    try:
        count = await db.clone_external_users(url, db_name, collection, bot_id)
        await msg.edit_text(
            f"✅ **Import Complete**\n"
            f"• Documents imported: `{count}`\n"
            f"• Stored under: `bot_{bot_id}_users`"
        )
    except Exception as e:
        await msg.edit_text(f"❌ Import failed: `{e}`")


@Client.on_message(filters.command("reset_mongo"))
@owner_only
async def reset_mongo(client: Client, message: Message):
    """
    /reset_mongo — reset all
    /reset_mongo <collection> — reset specific collection
    """
    if len(message.command) > 1:
        col_name = message.command[1]
        try:
            await db.reset_collection(col_name)
            await message.reply(f"✅ Collection `{col_name}` has been reset.")
        except Exception as e:
            await message.reply(f"❌ Error: `{e}`")
    else:
        # Confirm before full reset
        await message.reply(
            "⚠️ **WARNING:** This will drop the ENTIRE database!\n"
            "Reply `/confirm_reset` within 30 seconds to proceed."
        )


@Client.on_message(filters.command("confirm_reset"))
@owner_only
async def confirm_reset(client: Client, message: Message):
    try:
        await db.reset_all()
        await message.reply("✅ **Entire database has been reset.**")
    except Exception as e:
        await message.reply(f"❌ Error: `{e}`")
