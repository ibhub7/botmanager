import motor.motor_asyncio
from config import Config
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(Config.MONGO_URL)
        self.db = self.client["infinity_master"]
        self.users = self.db["users"]
        self.bots = self.db["bots"]
        self.fsub = self.db["fsub"]
        self.broadcast = self.db["broadcast"]

    # ── USER METHODS ──────────────────────────────────────────────
    async def add_user(self, user_id: int, user_data: dict):
        existing = await self.users.find_one({"_id": user_id})
        if not existing:
            user_data["_id"] = user_id
            await self.users.insert_one(user_data)

    async def get_user(self, user_id: int):
        return await self.users.find_one({"_id": user_id})

    async def get_all_users(self):
        return await self.users.find({}).to_list(length=None)

    async def total_users(self):
        return await self.users.count_documents({})

    async def delete_user(self, user_id: int):
        await self.users.delete_one({"_id": user_id})

    # ── BOT MANAGEMENT ────────────────────────────────────────────
    async def add_bot(self, bot_id: int, token: str, username: str, owner_id: int):
        existing = await self.bots.find_one({"_id": bot_id})
        if existing:
            return False
        await self.bots.insert_one({
            "_id": bot_id,
            "token": token,
            "username": username,
            "owner_id": owner_id,
            "active": True,
        })
        return True

    async def remove_bot(self, bot_id: int):
        result = await self.bots.delete_one({"_id": bot_id})
        return result.deleted_count > 0

    async def get_all_bots(self):
        return await self.bots.find({}).to_list(length=None)

    async def get_bot(self, bot_id: int):
        return await self.bots.find_one({"_id": bot_id})

    async def set_bot_status(self, bot_id: int, active: bool):
        await self.bots.update_one({"_id": bot_id}, {"$set": {"active": active}})

    async def total_bots(self):
        return await self.bots.count_documents({})

    # ── FSUB METHODS ──────────────────────────────────────────────
    async def get_fsub_channels(self, bot_id: int = 0):
        doc = await self.fsub.find_one({"_id": bot_id})
        return doc.get("channels", []) if doc else []

    async def add_fsub_channel(self, channel_id: int, bot_id: int = 0):
        channels = await self.get_fsub_channels(bot_id)
        if channel_id not in channels:
            channels.append(channel_id)
            await self.fsub.update_one(
                {"_id": bot_id},
                {"$set": {"channels": channels}},
                upsert=True,
            )
            return True
        return False

    async def remove_fsub_channel(self, channel_id: int, bot_id: int = 0):
        channels = await self.get_fsub_channels(bot_id)
        if channel_id in channels:
            channels.remove(channel_id)
            await self.fsub.update_one(
                {"_id": bot_id},
                {"$set": {"channels": channels}},
                upsert=True,
            )
            return True
        return False

    # ── MONGO TOOLS ───────────────────────────────────────────────
    async def clone_external_users(self, ext_url: str, db_name: str, collection: str, bot_id: int):
        """Clone users from an external MongoDB into master db under bot_id namespace."""
        try:
            ext_client = motor.motor_asyncio.AsyncIOMotorClient(ext_url)
            ext_col = ext_client[db_name][collection]
            docs = await ext_col.find({}).to_list(length=None)
            target = self.db[f"bot_{bot_id}_users"]
            if docs:
                for doc in docs:
                    await target.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
            ext_client.close()
            return len(docs)
        except Exception as e:
            logger.error(f"Clone error: {e}")
            raise

    async def reset_collection(self, col_name: str):
        await self.db[col_name].drop()

    async def reset_all(self):
        collections = await self.db.list_collection_names()
        for col in collections:
            await self.db[col].drop()

    async def check_url(self, url: str) -> bool:
        try:
            client = motor.motor_asyncio.AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
            await client.admin.command("ping")
            client.close()
            return True
        except Exception:
            return False
