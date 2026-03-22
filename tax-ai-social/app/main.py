import os
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

from app.database import init_db, get_drafts, get_all_posts, get_post, approve_post, reject_post, edit_post, mark_posted, mark_failed, get_stats
from app.llm import check_ollama_status
from app.poster import post_content, check_api_credentials
from app.scheduler import start_scheduler, get_next_run

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change_me")

# Initialize DB and start scheduler on startup
with app.app_context():
    init_db()

start_scheduler()

# ──────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

# ──────────────────────────────────────────
# API — Status
# ──────────────────────────────────────────

@app.route("/api/status")
def api_status():
    ollama = check_ollama_status()
    creds = check_api_credentials()
    stats = get_stats()
    return jsonify({
        "ollama": ollama,
        "meta_api": creds,
        "stats": stats,
        "next_generation": get_next_run(),
        "schedule": f"{os.getenv('SCHEDULE_HOUR','6')}:00 AM daily"
    })

# ──────────────────────────────────────────
# API — Posts
# ──────────────────────────────────────────

@app.route("/api/posts")
def api_posts():
    status_filter = request.args.get("status", None)
    posts = get_all_posts(limit=100)
    if status_filter:
        posts = [p for p in posts if p["status"] == status_filter]
    return jsonify(posts)

@app.route("/api/posts/drafts")
def api_drafts():
    return jsonify(get_drafts())

@app.route("/api/posts/<int:post_id>")
def api_get_post(post_id):
    post = get_post(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404
    return jsonify(post)

# ──────────────────────────────────────────
# API — Actions
# ──────────────────────────────────────────

@app.route("/api/posts/<int:post_id>/approve", methods=["POST"])
def api_approve(post_id):
    post = get_post(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    approve_post(post_id)

    # Auto-post if configured
    auto_post = os.getenv("AUTO_POST_ON_APPROVE", "true").lower() == "true"
    if auto_post:
        result = post_content(post["platform"], post["content"])
        if result.get("success"):
            mark_posted(post_id, result.get("post_id"))
            return jsonify({"success": True, "message": f"Approved and posted! Meta ID: {result.get('post_id')}", "meta_result": result})
        else:
            mark_failed(post_id, result.get("error", "Unknown error"))
            return jsonify({"success": False, "message": f"Approved but posting failed: {result.get('error')}", "meta_result": result})
    else:
        return jsonify({"success": True, "message": "Approved — post when ready"})

@app.route("/api/posts/<int:post_id>/reject", methods=["POST"])
def api_reject(post_id):
    data = request.get_json() or {}
    reason = data.get("reason", "")
    reject_post(post_id, reason)
    return jsonify({"success": True, "message": "Post rejected"})

@app.route("/api/posts/<int:post_id>/edit", methods=["POST"])
def api_edit(post_id):
    data = request.get_json() or {}
    new_content = data.get("content", "")
    if not new_content:
        return jsonify({"error": "Content required"}), 400
    edit_post(post_id, new_content)
    return jsonify({"success": True, "message": "Post updated"})

# ──────────────────────────────────────────
# API — Generate
# ──────────────────────────────────────────

@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json() or {}
    platform = data.get("platform")
    specialty = data.get("specialty")

    if not platform or not specialty:
        return jsonify({"error": "platform and specialty required"}), 400

    try:
        from app.generator import generate_post
        result = generate_post(platform, specialty)
        return jsonify({"success": True, "post": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/generate/batch", methods=["POST"])
def api_generate_batch():
    try:
        from app.generator import generate_daily_batch
        results, errors = generate_daily_batch()
        return jsonify({
            "success": True,
            "generated": len(results),
            "errors": errors,
            "posts": [{"post_id": r["post_id"], "platform": r["platform"], "specialty": r["specialty"]} for r in results]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ──────────────────────────────────────────
# API — Business Settings
# ──────────────────────────────────────────

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

SETTINGS_FIELDS = [
    "FIRM_NAME", "FIRM_LOCATION", "FIRM_SERVICES", "FIRM_AUDIENCE",
    "FIRM_PHONE", "FIRM_EMAIL", "FIRM_WHATSAPP", "FIRM_WEBSITE",
    "FIRM_ADDRESS", "FIRM_FAX", "FIRM_INSTAGRAM", "FIRM_FACEBOOK",
    "INCLUDE_CONTACT_BLOCK",
    "PAGE_ID", "PAGE_ACCESS_TOKEN", "INSTAGRAM_ACCOUNT_ID",
    "SCHEDULE_HOUR", "SCHEDULE_MINUTE", "OLLAMA_MODEL"
]

@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    settings = {k: os.getenv(k, "") for k in SETTINGS_FIELDS}
    return jsonify(settings)

@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    data = request.get_json() or {}
    try:
        # Read existing .env
        with open(ENV_PATH, "r") as f:
            lines = f.readlines()

        # Update or append each setting
        for key, value in data.items():
            if key not in SETTINGS_FIELDS:
                continue
            found = False
            for i, line in enumerate(lines):
                if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
                    lines[i] = f"{key}={value}\n"
                    found = True
                    break
            if not found:
                lines.append(f"{key}={value}\n")

        with open(ENV_PATH, "w") as f:
            f.writelines(lines)

        # Reload env vars into os.environ immediately
        for key, value in data.items():
            os.environ[key] = str(value)

        return jsonify({"success": True, "message": "Settings saved! Restart to apply schedule changes."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
