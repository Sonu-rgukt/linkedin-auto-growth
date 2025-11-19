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

# --- ELITE DATA SOURCES ---

# 1. DEEP TECH & AI (Authority Building)
# These sources make you look smarter than 99% of LinkedIn.
AI_FEEDS = [
    "http://googleaiblog.blogspot.com/atom.xml",                # Google AI Research (Direct Source)
    "https://openai.com/blog/rss.xml",                          # OpenAI Official (The bleeding edge)
    "https://www.mit.edu/newsoffice/topic/mit-artificial-intelligence-rss.xml", # MIT Research
    "https://feeds.arstechnica.com/arstechnica/index",          # Ars Technica (Deep analysis)
    "https://www.kdnuggets.com/feed",                           # Data Science Gold Standard
]

# 2. VIRAL TECH NEWS (Trend Riding)
# These sources trigger the "algorithm" because they are trending.
NEWS_FEEDS = [
    "https://feeds.feedburner.com/TheHackersNews",              # #1 Security & Hacker News
    "https://techcrunch.com/category/artificial-intelligence/feed/", # VC & Startup News
    "https://www.theverge.com/rss/index.xml",                   # Mainstream Tech
    "https://wired.com/feed/category/science/latest/rss",       # WIRED Science/Tech
]

# 3. HIGH-PAYING JOBS (Value Add)
# We only want Remote & Engineer roles. No low-tier spam.
JOB_FEEDS = [
    "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-machine-learning-ai-jobs.rss", # High Pay
    "https://remotive.com/remote-jobs/software-dev/feed",
    "https://www.python.org/jobs/feed/rss/",                    # Python.org (Very high quality)
]

def clean_text(raw_text):
    """Sanitizes AI output to remove robotic prefixes."""
    bad_phrases = ["Here is a LinkedIn post", "Here is the post", "Sure, here is", "**Title:**", "##", "Subject:"]
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

def fetch_data(mode):
    """
    Smart Fetcher:
    - Morning: Mixes Deep AI & Viral News.
    - Evening: Looks for Jobs.
    """
    if mode == "MORNING":
        # 50% chance of Deep AI, 50% chance of Viral News
        sources = AI_FEEDS if random.random() > 0.5 else NEWS_FEEDS
    else:
        sources = JOB_FEEDS

    random.shuffle(sources)
    print(f"🔍 Searching {mode} sources...")
    
    for feed in sources:
        try:
            response = requests.get(feed, timeout=10)
            if response.status_code == 200:
                # Handle Atom (XML) vs RSS differences
                root = ET.fromstring(response.content)
                
                # Atom feeds use specific namespaces, RSS is simpler. 
                # We try a generic search for 'item' or 'entry'
                items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
                
                # Look at first 5 items
                candidates = items[:5]
                if candidates:
                    item = random.choice(candidates)
                    
                    # Extract Title & Link safely
                    title = item.find("title").text if item.find("title") is not None else item.find("{http://www.w3.org/2005/Atom}title").text
                    
                    link_obj = item.find("link")
                    if link_obj is not None:
                        link = link_obj.text if link_obj.text else link_obj.attrib.get("href")
                    else:
                        link_obj = item.find("{http://www.w3.org/2005/Atom}link")
                        link = link_obj.attrib.get("href")
                    
                    # JOB FILTER: If evening, ensure it's a "Good" job
                    if mode == "EVENING":
                        # Only post if it mentions Senior, Lead, AI, or Python
                        keywords = ["Senior", "Lead", "Staff", "Principal", "AI", "Machine Learning", "Python", "Golang"]
                        if not any(k in title for k in keywords):
                            print(f"⚠️ Skipping low-tier job: {title}")
                            continue 
                            
                    return f"{title} - {link}"
        except Exception as e:
            print(f"⚠️ Error reading feed {feed}: {e}")
            continue
    return None

def generate_human_post(mode, topic):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    if mode == "MORNING":
        prompt = f"""
        Act as a Thought Leader in AI & Tech.
        News: "{topic}"
        
        Write a LinkedIn post.
        STRICT RULES:
        1. Output ONLY the post content.
        2. NO "Here is the post".
        3. Hook: A controversial or counter-intuitive statement about this news.
        4. Insight: What does this mean for the next 5 years? (One sentence).
        5. Advice: What should developers do today? (One sentence).
        6. Tags: #TechTrends #FutureOfWork #AI
        """
    else:
        prompt = f"""
        Act as a connection sharing a high-value opportunity.
        Job: "{topic}"
        
        Write a LinkedIn post.
        STRICT RULES:
        1. Output ONLY the post content.
        2. Hook: "Who is looking for a Senior/Lead role?"
        3. Why apply: "This company is hiring for [Role] and it looks legit."
        4. Call to Action: "Link is in the comments." (Do not put link in body).
        5. Tone: Casual helper.
        """

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        raw_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        final_text = clean_text(raw_text)
        
        # Append Link for Jobs
        if mode == "EVENING":
            link = topic.split(' - ')[-1]
            final_text += f"\n\n🔗 Apply Here: {link}"
            
        return final_text
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
    # Determine Mode
    current_hour = datetime.utcnow().hour
    MODE = "MORNING" if 2 <= current_hour <= 10 else "EVENING"
    
    # HUMAN DELAY (Keep this enabled for production!)
    # delay = random.randint(1, 20)
    # time.sleep(delay * 60)
    
    urn = get_user_urn()
    topic = fetch_data(MODE)
    
    if topic:
        print(f"📝 Premium Topic Found: {topic}")
        post_content = generate_human_post(MODE, topic)
        
        if post_content:
            post_to_linkedin(urn, post_content)
            print("✅ Posted World-Class Content.")
        else:
            print("❌ AI returned empty.")
    else:
        print("❌ No premium content found.")
