#!/bin/bash
# ============================================================
# MyLLM – One-command setup script
# Installs Ollama + Open WebUI + SearXNG on macOS or Linux
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}"
echo "╔══════════════════════════════════════════╗"
echo "║        MyLLM – Personal AI Setup         ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# ── 1. Check Docker ──────────────────────────────────────────
echo -e "${YELLOW}[1/5] Checking Docker...${NC}"
if ! command -v docker &>/dev/null; then
  echo -e "${RED}Docker not found. Please install Docker Desktop first:${NC}"
  echo "  https://www.docker.com/products/docker-desktop/"
  exit 1
fi
echo "✅ Docker found: $(docker --version)"

# ── 2. Install Ollama ────────────────────────────────────────
echo -e "${YELLOW}[2/5] Installing Ollama...${NC}"
if command -v ollama &>/dev/null; then
  echo "✅ Ollama already installed: $(ollama --version 2>/dev/null || echo 'installed')"
else
  echo "Downloading Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
  echo "✅ Ollama installed"
fi

# ── 3. Start Ollama service ──────────────────────────────────
echo -e "${YELLOW}[3/5] Starting Ollama service...${NC}"
if pgrep -x "ollama" > /dev/null 2>&1; then
  echo "✅ Ollama already running"
else
  ollama serve &>/dev/null &
  sleep 3
  echo "✅ Ollama started"
fi

# ── 4. Pull AI models ────────────────────────────────────────
echo -e "${YELLOW}[4/5] Pulling AI models (this may take a while)...${NC}"
echo "Pulling mistral:7b (4.4 GB) – general purpose chat..."
ollama pull mistral:7b
echo "Pulling deepseek-coder:6.7b (3.8 GB) – code generation..."
ollama pull deepseek-coder:6.7b
echo "✅ Models ready"

# ── 5. Start Docker services ─────────────────────────────────
echo -e "${YELLOW}[5/5] Starting SearXNG + Open WebUI via Docker...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
docker compose up -d
echo "✅ Services started"

# ── 6. Install Shopping Search Tool ─────────────────────────
echo -e "${YELLOW}[6/6] Installing Shopping Search Tool...${NC}"
echo "Waiting for Open WebUI to be ready..."
for i in {1..30}; do
  if curl -s http://localhost:3000/health &>/dev/null; then
    break
  fi
  sleep 2
done

# Get admin token (first user created becomes admin)
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗"
echo "║                    SETUP COMPLETE! 🎉                   ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                          ║"
echo "║  Open WebUI (Chat):  http://localhost:3000               ║"
echo "║  SearXNG (Search):   http://localhost:8080               ║"
echo "║  Ollama API:         http://localhost:11434              ║"
echo "║                                                          ║"
echo "║  NEXT STEPS:                                             ║"
echo "║  1. Open http://localhost:3000 in your browser           ║"
echo "║  2. Create your admin account (first signup = admin)     ║"
echo "║  3. Run: ./install-tools.sh <email> <password>           ║"
echo "║     to install the Shopping Search Tool                  ║"
echo "║                                                          ║"
echo "║  MODELS AVAILABLE:                                       ║"
echo "║  • mistral:7b       – General chat + web search          ║"
echo "║  • deepseek-coder   – Code generation & debugging        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
