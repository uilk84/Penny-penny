def run_scan(tickers):
    """
    Accepts a list of tickers, runs the scanner, and returns results as a list of dicts.
    """
    import yfinance as yf
    import pandas as pd

    results = []
    for ticker in tickers:
        try:
            df = yf.download(ticker, period="5d", interval="1d")
            if df.empty:
                continue

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
            results.append({"ticker": ticker, "error": str(e)})

    return results
