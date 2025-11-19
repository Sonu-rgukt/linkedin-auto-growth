import os
import asyncio
import csv
from telethon import TelegramClient
from telethon.sessions import StringSession
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
# Load secrets from GitHub Environment
api_id = int(os.environ['TG_API_ID'])
api_hash = os.environ['TG_API_HASH']
session_string = os.environ['TG_SESSION_STRING']

# Real Channels to Scan
TARGET_CHANNELS = [
    'freshers_opening',
    'offcampusjobs_4u',
    'jobsinternshipshub',
    'TorchBearerr',
    'hiringdaily',
    'gocareers',
    'offcampus_phodenge'
]

async def main():
    print("--- 🕵️‍♂️ Recruitment Engine (Listener) Starting ---")
    
    # 1. Prepare the CSV file
    # This matches exactly what poster.py looks for
    csv_filename = "jobs_data.csv"
    
    f = open(csv_filename, "w", newline="", encoding="utf-8")
    writer = csv.writer(f)
    writer.writerow(["Date", "Channel", "Raw_Text"]) # 'Raw_Text' is critical for poster.py
    
    async with TelegramClient(StringSession(session_string), api_id, api_hash) as client:
        print("✅ Login Successful. Scanning channels...")
        
        # Look back 24 hours to ensure we get fresh data
        time_limit = datetime.now(timezone.utc) - timedelta(hours=24)
        jobs_found = 0
        
        for channel in TARGET_CHANNELS:
            try:
                print(f"Scanning: {channel}...")
                async for message in client.iter_messages(channel, offset_date=time_limit, reverse=True):
                    
                    # Filter: Only keep messages with Links or "Apply" text
                    if message.text and ("http" in message.text or "Apply" in message.text):
                        
                        # Clean newlines to keep CSV tidy
                        clean_text = message.text.replace("\n", "  ")
                        
                        # Save to CSV
                        writer.writerow([
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                            channel, 
                            clean_text
                        ])
                        
                        print(f"   🎯 FOUND: {clean_text[:40]}...")
                        jobs_found += 1
                        
            except Exception as e:
                print(f"   ⚠️ Error accessing {channel}: {e}")

    f.close()
    print(f"--- ✅ Scan Complete. Found {jobs_found} jobs. Saved to {csv_filename} ---")

if __name__ == '__main__':
    asyncio.run(main())
