# 🤖 MyLLM – Personal AI on Your Mac

Run your own private AI assistant locally using **Ollama**, **Open WebUI**, and **SearXNG**. No cloud, no subscriptions, no data leaving your machine.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Your Computer                     │
│                                                      │
│  ┌──────────────┐    ┌──────────────────────────┐   │
│  │   Ollama     │    │      Docker              │   │
│  │  (host)      │    │  ┌────────────────────┐  │   │
│  │              │◄───┤  │   Open WebUI       │  │   │
│  │  mistral:7b  │    │  │   :3000            │  │   │
│  │  deepseek    │    │  └────────────────────┘  │   │
│  │  coder:6.7b  │    │  ┌────────────────────┐  │   │
│  └──────────────┘    │  │   SearXNG          │  │   │
│                      │  │   :8080            │  │   │
│                      │  └────────────────────┘  │   │
│                      └──────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## 📋 Requirements

- **macOS** (Apple Silicon M1/M2/M3/M4 recommended) or Linux
- **Docker Desktop** – https://www.docker.com/products/docker-desktop/
- **8 GB RAM minimum** (16 GB recommended)
- **15 GB free disk space** (for models)
- Internet connection (for initial setup only)

## 🚀 Quick Start (New Computer)

### Step 1 – Clone the repo
```bash
git clone https://github.com/jup313/MYLLM.git
cd myllm
```

### Step 2 – Run setup
```bash
chmod +x setup.sh install-tools.sh
./setup.sh
```

This will:
- Install Ollama
- Download mistral:7b and deepseek-coder:6.7b models
- Start Open WebUI on http://localhost:3000
- Start SearXNG on http://localhost:8080

### Step 3 – Create your account
1. Open http://localhost:3000 in your browser
2. Click **Sign Up** and create your admin account
3. The first account created is automatically the admin

### Step 4 – Install the Shopping Search Tool
```bash
./install-tools.sh your@email.com yourpassword
```

## 🌐 Services

| Service | URL | Description |
|---------|-----|-------------|
| **Open WebUI** | http://localhost:3000 | Chat interface |
| **SearXNG** | http://localhost:8080 | Private search engine |
| **Ollama API** | http://localhost:11434 | LLM API |

## 🤖 AI Models

| Model | Size | Best For |
|-------|------|----------|
| `mistral:7b` | 4.4 GB | General chat, Q&A, web search |
| `deepseek-coder:6.7b` | 3.8 GB | Code generation, debugging |

### Pull additional models
```bash
ollama pull llama3.2        # Meta's Llama 3.2 (3B)
ollama pull phi4            # Microsoft Phi-4 (14B)
ollama pull qwen2.5-coder   # Qwen coding model
ollama list                 # See all installed models
```

## 🔍 Web Search

Web search is enabled by default via SearXNG. To use it in chat:
1. Click the **✨ sparkle icon** in the chat input box
2. Toggle **Web Search** ON
3. Ask any question – the AI will search the web for current info

## 🛒 Shopping Search Tool

Search Amazon, eBay, Temu, and AliExpress directly from chat:
1. Click the **✨ sparkle icon**
2. Click **Tools** → enable **Shopping Search Tool**
3. Ask: *"Find me wireless headphones under $50"*

## 🛑 Stop / Start Services

```bash
# Stop all services
docker compose down

# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Restart a specific service
docker compose restart open-webui
```

## 📁 Project Structure

```
myllm/
├── README.md                  # This file
├── docker-compose.yml         # Docker services config
├── setup.sh                   # One-command setup script
├── install-tools.sh           # Installs Shopping Search Tool
├── shopping_search_tool.py    # Shopping search tool code
└── searxng/
    └── settings.yml           # SearXNG configuration
```

## 🔧 Troubleshooting

### Ollama not connecting
```bash
# Check if Ollama is running
ollama list
# If not running, start it:
ollama serve
```

### Docker containers not starting
```bash
docker compose down
docker compose up -d
docker compose logs
```

### Web search not working
- Make sure SearXNG is running: http://localhost:8080
- In Open WebUI: Settings → Web Search → Engine: SearXNG
- URL: `http://searxng:8080/search?q=<query>&format=json`

### Port conflicts
If ports 3000 or 8080 are in use, edit `docker-compose.yml`:
```yaml
ports:
  - "3001:8080"   # Change 3000 to 3001
```

## 🔒 Privacy

Everything runs **100% locally**:
- No data sent to OpenAI, Anthropic, or any cloud
- SearXNG proxies searches anonymously
- Your conversations stay on your machine

---
Built with ❤️ using [Ollama](https://ollama.com) + [Open WebUI](https://github.com/open-webui/open-webui) + [SearXNG](https://github.com/searxng/searxng)
