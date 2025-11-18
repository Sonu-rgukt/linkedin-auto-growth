import requests
import os
import json
import random
import sys

# --- CONFIGURATION ---
LINKEDIN_TOKEN = os.environ["LINKEDIN_ACCESS_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

def get_user_urn():
    """
    Fetches the User ID using the OpenID Connect (OIDC) endpoint.
    This works with the 'openid' and 'profile' scopes.
    """
    # SWITCHED TO NEW ENDPOINT
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {LINKEDIN_TOKEN}"}
    
    print(f"🔍 Fetching User ID from: {url}")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        user_data = response.json()
        # 'sub' is the unique ID in OpenID. We must verify it exists.
        user_id = user_data.get('sub') 
        if user_id:
            # LinkedIn needs the ID in this specific format: urn:li:person:YOUR_ID
            final_urn = f"urn:li:person:{user_id}"
            print(f"✅ Found User URN: {final_urn}")
            return final_urn
        else:
            print(f"❌ Error: 'sub' ID not found in response: {user_data}")
            sys.exit(1)
    else:
        print(f"❌ FATAL: Could not fetch User ID. Status: {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)

def generate_viral_post():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = "Write a short, professional LinkedIn post (under 50 words) announcing that I am starting an automated AI experiment. Include 2 hashtags."
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    else:
        print(f"❌ AI Generation Failed: {response.text}")
        sys.exit(1)

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
                "shareCommentary": {
                    "text": content
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    
    print(f"🚀 Attempting to post to: {urn}")
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 201:
        print("✅ SUCCESS! Post is live.")
        print(f"Post ID: {response.json().get('id')}")
    else:
        print(f"❌ POST FAILED. Status: {response.status_code}")
        print(f"ERROR DETAILS: {response.text}")
        sys.exit(1)

if __name__ == "__main__":
    print("--- STARTING BOT ---")
    urn = get_user_urn()
    
    post_text = generate_viral_post()
    print("📝 Generated Content. Posting now...")
    
    post_to_linkedin(urn, post_text)
