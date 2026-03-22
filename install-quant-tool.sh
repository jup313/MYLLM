#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# install-quant-tool.sh
# Installs the Quant AI Tool into Open WebUI
# Usage: ./install-quant-tool.sh <email> <password>
# ─────────────────────────────────────────────────────────────────────────────

set -e

WEBUI_URL="http://localhost:3000"
TOOL_FILE="$(dirname "$0")/quant_tool.py"

if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: ./install-quant-tool.sh <email> <password>"
  echo "Example: ./install-quant-tool.sh admin@example.com mypassword"
  exit 1
fi

EMAIL="$1"
PASSWORD="$2"

echo "⏳ Logging in to Open WebUI..."
TOKEN=$(curl -s -X POST "$WEBUI_URL/api/v1/auths/signin" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed. Check your email and password."
  exit 1
fi
echo "✅ Logged in successfully"

echo "⏳ Installing Quant AI Tool..."
TOOL_CONTENT=$(cat "$TOOL_FILE")
RESULT=$(curl -s -X POST "$WEBUI_URL/api/v1/tools/create" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"quant_ai\",
    \"name\": \"Quant AI Tool\",
    \"meta\": {
      \"description\": \"Stock quotes, technical indicators, risk metrics, backtesting, earnings analysis, portfolio risk, and vector memory\"
    },
    \"content\": $(python3 -c "import json; print(json.dumps(open('$TOOL_FILE').read()))")
  }" 2>/dev/null)

if echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('id') else 1)" 2>/dev/null; then
  echo "✅ Quant AI Tool installed!"
else
  echo "⚠️  Tool may already exist or there was an error. Response: $(echo $RESULT | head -c 200)"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║           🏦 Quant AI Tool Installed!                    ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  In Open WebUI chat:                                     ║"
echo "║  1. Click the ✨ sparkle icon                            ║"
echo "║  2. Click Tools → enable Quant AI Tool                  ║"
echo "║                                                          ║"
echo "║  Example prompts:                                        ║"
echo "║  • 'Get me a quote for NVDA'                             ║"
echo "║  • 'Show technical indicators for AAPL'                  ║"
echo "║  • 'Backtest SMA crossover on TSLA since 2022'           ║"
echo "║  • 'Analyze portfolio risk for AAPL,MSFT,NVDA'          ║"
echo "║  • 'What are AMZN earnings and analyst targets?'         ║"
echo "╚══════════════════════════════════════════════════════════╝"
