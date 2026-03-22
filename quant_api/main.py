"""
Quant API - Financial data, signals, backtesting, and vector memory
Runs on port 8001 — called by Open WebUI LLM tools
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import ta
import chromadb
from chromadb.utils import embedding_functions
import json
import os
from datetime import datetime
from typing import Optional
from curl_cffi import requests as cffi_requests
import vectorbt as vbt

app = FastAPI(title="Quant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ChromaDB (Vector Database) ────────────────────────────────────────────────
chroma_client = chromadb.PersistentClient(path="/data/chromadb")
embed_fn = embedding_functions.DefaultEmbeddingFunction()
memory_collection = chroma_client.get_or_create_collection(
    name="quant_memory",
    embedding_function=embed_fn
)

# ── Models ────────────────────────────────────────────────────────────────────
class BacktestRequest(BaseModel):
    ticker: str
    strategy: str = "sma_crossover"
    start: str = "2022-01-01"
    end: Optional[str] = None
    fast: int = 20
    slow: int = 50

class MemoryRequest(BaseModel):
    text: str
    metadata: dict = {}

# ── Yahoo Finance direct calls (bypass yfinance 429 issues) ───────────────────
def _session():
    return cffi_requests.Session(impersonate="chrome110")

def _yf_chart(ticker: str, interval: str = "1d", range_: str = "1y") -> dict:
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?interval={interval}&range={range_}")
    r = _session().get(url)
    if r.status_code != 200:
        raise HTTPException(503, f"Yahoo Finance returned {r.status_code} for {ticker}")
    d = r.json()
    result = d.get("chart", {}).get("result")
    if not result:
        raise HTTPException(404, f"Ticker {ticker} not found")
    return result[0]

def _yf_summary(ticker: str) -> dict:
    url = (f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
           f"?modules=summaryDetail,defaultKeyStatistics,assetProfile,"
           f"financialData,calendarEvents")
    r = _session().get(url)
    if r.status_code != 200:
        return {}
    d = r.json()
    qs = d.get("quoteSummary", {}).get("result")
    if not qs:
        return {}
    merged = {}
    for module in qs:
        merged.update(module)
    return merged

def _chart_to_df(result: dict) -> pd.DataFrame:
    timestamps = result["timestamp"]
    q = result["indicators"]["quote"][0]
    df = pd.DataFrame({
        "Open": q.get("open", []),
        "High": q.get("high", []),
        "Low": q.get("low", []),
        "Close": q.get("close", []),
        "Volume": q.get("volume", []),
    }, index=pd.to_datetime(timestamps, unit="s", utc=True))
    df.dropna(subset=["Close"], inplace=True)
    return df

def get_ohlcv(ticker: str, period: str = "1y") -> pd.DataFrame:
    result = _yf_chart(ticker, interval="1d", range_=period)
    df = _chart_to_df(result)
    if df.empty:
        raise HTTPException(404, f"No price data for {ticker}")
    return df

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close = df["Close"]
    df["sma_20"]    = ta.trend.sma_indicator(close, window=20)
    df["sma_50"]    = ta.trend.sma_indicator(close, window=50)
    df["sma_200"]   = ta.trend.sma_indicator(close, window=200)
    df["ema_12"]    = ta.trend.ema_indicator(close, window=12)
    df["ema_26"]    = ta.trend.ema_indicator(close, window=26)
    df["rsi"]       = ta.momentum.rsi(close, window=14)
    macd_obj        = ta.trend.MACD(close)
    df["macd"]      = macd_obj.macd()
    df["macd_sig"]  = macd_obj.macd_signal()
    df["macd_hist"] = macd_obj.macd_diff()
    bb              = ta.volatility.BollingerBands(close)
    df["bb_high"]   = bb.bollinger_hband()
    df["bb_low"]    = bb.bollinger_lband()
    df["atr"]       = ta.volatility.average_true_range(df["High"], df["Low"], close)
    df["obv"]       = ta.volume.on_balance_volume(close, df["Volume"])
    return df

def _flat(d: dict, key: str):
    """Pull a value from Yahoo quoteSummary (handles {raw, fmt} dicts)"""
    v = d.get(key)
    if isinstance(v, dict):
        return v.get("raw")
    return v

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


@app.get("/quote/{ticker}")
def get_quote(ticker: str):
    """Real-time quote + key stats"""
    ticker = ticker.upper()
    result = _yf_chart(ticker, interval="1d", range_="5d")
    df = _chart_to_df(result)
    meta = result.get("meta", {})
    last = float(df["Close"].iloc[-1])
    prev = float(df["Close"].iloc[-2]) if len(df) > 1 else last
    chg  = last - prev
    pct  = chg / prev * 100 if prev else 0
    info = _yf_summary(ticker)
    sd   = info.get("summaryDetail", {})
    fp   = info.get("financialData", {})
    ap   = info.get("assetProfile", {})
    ks   = info.get("defaultKeyStatistics", {})
    return {
        "ticker": ticker,
        "price": round(last, 4),
        "change": round(chg, 4),
        "change_pct": round(pct, 2),
        "volume": int(df["Volume"].iloc[-1]),
        "market_cap": _flat(sd, "marketCap"),
        "pe_ratio": _flat(sd, "trailingPE"),
        "52w_high": _flat(sd, "fiftyTwoWeekHigh") or meta.get("fiftyTwoWeekHigh"),
        "52w_low":  _flat(sd, "fiftyTwoWeekLow")  or meta.get("fiftyTwoWeekLow"),
        "sector": ap.get("sector", "N/A"),
        "industry": ap.get("industry", "N/A"),
        "summary": ap.get("longBusinessSummary", "")[:500],
    }


@app.get("/indicators/{ticker}")
def get_indicators(ticker: str, period: str = "6mo"):
    """Technical indicators — latest values"""
    df = get_ohlcv(ticker.upper(), period)
    df = add_indicators(df)
    latest = df.iloc[-1]
    close  = float(latest["Close"])
    def v(col):
        val = latest.get(col)
        return round(float(val), 4) if val is not None and not pd.isna(val) else None
    signal, reasons = "NEUTRAL", []
    if v("sma_50"):
        if close > v("sma_50"):
            reasons.append("price above SMA50 (bullish)")
        else:
            reasons.append("price below SMA50 (bearish)")
    if v("rsi"):
        rsi = v("rsi")
        if rsi < 30:
            reasons.append(f"RSI={rsi} oversold (bullish)"); signal = "BUY"
        elif rsi > 70:
            reasons.append(f"RSI={rsi} overbought (bearish)"); signal = "SELL"
    if v("macd") is not None and v("macd_sig") is not None:
        if v("macd") > v("macd_sig"):
            reasons.append("MACD above signal (bullish)")
        else:
            reasons.append("MACD below signal (bearish)")
    return {
        "ticker": ticker.upper(),
        "price": close,
        "signal": signal,
        "reasons": reasons,
        "indicators": {
            "sma_20": v("sma_20"), "sma_50": v("sma_50"), "sma_200": v("sma_200"),
            "ema_12": v("ema_12"), "ema_26": v("ema_26"),
            "rsi": v("rsi"),
            "macd": v("macd"), "macd_signal": v("macd_sig"), "macd_hist": v("macd_hist"),
            "bb_high": v("bb_high"), "bb_low": v("bb_low"),
            "atr": v("atr"),
        },
    }


@app.get("/risk/{ticker}")
def get_risk(ticker: str, period: str = "1y", benchmark: str = "SPY"):
    """Risk metrics vs benchmark"""
    t_close = get_ohlcv(ticker.upper(), period)["Close"]
    b_close = get_ohlcv(benchmark.upper(), period)["Close"]
    t_ret = t_close.pct_change().dropna()
    b_ret = b_close.pct_change().dropna()
    aligned = pd.concat([t_ret, b_ret], axis=1).dropna()
    aligned.columns = ["asset", "bench"]
    cov = np.cov(aligned["asset"], aligned["bench"])
    beta  = cov[0, 1] / cov[1, 1]
    alpha = (aligned["asset"].mean() - beta * aligned["bench"].mean()) * 252
    sharpe = (t_ret.mean() / t_ret.std()) * np.sqrt(252)
    cum = (1 + t_ret).cumprod()
    drawdown = (cum - cum.cummax()) / cum.cummax()
    return {
        "ticker": ticker.upper(), "benchmark": benchmark.upper(),
        "beta": round(float(beta), 4),
        "alpha_annual": round(float(alpha), 4),
        "sharpe_ratio": round(float(sharpe), 4),
        "max_drawdown_pct": round(float(drawdown.min()) * 100, 2),
        "annual_volatility_pct": round(float(t_ret.std() * np.sqrt(252)) * 100, 2),
        "total_return_pct": round((float(cum.iloc[-1]) - 1) * 100, 2),
    }


@app.post("/backtest")
def run_backtest(req: BacktestRequest):
    """Backtest a trading strategy"""
    end = req.end or datetime.now().strftime("%Y-%m-%d")
    df = get_ohlcv(req.ticker.upper(), "5y")
    df = df[df.index >= pd.Timestamp(req.start, tz="UTC")]
    if df.empty:
        raise HTTPException(404, f"No data for {req.ticker} from {req.start}")
    close = df["Close"]
    if req.strategy == "sma_crossover":
        fast_ma = vbt.MA.run(close, req.fast)
        slow_ma = vbt.MA.run(close, req.slow)
        entries = fast_ma.ma_crossed_above(slow_ma)
        exits   = fast_ma.ma_crossed_below(slow_ma)
    elif req.strategy == "rsi":
        rsi_ind = vbt.RSI.run(close, 14)
        entries = rsi_ind.rsi_crossed_below(30)
        exits   = rsi_ind.rsi_crossed_above(70)
    elif req.strategy == "macd":
        macd_ind = vbt.MACD.run(close, 12, 26, 9)
        entries  = macd_ind.macd_crossed_above(macd_ind.signal)
        exits    = macd_ind.macd_crossed_below(macd_ind.signal)
    else:
        raise HTTPException(400, f"Unknown strategy: {req.strategy}")
    pf = vbt.Portfolio.from_signals(close, entries, exits, freq="D")
    stats = pf.stats()
    def s(key): return round(float(stats.get(key, 0)), 2)
    return {
        "ticker": req.ticker.upper(), "strategy": req.strategy,
        "start": req.start, "end": end,
        "total_return_pct": s("Total Return [%]"),
        "sharpe_ratio": round(float(stats.get("Sharpe Ratio", 0)), 4),
        "max_drawdown_pct": s("Max Drawdown [%]"),
        "num_trades": int(stats.get("Total Trades", 0)),
        "win_rate_pct": s("Win Rate [%]"),
        "buy_hold_return_pct": s("Benchmark Return [%]"),
    }


@app.get("/earnings/{ticker}")
def get_earnings(ticker: str):
    """Earnings & fundamentals"""
    ticker = ticker.upper()
    info   = _yf_summary(ticker)
    fd  = info.get("financialData", {})
    ks  = info.get("defaultKeyStatistics", {})
    sd  = info.get("summaryDetail", {})
    cal = info.get("calendarEvents", {})
    earnings_dates = cal.get("earnings", {}).get("earningsDate", [])
    next_date = str(earnings_dates[0].get("fmt", "N/A")) if earnings_dates else "N/A"
    def pct(key, src):
        v = _flat(src, key)
        return round(v * 100, 2) if v else None
    return {
        "ticker": ticker,
        "eps_trailing": _flat(ks, "trailingEps"),
        "eps_forward": _flat(ks, "forwardEps"),
        "revenue_ttm": _flat(fd, "totalRevenue"),
        "profit_margin": pct("profitMargins", fd),
        "revenue_growth": pct("revenueGrowth", fd),
        "earnings_growth": pct("earningsGrowth", fd),
        "next_earnings_date": next_date,
        "analyst_target_price": _flat(fd, "targetMeanPrice"),
        "recommendation": fd.get("recommendationKey"),
        "num_analysts": _flat(fd, "numberOfAnalystOpinions"),
    }


@app.get("/portfolio/risk")
def portfolio_risk(tickers: str, weights: Optional[str] = None, period: str = "1y"):
    """Multi-asset portfolio risk"""
    syms = [s.strip().upper() for s in tickers.split(",")]
    wts  = [float(w) for w in weights.split(",")] if weights else [1/len(syms)] * len(syms)
    prices = {s: get_ohlcv(s, period)["Close"] for s in syms}
    df_all = pd.DataFrame(prices).dropna()
    rets   = df_all.pct_change().dropna()
    wt     = np.array(wts)
    port_ret = (rets * wt).sum(axis=1)
    sharpe   = (port_ret.mean() / port_ret.std()) * np.sqrt(252)
    cov      = rets.cov() * 252
    port_var = float(wt @ cov.values @ wt)
    cum      = (1 + port_ret).cumprod()
    drawdown = (cum - cum.cummax()) / cum.cummax()
    return {
        "tickers": syms, "weights": wts,
        "portfolio_sharpe": round(float(sharpe), 4),
        "portfolio_annual_vol_pct": round(float(np.sqrt(port_var)) * 100, 2),
        "portfolio_max_drawdown_pct": round(float(drawdown.min()) * 100, 2),
        "portfolio_total_return_pct": round((float(cum.iloc[-1]) - 1) * 100, 2),
        "correlation_matrix": rets.corr().round(4).to_dict(),
    }


# ── Vector Memory ─────────────────────────────────────────────────────────────

@app.post("/memory/store")
def store_memory(req: MemoryRequest):
    doc_id = f"mem_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    memory_collection.add(
        documents=[req.text],
        metadatas=[{**req.metadata, "timestamp": datetime.now().isoformat()}],
        ids=[doc_id]
    )
    return {"stored": True, "id": doc_id}


@app.get("/memory/search")
def search_memory(q: str, n: int = 5):
    results = memory_collection.query(query_texts=[q], n_results=min(n, 10))
    docs  = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    return {"query": q, "results": [{"text": d, "meta": m} for d, m in zip(docs, metas)]}
