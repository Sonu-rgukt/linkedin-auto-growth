import requests
import os
import sys
import json
import random
import time
from google import genai
from google.genai import types

# --- 1. EMPIRE CONFIGURATION ---
LINKEDIN_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GOOGLE_SEARCH_API_KEY = os.environ.get("GOOGLE_SEARCH_API_KEY")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID")

# --- INTELLIGENCE GRID ---
SEARCH_TOPICS = [
    # 1. THE ARCHITECT (Hard Engineering & Deep Tech)
    "post-quantum cryptography implementation 2025",
    "rust vs go for backend performance 2025",
    "multi-agent ai system architecture patterns",
    "kubernetes alternatives for edge computing",
    "future of platform engineering vs ai agents",

    # 2. THE STRATEGIST (Enterprise & Market Shifts)
    "gartner top strategic technology trends 2026",
    "vertical ai startups healthcare legal construction",
    "small language models slm vs llm enterprise adoption",
    "ai governance and digital sovereignty regulations 2025",
    "generative ai unit economics profitability",

    # 3. THE FOUNDER (Startup Signals & VC Movement)
    "y combinator request for startups winter 2025 analysis",
    "contrarian tech startup trends 2025",
    "bootstrapped saas success stories 2025",
    "impact of ai on junior developer job market",
    "non-obvious ai startup ideas reddit",

    # 4. THE VISIONARY (Breakthroughs)
    "solid state battery commercialization news",
    "nuclear fusion energy breakthrough 2025",
    "brain computer interface startups beyond neuralink",
    "CRISPR gene editing commercial applications 2025",
    "room temperature superconductor replication attempts"
]

HISTORY_FILE = "posted_history.txt"

if not all([LINKEDIN_TOKEN, GEMINI_API_KEY, GOOGLE_SEARCH_API_KEY, GOOGLE_CSE_ID]):
    print("❌ CRITICAL: Missing one or more API Keys. System Halting.")
    sys.exit(1)

# --- 2. THE ARCHIVIST (Memory) ---
def load_history():
    if not os.path.exists(HISTORY_FILE): return []
    with open(HISTORY_FILE, "r") as f:
        return [line.strip() for line in f.readlines()]

def save_to_history(link):
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{link}\n")

# --- 3. THE HUNTER (Google Web Search) ---
def search_the_web_for_news():
    """
    Uses Google Custom Search API to find high-signal news from the last 24 hours.
    """
    print("📡 Satellites aligning. Scanning the entire web for fresh signals...")
    
    candidates = []
    history = load_history()
    
    # Pick 2 random topics to search
    daily_topics = random.sample(SEARCH_TOPICS, 2)
    
    for query in daily_topics:
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "q": query,
                "cx": GOOGLE_CSE_ID,
                "key": GOOGLE_SEARCH_API_KEY,
                "num": 3,             
                "dateRestrict": "d1", # Only last 24 hours
                "safe": "active"
            }
            
            resp = requests.get(url, params=params)
            data = resp.json()
            
            if "items" in data:
                for item in data["items"]:
                    title = item.get("title")
                    link = item.get("link")
                    snippet = item.get("snippet")
                    
                    if link not in history:
                        candidates.append({
                            "title": title,
                            "link": link,
                            "snippet": snippet,
                            "source": "Google Search"
                        })
            time.sleep(1) # Be nice to Google Search API
                        
        except Exception as e:
            print(f"⚠️ Search Glitch on '{query}': {e}")
            continue

    return candidates

