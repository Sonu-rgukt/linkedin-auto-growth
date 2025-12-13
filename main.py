import requests
import os
import sys
import re
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import google.generativeai as genai
from bs4 import BeautifulSoup
import time

# --- 0. GOD MODE CONFIGURATION ---
# Security Note: Ensure these are set in your environment variables
LINKEDIN_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Optional: For Google Image Search (Fallback if source image fails)
# Get these from: https://developers.google.com/custom-search/v1/overview
GOOGLE_SEARCH_API_KEY = os.environ.get("GOOGLE_SEARCH_API_KEY") 
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID") 

HISTORY_FILE = "posted_history.txt"

if not LINKEDIN_TOKEN or not GEMINI_API_KEY:
    print("❌ CRITICAL: Missing API Keys (LinkedIn or Gemini). Shutting Down.")
    sys.exit(1)

# --- 1. THE DATA LAKE (High Signal Sources) ---
FEEDS = [
    # Startups & VC
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.ycombinator.com/blog/feed",
    "https://feeds.feedburner.com/venturebeat/SZYF",
    # Engineering & Big Tech
    "https://openai.com/blog/rss.xml",
    "http://googleaiblog.blogspot.com/atom.xml",
    "https://aws.amazon.com/blogs/machine-learning/feed/",
    "https://netflixtechblog.com/feed",
    # Macro & Crypto
    "https://cointelegraph.com/rss"
]

# --- 2. THE ANALYST (Utils) ---
def load_history():
    if not os.path.exists(HISTORY_FILE): return []
    with open(HISTORY_FILE, "r") as f:
        return [line.strip() for line in f.readlines()]

def save_to_history(link):
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{link}\n")

def clean_text(text):
    text = re.sub(r'<[^>]+>', '', text) # Strip HTML
    return text.strip()

def get_linkedin_user_urn():
    """Fetches the authenticated user's URN."""
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return f"urn:li:person:{response.json()['sub']}"
    sys.exit(f"❌ Auth Failed: {response.status_code} - {response.text}")

# --- 3. THE COLLECTOR (News Aggregation) ---
def fetch_all_candidates():
    """Scrapes ALL feeds and returns a list of dictionaries."""
    print("📡 Scanning Global Frequencies...")
    history = load_history()
    candidates = []

    for feed_url in FEEDS:
        try:
            resp = requests.get(feed_url, timeout=5)
            if resp.status_code != 200: continue
            
            # Simple XML Parse
            root = ET.fromstring(resp.content)
            
            # Handle Atom vs RSS
            items = root.findall(".//item") + root.findall(".//{http://www.w3.org/2005/Atom}entry")
            
            for item in items[:3]: # Take top 3 from each feed
                title = item.findtext("title") or item.findtext("{http://www.w3.org/2005/Atom}title")
                link = item.findtext("link") or item.findtext("{http://www.w3.org/2005/Atom}link")
                
                # Atom link handling
                if not link:
                    link_node = item.find("{http://www.w3.org/2005/Atom}link")
                    if link_node is not None: link = link_node.attrib.get("href")

                if link and link not in history:
                    candidates.append({"title": title, "link": link, "source": feed_url})
        except Exception:
            continue
            
    return candidates

# --- 4. THE EDITOR-IN-CHIEF (Gemini Decision Logic) ---
def select_best_story(candidates):
    """Uses Gemini to pick the ONE best story from the list."""
    if not candidates: return None

    print(f"🧠 AI Analyzing {len(candidates)} potential stories...")
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash') # Fast model for decision making

    candidate_str = "\n".join([f"{i}. {c['title']} (Link: {c['link']})" for i, c in enumerate(candidates)])
    
    prompt = f"""
    You are the Editor-in-Chief of a top Tech Newsletter.
    Here are the trending stories today:
    
    {candidate_str}

    TASK: Select the SINGLE story with the highest viral potential for LinkedIn.
    Criteria: Contrarian, deeply technical yet accessible, or major market shift.
    
    Return ONLY the JSON format: {{"index": <number>, "reason": "<short_reason>"}}
    """
    
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        result = json.loads(response.text)
        winner = candidates[result['index']]
        print(f"🌟 WINNER: {winner['title']}")
        print(f"🤔 Reason: {result['reason']}")
        return winner
    except Exception as e:
        print(f"❌ Selection Error: {e}")
        return candidates[0] # Fallback to first

def write_viral_post(article):
    """Writes the actual LinkedIn post content."""
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash') # High quality model for writing

    prompt = f"""
    Topic: {article['title']}
    Source Link: {article['link']}
    
    Write a LinkedIn post.
    Style: "God Level" Thought Leader. 
    Structure:
    1. The Hook (One sentence, punchy, maybe controversial).
    2. The Context (Why this matters NOW).
    3. The Insight (What most people miss).
    4. The Actionable Takeaway.
    5. A Question to drive comments.
    
    Constraints: 
    - No "I'm thrilled to announce".
    - Use line breaks for readability.
    - Max 3 hashtags at the very bottom.
    - Tone: Confident, crisp, professional but human.
    """
    
    response = model.generate_content(prompt)
    return response.text.strip()

