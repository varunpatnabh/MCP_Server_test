import asyncio
import json
import yfinance as yf
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
import uvicorn

# ── MCP Server setup ──────────────────────────────────────────────────────────
app = Server("stock-info-server")

# ── Helper ────────────────────────────────────────────────────────────────────
def fmt(value, prefix="", suffix="", decimals=2):
    """Safely format a numeric value."""
    try:
        if value is None or value != value:   # None or NaN
            return "N/A"
        if isinstance(value, (int, float)):
            if abs(value) >= 1_000_000_000_000:
                return f"{prefix}{value/1_000_000_000_000:.{decimals}f}T{suffix}"
            elif abs(value) >= 1_000_000_000:
                return f"{prefix}{value/1_000_000_000:.{decimals}f}B{suffix}"
            elif abs(value) >= 1_000_000:
                return f"{prefix}{value/1_000_000:.{decimals}f}M{suffix}"
            else:
                return f"{prefix}{value:,.{decimals}f}{suffix}"
        return str(value)
    except Exception:
        return "N/A"

# ── Tool definitions ──────────────────────────────────────────────────────────
@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_stock_info",
            description=(
                "Get real-time stock price and key metrics for a company. "
                "You can pass a company name (e.g. 'Apple') or ticker symbol (e.g. 'AAPL')."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "company": {
                        "type": "string",
                        "description": "Company name or ticker symbol, e.g. 'Tesla' or 'TSLA'"
                    }
                },
                "required": ["company"]
            }
        ),
        Tool(
            name="get_company_financials",
            description=(
                "Get detailed financial data for a company: revenue, net income, EPS, "
                "profit margin, debt, and more."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "company": {
                        "type": "string",
                        "description": "Company name or ticker symbol"
                    }
                },
                "required": ["company"]
            }
        ),
        Tool(
            name="search_ticker",
            description="Search for a stock ticker symbol by company name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "The company name to search for, e.g. 'Microsoft'"
                    }
                },
                "required": ["company_name"]
            }
        ),
        Tool(
            name="compare_stocks",
            description="Compare key metrics of two companies side by side.",
            inputSchema={
                "type": "object",
                "properties": {
                    "company1": {"type": "string", "description": "First company name or ticker"},
                    "company2": {"type": "string", "description": "Second company name or ticker"}
                },
                "required": ["company1", "company2"]
            }
        )
    ]

# ── Ticker resolution ─────────────────────────────────────────────────────────
COMMON_TICKERS = {
    "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL",
    "amazon": "AMZN", "tesla": "TSLA", "meta": "META", "facebook": "META",
    "nvidia": "NVDA", "netflix": "NFLX", "twitter": "TWTR", "x": "TWTR",
    "samsung": "005930.KS", "toyota": "TM", "sony": "SONY",
    "infosys": "INFY", "tata": "TCS.NS", "tcs": "TCS.NS", "wipro": "WIPRO.NS",
    "reliance": "RELIANCE.NS", "hdfc": "HDFCBANK.NS", "icici": "ICICIBANK.NS",
    "berkshire": "BRK-B", "jpmorgan": "JPM", "visa": "V", "mastercard": "MA",
    "disney": "DIS", "coca cola": "KO", "pepsi": "PEP", "nike": "NKE",
    "intel": "INTC", "amd": "AMD", "qualcomm": "QCOM", "ibm": "IBM",
    "salesforce": "CRM", "adobe": "ADBE", "paypal": "PYPL", "uber": "UBER",
    "airbnb": "ABNB", "spotify": "SPOT", "shopify": "SHOP", "zoom": "ZM",
}

def resolve_ticker(company: str) -> str:
    """Try to resolve a company name to a ticker symbol."""
    cleaned = company.strip().upper()
    # If it looks like a ticker already (short, all caps, maybe with . or -)
    if len(cleaned) <= 6 and cleaned.replace(".", "").replace("-", "").isalpha():
        return cleaned
    # Check our map
    lower = company.strip().lower()
    if lower in COMMON_TICKERS:
        return COMMON_TICKERS[lower]
    # Try using yfinance search
    try:
        ticker = yf.Ticker(cleaned)
        info = ticker.info
        if info.get("regularMarketPrice") or info.get("currentPrice"):
            return cleaned
    except Exception:
        pass
    return cleaned   # fallback

