import os
import pytz
from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from database import get_all_bots
from config import Config

router = APIRouter()

# Path handling logic
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_path = os.path.join(base_dir, "web")
templates = Jinja2Templates(directory=template_path)

@router.get("/")
async def dashboard(request: Request):
    IST = pytz.timezone(Config.TIME_ZONE)
    now = datetime.now(IST)
    current_time = now.strftime('%H:%M:%S')
    current_date = now.strftime('%d %B %Y')
    
    bot_list = []
    try:
        # Cursor fetch karna
        cursor = await get_all_bots()
        
        # Cursor ko list mein convert karna (Zyada reliable method)
        raw_bots = await cursor.to_list(length=100) 
        
        for bot_data in raw_bots:
            bot_list.append({
                "name": bot_data.get("name", "Unknown Bot"),
                "username": bot_data.get("username", "bot"),
                "status": bot_data.get("status", "❌ Offline")
            })
    except Exception as e:
        print(f"Dashboard Error: {e}")

    # Log check karne ke liye (Koyeb logs mein dikhega)
    print(f"Bots found for dashboard: {len(bot_list)}")

    return templates.TemplateResponse(
        request=request, 
        name="startup.html", 
        context={
            "request": request, # Safety ke liye context mein bhi request daal do
            "bots": bot_list, 
            "time": current_time,
            "date": current_date
        }
    )

@router.get("/health")
async def health():
    return {"status": "connected", "message": "Monitor is stable"}