import requests
import os
import random
import sys
import re
import xml.etree.ElementTree as ET
from datetime import datetime
import google.generativeai as genai  # <--- NEW IMPORT

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
    try:
        it = ET.iterparse(xml_content)
        for _, el in it:
            if '}' in el.tag:
                el.tag = el.tag.split('}', 1)[1]  # Strip {http://...}
        root = it.root
        return root
    except:
        return ET.fromstring(xml_content)

def clean_ai_slop(text):
    forbidden = [
        "delve", "tapestry", "landscape", "realm", "underscore",
        "testament", "leverage", "spearhead", "In conclusion",
        "Here is a post", "Sure!", "**Title**"
    ]
    for word in forbidden:
        text = text.replace(word, "")
        text = text.replace(word.capitalize(), "")
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) 
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
            
            with open("temp_feed.xml", "wb") as f:
                f.write(resp.content)

            tree = ET.parse("temp_feed.xml")
            root = tree.getroot()
            
            items = []
            for x in root.findall(".//item"): items.append(x)
            for x in root.findall(".//entry"): items.append(x)
            for x in root.findall(".//{http://www.w3.org/2005/Atom}entry"): items.append(x)

            if not items: continue

            candidates = items[:5]
            item = random.choice(candidates)

            title = item.findtext("title") or item.findtext("{http://www.w3.org/2005/Atom}title")
            link = item.findtext("link")
            if not link:
                link_node = item.find("{http://www.w3.org/2005/Atom}link")
                if link_node is not None:
                    link = link_node.attrib.get("href")
            
            if title and link:
                return f"{title} ({link})"
                
        except Exception as e:
            print(f"⚠️ Feed Error: {e}")
            continue
            
    return None

# --- 4. THE GHOSTWRITER ENGINE (Gemini SDK Update) ---
def generate_viral_post(topic):
    """
    Constructs a post using the Official Google GenAI SDK.
    """
    
    # 1. Configure
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Using 'gemini-1.5-flash' - currently the most reliable model
        model = genai.GenerativeModel('gemini-2.5-flash')
    except Exception as e:
        print(f"❌ SDK Config Error: {e}")
        return None

    # 2. Prompt
    system_instruction = f"""
    You are a top-tier Tech Thought Leader.
    Topic: "{topic}"
    GOAL: Write a high-engagement LinkedIn text post.
    
    RULES:
    1. Hook: Start with a punchy, contrarian statement.
    2. Spacing: Short paragraphs. Empty line between thoughts.
    3. Value: Explain how to USE this news (The Shovel).
    4. Tone: Confident, slightly informal.
    5. Length: Under 150 words.
    6. Ending: Ask a specific question.
    7. NO HASHTAGS in body. 3 hashtags at the end.
    """

    # 3. Generate
    try:
        response = model.generate_content(system_instruction)
        if response.text:
            return clean_ai_slop(response.text)
    except Exception as e:
        print(f"❌ Gemini API Error: {e}")
        return None

def generate_evergreen_post():
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
    
    try:
        user_urn = get_user_urn()
        print(f"👤 Authenticated as: {user_urn}")
    except Exception as e:
        print(f"❌ Auth Fatal Error: {e}")
        sys.exit(1)

    hour = datetime.utcnow().hour
    if 6 <= hour < 12:
        category = "OPPORTUNITY"
    elif 12 <= hour < 18:
        category = "MARKET_SHIFT"
    else:
        category = "BREAKTHROUGH"

    topic_data = fetch_high_value_signal(category)
    
    if topic_data:
        print(f"🧠 Synthesizing: {topic_data[:50]}...")
        post_content = generate_viral_post(topic_data)
    else:
        print("⚠️ No fresh signals. Deploying Evergreen Protocol.")
        post_content = generate_evergreen_post()

    if post_content:
        publish_to_linkedin(user_urn, post_content)
    else:
        print("❌ Generation Failed.")
