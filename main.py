from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import screener  # your existing scanner logic

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

        # Run your existing scan logic from screener.py
        results = screener.run_scan(tickers)  # <-- Make sure screener.py has this function

        return jsonify({
            "status": "success",
            "count": len(results),
            "results": results
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
