#!/bin/bash
# ============================================================
# install-tools.sh – Installs the Shopping Search Tool
# into Open WebUI via the API
#
# Usage: ./install-tools.sh <email> <password>
# Example: ./install-tools.sh admin@example.com mypassword
# ============================================================

set -e

EMAIL="${1}"
PASSWORD="${2}"

if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
  echo "Usage: ./install-tools.sh <email> <password>"
  echo "Example: ./install-tools.sh admin@example.com mypassword"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_FILE="$SCRIPT_DIR/shopping_search_tool.py"

if [ ! -f "$TOOL_FILE" ]; then
  echo "❌ shopping_search_tool.py not found in $SCRIPT_DIR"
  exit 1
fi

echo "🔐 Logging in to Open WebUI..."
TOKEN=$(curl -s -X POST "http://localhost:3000/api/v1/auths/signin" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed. Check your email and password."
  exit 1
fi
echo "✅ Logged in"

echo "🛒 Installing Shopping Search Tool..."
TOOL_CONTENT=$(python3 -c "import json; print(json.dumps(open('$TOOL_FILE').read()))")

RESULT=$(curl -s -X POST "http://localhost:3000/api/v1/tools/create" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"shopping_search\",
    \"name\": \"Shopping Search Tool\",
    \"meta\": {
      \"description\": \"Search Amazon, eBay, Temu, and AliExpress for products using SearXNG\"
    },
    \"content\": $TOOL_CONTENT
  }")

if echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('id') else 1)" 2>/dev/null; then
  echo "✅ Shopping Search Tool installed!"
  echo ""
  echo "To use it in chat:"
  echo "  1. Open http://localhost:3000"
  echo "  2. Click the ✨ sparkle icon in the chat box"
  echo "  3. Enable 'Shopping Search Tool'"
  echo "  4. Ask: 'Find me wireless headphones under \$50'"
else
  echo "⚠️  Tool may already exist or there was an error."
  echo "Response: $RESULT" | head -c 200
fi
