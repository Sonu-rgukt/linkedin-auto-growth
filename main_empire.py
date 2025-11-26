import requests
import os
import random
import sys
import time
import re
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime
from huggingface_hub import InferenceClient
import google.generativeai as genai # <--- NEW IMPORT

# --- 0. ARCHITECT CONFIGURATION ---
LINKEDIN_TOKEN = os.environ["LINKEDIN_ACCESS_TOKEN"]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
HF_TOKEN = os.environ["HUGGINGFACE_TOKEN"]

if not LINKEDIN_TOKEN or not GEMINI_API_KEY or not HF_TOKEN:
    print("❌ CRITICAL: Missing API Keys. System Shutting Down.")
    sys.exit(1)

# --- 1. UTILITIES ---
def clean_ai_slop(text):
    forbidden = ["delve", "tapestry", "landscape", "realm", "underscore", "testament", "In conclusion", "**Title**"]
    for word in forbidden:
        text = text.replace(word, "")
        text = text.replace(word.capitalize(), "")
    return text.strip()

# --- 2. THE QUANT QUANT (Charts) ---
def generate_pro_chart(ticker):
    print(f"📉 Quant Engine: Analyzing {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1mo", interval="1d")
        if df.empty: return None

        df['SMA_5'] = df['Close'].rolling(window=5).mean()

        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.plot(df.index, df['Close'], label='Price', color='#00ff41', linewidth=2) 
        ax.plot(df.index, df['SMA_5'], label='Trend', color='#ff00ff', linestyle='--', linewidth=1.5) 

        ax.set_title(f"${ticker} | MARKET VELOCITY", color='white', fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, color='#333333', linestyle='--', alpha=0.5)
        ax.legend(loc='upper left', frameon=False)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        plt.xticks(rotation=45)
        
        chart_path = "assets_chart.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='black')
        plt.close()
        print("✅ Chart Rendered.")
        return chart_path
    except Exception as e:
        print(f"⚠️ Chart Failed: {e}")
        return None

# --- 3. THE VISIONARY (Art) ---
def generate_architectural_art(topic):
    print(f"🎨 Rendering Schematic for: {topic}")
    client = InferenceClient(token=HF_TOKEN)
    base_prompt = (f"technical blueprint schematic of {topic}, isometric view, engineering diagram style, cyan lines on dark blue, 8k")
    try:
        image = client.text_to_image(prompt=base_prompt, model="black-forest-labs/FLUX.1-schnell")
        image_path = "assets_visual.png"
        image.save(image_path)
        print("✅ Visual Asset Created.")
        return image_path
    except Exception as e:
        print(f"⚠️ Art Gen Failed: {e}")
        return None

# --- 4. THE GHOSTWRITER (Gemini SDK Update) ---
def generate_analysis_text(mode, topic):
    
    # 1. Configure SDK
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        print(f"❌ SDK Config Error: {e}")
        return None

    # 2. Select Prompt
    if mode == "FINANCE":
        system_prompt = f"Act as a Quant Trader. Topic: ${topic}. Analyze volatility. Style: Short, data-driven. Start with 'Market Update:'"
    elif mode == "TECH":
        system_prompt = f"Act as a Systems Architect. Topic: {topic}. Explain the engineering value. Style: Technical."
    else:
        system_prompt = f"Act as a Startup Founder. Topic: {topic}. Give harsh but useful advice. Style: Stoic."

    # 3. Generate
    try:
        response = model.generate_content(system_prompt)
        return clean_ai_slop(response.text)
    except Exception as e:
        print(f"❌ Gemini API Error: {e}")
        return None

# --- 5. THE UPLINK ---
def post_visual_asset(urn, text, image_path):
    print("🚀 Uploading Asset to LinkedIn...")
    reg_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}"}
    reg_body = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": urn,
            "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
        }
    }
    
    try:
        reg_res = requests.post(reg_url, headers=headers, json=reg_body)
        reg_res.raise_for_status()
        data = reg_res.json()
        upload_url = data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
        asset_urn = data['value']['asset']
        
        with open(image_path, "rb") as f:
            requests.put(upload_url, headers={"Authorization": f"Bearer {LINKEDIN_TOKEN}"}, data=f)
            
        pub_url = "https://api.linkedin.com/v2/ugcPosts"
        pub_body = {
            "author": urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "IMAGE",
                    "media": [{"status": "READY", "description": {"text": "AI Analysis"}, "media": asset_urn, "title": {"text": "Insight"}}]
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }
        
        requests.post(pub_url, headers=headers, json=pub_body)
        print("✅ SUCCESS: Visual Post Deployed.")
        
    except Exception as e:
        print(f"❌ Upload Sequence Failed: {e}")

def get_urn():
    try:
        res = requests.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {LINKEDIN_TOKEN}"})
        return f"urn:li:person:{res.json()['sub']}"
    except:
        sys.exit("❌ Auth Failed")

if __name__ == "__main__":
    user_urn = get_urn()
    choice = random.choices(["FINANCE", "TECH", "MINDSET"], weights=[40, 40, 20], k=1)[0]
    
    asset_file = None
    topic = ""
    
    if choice == "FINANCE":
        topic = random.choice(["NVDA", "MSTR", "COIN", "TSLA", "AMD", "ETH-USD", "SOL-USD"])
        asset_file = generate_pro_chart(topic)
    elif choice == "TECH":
        topic = random.choice(["Kubernetes Clusters", "Neural Network Layers", "Rust Memory Safety"])
        asset_file = generate_architectural_art(topic)
    elif choice == "MINDSET":
        topic = random.choice(["Deep Work", "Shipping MVP", "Code Quality"])
        asset_file = generate_architectural_art(f"minimalist icon representing {topic}")

    if asset_file:
        post_text = generate_analysis_text(choice, topic)
        if post_text:
            print(f"📝 Topic: {topic} | Mode: {choice}")
            post_visual_asset(user_urn, post_text, asset_file)
            if os.path.exists(asset_file): os.remove(asset_file)
        else:
            print("❌ Text Generation Failed.")
    else:
        print("❌ Visual Generation Failed.")
