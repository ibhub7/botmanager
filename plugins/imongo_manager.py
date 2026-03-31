import time
from pyrogram import Client, filters, enums
from motor.motor_asyncio import AsyncIOMotorClient
from database import db 
from config import Config

# Helper filter for owner only
def owner_only(f):
    return filters.user(Config.OWNER_ID)

@Client.on_message(filters.command("icheck") & owner_only)
async def check_mongo_health(client, message):
    start = time.perf_counter()
    try:
        await db.command("ping")
        latency = (time.perf_counter() - start) * 1000
        await message.reply(
            f"✅ <b>MongoDB Connection Healthy!</b>\n⏱ <b>Ping:</b> <code>{latency:.2f}ms</code>",
            parse_mode=enums.ParseMode.HTML
        )
    except Exception as e:
        await message.reply(f"❌ <b>MongoDB Connection Failed!</b>\n<code>{e}</code>", parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("ishow") & owner_only)
async def show_collections(client, message):
    collections = await db.list_collection_names()
    if not collections:
        return await message.reply("📂 <b>No collections found in Database.</b>", parse_mode=enums.ParseMode.HTML)
    
    res = "📂 <b>Database Collections:</b>\n\n"
    for col in collections:
        count = await db[col].count_documents({})
        res += f"🔹 <code>{col}</code>: <b>{count}</b> documents\n"
    await message.reply(res, parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("iclearmongo") & owner_only)
async def clear_all_mongo(client, message):
    collections = await db.list_collection_names()
    for col in collections:
        await db[col].drop()
    await message.reply("🗑 <b>All collections deleted successfully!</b>", parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("idelmongocol") & owner_only)
async def delete_specific_col(client, message):
    if len(message.command) < 2:
        return await message.reply("❌ <b>Usage:</b> <code>/idelmongocol collection_name</code>", parse_mode=enums.ParseMode.HTML)
    col_name = message.command[1]
    await db[col_name].drop()
    await message.reply(f"🗑 Collection <code>{col_name}</code> dropped.", parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("iclone") & owner_only)
async def clone_db(client, message):
    if len(message.command) < 2:
        return await message.reply("❌ <b>Usage:</b> <code>/iclone NEW_MONGO_URL</code>", parse_mode=enums.ParseMode.HTML)
    
    new_url = message.command[1]
    msg = await message.reply("⏳ <b>Cloning started... please wait.</b>", parse_mode=enums.ParseMode.HTML)
    
    try:
        new_client = AsyncIOMotorClient(new_url)
        new_database = new_client.get_default_database()
        
        collections = await db.list_collection_names()
        for col_name in collections:
            docs = await db[col_name].find().to_list(length=None)
            if docs:
                await new_database[col_name].insert_many(docs)
        
        await msg.edit("✅ <b>Cloning Successful!</b> All data moved to new MongoDB.", parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        await msg.edit(f"❌ <b>Cloning Failed!</b>\n<code>{e}</code>", parse_mode=enums.ParseMode.HTML)