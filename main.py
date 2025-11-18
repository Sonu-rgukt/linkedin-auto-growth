import requests
import os
import json
import random
import sys
import xml.etree.ElementTree as ET
import time

# --- CONFIGURATION ---
LINKEDIN_TOKEN = os.environ["LINKEDIN_ACCESS_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# Trusted Sources (Tech, AI, Remote Work)
RSS_FEEDS = [
    "https://feeds.feedburner.com/TheHackersNews",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://openai.com/blog/rss/",
    "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss"
]

def get_user_urn():
    """Fetches User ID via OpenID endpoint."""
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        user_data = response.json()
        return f"urn:li:person:{user_data['sub']}"
    else:
        print(f"❌ FATAL: Auth Failed. {response.text}")
        sys.exit(1)

def fetch_fresh_news():
    """Scans RSS feeds for the latest tech news."""
    print("🔍 Scanning the web for fresh data...")
    # Shuffle feeds so we don't always pick the same source
    random.shuffle(RSS_FEEDS)
    
    for feed in RSS_FEEDS:
        try:
            response = requests.get(feed, timeout=5)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                # Get the first 2 items from this feed
                items = root.findall("./channel/item")[:2]
                if items:
                    item = random.choice(items)
                    title = item.find("title").text
                    link = item.find("link").text
                    print(f"✅ Found Topic: {title}")
                    return f"{title} - {link}"
        except Exception as e:
            print(f"⚠️ Error reading feed {feed}: {e}")
            continue
    
    print("❌ No fresh news found in any feed.")
    return None

def generate_viral_post(topic):
    """Uses Gemini 2.5 to write the post."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    Act as a top Tech Influencer (Context: 2025 AI Trends).
    I found this news: "{topic}"
    
    Write a high-impact LinkedIn post about it.
    
    Structure:
    1. HOOK: A punchy 1-sentence opinion or fact.
    2. INSIGHT: 2-3 bullet points explaining why this matters for developers/engineers.
    3. PREDICTION: A 1-sentence prediction about the future of this tech.
    4. ENGAGEMENT: A short question to the audience.
    
    Constraints:
    - Total length: Under 120 words.
    - Tone: Professional, optimistic, authoritative.
    - No emojis in the first line.
    - Include 3 hashtags.
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    print(f"🧠 Sending to Gemini 2.5...")
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    else:
        print(f"❌ AI Error: {response.text}")
        return None

def post_to_linkedin(urn, content):
    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {LINKEDIN_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    
    payload = {
        "author": urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        print("✅ SUCCESS! Post is live.")
    else:
        print(f"❌ Posting Failed: {response.text}")
        sys.exit(1)

if __name__ == "__main__":
    urn = get_user_urn()
    
    # 1. Find News
    news_item = fetch_fresh_news()
    
    if news_item:
        # 2. Write Post
        post_content = generate_viral_post(news_item)
        
        if post_content:
            # 3. Publish
            post_to_linkedin(urn, post_content)
        else:
            print("❌ Aborting: AI failed to generate text.")
            sys.exit(1)
    else:
        print("❌ Aborting: No news found.")
        sys.exit(1)
