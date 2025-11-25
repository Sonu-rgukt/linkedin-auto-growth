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

# --- 0. ARCHITECT CONFIGURATION ---
LINKEDIN_TOKEN = os.environ["LINKEDIN_ACCESS_TOKEN"]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
HF_TOKEN = os.environ["HUGGINGFACE_TOKEN"]

if not LINKEDIN_TOKEN or not GEMINI_API_KEY or not HF_TOKEN:
    print("❌ CRITICAL: Missing API Keys. System Shutting Down.")
    sys.exit(1)

# --- 1. UTILITIES: The Polish ---
def clean_ai_slop(text):
    """Sanitizes text to remove the 'ChatGPT accent'."""
    forbidden = [
        "delve", "tapestry", "landscape", "realm", "underscore",
        "testament", "leverage", "In conclusion", "**Title**", "##"
    ]
    for word in forbidden:
        text = text.replace(word, "")
        text = text.replace(word.capitalize(), "")
    return text.strip()

# --- 2. THE QUANT QUANT (Advanced Financial Charts) ---
def generate_pro_chart(ticker):
    """
    Generates a 'Dark Mode' institutional-grade chart.
    Visuals stop the scroll. Dark mode implies 'Pro'.
    """
    print(f"📉 Quant Engine: Analyzing {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        # Fetch 1 month of data for better trend visualization
        df = stock.history(period="1mo", interval="1d")
        
        if df.empty: return None

        # Calculate Simple Moving Average (SMA) - The "Signal"
        df['SMA_5'] = df['Close'].rolling(window=5).mean()

        # SETUP: Bloomberg Terminal Style
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot Price
        ax.plot(df.index, df['Close'], label='Price', color='#00ff41', linewidth=2) # Matrix Green
        # Plot SMA (The Analysis)
        ax.plot(df.index, df['SMA_5'], label='5-Day Trend', color='#ff00ff', linestyle='--', linewidth=1.5) # Neon Pink

        # Styling
        ax.set_title(f"${ticker} | MARKET VELOCITY", color='white', fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, color='#333333', linestyle='--', alpha=0.5)
        ax.legend(loc='upper left', frameon=False)
        
        # Date Formatting
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        plt.xticks(rotation=45)
        
        # Save high quality
        chart_path = "assets_chart.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='black')
        plt.close()
        
        print("✅ Chart Rendered.")
        return chart_path
    except Exception as e:
        print(f"⚠️ Chart Failed: {e}")
        return None

# --- 3. THE VISIONARY (High-Fidelity AI Art) ---
def generate_architectural_art(topic):
    """
    Generates technical, schematic-style art rather than generic 'fantasy' art.
    Target Audience: Engineers & Builders.
    """
    print(f"🎨 Rendering Schematic for: {topic}")
    client = InferenceClient(token=HF_TOKEN)
    
    # Prompt Engineering for "The Shovel" look (Schematics, Blueprints, Data Centers)
    base_prompt = (
        f"technical blueprint schematic of {topic}, isometric view, "
        "engineering diagram style, highly detailed, neon cyan lines on dark blue background, "
        "unreal engine 5 render, 8k, data visualization aesthetics"
    )
    
    try:
        image = client.text_to_image(
            prompt=base_prompt,
            model="black-forest-labs/FLUX.1-schnell" # The Speed King
        )
        image_path = "assets_visual.png"
        image.save(image_path)
        print("✅ Visual Asset Created.")
        return image_path
    except Exception as e:
        print(f"⚠️ Art Gen Failed: {e}")
        return None

# --- 4. THE GHOSTWRITER (Gemini) ---
def generate_analysis_text(mode, topic):
    """
    Writes the post. Focuses on 'Actionable Insight' over 'Description'.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    if mode == "FINANCE":
        system_prompt = f"""
        You are a Quant Trader.
        Topic: ${topic}
        Task: Write a LinkedIn post analyzing the chart.
        Style: "Here is the data." Short, punchy, numerical.
        Hook: Start with a prediction or observation about volatility.
        Value: Explain ONE thing a trader should look for next week.
        Format: Short lines. No "Intro". End with 3 tags.
        """
    elif mode == "TECH":
        system_prompt = f"""
        You are a Systems Architect.
        Topic: {topic}
        Task: Explain this concept using the attached blueprint metaphor.
        Style: Technical but accessible.
        Value: Why is this specific tech the "shovel" for the future?
        Format: Bullet points for key benefits. End with 3 tags.
        """
    else: # MOTIVATION (But for Builders)
        system_prompt = f"""
        You are a Startup Founder.
        Topic: {topic}
        Task: Write a "Builder's Mindset" post.
        Style: Stoic, hard truths.
        Value: One actionable habit to build better things.
        Format: 3 short sentences max per paragraph. End with 3 tags.
        """

    payload = {
        "contents": [{"parts": [{"text": system_prompt}]}],
        "generationConfig": {"temperature": 0.7}
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            raw = response.json()['candidates'][0]['content']['parts'][0]['text']
            return clean_ai_slop(raw)
    except Exception as e:
        print(f"⚠️ Text Gen Error: {e}")
        
    return None

# --- 5. THE UPLINK (LinkedIn Media Handler) ---
def post_visual_asset(urn, text, image_path):
    print("🚀 Uploading Asset to LinkedIn...")
    
    # 1. Register
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
        
        # 2. Upload
        with open(image_path, "rb") as f:
            up_res = requests.put(upload_url, headers={"Authorization": f"Bearer {LINKEDIN_TOKEN}"}, data=f)
            up_res.raise_for_status()
            
        # 3. Publish
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
        
        fin_res = requests.post(pub_url, headers=headers, json=pub_body)
        fin_res.raise_for_status()
        print("✅ SUCCESS: Visual Post Deployed.")
        
    except Exception as e:
        print(f"❌ Upload Sequence Failed: {e}")

def get_urn():
    try:
        res = requests.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {LINKEDIN_TOKEN}"})
        return f"urn:li:person:{res.json()['sub']}"
    except:
        sys.exit("❌ Auth Failed")

# --- MAIN ---
if __name__ == "__main__":
    user_urn = get_urn()
    
    # Weighted Randomness: Focus heavily on Tech & Finance (The "Shovel" Niches)
    # 40% Finance, 40% Tech, 20% Mindset
    choice = random.choices(["FINANCE", "TECH", "MINDSET"], weights=[40, 40, 20], k=1)[0]
    
    asset_file = None
    topic = ""
    
    if choice == "FINANCE":
        # High volatility tickers only
        topic = random.choice(["NVDA", "MSTR", "COIN", "TSLA", "AMD", "ETH-USD", "SOL-USD"])
        asset_file = generate_pro_chart(topic)
        
    elif choice == "TECH":
        topic = random.choice(["Kubernetes Clusters", "Neural Network Layers", "Rust Memory Safety", "Blockchain Sharding"])
        asset_file = generate_architectural_art(topic)
        
    elif choice == "MINDSET":
        topic = random.choice(["Deep Work", "Shipping MVP", "Code Quality", "Technical Debt"])
        # For mindset, we use a clean, minimal "Blueprint" style image
        asset_file = generate_architectural_art(f"minimalist icon representing {topic}")

    # Generate Text & Post
    if asset_file:
        post_text = generate_analysis_text(choice, topic)
        if post_text:
            print(f"📝 Topic: {topic} | Mode: {choice}")
            post_visual_asset(user_urn, post_text, asset_file)
            
            # Cleanup
            if os.path.exists(asset_file):
                os.remove(asset_file)
        else:
            print("❌ Text Generation Failed.")
    else:
        print("❌ Visual Generation Failed.")
