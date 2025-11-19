import os
import asyncio
import csv
from telethon import TelegramClient
from telethon.sessions import StringSession
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
api_id = int(os.environ['TG_API_ID'])
api_hash = os.environ['TG_API_HASH']
session_string = os.environ['TG_SESSION_STRING']

# Cleaned List (Removed broken channels)
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
    print("--- 🕵️‍♂️ Recruitment Engine Starting ---")
    
    # Prepare the CSV file
    csv_filename = "jobs_data.csv"
    # Open file and write headers
    f = open(csv_filename, "w", newline="", encoding="utf-8")
    writer = csv.writer(f)
    writer.writerow(["Date", "Channel", "Raw_Text"]) # Columns
    
    async with TelegramClient(StringSession(session_string), api_id, api_hash) as client:
        print("✅ Login Successful. Scanning channels...")
        
        # Look back 24 hours
        time_limit = datetime.now(timezone.utc) - timedelta(hours=24)
        jobs_found = 0
        
        for channel in TARGET_CHANNELS:
            try:
                print(f"Scanning: {channel}...")
                async for message in client.iter_messages(channel, offset_date=time_limit, reverse=True):
                    
                    if message.text and ("http" in message.text or "Apply" in message.text):
                        # Clean text slightly for CSV (remove excessive newlines)
                        clean_text = message.text.replace("\n", "  ")[:500] 
                        
                        # Save to CSV
                        writer.writerow([datetime.now(), channel, clean_text])
                        
                        print(f"   🎯 SAVED: {clean_text[:40]}...")
                        jobs_found += 1
                        
            except Exception as e:
                print(f"   ⚠️ Error accessing {channel}: {e}")

    # Close the file
    f.close()
    print(f"--- ✅ Scan Complete. Found {jobs_found} jobs. Saved to {csv_filename} ---")

if __name__ == '__main__':
    asyncio.run(main())
