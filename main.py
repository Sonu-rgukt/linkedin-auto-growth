import requests
import os
import json
import xml.etree.ElementTree as ET
import random
import time

# --- CONFIGURATION ---
LINKEDIN_TOKEN = os.environ["LINKEDIN_ACCESS_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# Trusted Sources (Tech News & Remote Jobs)
RSS_FEEDS = [
    "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    "https://feeds.feedburner.com/TheHackersNews",
    "https://techcrunch.com/feed/",
    "https://mashable.com/feeds/rss/tech"
]

def get_user_urn():
    """Automatically fetches your LinkedIn User ID (URN)."""
    url = "https://api.linkedin.com/v2/me"
    headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        user_data = response.json()
        return f"urn:li:person:{user_data['id']}"
    else:
        print(f"❌ Error fetching User ID: {response.text}")
        return None

def fetch_content():
    """Fetches a random news item or job from RSS feeds."""
    print("🔍 Scanning the web for trends...")
    selected_feed = random.choice(RSS_FEEDS)
    
    try:
        response = requests.get(selected_feed, timeout=10)
        root = ET.fromstring(response.content)
        
        # Get the first 3 items and pick one randomly to avoid repetition
        items = root.findall("./channel/item")[:3]
        if not items:
            return None
            
        item = random.choice(items)
        title = item.find("title").text
        link = item.find("link").text
        return f"{title} - {link}"
    except Exception as e:
        print(f"❌ Error fetching RSS: {e}")
        return None

def generate_viral_post(topic):
    """Uses Gemini to write a high-engagement LinkedIn post."""
    print(f"🧠 Generating insights on: {topic}")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    Act as a world-class Tech Thought Leader (like Naval Ravikant or Justin Welsh).
    I found this update: "{topic}"
    
    Write a LinkedIn post about this.
    Rules:
    1. HOOK: Start with a controversial or punchy one-liner.
    2. VALUE: Use bullet points to explain why this matters to a software engineer's career.
    3. TONE: Professional, insightful, but easy to read. No robotic words like "delve" or "unlock".
    4. LENGTH: Short (under 150 words).
    5. ENDING: Ask a specific question to drive comments.
    6. HASHTAGS: Use 3 relevant tags.
    """
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    else:
        print(f"❌ Gemini Error: {response.text}")
        return None

def post_to_linkedin(urn, content):
    """Publishes the generated content to LinkedIn."""
    url = "https://api.linkedin.com/v2/ugcPosts"
    
    headers = {
        "Authorization": f"Bearer {LINKEDIN_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "author": urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": content
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 201:
        print("✅ SUCCESS! Post published to LinkedIn.")
        print("Check your profile now!")
    else:
        print(f"❌ Posting Failed: {response.text}")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # 1. Get User ID
    urn = get_user_urn()
    
    if urn:
        # 2. Find Content
        raw_topic = fetch_content()
        
        if raw_topic:
            # 3. Write Post
            final_post = generate_viral_post(raw_topic)
            
            if final_post:
                # 4. Publish
                post_to_linkedin(urn, final_post)
            else:
                print("Skipping: Failed to generate text.")
        else:
            print("Skipping: No content found.")
    else:
        print("System Exit: Could not authenticate.")
