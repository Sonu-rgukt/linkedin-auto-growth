import pandas as pd
import os
import random
import requests
import json
import sys

# --- CONFIGURATION ---
LINKEDIN_TOKEN = os.environ["LINKEDIN_ACCESS_TOKEN"]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

def get_user_urn():
    """Get your LinkedIn ID (URN)"""
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return f"urn:li:person:{response.json()['sub']}"
    print(f"❌ LinkedIn Error: {response.text}")
    sys.exit(1)

def generate_viral_post(raw_job_text):
    """Uses Gemini to turn raw spammy text into a professional post"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    You are a Tech Recruiter influencer. 
    Turn this raw job alert into a professional, engaging LinkedIn post.
    
    RAW DATA:
    "{raw_job_text[:1000]}"
    
    RULES:
    1. Headline: Use a catchy Hook (e.g., "🚨 Qualcomm is Hiring Freshers!").
    2. Formatting: Use bullet points for Role, Batch, Salary (if available).
    3. Tone: Helpful, urgent, and professional. No cringe emojis.
    4. Call to Action: "Link in comments 👇" (Note: The API can't comment, so put the link in the post body for now).
    5. Hashtags: Add 3 relevant tags (e.g., #Freshers #Qualcomm #Hiring).
    
    OUTPUT ONLY THE POST TEXT.
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return response.json()['candidates'][0]['content']['parts'][0]['text']
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
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        print("✅ Success! Job posted to LinkedIn.")
    else:
        print(f"❌ Failed to post: {response.text}")

def main():
    print("--- 🚀 Job Poster Engine Starting ---")
    
    # 1. Load the CSV
    try:
        df = pd.read_csv("jobs_data.csv")
    except FileNotFoundError:
        print("⚠️ No jobs_data.csv found. Run listener.py first.")
        return

    if df.empty:
        print("⚠️ CSV is empty. No jobs to post.")
        return

    # 2. Filter for meaningful rows (ignore raw errors)
    # We just take a random job from the file
    # (Since the file is rewritten every run, these are all 'new' jobs)
    
    print(f"📊 Found {len(df)} jobs in CSV.")
    
    # Pick 1 random job to avoid spamming (or loop if you want multiple)
    # Let's pick a random one
    job_row = df.sample(1).iloc[0]
    raw_text = job_row['Raw_Text']
    
    print(f"🎯 Selected Job: {raw_text[:50]}...")
    
    # 3. Generate Content
    post_content = generate_viral_post(raw_text)
    
    if post_content:
        print("\n--- Generated Post ---")
        print(post_content)
        print("----------------------\n")
        
        # 4. Post to LinkedIn
        urn = get_user_urn()
        post_to_linkedin(urn, post_content)
    else:
        print("❌ AI failed to generate post.")

if __name__ == "__main__":
    main()
