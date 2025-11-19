import requests
import os
import json
import random
import sys
import xml.etree.ElementTree as ET
import time
from datetime import datetime

# --- CONFIGURATION ---
LINKEDIN_TOKEN = os.environ["LINKEDIN_ACCESS_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# --- 1. THE DATA STREAM (The World's Best Sources) ---
FEEDS = {
    "CRISIS": [ # Breaking Outages (High Virality)
        "https://www.githubstatus.com/history.atom",
        "https://www.cloudflarestatus.com/history.atom",
        "https://status.openai.com/history.atom"
    ],
    "FINANCE": [ # Money & Business (High Value)
        "https://cointelegraph.com/rss",
        "https://feeds.feedburner.com/TechCrunch/startups",
        "https://www.investing.com/rss/news.rss"
    ],
    "FUTURE": [ # AI & Deep Tech (Authority)
        "http://googleaiblog.blogspot.com/atom.xml",
        "https://www.mit.edu/newsoffice/topic/mit-artificial-intelligence-rss.xml",
        "https://openai.com/blog/rss.xml"
    ],
    "TREND": [ # What People Are Talking About
        "https://trends.google.com/trending/rss?geo=US", # Change US to IN for India specific
        "https://www.theverge.com/rss/index.xml",
        "https://wired.com/feed/category/science/latest/rss"
    ]
}

# --- 2. THE "HUMANIZER" ENGINE ---
def clean_text(raw_text):
    """Removes AI slop. We want pure human text."""
    bad_phrases = [
        "Here is a LinkedIn post", "Here is the post", "Sure!", "ChatGPT", 
        "**Title:**", "##", "Subject:", "Delve", "Realm", "Landscape"
    ]
    for phrase in bad_phrases:
        raw_text = raw_text.replace(phrase, "")
    return raw_text.strip().strip('"').strip("'")

def get_user_urn():
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return f"urn:li:person:{response.json()['sub']}"
    sys.exit(1)

def fetch_data(category):
    """Smart Fetcher that knows what to look for."""
    print(f"🔍 Scanning Category: {category}...")
    sources = FEEDS[category]
    random.shuffle(sources)
    
    for feed in sources:
        try:
            response = requests.get(feed, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                # Handle Atom (ns) vs RSS
                items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
                
                candidates = items[:5]
                if candidates:
                    item = random.choice(candidates)
                    
                    # Extract Title
                    title = item.find("title").text if item.find("title") is not None else item.find("{http://www.w3.org/2005/Atom}title").text
                    
                    # Extract Link
                    link_obj = item.find("link")
                    if link_obj is not None:
                        link = link_obj.text if link_obj.text else link_obj.attrib.get("href")
                    else:
                        link = item.find("{http://www.w3.org/2005/Atom}link").attrib.get("href")
                    
                    # CRISIS FILTER: Only post if it's actually an incident
                    if category == "CRISIS":
                        if "investigating" not in title.lower() and "outage" not in title.lower():
                            continue # Skip boring status updates
                            
                    return f"{title} - {link}"
        except Exception:
            continue
    return None

def generate_storyteller_post(category, topic):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    # DIFFERENT PERSONAS FOR DIFFERENT NEWS
    prompts = {
        "CRISIS": f"""
        You are a Breaking News Reporter.
        Topic: "{topic}"
        Action: The internet is breaking. Write a post alerting people.
        Style: Urgent, short, punchy. "Just in 🚨".
        Do not mention the URL in the text.
        """,
        
        "FINANCE": f"""
        You are a Market Analyst like specialized in Tech Money.
        Topic: "{topic}"
        Action: Explain how this impacts the economy/startups.
        Style: Analytical but simple. Use numbers if possible.
        Start with a bold claim.
        """,
        
        "FUTURE": f"""
        You are a Visionary Tech Leader.
        Topic: "{topic}"
        Action: Translate this complex research into a simple benefit for humanity.
        Style: Optimistic, inspiring. "Imagine a world where..."
        """,
        
        "TREND": f"""
        You are a Cultural Commentator (like Marques Brownlee).
        Topic: "{topic}"
        Action: Give your opinion on this trend. Is it hype or real?
        Style: Conversational, skeptical but open-minded.
        """
    }

    prompt = f"""
    {prompts[category]}
    
    STRICT RULES FOR HUMAN TOUCH:
    1. Output ONLY the post body. NO intro/outro.
    2. Do not use emojis in the first sentence.
    3. Use line breaks between thoughts.
    4. End with a specific question to the audience.
    5. Add 3 relevant hashtags at the very bottom.
    """

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        raw = response.json()['candidates'][0]['content']['parts'][0]['text']
        return clean_text(raw)
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
    requests.post(url, headers=headers, json=payload)

if __name__ == "__main__":
    # SMART SCHEDULER (Based on Time of Day)
    hour = datetime.utcnow().hour
    
    # 0-4 UTC (Morning IST) -> FUTURE / FINANCE (Serious reads)
    # 5-12 UTC (Afternoon IST) -> TREND (Viral stuff)
    # 13+ UTC (Evening IST) -> CRISIS / TECH (News wrap up)
    
    if 0 <= hour < 5:
        CATEGORY = "FINANCE" if random.random() > 0.5 else "FUTURE"
    elif 5 <= hour < 13:
        CATEGORY = "TREND"
    else:
        # 20% chance to check for CRISIS, otherwise TREND
        CATEGORY = "CRISIS" if random.random() > 0.8 else "TREND"

    # HUMAN DELAY (Enable for Production)
    # delay = random.randint(5, 40)
    # time.sleep(delay * 60)
    
    urn = get_user_urn()
    topic = fetch_data(CATEGORY)
    
    # Fallback: If no Crisis found, default to Future news
    if not topic and CATEGORY == "CRISIS":
        print("No Crisis found. Switching to FUTURE news.")
        CATEGORY = "FUTURE"
        topic = fetch_data(CATEGORY)

    if topic:
        print(f"📝 Storytelling on: {topic}")
        post = generate_storyteller_post(CATEGORY, topic)
        if post:
            post_to_linkedin(urn, post)
            print("✅ Live on LinkedIn.")
    else:
        print("❌ No interesting stories found today.")
