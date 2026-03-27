"""
database/db.py — Single Motor client shared across the whole app
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import MONGO_URI, DB_NAME

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            MONGO_URI,
            serverSelectionTimeoutMS=10_000,
            maxPoolSize=50,
        )
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[DB_NAME]


async def ping_db() -> bool:
    """Health-check: returns True if MongoDB is reachable."""
    try:
        await get_client().admin.command("ping")
        return True
    except Exception:
        return False