# --- 4. THE EDITOR-IN-CHIEF (Gemini Selection) ---
def select_viral_story(client, candidates):
    """
    Feeds all search results to Gemini to pick the potential viral hit.
    """
    if not candidates: return None

    print(f"🧠 AI Analyzing {len(candidates)} raw intelligence reports...")
    
    # Prepare data for AI
    candidate_list = []
    for i, c in enumerate(candidates):
        candidate_list.append(f"ID {i}: {c['title']} - {c['snippet']} (Link: {c['link']})")
    
    prompt = f"""
    You are the Editor-in-Chief of a world-class Tech publication.
    I have a list of potential stories found on the web today.
    
    STORY LIST:
    {json.dumps(candidate_list)}

    MISSION:
    Identify the single story with the highest potential for LinkedIn engagement.
    Look for: Contrarian views, major industry shifts, or highly actionable insights.
    
    RESPONSE FORMAT (JSON ONLY):
    {{"id": <integer_id>, "reason": "<why_you_chose_this>"}}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash', # Stable, High Quota Model
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        result = json.loads(response.text)
        winner = candidates[result['id']]
        print(f"🌟 WINNER SELECTED: {winner['title']}")
        print(f"🤔 Strategy: {result['reason']}")
        return winner
    except Exception as e:
        print(f"❌ Selection Error: {e}")
        return candidates[0]

# --- 5. THE GHOSTWRITER (Gemini Content Gen) ---
def write_empire_post(client, article):
    print("⏳ Cooling down AI engines (5s)...")
    time.sleep(5) 

    prompt = f"""
    SOURCE MATERIAL:
    Title: {article['title']}
    Snippet: {article['snippet']}
    Link: {article['link']}

    IDENTITY:
    You are a "LinkedIn Top Voice" in Technology and Startups.
    You sound like a seasoned founder or CTO sharing a critical insight.

    WRITING FRAMEWORK (Use this structure):
    1. The Hook: A short, punchy, slightly polarizing statement about the topic. (Max 12 words)
    2. The "Meat": Explain the news, but focus on the *implication*, not just the event. Use 3-4 short bullet points.
    3. The Pivot: "Why this matters to you."
    4. The Engagement: Ask a question that forces people to pick a side.

    RULES:
    - NO emojis in the first 2 lines.
    - Use line breaks generously.
    - Tone: Confident, crisp, authoritative.
    - END with 3 relevant hashtags.
    - Do NOT start with "In the rapidly evolving landscape..."
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash', # Keeping 1.5-flash for reliability
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"❌ Writing Error: {e}")
        return None

# --- 6. THE ART DIRECTOR (Google Image Search) ---
def find_perfect_image(query_term):
    print(f"🎨 Commissioning art for: '{query_term}'...")
    image_path = "viral_visual.jpg"
    
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "q": query_term + " technology wallpaper", 
            "cx": GOOGLE_CSE_ID,
            "key": GOOGLE_SEARCH_API_KEY,
            "searchType": "image",
            "imgSize": "large",      
            "imgType": "photo",      
            "num": 1,
            "safe": "active"
        }
        
        resp = requests.get(url, params=params)
        data = resp.json()
        
        if "items" in data:
            img_url = data["items"][0]["link"]
            print(f"🖼️ Image Found: {img_url}")
            img_data = requests.get(img_url, timeout=10).content
            with open(image_path, 'wb') as f:
                f.write(img_data)
            return image_path
            
    except Exception as e:
        print(f"⚠️ Image Search Failed: {e}")
    
    return None

# --- 7. THE PUBLISHER (LinkedIn API) ---
def get_urn():
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"❌ LinkedIn Auth Error: {resp.text}")
        sys.exit(1)
    return f"urn:li:person:{resp.json()['sub']}"

def upload_image(urn, image_path):
    reg_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": urn,
            "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
        }
    }
    
    try:
        reg_resp = requests.post(reg_url, headers=headers, json=payload)
        reg = reg_resp.json()
        upload_url = reg['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
        asset = reg['value']['asset']
        
        with open(image_path, "rb") as f:
            requests.put(upload_url, headers={"Authorization": f"Bearer {LINKEDIN_TOKEN}"}, data=f.read())
            
        return asset
    except Exception as e:
        print(f"❌ Image Upload Failed: {e}")
        return None

def post_to_linkedin(urn, text, image_asset=None):
    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}", "Content-Type": "application/json", "X-Restli-Protocol-Version": "2.0.0"}
    
    share_content = {"shareCommentary": {"text": text}, "shareMediaCategory": "NONE"}
    if image_asset:
        share_content["shareMediaCategory"] = "IMAGE"
        share_content["media"] = [{"status": "READY", "description": {"text": "Image"}, "media": image_asset, "title": {"text": "Visual"}}]

    payload = {
        "author": urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": share_content},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code == 201:
        print("✅ POST LIVE ON LINKEDIN.")
        return True
    print(f"❌ Publish Failed: {resp.text}")
    return False

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("🚀 EMPIRE ENGINE STARTING...")
    
    # 0. Initialize New Gemini Client
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"❌ Gemini Client Error: {e}")
        sys.exit(1)

    # 1. Get User
    urn = get_urn()

    # 2. Search Web (Last 24h)
    candidates = search_the_web_for_news()
    if not candidates:
        print("⚠️ No fresh news found. Sleeping.")
        sys.exit(0)

    # 3. Select Best
    story = select_viral_story(client, candidates)

    # 4. Write Copy
    copy = write_empire_post(client, story)
    
    if not copy:
        print("❌ AI failed to write copy. Exiting.")
        sys.exit(1)
        
    print("\n--- FINAL COPY ---\n" + copy + "\n------------------\n")

    # 5. Get Image
    img_path = find_perfect_image(story['title'])

    # 6. Publish
    asset = upload_image(urn, img_path) if img_path else None
    if post_to_linkedin(urn, copy, asset):
        save_to_history(story['link'])
        if img_path and os.path.exists(img_path): os.remove(img_path)
