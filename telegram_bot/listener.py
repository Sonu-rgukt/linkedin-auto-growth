import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
# Load secrets from GitHub Environment
api_id = int(os.environ['TG_API_ID'])
api_hash = os.environ['TG_API_HASH']
session_string = os.environ['TG_SESSION_STRING']

# The Channels you want to spy on (Add real usernames here)
TARGET_CHANNELS = [
    'gate_jobs_channel', 
    'naukri_updates', 
    'remote_jobs',
    'developers_india',
    'freshers_opening',
    'offcampusjobs_4u',
    'jobsinternshipshub',
    'TorchBearerr',
    'hiringdaily',
    'gocareers',
    'offcampus_phodenge'
]

async def main():
    print("--- 🕵️‍♂️ Recruitment Engine Starting ---")
    
    async with TelegramClient(StringSession(session_string), api_id, api_hash) as client:
        print("✅ Login Successful. Scanning channels...")
        
        # We scan the last 2 hours of messages
        # This prevents processing old jobs every time the bot wakes up
        time_limit = datetime.now(timezone.utc) - timedelta(hours=2)
        
        jobs_found = 0
        
        for channel in TARGET_CHANNELS:
            try:
                print(f"Scanning: {channel}...")
                async for message in client.iter_messages(channel, offset_date=time_limit, reverse=True):
                    
                    # FILTER: We only want messages with links or "Apply" text
                    if message.text and ("http" in message.text or "Apply" in message.text):
                        
                        # Clean up the text (First 100 chars)
                        snippet = message.text[:100].replace('\n', ' ')
                        print(f"   🎯 JOB FOUND: {snippet}...")
                        jobs_found += 1
                        
                        # TODO: In the next phase, we will save this to Google Sheets
                        
            except Exception as e:
                print(f"   ⚠️ Error accessing {channel}: {e}")

        print(f"--- ✅ Scan Complete. Found {jobs_found} potential jobs. ---")

if __name__ == '__main__':
    asyncio.run(main())
