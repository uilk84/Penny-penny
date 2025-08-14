from flask import Flask, jsonify
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def get_penny_stock_tickers():
    """
    Scrapes Finviz for penny stocks under $1 with volume > 500K.
    """
    url = "https://finviz.com/screener.ashx?v=111&f=sh_price_u1,sh_relvol_o0.5,sh_avgvol_o500&ft=4"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    tickers = []
    for a in soup.find_all("a", class_="screener-link-primary"):
        tickers.append(a.text.strip())

    return tickers

@app.route("/")
def home():
    return "✅ PennyGems Stock Scanner (Finviz Auto Mode) is running on Render!"

@app.route("/scan")
def scan():
    try:
        tickers = get_penny_stock_tickers()
        if not tickers:
            return jsonify({"status": "error", "message": "No tickers found"}), 500

        results = []

        for ticker in tickers:
            try:
                df = yf.download(ticker, period="5d", interval="1d")
                if df.empty:
                    continue

                # Breakout logic
                last_close = df["Close"].iloc[-1]
                prev_close = df["Close"].iloc[-2]
                change_pct = ((last_close - prev_close) / prev_close) * 100

                if change_pct > 5:
                    signal = "BUY"
                elif change_pct < -5:
                    signal = "SELL"
                else:
                    signal = "WATCH"

                results.append({
                    "ticker": ticker,
                    "last_close": round(last_close, 4),
                    "change_pct": round(change_pct, 2),
                    "signal": signal
                })

            except Exception as e:
                results.append({
                    "ticker": ticker,
                    "error": str(e)
                })

        return jsonify({
            "status": "success",
            "count": len(results),
            "results": results
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