# --- 5. THE ART DIRECTOR (Image Retrieval) ---
def get_best_image(article_url, query_term):
    """Tries to get Source Image (OG Tag). If fails, falls back to Google Search."""
    image_path = "temp_image.jpg"
    
    # Method A: Scrape the Source (Preferred - Highest Relevance)
    try:
        print("🎨 Attempting to extract source image...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        r = requests.get(article_url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.content, 'html.parser')
        og_image = soup.find("meta", property="og:image")
        
        if og_image and og_image.get("content"):
            img_url = og_image["content"]
            img_data = requests.get(img_url).content
            with open(image_path, 'wb') as f: f.write(img_data)
            print("✅ Acquired Source Image.")
            return image_path
    except Exception as e:
        print(f"⚠️ Source Scraping Failed: {e}")

    # Method B: Google Custom Search API (Fallback)
    if GOOGLE_SEARCH_API_KEY and GOOGLE_CSE_ID:
        try:
            print("🔍 Falling back to Google Image Search...")
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "q": query_term,
                "cx": GOOGLE_CSE_ID,
                "key": GOOGLE_SEARCH_API_KEY,
                "searchType": "image",
                "num": 1,
                "imgSize": "large",
                "safe": "active"
            }
            res = requests.get(url, params=params)
            data = res.json()
            
            if "items" in data:
                img_url = data["items"][0]["link"]
                img_data = requests.get(img_url).content
                with open(image_path, 'wb') as f: f.write(img_data)
                print("✅ Acquired Google Image.")
                return image_path
        except Exception as e:
            print(f"⚠️ Google Search Failed: {e}")

    print("❌ No image found. Text only mode.")
    return None

# --- 6. THE PUBLISHER (LinkedIn Image Upload Flow) ---
def upload_image_to_linkedin(urn, image_path):
    """
    Step 1: Register Upload
    Step 2: PUT Binary File
    Step 3: Return Asset ID
    """
    # 1. Register
    reg_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": urn,
            "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
        }
    }
    
    reg_response = requests.post(reg_url, headers=headers, json=payload)
    if reg_response.status_code != 200:
        print(f"❌ Register Failed: {reg_response.text}")
        return None
        
    data = reg_response.json()
    upload_url = data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
    asset_urn = data['value']['asset']
    
    # 2. Upload
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    upload_headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}"} # Sometimes needs NO content-type, let requests handle it
    upload_resp = requests.put(upload_url, headers=upload_headers, data=image_data)
    
    if upload_resp.status_code != 201:
        print(f"❌ Binary Upload Failed: {upload_resp.status_code}")
        return None
        
    return asset_urn

def publish_post(urn, text, image_asset=None):
    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {LINKEDIN_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    
    share_content = {
        "shareCommentary": {"text": text},
        "shareMediaCategory": "NONE"
    }
    
    if image_asset:
        share_content["shareMediaCategory"] = "IMAGE"
        share_content["media"] = [{
            "status": "READY",
            "description": {"text": "Image"},
            "media": image_asset,
            "title": {"text": "Shared Image"}
        }]

    payload = {
        "author": urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": share_content
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }

    res = requests.post(url, headers=headers, json=payload)
    if res.status_code == 201:
        print("✅ SUCCESS: Post Published Successfully.")
        return True
    else:
        print(f"❌ Publish Error: {res.text}")
        return False

# --- MAIN ENGINE ---
if __name__ == "__main__":
    print("🚀 Initializing God-Level Publisher...")
    
    # 1. Auth
    try:
        user_urn = get_linkedin_user_urn()
        print(f"👤 Logged in as: {user_urn}")
    except Exception as e:
        print(e)
        sys.exit(1)

    # 2. Gather
    candidates = fetch_all_candidates()
    if not candidates:
        print("⚠️ No fresh news found.")
        sys.exit(0)

    # 3. Select (The "One Post" Logic)
    best_story = select_best_story(candidates)
    
    # 4. Write
    post_text = write_viral_post(best_story)
    print("\n--- GENERATED COPY ---\n")
    print(post_text)
    print("\n----------------------\n")

    # 5. Visuals
    image_asset_urn = None
    local_image = get_best_image(best_story['link'], best_story['title'])
    
    if local_image:
        print("📤 Uploading Asset to LinkedIn...")
        image_asset_urn = upload_image_to_linkedin(user_urn, local_image)
    
    # 6. Publish
    success = publish_post(user_urn, post_text, image_asset_urn)
    
    # 7. Cleanup & History
    if success:
        save_to_history(best_story['link'])
        if local_image and os.path.exists(local_image):
            os.remove(local_image)
