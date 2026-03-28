import logging
import asyncio
from pyrogram import Client
from pyrogram.errors import (
    UserNotParticipant, ChatAdminRequired, ChannelInvalid,
    FloodWait, UserBannedInChannel
)
from database import db

logger = logging.getLogger(__name__)


async def check_fsub(client: Client, user_id: int, bot_id: int = 0) -> list:
    """Returns list of channels the user hasn't joined."""
    channels = await db.get_fsub_channels(bot_id)
    not_joined = []
    for ch_id in channels:
        try:
            member = await client.get_chat_member(ch_id, user_id)
            if member.status.value in ("left", "banned", "restricted"):
                not_joined.append(ch_id)
        except UserNotParticipant:
            not_joined.append(ch_id)
        except Exception as e:
            logger.warning(f"FSub check error for {ch_id}: {e}")
    return not_joined


async def get_invite_links(client: Client, channel_ids: list) -> list:
    """Fetch invite links for channels."""
    links = []
    for ch_id in channel_ids:
        try:
            chat = await client.get_chat(ch_id)
            if chat.username:
                links.append({"name": chat.title, "link": f"https://t.me/{chat.username}"})
            else:
                link = await client.create_chat_invite_link(ch_id)
                links.append({"name": chat.title, "link": link.invite_link})
        except Exception as e:
            logger.error(f"Invite link error for {ch_id}: {e}")
    return links


def humanbytes(size: int) -> str:
    if not size:
        return "0 B"
    power = 2 ** 10
    n = 0
    units = {0: "B", 1: "KB", 2: "MB", 3: "GB", 4: "TB"}
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {units[n]}"


async def broadcast_message(client: Client, users: list, message, pin: bool = False):
    """Broadcast a message to a list of user IDs."""
    success, failed = 0, 0
    for user in users:
        uid = user["_id"]
        try:
            sent = await message.copy(uid)
            if pin:
                try:
                    await sent.pin()
                except Exception:
                    pass
            success += 1
            await asyncio.sleep(0.05)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            failed += 1
    return success, failed
