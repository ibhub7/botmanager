import time
from pyrogram import Client, filters, enums
from motor.motor_asyncio import AsyncIOMotorClient

@Client.on_message(filters.command("check") & filters.private)
async def check_mongo(client, message):
    if len(message.command) < 2:
        return await message.reply("❌ <b>Usage:</b> <code>/check MONGO_URL</code>")
    
    url = message.command[1]
    start = time.perf_counter()
    try:
        temp_client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
        await temp_client.admin.command("ping")
        latency = (time.perf_counter() - start) * 1000
        await message.reply(f"✅ <b>Alive!</b> ⏱ <code>{latency:.2f}ms</code>")
    except Exception as e:
        await message.reply(f"❌ <b>Error:</b> <code>{e}</code>")

@Client.on_message(filters.command("show") & filters.private)
async def show_cols(client, message):
    if len(message.command) < 2:
        return await message.reply("❌ <b>Usage:</b> <code>/show MONGO_URL</code>")
    
    url = message.command[1]
    try:
        temp_db = AsyncIOMotorClient(url).get_default_database()
        cols = await temp_db.list_collection_names()
        res = "📂 <b>Collections:</b>\n" + "\n".join([f"🔹 <code>{c}</code>" for c in cols])
        await message.reply(res if cols else "📂 <b>Empty DB</b>")
    except Exception as e:
        await message.reply(f"❌ <b>Error:</b> <code>{e}</code>")

@Client.on_message(filters.command("clearmongo") & filters.private)
async def clear_mongo(client, message):
    if len(message.command) < 2:
        return await message.reply("❌ <b>Usage:</b> <code>/clearmongo MONGO_URL</code>")
    
    try:
        temp_db = AsyncIOMotorClient(message.command[1]).get_default_database()
        for col in await temp_db.list_collection_names():
            await temp_db[col].drop()
        await message.reply("🗑 <b>Database Cleared!</b>")
    except Exception as e:
        await message.reply(f"❌ <b>Error:</b> <code>{e}</code>")

@Client.on_message(filters.command("clone") & filters.private)
async def clone_db(client, message):
    if len(message.command) < 3:
        return await message.reply("❌ <b>Usage:</b> <code>/clone SOURCE TARGET</code>")
    
    try:
        s_db = AsyncIOMotorClient(message.command[1]).get_default_database()
        t_db = AsyncIOMotorClient(message.command[2]).get_default_database()
        for col in await s_db.list_collection_names():
            docs = await s_db[col].find().to_list(None)
            if docs: await t_db[col].insert_many(docs)
        await message.reply("✅ <b>Clone Successful!</b>")
    except Exception as e:
        await message.reply(f"❌ <b>Error:</b> <code>{e}</code>")