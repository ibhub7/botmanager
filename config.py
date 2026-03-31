import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    MONGO_URI = os.getenv("MONGO_URI", "")
    OWNER_ID = int(os.getenv("OWNER_ID", 0))
    STATUS_CHANNEL_ID = int(os.getenv("STATUS_CHANNEL_ID", 0))
    STATUS_MESSAGE_ID = int(os.getenv("STATUS_MESSAGE_ID", 0))
    
    TIME_ZONE = "Asia/Kolkata"
    CHECK_INTERVAL = 300  # 5 minutes