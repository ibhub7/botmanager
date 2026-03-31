import motor.motor_asyncio
from config import Config

client = motor.motor_asyncio.AsyncIOMotorClient(Config.MONGO_URI)
db = client.status_db.mpbots

async def add_bot(name, url, username):
    await db.update_one(
        {"name": name}, 
        {"$set": {
            "name": name, 
            "url": url, 
            "username": username,
            "status": "✅ Online"
        }}, 
        upsert=True
    )

async def remove_bot(name):
    await db.delete_one({"name": name})

async def get_all_bots():
    return db.find({})