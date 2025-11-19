import requests
import os
import json
import random
import sys
import xml.etree.ElementTree as ET
import time
from datetime import datetime

# --- CONFIGURATION ---
LINKEDIN_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")
# Tries both key names to be safe
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

if not LINKEDIN_TOKEN or not GEMINI_API_KEY:
    print("❌ CRITICAL: Missing API Keys. Check GitHub Secrets.")
    sys.exit(1)

# --- 1. THE DATA STREAM ---
FEEDS = {
    "CRISIS": [ 
        "https://www.githubstatus.com/history.atom",
        "https://www.cloudflarestatus.com/history.atom",
        "https://status.openai.com/history.atom"
    ],
    "FINANCE": [ 
        "https://cointelegraph.com/rss",
        "https://feeds.feedburner.com/TechCrunch/startups",
        "https://www.investing.com/rss/news.rss"
    ],
    "FUTURE": [ 
        "http://googleaiblog.blogspot.com/atom.xml",
        "https://www.mit.edu/newsoffice/topic/mit-artificial-intelligence-rss.xml",
        "https://openai.com/blog/rss.xml"
    ],
    "TREND": [ 
        "https://trends.google.com/trending/rss?geo=US", 
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
    
    print(f"❌ LinkedIn Auth Failed: {response.text}")
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
                    title_node = item.find("title")
                    if title_node is None:
                        title_node = item.find("{http://www.w3.org/2005/Atom}title")
                    title = title_node.text if title_node is not None else "News Update"
                    
                    # Extract Link
                    link = "No Link"
                    link_obj = item.find("link")
                    if link_obj is not None:
                        link = link_obj.text if link_obj.text else link_obj.attrib.get("href")
                    else:
                        atom_link = item.find("{http://www.w3.org/2005/Atom}link")
                        if atom_link is not None:
                            link = atom_link.attrib.get("href")
                    
                    # CRISIS FILTER
                    if category == "CRISIS":
                        if "investigating" not in title.lower() and "outage" not in title.lower():
                            continue 
                            
                    return f"{title} - {link}"
        except Exception as e:
            # print(f"Feed Error: {e}") 
            continue
    return None

def generate_storyteller_post(category, topic):
    # ✅ FIXED MODEL NAME: Using the stable 1.5 Flash model
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
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
        You are a Cultural Commentator.
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
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        
        if response.status_code == 200:
            raw = response.json()['candidates'][0]['content']['parts'][0]['text']
            return clean_text(raw)
        else:
            # ✅ FIX: Print error if API fails
            print(f"❌ Gemini API Error {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
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
    
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code == 201:
        print("✅ Live on LinkedIn.")
    else:
        print(f"❌ Post Failed: {res.text}")

if __name__ == "__main__":
    hour = datetime.utcnow().hour
    
    # Simple logic to pick category based on time
    if 0 <= hour < 5:
        CATEGORY = "FINANCE" if random.random() > 0.5 else "FUTURE"
    elif 5 <= hour < 13:
        CATEGORY = "TREND"
    else:
        CATEGORY = "CRISIS" if random.random() > 0.8 else "TREND"

    # Uncomment to force a specific category for testing:
    # CATEGORY = "TREND"

    print(f"🚀 Starting News Engine. Category: {CATEGORY}")

    urn = get_user_urn()
    topic = fetch_data(CATEGORY)
    
    # Fallback logic
    if not topic and CATEGORY == "CRISIS":
        print("No Crisis found. Switching to FUTURE news.")
        CATEGORY = "FUTURE"
        topic = fetch_data(CATEGORY)

    if topic:
        print(f"📝 Storytelling on: {topic}")
        post = generate_storyteller_post(CATEGORY, topic)
        if post:
            post_to_linkedin(urn, post)
        else:
            print("❌ Failed to generate post content (Check Gemini API Error above).")
    else:
        print("❌ No interesting stories found today.")
