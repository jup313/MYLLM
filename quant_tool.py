"""
title: Quant AI Tool
author: MyLLM
description: Stock quotes, technical indicators, risk metrics, backtesting, earnings, portfolio analysis, and vector memory — all powered by a local Quant API.
version: 1.0.0
"""

import json
import httpx
from pydantic import BaseModel, Field
from typing import Optional

QUANT_API = "http://host.docker.internal:8001"

class Tools:

    # ── Quote ──────────────────────────────────────────────────────────────────
    def get_stock_quote(self, ticker: str) -> str:
        """
        Get a real-time stock quote with price, change, volume, P/E, market cap,
        52-week high/low, sector, and a short company description.
        :param ticker: Stock ticker symbol (e.g. AAPL, TSLA, NVDA)
        """
        try:
            r = httpx.get(f"{QUANT_API}/quote/{ticker.upper()}", timeout=15)
            d = r.json()
            lines = [
                f"📈 **{d['ticker']}** — ${d['price']} ({d['change_pct']:+.2f}%)",
                f"Volume: {d['volume']:,}",
                f"Market Cap: ${d['market_cap']:,}" if d.get('market_cap') else "",
                f"P/E: {d['pe_ratio']}" if d.get('pe_ratio') else "",
                f"52W High: ${d['52w_high']} | Low: ${d['52w_low']}",
                f"Sector: {d['sector']} | Industry: {d['industry']}",
                f"\n{d['summary']}" if d.get('summary') else "",
            ]
            return "\n".join(l for l in lines if l)
        except Exception as e:
            return f"Error fetching quote for {ticker}: {e}"

    # ── Technical Indicators ───────────────────────────────────────────────────
    def get_technical_indicators(self, ticker: str, period: str = "6mo") -> str:
        """
        Get technical analysis indicators: RSI, MACD, Bollinger Bands, SMA/EMA,
        ATR, and an overall BUY/SELL/NEUTRAL signal with reasoning.
        :param ticker: Stock ticker symbol (e.g. AAPL)
        :param period: Lookback period — 1mo, 3mo, 6mo, 1y, 2y (default: 6mo)
        """
        try:
            r = httpx.get(f"{QUANT_API}/indicators/{ticker.upper()}",
                          params={"period": period}, timeout=20)
            d = r.json()
            ind = d["indicators"]
            lines = [
                f"📊 **{d['ticker']}** Technical Analysis — Signal: **{d['signal']}**",
                "",
                "**Reasons:**",
                *[f"  • {reason}" for reason in d["reasons"]],
                "",
                f"**Moving Averages:**",
                f"  SMA20: {ind['sma_20']} | SMA50: {ind['sma_50']} | SMA200: {ind['sma_200']}",
                f"  EMA12: {ind['ema_12']} | EMA26: {ind['ema_26']}",
                "",
                f"**Momentum:**",
                f"  RSI(14): {ind['rsi']}",
                f"  MACD: {ind['macd']} | Signal: {ind['macd_signal']} | Hist: {ind['macd_hist']}",
                "",
                f"**Volatility:**",
                f"  BB High: {ind['bb_high']} | BB Low: {ind['bb_low']}",
                f"  ATR: {ind['atr']}",
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"Error getting indicators for {ticker}: {e}"

    # ── Risk ───────────────────────────────────────────────────────────────────
    def get_stock_risk_metrics(self, ticker: str, period: str = "1y", benchmark: str = "SPY") -> str:
        """
        Calculate risk metrics for a stock: Beta, Alpha, Sharpe Ratio,
        Max Drawdown, Annual Volatility, and Total Return vs benchmark.
        :param ticker: Stock ticker symbol
        :param period: 6mo, 1y, 2y, 5y (default: 1y)
        :param benchmark: Benchmark ticker (default: SPY)
        """
        try:
            r = httpx.get(f"{QUANT_API}/risk/{ticker.upper()}",
                          params={"period": period, "benchmark": benchmark}, timeout=20)
            d = r.json()
            return (
                f"⚠️ **{d['ticker']} Risk vs {d['benchmark']}** ({period})\n\n"
                f"Beta: {d['beta']}  |  Alpha (annual): {d['alpha_annual']}\n"
                f"Sharpe Ratio: {d['sharpe_ratio']}\n"
                f"Max Drawdown: {d['max_drawdown_pct']}%\n"
                f"Annual Volatility: {d['annual_volatility_pct']}%\n"
                f"Total Return: {d['total_return_pct']}%"
            )
        except Exception as e:
            return f"Error getting risk for {ticker}: {e}"

    # ── Backtest ───────────────────────────────────────────────────────────────
    def run_backtest(
        self,
        ticker: str,
        strategy: str = "sma_crossover",
        start: str = "2022-01-01",
        fast: int = 20,
        slow: int = 50,
    ) -> str:
        """
        Backtest a trading strategy on a stock.
        Strategies: sma_crossover (golden cross), rsi (oversold/overbought), macd (crossover).
        Returns total return, Sharpe ratio, max drawdown, number of trades, win rate.
        :param ticker: Stock ticker symbol
        :param strategy: sma_crossover | rsi | macd (default: sma_crossover)
        :param start: Start date YYYY-MM-DD (default: 2022-01-01)
        :param fast: Fast MA period for sma_crossover (default: 20)
        :param slow: Slow MA period for sma_crossover (default: 50)
        """
        try:
            payload = {"ticker": ticker, "strategy": strategy, "start": start,
                       "fast": fast, "slow": slow}
            r = httpx.post(f"{QUANT_API}/backtest", json=payload, timeout=60)
            d = r.json()
            return (
                f"🔬 **Backtest: {d['ticker']} — {d['strategy']}** ({d['start']} to {d['end']})\n\n"
                f"Total Return: **{d['total_return_pct']}%**  "
                f"(Buy & Hold: {d['buy_hold_return_pct']}%)\n"
                f"Sharpe Ratio: {d['sharpe_ratio']}\n"
                f"Max Drawdown: {d['max_drawdown_pct']}%\n"
                f"Trades: {d['num_trades']}  |  Win Rate: {d['win_rate_pct']}%"
            )
        except Exception as e:
            return f"Error running backtest: {e}"

    # ── Earnings ───────────────────────────────────────────────────────────────
    def get_earnings_summary(self, ticker: str) -> str:
        """
        Get earnings data: EPS (trailing & forward), revenue, profit margin,
        growth rates, next earnings date, analyst price target, and recommendation.
        :param ticker: Stock ticker symbol
        """
        try:
            r = httpx.get(f"{QUANT_API}/earnings/{ticker.upper()}", timeout=15)
            d = r.json()
            lines = [
                f"💰 **{d['ticker']} Earnings & Fundamentals**",
                f"EPS Trailing: {d['eps_trailing']}  |  EPS Forward: {d['eps_forward']}",
                f"Revenue (TTM): ${d['revenue_ttm']:,}" if d.get('revenue_ttm') else "",
                f"Profit Margin: {round(d['profit_margin']*100,2)}%" if d.get('profit_margin') else "",
                f"Revenue Growth: {round(d['revenue_growth']*100,2)}%" if d.get('revenue_growth') else "",
                f"Earnings Growth: {round(d['earnings_growth']*100,2)}%" if d.get('earnings_growth') else "",
                f"Next Earnings: {d['next_earnings_date']}",
                f"Analyst Target: ${d['analyst_target_price']}  |  Recommendation: {d['recommendation']}  ({d['num_analysts']} analysts)",
            ]
            return "\n".join(l for l in lines if l)
        except Exception as e:
            return f"Error fetching earnings for {ticker}: {e}"

    # ── Portfolio Risk ─────────────────────────────────────────────────────────
    def get_portfolio_risk(self, tickers: str, weights: Optional[str] = None, period: str = "1y") -> str:
        """
        Analyze a multi-asset portfolio: Sharpe, volatility, max drawdown,
        total return, and correlation matrix.
        :param tickers: Comma-separated tickers e.g. AAPL,MSFT,NVDA
        :param weights: Comma-separated weights e.g. 0.4,0.3,0.3 (optional, equal if omitted)
        :param period: 6mo, 1y, 2y (default: 1y)
        """
        try:
            params = {"tickers": tickers, "period": period}
            if weights:
                params["weights"] = weights
            r = httpx.get(f"{QUANT_API}/portfolio/risk", params=params, timeout=30)
            d = r.json()
            corr = d["correlation_matrix"]
            syms = d["tickers"]
            corr_lines = []
            for s1 in syms:
                row = "  " + s1 + ": " + "  ".join(f"{s2}={corr[s1][s2]:.2f}" for s2 in syms)
                corr_lines.append(row)
            return (
                f"📊 **Portfolio Risk Analysis** ({period})\n"
                f"Assets: {', '.join(syms)}\n"
                f"Weights: {', '.join(str(w) for w in d['weights'])}\n\n"
                f"Sharpe Ratio: {d['portfolio_sharpe']}\n"
                f"Annual Volatility: {d['portfolio_annual_vol_pct']}%\n"
                f"Max Drawdown: {d['portfolio_max_drawdown_pct']}%\n"
                f"Total Return: {d['portfolio_total_return_pct']}%\n\n"
                f"**Correlation Matrix:**\n" + "\n".join(corr_lines)
            )
        except Exception as e:
            return f"Error analyzing portfolio: {e}"

    # ── Vector Memory ──────────────────────────────────────────────────────────
    def save_trading_note(self, note: str, tags: str = "") -> str:
        """
        Save a trading insight, strategy, or note to the vector database
        so it can be recalled later with semantic search.
        :param note: The text to save (strategy, observation, thesis, etc.)
        :param tags: Optional comma-separated tags (e.g. momentum,NVDA,earnings)
        """
        try:
            payload = {"text": note, "metadata": {"tags": tags}}
            r = httpx.post(f"{QUANT_API}/memory/store", json=payload, timeout=10)
            d = r.json()
            return f"✅ Note saved to vector memory (id: {d['id']})"
        except Exception as e:
            return f"Error saving note: {e}"

    def search_trading_notes(self, query: str, n: int = 5) -> str:
        """
        Search your saved trading notes and strategies using semantic similarity.
        :param query: Natural language query (e.g. 'RSI strategy for tech stocks')
        :param n: Number of results to return (default: 5)
        """
        try:
            r = httpx.get(f"{QUANT_API}/memory/search",
                          params={"q": query, "n": n}, timeout=10)
            d = r.json()
            if not d["results"]:
                return "No matching notes found."
            lines = [f"🔍 **Search: '{query}'** — {len(d['results'])} result(s)\n"]
            for i, res in enumerate(d["results"], 1):
                lines.append(f"**{i}.** {res['text']}")
                if res["meta"].get("tags"):
                    lines.append(f"   Tags: {res['meta']['tags']}")
                lines.append(f"   Saved: {res['meta'].get('timestamp','')[:10]}")
                lines.append("")
            return "\n".join(lines)
        except Exception as e:
            return f"Error searching notes: {e}"
