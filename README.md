# 📈 Stock MCP Server

A free, public MCP server that provides real-time stock prices and company financials.  
Hosted on **Render** — no cost, accessible by anyone with the URL.

---

## 🛠️ Tools Available

| Tool | What it does |
|---|---|
| `get_stock_info` | Price, market cap, P/E, 52-week high/low, volume |
| `get_company_financials` | Revenue, net income, margins, debt, cash flow |
| `search_ticker` | Find ticker symbol by company name |
| `compare_stocks` | Side-by-side comparison of two companies |

---

## 🚀 Deploy to Render (Step-by-Step)

### Step 1 — Push to GitHub

1. Create a free account at https://github.com
2. Create a **new repository** (e.g. `stock-mcp-server`)
3. Upload these 3 files:
   - `server.py`
   - `requirements.txt`
   - `render.yaml`

```bash
# OR use git commands:
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/stock-mcp-server.git
git push -u origin main
```

---

### Step 2 — Deploy on Render

1. Go to https://render.com → Sign up free (use GitHub login)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account → Select your `stock-mcp-server` repo
4. Render auto-detects `render.yaml` — just click **"Deploy"**
5. Wait ~2 minutes for build to complete
6. Your URL will be: `https://stock-mcp-server.onrender.com`

---

### Step 3 — Connect Claude Desktop

Edit your Claude Desktop config file:

**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "stock-server": {
      "url": "https://stock-mcp-server.onrender.com/sse"
    }
  }
}
```

Restart Claude Desktop → you'll see the stock tools available!

---

### Step 4 — Share with Your Friend

Just send them your Render URL:
```
https://stock-mcp-server.onrender.com/sse
```

They add the same config block above to their Claude Desktop config.  
**That's it — they can use your server too!**

---

## 💬 Example Prompts

Once connected to Claude Desktop:

- *"What is Apple's current stock price?"*
- *"Show me Tesla's financials"*
- *"Compare Microsoft and Google stocks"*
- *"Search for Infosys ticker"*

---

## ⚠️ Free Tier Notes

- Render free tier **spins down after 15 minutes of inactivity**
- First request after sleep takes ~30 seconds (cold start)
- Upgrade to Render's $7/month plan for always-on
- yfinance data is delayed ~15 minutes for most markets

---

## 🔧 Local Testing (Optional)

```bash
pip install -r requirements.txt
python server.py
# Server runs at http://localhost:8000/sse
```
