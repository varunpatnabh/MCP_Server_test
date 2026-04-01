import os
import yfinance as yf
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.requests import Request
from starlette.responses import JSONResponse
import uvicorn

# ── FastMCP setup ─────────────────────────────────────────────────────────────
mcp = FastMCP("stock-info-server")

# ── Helper ────────────────────────────────────────────────────────────────────
def fmt(value, prefix="", suffix="", decimals=2):
    try:
        if value is None or (isinstance(value, float) and value != value):
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

# ── Ticker resolution ─────────────────────────────────────────────────────────
COMMON_TICKERS = {
    "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL", "alphabet": "GOOGL",
    "amazon": "AMZN", "tesla": "TSLA", "meta": "META", "facebook": "META",
    "nvidia": "NVDA", "netflix": "NFLX",
    "samsung": "005930.KS", "toyota": "TM", "sony": "SONY",
    "infosys": "INFY", "tata consultancy": "TCS.NS", "tcs": "TCS.NS",
    "wipro": "WIPRO.NS", "reliance": "RELIANCE.NS", "hdfc": "HDFCBANK.NS",
    "icici": "ICICIBANK.NS", "berkshire": "BRK-B", "jpmorgan": "JPM",
    "visa": "V", "mastercard": "MA", "disney": "DIS", "coca cola": "KO",
    "pepsi": "PEP", "nike": "NKE", "intel": "INTC", "amd": "AMD",
    "qualcomm": "QCOM", "ibm": "IBM", "salesforce": "CRM", "adobe": "ADBE",
    "paypal": "PYPL", "uber": "UBER", "airbnb": "ABNB", "spotify": "SPOT",
    "shopify": "SHOP", "zoom": "ZM",
}

def resolve_ticker(company: str) -> str:
    cleaned = company.strip().upper()
    if len(cleaned) <= 6 and cleaned.replace(".", "").replace("-", "").isalpha():
        return cleaned
    lower = company.strip().lower()
    if lower in COMMON_TICKERS:
        return COMMON_TICKERS[lower]
    return cleaned

def get_info(company: str):
    symbol = resolve_ticker(company)
    info = yf.Ticker(symbol).info
    return symbol, info

# ── Tools ─────────────────────────────────────────────────────────────────────
@mcp.tool()
def get_stock_info(company: str) -> str:
    """Get real-time stock price and key metrics. Pass company name like 'Apple' or ticker 'AAPL'."""
    try:
        symbol, info = get_info(company)
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

        change = ""
        if price and prev_close:
            delta = price - prev_close
            pct   = (delta / prev_close) * 100
            arrow = "▲" if delta >= 0 else "▼"
            change = f"{arrow} {abs(delta):.2f} ({abs(pct):.2f}%) vs prev close"

        return f"""
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
    except Exception as e:
        return f"❌ Error fetching data for '{company}': {e}"


@mcp.tool()
def get_company_financials(company: str) -> str:
    """Get detailed financials: revenue, net income, EPS, margins, debt, cash flow."""
    try:
        symbol, info = get_info(company)
        long_name     = info.get("longName") or symbol
        revenue       = info.get("totalRevenue")
        gross_profit  = info.get("grossProfits")
        net_income    = info.get("netIncomeToCommon")
        ebitda        = info.get("ebitda")
        eps           = info.get("trailingEps")
        profit_margin = info.get("profitMargins")
        op_margin     = info.get("operatingMargins")
        roe           = info.get("returnOnEquity")
        roa           = info.get("returnOnAssets")
        total_debt    = info.get("totalDebt")
        total_cash    = info.get("totalCash")
        free_cashflow = info.get("freeCashflow")
        employees     = info.get("fullTimeEmployees")
        description   = info.get("longBusinessSummary", "")
        if description and len(description) > 300:
            description = description[:300] + "…"

        return f"""
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
    except Exception as e:
        return f"❌ Error fetching financials for '{company}': {e}"


@mcp.tool()
def search_ticker(company_name: str) -> str:
    """Search for a stock ticker symbol by company name."""
    lower = company_name.lower()
    matches = {k: v for k, v in COMMON_TICKERS.items() if lower in k}
    if matches:
        lines = "\n".join(f"  {k.title():25} → {v}" for k, v in matches.items())
        return f"🔍 Ticker Search Results for '{company_name}':\n{lines}"
    return f"🔍 No match found for '{company_name}'. Try using the ticker directly."


@mcp.tool()
def compare_stocks(company1: str, company2: str) -> str:
    """Compare key metrics of two companies side by side."""
    try:
        sym1, i1 = get_info(company1)
        sym2, i2 = get_info(company2)

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

        n1 = (i1.get("shortName") or sym1)[:16]
        n2 = (i2.get("shortName") or sym2)[:16]

        return f"""
⚖️  STOCK COMPARISON
{'='*60}
  {'Metric':<22} {n1:<18} {n2}
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
    except Exception as e:
        return f"❌ Error comparing stocks: {e}"


# ── App: health route + FastMCP SSE mounted at "/" ────────────────────────────
async def health(request: Request):
    return JSONResponse({"status": "ok", "server": "stock-mcp-server"})

app = Starlette(
    routes=[
        Route("/health", endpoint=health),
        Mount("/", app=mcp.sse_app()),   # handles /sse and /messages/ correctly
    ]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)