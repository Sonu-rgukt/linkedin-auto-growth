import requests
import os
import json
import random
import sys
import re
import xml.etree.ElementTree as ET
from datetime import datetime

# --- 0. ARCHITECT CONFIGURATION ---
LINKEDIN_TOKEN = os.environ["LINKEDIN_ACCESS_TOKEN"]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

if not LINKEDIN_TOKEN or not GEMINI_API_KEY:
    print("❌ CRITICAL: Missing API Keys. System Shutting Down.")
    sys.exit(1)

# --- 1. THE DATA LAKE (High Signal Sources) ---
FEEDS = {
    "OPPORTUNITY": [ # Focus on startups and building
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.ycombinator.com/blog/feed",
        "https://feeds.feedburner.com/venturebeat/SZYF"
    ],
    "BREAKTHROUGH": [ # Deep tech
        "https://openai.com/blog/rss.xml",
        "http://googleaiblog.blogspot.com/atom.xml",
        "https://aws.amazon.com/blogs/machine-learning/feed/"
    ],
    "MARKET_SHIFT": [ # Where the money is moving
        "https://cointelegraph.com/rss",
        "https://www.theverge.com/rss/index.xml"
    ]
}

# --- 2. UTILITY: The XML Sanitizer ---
def parse_feed_robust(xml_content):
    """
    Normalizes RSS vs Atom feeds by stripping namespaces.
    This prevents the parser from failing on different XML standards.
    """
    try:
        # Brutal namespace stripping for easier parsing
        it = ET.iterparse(xml_content)
        for _, el in it:
            if '}' in el.tag:
                el.tag = el.tag.split('}', 1)[1]  # Strip {http://...}
        root = it.root
        return root
    except:
        # Fallback to standard string parsing if iterparse fails
        return ET.fromstring(xml_content)

def clean_ai_slop(text):
    """
    The Anti-Bot Filter. Removes words that scream 'I am ChatGPT'.
    """
    forbidden = [
        "delve", "tapestry", "landscape", "realm", "underscore",
        "testament", "leverage", "spearhead", "In conclusion",
        "Here is a post", "Sure!", "**Title**"
    ]
    for word in forbidden:
        text = text.replace(word, "")
        text = text.replace(word.capitalize(), "")
    
    # Fix double spaces and weird markdown artifacts
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) # Remove bold markdown (LinkedIn raw text prefers caps or unicode)
    return text.strip()

def get_user_urn():
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return f"urn:li:person:{response.json()['sub']}"
    sys.exit(f"❌ Auth Failed: {response.status_code}")

# --- 3. THE INTELLIGENCE LAYER (Sourcing) ---
def fetch_high_value_signal(category):
    print(f"📡 Scanning Frequency: {category}...")
    sources = FEEDS.get(category, FEEDS["OPPORTUNITY"])
    random.shuffle(sources)
    
    for feed_url in sources:
        try:
            resp = requests.get(feed_url, timeout=10)
            if resp.status_code != 200: continue

            # Save to temporary file to parse (ET requires file or robust string handling)
            with open("temp_feed.xml", "wb") as f:
                f.write(resp.content)

            tree = ET.parse("temp_feed.xml")
            root = tree.getroot()
            
            # Handle RSS (channel/item) vs Atom (entry)
            items = []
            for x in root.findall(".//item"): items.append(x)
            for x in root.findall(".//entry"): items.append(x)
            for x in root.findall(".//{http://www.w3.org/2005/Atom}entry"): items.append(x)

            if not items: continue

            # Pick a random candidate from top 5
            candidates = items[:5]
            item = random.choice(candidates)

            # Extract Data Robustly
            title = item.findtext("title") or item.findtext("{http://www.w3.org/2005/Atom}title")
            link = item.findtext("link")
            if not link:
                # Atom feeds often have link as an attribute
                link_node = item.find("{http://www.w3.org/2005/Atom}link")
                if link_node is not None:
                    link = link_node.attrib.get("href")
            
            if title and link:
                return f"{title} ({link})"
                
        except Exception as e:
            print(f"⚠️ Feed Error: {e}")
            continue
            
    return None

