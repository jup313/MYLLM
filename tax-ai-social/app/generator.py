import os
from dotenv import load_dotenv
from app.llm import generate_from_llm
from app.compliance import compliance_check, add_disclaimer_if_needed
from app.database import save_post

load_dotenv()

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")

FIRM_NAME = os.getenv("FIRM_NAME", "JP Services PSL")
FIRM_LOCATION = os.getenv("FIRM_LOCATION", "Port Saint Lucie, FL")


def build_contact_block():
    """Build the contact footer block from .env settings."""
    if os.getenv("INCLUDE_CONTACT_BLOCK", "true").lower() != "true":
        return ""

    lines = []
    phone = os.getenv("FIRM_PHONE", "")
    email = os.getenv("FIRM_EMAIL", "")
    whatsapp = os.getenv("FIRM_WHATSAPP", "")
    website = os.getenv("FIRM_WEBSITE", "")
    address = os.getenv("FIRM_ADDRESS", "")
    fax = os.getenv("FIRM_FAX", "")
    instagram = os.getenv("FIRM_INSTAGRAM", "")
    facebook = os.getenv("FIRM_FACEBOOK", "")

    lines.append("\n\n📞 Contact Us:")
    if phone:    lines.append(f"📱 Phone: {phone}")
    if whatsapp: lines.append(f"💬 WhatsApp: {whatsapp}")
    if email:    lines.append(f"📧 Email: {email}")
    if website:  lines.append(f"🌐 Website: {website}")
    if address:  lines.append(f"📍 {address}")
    if fax:      lines.append(f"📠 Fax: {fax}")
    if instagram:lines.append(f"Instagram: {instagram}")
    if facebook: lines.append(f"Facebook: {facebook}")

    return "\n".join(lines) if len(lines) > 1 else ""


def load_prompt(filename):
    path = os.path.join(PROMPTS_DIR, filename)
    with open(path, "r") as f:
        return f.read()

def generate_post(platform, specialty):
    """
    Generate a single social media post.
    Returns dict with post_id, content, compliance result.
    """
    # Map to prompt file
    prompt_map = {
        ("instagram", "tax_prep"):        "instagram_tax_prep.txt",
        ("instagram", "tax_resolution"):  "instagram_tax_resolution.txt",
        ("instagram", "bookkeeping"):     "instagram_bookkeeping.txt",
        ("facebook",  "tax_prep"):        "facebook_tax_prep.txt",
        ("facebook",  "tax_resolution"):  "facebook_tax_resolution.txt",
        ("facebook",  "bookkeeping"):     "facebook_bookkeeping.txt",
        ("tiktok",    "tax_prep"):        "tiktok_script.txt",
        ("tiktok",    "tax_resolution"):  "tiktok_script.txt",
        ("tiktok",    "bookkeeping"):     "tiktok_script.txt",
    }

    prompt_file = prompt_map.get((platform, specialty))
    if not prompt_file:
        raise ValueError(f"No prompt for platform={platform} specialty={specialty}")

    prompt_template = load_prompt(prompt_file)
    
    # Inject specialty for TikTok (shared template)
    prompt = prompt_template.replace("{SPECIALTY}", specialty.replace("_", " ").title())
    prompt = prompt.replace("{FIRM_NAME}", FIRM_NAME)
    prompt = prompt.replace("{FIRM_LOCATION}", FIRM_LOCATION)

    # Generate content
    content = generate_from_llm(prompt)

    # Run compliance check
    result = compliance_check(content)

    # Add disclaimer if needed
    content = add_disclaimer_if_needed(content, result)

    # Append contact block
    contact_block = build_contact_block()
    if contact_block:
        content = content + contact_block

    # Save to DB
    post_id = save_post(platform, specialty, content, result["passed"])

    return {
        "post_id": post_id,
        "platform": platform,
        "specialty": specialty,
        "content": content,
        "compliance": result
    }


def generate_daily_batch():
    """
    Generate all 5 posts for the day:
    - 3 Instagram posts (one per specialty)
    - 1 Facebook post (tax_prep)
    - 1 TikTok script (rotates specialty)
    Returns list of results.
    """
    from datetime import date
    
    results = []
    errors = []

    tasks = [
        ("instagram", "tax_prep"),
        ("instagram", "tax_resolution"),
        ("instagram", "bookkeeping"),
        ("facebook",  "tax_prep"),
        ("tiktok",    "tax_resolution"),
    ]

    for platform, specialty in tasks:
        try:
            result = generate_post(platform, specialty)
            results.append(result)
            print(f"✅ Generated: {platform}/{specialty} (post #{result['post_id']})")
        except Exception as e:
            error_msg = f"❌ Failed {platform}/{specialty}: {str(e)}"
            errors.append(error_msg)
            print(error_msg)

    print(f"\n📊 Daily batch: {len(results)} generated, {len(errors)} failed")
    return results, errors
