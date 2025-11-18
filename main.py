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

# --- DATA SOURCES ---
# 1. Morning Sources (News & Trends)
NEWS_FEEDS = [
    "https://feeds.feedburner.com/TheHackersNews",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://openai.com/blog/rss/",
    "https://googleaiblog.blogspot.com/atom.xml"
]

# 2. Evening Sources (Jobs & Career Advice)
JOB_FEEDS = [
    "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss",
    "https://remotive.com/remote-jobs/software-dev/feed", 
    "https://stackoverflow.com/jobs/feed" 
]

def human_delay():
    """Waits between 2 to 45 minutes to simulate human behavior."""
    delay_minutes = random.randint(2, 45)
    print(f"⏳ Sleeping for {delay_minutes} minutes to act human...")
    time.sleep(delay_minutes * 60)
    print("⏰ Waking up to post!")

def get_user_urn():
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return f"urn:li:person:{response.json()['sub']}"
    sys.exit(1)

def fetch_data(mode):
    """Fetches content based on time of day."""
    sources = NEWS_FEEDS if mode == "MORNING" else JOB_FEEDS
    random.shuffle(sources)
    
    print(f"🔍 Searching {mode} sources...")
    for feed in sources:
        try:
            response = requests.get(feed, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                # Check first 3 items, pick one randomly
                items = root.findall("./channel/item")[:3]
                if items:
                    item = random.choice(items)
                    title = item.find("title").text
                    link = item.find("link").text
                    return f"{title} - {link}"
        except:
            continue
    return None

def generate_post(mode, topic):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    if mode == "MORNING":
        # Educational / Insight Style
        prompt = f"""
        Act as a Senior Tech Mentor for students and developers.
        Topic: "{topic}"
        
        Write a LinkedIn post.
        - HOOK: Start with a "Did you know?" or a strong opinion.
        - BODY: Explain specifically why this technology matters for a student's future.
        - TAKEAWAY: Give 1 actionable advice (e.g., "Start learning X").
        - TONE: Encouraging, insightful, clear.
        - HASHTAGS: #TechNews #Learning #FutureOfWork
        """
    else:
        # Career / Job Opportunity Style
        prompt = f"""
        Act as a Career Coach for developers.
        Opportunity: "{topic}"
        
        Write a LinkedIn post.
        - HOOK: "Remote Opportunity Alert 🚨" or similar.
        - VALUE: Mention why this role/skill is in demand.
        - ADVICE: Tell them what 2 skills they need to apply for jobs like this.
        - CTA: "Check the link in the comments if interested!" (Don't put link in body).
        - TONE: Urgent, helpful.
        - HASHTAGS: #RemoteJobs #Hiring #CareerGrowth
        """

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        text = response.json()['candidates'][0]['content']['parts'][0]['text']
        # Append the link at the very bottom if it's a job
        if mode == "EVENING":
            text += f"\n\n(Link found in source: {topic.split(' - ')[-1]})"
        return text
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
    # 1. Determine Mode (UTC Time)
    current_hour = datetime.utcnow().hour
    # If it's between 2 AM and 10 AM UTC (Morning in India/Europe), run Morning Mode
    if 2 <= current_hour <= 10:
        MODE = "MORNING"
    else:
        MODE = "EVENING"
    
    print(f"--- RUNNING {MODE} ROUTINE ---")
    
    # 2. Human Delay (The Anti-Robot)
    human_delay()
    
    # 3. Execution
    urn = get_user_urn()
    data = fetch_data(MODE)
    
    if data:
        print(f"📝 Found Topic: {data}")
        post = generate_post(MODE, data)
        if post:
            post_to_linkedin(urn, post)
            print("✅ Posted successfully.")
    else:
        print("❌ No data found.")