# --- 4. THE GHOSTWRITER ENGINE (Gemini) ---
def generate_viral_post(topic):
    """
    Constructs a post based on 'Top Voice' frameworks.
    """
    
    # ARCHITECT NOTE: This prompt is the "Shovel". It forces the AI to sell the solution, not just the news.
    system_instruction = f"""
    You are a top-tier Tech Thought Leader and Angel Investor on LinkedIn.
    You do not "summarize news". You analyze **implications** and **opportunities**.
    
    CONTEXT:
    The topic is: "{topic}"
    
    YOUR GOAL:
    Write a high-engagement LinkedIn text post about this topic.
    
    STRICT FORMATTING RULES:
    1. **The Hook:** Start with a punchy, contrarian, or surprising 1-sentence statement. No "Subject:" lines.
    2. **The Spacing:** Use short paragraphs (1-2 sentences max). Add an empty line between every paragraph.
    3. **The 'Shovel' Philosophy:** Do not just say what happened. Explain how engineers/founders can USE this to build something (sell the shovel).
    4. **Visuals:** Use bullet points (•) for lists.
    5. **Tone:** Confident, slightly informal, professional but not academic.
    6. **Ending:** End with a question to drive comments.
    7. **Length:** Keep it under 150 words. Crisp.
    8. NO HASHTAGS in the body. Put 3 specific hashtags at the very end.
    """

    payload = {
        "contents": [{"parts": [{"text": system_instruction}]}],
        "generationConfig": {
            "temperature": 0.7, # Creative but stable
            "maxOutputTokens": 400,
        }
    }

    # Model Priority Queue
    models = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"]
    
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            response = requests.post(url, json=payload, timeout=20)
            if response.status_code == 200:
                raw_text = response.json()['candidates'][0]['content']['parts'][0]['text']
                return clean_ai_slop(raw_text)
        except:
            continue
            
    return None

def generate_evergreen_post():
    """Fallback if news is slow. Generates timeless advice."""
    topics = ["The importance of shipping code fast", "Why 'perfect' is the enemy of 'good'", "How AI is changing entry-level coding"]
    return generate_viral_post(random.choice(topics))

# --- 5. THE PUBLISHER ---
def publish_to_linkedin(urn, text):
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
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code == 201:
        print("✅ SUCCESS: Post is Live.")
        print("-" * 20)
        print(text)
        print("-" * 20)
    else:
        print(f"❌ ERROR: {res.text}")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("🚀 Initializing Viral Engine V2...")
    
    # 1. Authenticate
    try:
        user_urn = get_user_urn()
        print(f"👤 Authenticated as: {user_urn}")
    except Exception as e:
        print(f"❌ Auth Fatal Error: {e}")
        sys.exit(1)

    # 2. Determine Strategy based on Time
    hour = datetime.utcnow().hour
    if 6 <= hour < 12:
        category = "OPPORTUNITY" # Morning: Motivation/Startups
    elif 12 <= hour < 18:
        category = "MARKET_SHIFT" # Afternoon: Business/Crypto
    else:
        category = "BREAKTHROUGH" # Evening: Deep Tech/Learning

    # 3. Hunt for Data
    topic_data = fetch_high_value_signal(category)
    
    # 4. Generate Content
    if topic_data:
        print(f"🧠 Synthesizing: {topic_data[:50]}...")
        post_content = generate_viral_post(topic_data)
    else:
        print("⚠️ No fresh signals. Deploying Evergreen Protocol.")
        post_content = generate_evergreen_post()

    # 5. Publish
    if post_content:
        publish_to_linkedin(user_urn, post_content)
    else:
        print("❌ Generation Failed.")