def get_ticker_data(company: str):
    """Fetch yfinance info dict, returning (ticker_symbol, info_dict)."""
    symbol = resolve_ticker(company)
    ticker = yf.Ticker(symbol)
    info = ticker.info
    return symbol, info

# ── Tool handlers ─────────────────────────────────────────────────────────────
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:

    # ── get_stock_info ────────────────────────────────────────────────────────
    if name == "get_stock_info":
        company = arguments["company"]
        try:
            symbol, info = get_ticker_data(company)
            long_name   = info.get("longName") or info.get("shortName") or symbol
            currency    = info.get("currency", "USD")
            price       = info.get("currentPrice") or info.get("regularMarketPrice")
            prev_close  = info.get("previousClose") or info.get("regularMarketPreviousClose")
            day_high    = info.get("dayHigh") or info.get("regularMarketDayHigh")
            day_low     = info.get("dayLow") or info.get("regularMarketDayLow")
            week52_high = info.get("fiftyTwoWeekHigh")
            week52_low  = info.get("fiftyTwoWeekLow")
            volume      = info.get("volume") or info.get("regularMarketVolume")
            mkt_cap     = info.get("marketCap")
            pe_ratio    = info.get("trailingPE")
            div_yield   = info.get("dividendYield")
            exchange    = info.get("exchange") or info.get("fullExchangeName", "N/A")
            sector      = info.get("sector", "N/A")
            industry    = info.get("industry", "N/A")

            # Price change
            change = ""
            if price and prev_close:
                delta = price - prev_close
                pct   = (delta / prev_close) * 100
                arrow = "▲" if delta >= 0 else "▼"
                change = f"  {arrow} {abs(delta):.2f} ({abs(pct):.2f}%) vs prev close"

            result = f"""
📈 STOCK INFORMATION — {long_name} ({symbol})
{'='*55}
🏢 Exchange   : {exchange}
🏭 Sector     : {sector}
🏗️  Industry   : {industry}

💰 PRICE DATA
  Current Price   : {fmt(price, prefix=currency+' ')}
  Previous Close  : {fmt(prev_close, prefix=currency+' ')}
  Change          : {change}
  Day High        : {fmt(day_high, prefix=currency+' ')}
  Day Low         : {fmt(day_low, prefix=currency+' ')}
  52-Week High    : {fmt(week52_high, prefix=currency+' ')}
  52-Week Low     : {fmt(week52_low, prefix=currency+' ')}

📊 KEY METRICS
  Market Cap      : {fmt(mkt_cap, prefix='$')}
  P/E Ratio       : {fmt(pe_ratio, decimals=2)}
  Dividend Yield  : {fmt(div_yield*100 if div_yield else None, suffix='%', decimals=2)}
  Volume (today)  : {fmt(volume, decimals=0)}
""".strip()
            return [TextContent(type="text", text=result)]

        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error fetching data for '{company}': {e}")]

    # ── get_company_financials ────────────────────────────────────────────────
    elif name == "get_company_financials":
        company = arguments["company"]
        try:
            symbol, info = get_ticker_data(company)
            long_name       = info.get("longName") or symbol
            revenue         = info.get("totalRevenue")
            gross_profit    = info.get("grossProfits")
            net_income      = info.get("netIncomeToCommon")
            ebitda          = info.get("ebitda")
            eps             = info.get("trailingEps")
            profit_margin   = info.get("profitMargins")
            op_margin       = info.get("operatingMargins")
            roe             = info.get("returnOnEquity")
            roa             = info.get("returnOnAssets")
            total_debt      = info.get("totalDebt")
            total_cash      = info.get("totalCash")
            free_cashflow   = info.get("freeCashflow")
            employees       = info.get("fullTimeEmployees")
            description     = info.get("longBusinessSummary", "")
            if description and len(description) > 300:
                description = description[:300] + "…"

            result = f"""
💼 COMPANY FINANCIALS — {long_name} ({symbol})
{'='*55}
📝 About: {description}

💵 INCOME
  Total Revenue     : {fmt(revenue, prefix='$')}
  Gross Profit      : {fmt(gross_profit, prefix='$')}
  Net Income        : {fmt(net_income, prefix='$')}
  EBITDA            : {fmt(ebitda, prefix='$')}
  EPS (trailing)    : {fmt(eps, prefix='$', decimals=2)}

📉 MARGINS
  Profit Margin     : {fmt(profit_margin*100 if profit_margin else None, suffix='%')}
  Operating Margin  : {fmt(op_margin*100 if op_margin else None, suffix='%')}
  Return on Equity  : {fmt(roe*100 if roe else None, suffix='%')}
  Return on Assets  : {fmt(roa*100 if roa else None, suffix='%')}

🏦 BALANCE SHEET
  Total Debt        : {fmt(total_debt, prefix='$')}
  Total Cash        : {fmt(total_cash, prefix='$')}
  Free Cash Flow    : {fmt(free_cashflow, prefix='$')}

👥 Employees        : {f"{employees:,}" if employees else "N/A"}
""".strip()
            return [TextContent(type="text", text=result)]

        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error fetching financials for '{company}': {e}")]

    # ── search_ticker ─────────────────────────────────────────────────────────
    elif name == "search_ticker":
        company_name = arguments["company_name"]
        lower = company_name.lower()
        matches = {k: v for k, v in COMMON_TICKERS.items() if lower in k}
        if matches:
            lines = "\n".join(f"  {k.title():25} → {v}" for k, v in matches.items())
            result = f"🔍 Ticker Search Results for '{company_name}':\n{lines}"
        else:
            symbol = company_name.strip().upper()
            result = (
                f"🔍 No exact match found for '{company_name}'.\n"
                f"Try using the ticker directly. Common format: first few letters of name.\n"
                f"Attempted: {symbol}"
            )
        return [TextContent(type="text", text=result)]

    # ── compare_stocks ────────────────────────────────────────────────────────
    elif name == "compare_stocks":
        c1, c2 = arguments["company1"], arguments["company2"]
        try:
            sym1, i1 = get_ticker_data(c1)
            sym2, i2 = get_ticker_data(c2)

            def row(label, key, prefix="", suffix="", is_pct=False, decimals=2):
                v1 = i1.get(key)
                v2 = i2.get(key)
                if is_pct:
                    v1 = v1 * 100 if v1 else None
                    v2 = v2 * 100 if v2 else None
                return (
                    f"  {label:<22} {fmt(v1, prefix=prefix, suffix=suffix, decimals=decimals):<18} "
                    f"{fmt(v2, prefix=prefix, suffix=suffix, decimals=decimals)}"
                )

            n1 = i1.get("shortName") or sym1
            n2 = i2.get("shortName") or sym2
            header = f"  {'Metric':<22} {n1[:16]:<18} {n2[:16]}"

            result = f"""
⚖️  STOCK COMPARISON
{'='*60}
{header}
{'-'*60}
{row('Current Price',   'currentPrice',       prefix='$')}
{row('Market Cap',      'marketCap',           prefix='$')}
{row('P/E Ratio',       'trailingPE')}
{row('EPS',             'trailingEps',         prefix='$')}
{row('Revenue',         'totalRevenue',        prefix='$')}
{row('Net Income',      'netIncomeToCommon',   prefix='$')}
{row('Profit Margin',   'profitMargins',       suffix='%', is_pct=True)}
{row('Dividend Yield',  'dividendYield',       suffix='%', is_pct=True)}
{row('52W High',        'fiftyTwoWeekHigh',    prefix='$')}
{row('52W Low',         'fiftyTwoWeekLow',     prefix='$')}
{'='*60}
""".strip()
            return [TextContent(type="text", text=result)]

        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error comparing stocks: {e}")]

    return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]


# ── Starlette / SSE wiring ────────────────────────────────────────────────────
def create_starlette_app(mcp_server: Server) -> Starlette:
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp_server.run(
                streams[0], streams[1],
                mcp_server.create_initialization_options()
            )

    return Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
            Route("/health", endpoint=lambda r: __import__("starlette.responses", fromlist=["JSONResponse"]).JSONResponse({"status": "ok"})),
        ]
    )


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    starlette_app = create_starlette_app(app)
    uvicorn.run(starlette_app, host="0.0.0.0", port=port)
