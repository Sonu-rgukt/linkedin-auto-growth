import os
import asyncio
import csv
import json
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
api_id = int(os.environ['TG_API_ID'])
api_hash = os.environ['TG_API_HASH']
session_string = os.environ['TG_SESSION_STRING']
gemini_key = os.environ['GEMINI_API_KEY'] # Ensure this Secret exists in GitHub

# The Channels
TARGET_CHANNELS = [
    'freshers_opening',
    'offcampusjobs_4u',
    'jobsinternshipshub',
    'TorchBearerr',
    'hiringdaily',
    'gocareers',
    'offcampus_phodenge'
]

def clean_data_with_ai(raw_text):
    """
    Sends raw job text to Gemini and asks for structured JSON.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
    
    # Strict Prompt for consistent JSON
    prompt = f"""
    Extract these details from the job post:
    - Company
    - Role
    - Batch (e.g., 2024, 2025, or N/A)
    - Apply_Link (The http url)

    Input Text: "{raw_text[:800]}"
    
    Return ONLY valid JSON. Format: {{"Company": "...", "Role": "...", "Batch": "...", "Apply_Link": "..."}}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            # Clean the response (sometimes AI adds ```json ... ```)
            text = response.json()['candidates'][0]['content']['parts'][0]['text']
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
    except Exception as e:
        print(f"   ⚠️ AI Cleaning Failed: {e}")
    
    return None

async def main():
    print("--- 🕵️‍♂️ Recruitment Engine (AI Powered) Starting ---")
    
    # New CSV Structure
    csv_filename = "clean_jobs.csv"
    f = open(csv_filename, "w", newline="", encoding="utf-8")
    writer = csv.writer(f)
    writer.writerow(["Date", "Company", "Role", "Batch", "Link", "Source"]) # Clean Headers
    
    async with TelegramClient(StringSession(session_string), api_id, api_hash) as client:
        print("✅ Login Successful. Scanning channels...")
        
        time_limit = datetime.now(timezone.utc) - timedelta(hours=24)
        jobs_found = 0
        
        for channel in TARGET_CHANNELS:
            try:
                print(f"Scanning: {channel}...")
                async for message in client.iter_messages(channel, offset_date=time_limit, reverse=True):
                    
                    # Basic Filter
                    if message.text and ("http" in message.text or "Apply" in message.text):
                        
                        print(f"   🧠 Found Job. Cleaning with AI...")
                        
                        # 1. Send to AI
                        clean_data = clean_data_with_ai(message.text)
                        
                        if clean_data:
                            # 2. Save Clean Data
                            writer.writerow([
                                datetime.now().strftime("%Y-%m-%d"),
                                clean_data.get("Company", "Unknown"),
                                clean_data.get("Role", "Unknown"),
                                clean_data.get("Batch", "N/A"),
                                clean_data.get("Apply_Link", "N/A"),
                                channel
                            ])
                            print(f"      ✨ Saved: {clean_data.get('Company')} - {clean_data.get('Role')}")
                            jobs_found += 1
                        else:
                            print("      ⚠️ AI couldn't parse this one. Skipping.")
                        
            except Exception as e:
                print(f"   ⚠️ Error accessing {channel}: {e}")

    f.close()
    print(f"--- ✅ Scan Complete. Saved {jobs_found} CLEAN jobs to {csv_filename} ---")

if __name__ == '__main__':
    asyncio.run(main())
