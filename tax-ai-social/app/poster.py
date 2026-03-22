import requests
import os
from dotenv import load_dotenv

load_dotenv()

PAGE_ID = os.getenv("PAGE_ID", "")
ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "")

def post_to_facebook(content):
    """Post text to Facebook Page feed."""
    if not PAGE_ID or not ACCESS_TOKEN:
        return {"success": False, "error": "Missing PAGE_ID or PAGE_ACCESS_TOKEN in .env"}
    
    url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/feed"
    payload = {
        "message": content,
        "access_token": ACCESS_TOKEN
    }
    try:
        r = requests.post(url, data=payload, timeout=30)
        data = r.json()
        if "id" in data:
            return {"success": True, "post_id": data["id"]}
        else:
            return {"success": False, "error": data.get("error", {}).get("message", str(data))}
    except Exception as e:
        return {"success": False, "error": str(e)}


def post_to_instagram(content, image_url=None):
    """
    Post to Instagram Business Account.
    Requires image_url for Instagram (text-only not supported by Meta API).
    If no image_url provided, returns instructions.
    """
    if not INSTAGRAM_ACCOUNT_ID or not ACCESS_TOKEN:
        return {"success": False, "error": "Missing INSTAGRAM_ACCOUNT_ID or PAGE_ACCESS_TOKEN in .env"}

    if not image_url:
        return {
            "success": False,
            "error": "Instagram requires an image. Save caption and post manually via Creator Studio.",
            "caption": content
        }

    # Step 1: Create media container
    container_url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}/media"
    container_payload = {
        "image_url": image_url,
        "caption": content,
        "access_token": ACCESS_TOKEN
    }
    try:
        r = requests.post(container_url, data=container_payload, timeout=30)
        container = r.json()
        if "id" not in container:
            return {"success": False, "error": container.get("error", {}).get("message", str(container))}
        
        container_id = container["id"]

        # Step 2: Publish media container
        publish_url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}/media_publish"
        publish_payload = {
            "creation_id": container_id,
            "access_token": ACCESS_TOKEN
        }
        r2 = requests.post(publish_url, data=publish_payload, timeout=30)
        publish_data = r2.json()
        if "id" in publish_data:
            return {"success": True, "post_id": publish_data["id"]}
        else:
            return {"success": False, "error": publish_data.get("error", {}).get("message", str(publish_data))}
    except Exception as e:
        return {"success": False, "error": str(e)}


def post_content(platform, content, image_url=None):
    """Route to correct posting function based on platform."""
    if platform == "facebook":
        return post_to_facebook(content)
    elif platform == "instagram":
        return post_to_instagram(content, image_url)
    elif platform == "tiktok":
        # TikTok posting requires video — save as script for manual use
        return {
            "success": False,
            "error": "TikTok requires video upload. This is a script — record your video manually.",
            "script": content
        }
    else:
        return {"success": False, "error": f"Unknown platform: {platform}"}


def check_api_credentials():
    """Verify Meta API credentials are configured."""
    issues = []
    if not PAGE_ID or PAGE_ID == "your_facebook_page_id":
        issues.append("PAGE_ID not set in .env")
    if not ACCESS_TOKEN or ACCESS_TOKEN == "your_long_lived_page_access_token":
        issues.append("PAGE_ACCESS_TOKEN not set in .env")
    if not INSTAGRAM_ACCOUNT_ID or INSTAGRAM_ACCOUNT_ID == "your_instagram_business_account_id":
        issues.append("INSTAGRAM_ACCOUNT_ID not set in .env (optional)")
    return {"configured": len(issues) == 0, "issues": issues}
