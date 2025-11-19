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
gemini_key = os.environ['GEMINI_API_KEY']  # Make sure to add this to GitHub Secrets!

TARGET_CHANNELS = [
    'freshers_opening', 'offcampusjobs_4u', 'jobsinternshipshub',
    'TorchBearerr', 'hiringdaily', 'gocareers', 'offcampus_phodenge'
]

def clean_with_gemini(raw_text):
    """Uses Gemini Flash to extract structured data from messy text"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
    
    prompt = f"""
    Extract the following details from this job post into a JSON format:
    - Company
    - Role
    - Experience (or Batch)
    - Salary (if mentioned, else "Not Disclosed")
    - Apply_Link (The main URL to apply)

    Input Text: "{raw_text[:500]}"
    
    Return ONLY the JSON. No markdown.
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            # Clean up the response to get pure JSON
            text_res = response.json()['candidates'][0]['content']['parts'][0]['text']
            text_res = text_res.replace("```json", "").replace("```", "").strip()
            return json.loads(text_res)
    except Exception as e:
        print(f"   ⚠️ AI Error: {e}")
    
    return None

async def main():
    print("--- 🕵️‍♂️ Recruitment Engine Starting ---")
    
    # New CSV with CLEAN columns
    csv_filename = "clean_jobs.csv"
    f = open(csv_filename, "w", newline="", encoding="utf-8")
    writer = csv.writer(f)
    writer.writerow(["Date", "Company", "Role", "Batch", "Salary", "Link", "Source"])
    
    async with TelegramClient(StringSession(session_string), api_id, api_hash) as client:
        print("✅ Login Successful. Scanning channels...")
        
        time_limit = datetime.now(timezone.utc) - timedelta(hours=24)
        jobs_found = 0
        
        for channel in TARGET_CHANNELS:
            try:
                print(f"Scanning: {channel}...")
                async for message in client.iter_messages(channel, offset_date=time_limit, reverse=True):
                    if message.text and ("http" in message.text or "Apply" in message.text):
                        
                        print(f"   🧠 Cleaning job from {channel}...")
                        
                        # 1. Ask Gemini to Clean it
                        data = clean_with_gemini(message.text)
                        
                        if data:
                            # 2. Save Clean Data
                            writer.writerow([
                                datetime.now().strftime("%Y-%m-%d"),
                                data.get("Company", "N/A"),
                                data.get("Role", "N/A"),
                                data.get("Experience", "N/A"),
                                data.get("Salary", "N/A"),
                                data.get("Apply_Link", "N/A"),
                                channel
                            ])
                            print(f"      ✨ Saved: {data.get('Company')} - {data.get('Role')}")
                            jobs_found += 1
                        
            except Exception as e:
                print(f"   ⚠️ Error in {channel}: {e}")

    f.close()
    print(f"--- ✅ Found & Cleaned {jobs_found} jobs. Saved to {csv_filename} ---")

if __name__ == '__main__':
    asyncio.run(main())
