import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
api_id = int(os.environ['TG_API_ID'])
api_hash = os.environ['TG_API_HASH']
session_string = os.environ['TG_SESSION_STRING']

# ✅ CLEAN LIST (Only the ones that worked)
TARGET_CHANNELS = [
    'developersIndia',
    'freshers_opening',
    'offcampusjobs_4u',
    'jobsinternshipshub',
    'TorchBearerr',
    'hiringdaily',
    'gocareers',
    'offcampus_phodenge',
    'developersIndia'
]

async def main():
    print("--- 🕵️‍♂️ Recruitment Engine Starting ---")
    
    async with TelegramClient(StringSession(session_string), api_id, api_hash) as client:
        print("✅ Login Successful. Scanning channels...")
        
        # 🔄 CHANGE: Looking back 24 HOURS to find data
        time_limit = datetime.now(timezone.utc) - timedelta(hours=24)
        
        jobs_found = 0
        
        for channel in TARGET_CHANNELS:
            try:
                print(f"Scanning: {channel}...")
                async for message in client.iter_messages(channel, offset_date=time_limit, reverse=True):
                    
                    # FILTER: strict check for links
                    if message.text and ("http" in message.text):
                        
                        snippet = message.text[:60].replace('\n', ' ')
                        print(f"   🎯 JOB FOUND: {snippet}...")
                        jobs_found += 1
                        
            except Exception as e:
                print(f"   ⚠️ Error accessing {channel}: {e}")

        print(f"--- ✅ Scan Complete. Found {jobs_found} potential jobs in last 24h. ---")

if __name__ == '__main__':
    asyncio.run(main())
