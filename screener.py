
import os, math, time
from datetime import datetime
from typing import List, Dict, Any, Optional

import pandas as pd
import pytz
import yfinance as yf
import requests

US_EASTERN = pytz.timezone("US/Eastern")

DEFAULTS = {
    "price_min": 0.50,
    "price_max": 3.00,
    "pct_min_regular": 10.0,
    "pct_min_premarket": 5.0,
    "vol_min_regular": 500_000,
    "vol_min_premarket": 100_000,
    "mktcap_max": 300_000_000,
    "rel_vol_min": 1.5,
}

def _now_et():
    return datetime.now(US_EASTERN)

def _session_now() -> str:
    t = _now_et().time()
    if t >= datetime.strptime("16:00","%H:%M").time() and t <= datetime.strptime("20:00","%H:%M").time():
        return "POST"
    if t < datetime.strptime("09:30","%H:%M").time():
        return "PRE"
    if t <= datetime.strptime("16:00","%H:%M").time():
        return "REG"
    return "POST"

def load_universe(csv_path: str) -> List[str]:
    df = pd.read_csv(csv_path)
    return sorted(list(set([s.strip().upper() for s in df.iloc[:,0].dropna().tolist()])))

def _safe_float(x, default=None):
    try:
        return float(x)
    except Exception:
        return default

def fetch_snapshot(ticker: str, session: str) -> Optional[Dict[str, Any]]:
    try:
        tk = yf.Ticker(ticker)
        info = tk.fast_info
        prev_close = _safe_float(info.get("previous_close"))
        last_price = _safe_float(info.get("last_price") or info.get("last"))
        market_cap = _safe_float(info.get("market_cap"))
        day_volume = _safe_float(info.get("last_volume") or info.get("volume"))
        ten_day_avg_vol = _safe_float(info.get("ten_day_average_volume"))

        pct_change = None
        if prev_close and last_price:
            pct_change = ((last_price - prev_close) / prev_close) * 100.0

        rel_vol = None
        if ten_day_avg_vol and day_volume:
            rel_vol = day_volume / ten_day_avg_vol if ten_day_avg_vol > 0 else None

        return {
            "ticker": ticker,
            "price": last_price,
            "prev_close": prev_close,
            "percent_change": pct_change,
            "volume": int(day_volume) if day_volume is not None else None,
            "market_cap": market_cap,
            "rel_volume": rel_vol,
            "session": session
        }
    except Exception:
        return None

def breakout_score(s: Dict[str, Any]) -> int:
    score = 0.0
    pc = _safe_float(s.get("percent_change"), 0)
    score += max(0.0, min(pc, 50.0)) * 1.0
    rv = _safe_float(s.get("rel_volume"), 0) or 0
    score += max(0.0, min(rv, 3.0)) * 10.0
    price = _safe_float(s.get("price"), 0) or 0
    if 0.50 <= price <= 2.00:
        score += 10
    return int(round(min(score, 100.0)))

def classify_signal(s: Dict[str, Any], limits=DEFAULTS) -> str:
    score = breakout_score(s)
    rv = _safe_float(s.get("rel_volume"), 0) or 0
    price = _safe_float(s.get("price"), 0) or 0
    if limits["price_min"] <= price <= limits["price_max"]:
        if score >= 75 and rv >= limits["rel_vol_min"]:
            return "BUY"
        if score >= 55:
            return "WATCH"
    return "IGNORE"

def filter_row(s: Dict[str, Any], session: str, limits=DEFAULTS) -> bool:
    price = _safe_float(s.get("price"), None)
    pct = _safe_float(s.get("percent_change"), None)
    volume = s.get("volume") or 0
    mktcap = _safe_float(s.get("market_cap"), None)

    if price is None or pct is None:
        return False

    pct_min = limits["pct_min_regular"] if session=="REG" else limits["pct_min_premarket"]
    vol_min = limits["vol_min_regular"] if session=="REG" else limits["vol_min_premarket"]

    return (limits["price_min"] <= price <= limits["price_max"] and
            pct >= pct_min and
            (volume is not None and volume >= vol_min) and
            (mktcap is None or mktcap <= limits["mktcap_max"]))

def scan(universe: List[str], session: Optional[str]=None, limits=DEFAULTS) -> List[Dict[str, Any]]:
    if session is None or session == "AUTO":
        session = _session_now()

    results = []
    for sym in universe:
        snap = fetch_snapshot(sym, session)
        if not snap:
            continue
        if filter_row(snap, session, limits):
            sig = classify_signal(snap, limits)
            if sig != "IGNORE":
                snap["signal"] = sig
                snap["breakout_score"] = breakout_score(snap)
                results.append(snap)
        time.sleep(0.05)
    results.sort(key=lambda x: (x.get("percent_change") or -9999), reverse=True)
    return results

def send_telegram_alerts(items, session: str) -> int:
    token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    if not token or not chat_id or not items:
        return 0
    sent = set()
    state_path = os.getenv("ALERT_STATE_PATH", "alert_state.json")
    if os.path.exists(state_path):
        import json as _json
        try:
            sent = set(_json.load(open(state_path)).get("sent", []))
        except Exception:
            sent = set()
    new = 0
    today = datetime.now().strftime("%Y%m%d")
    for s in items[:20]:
        key = f"{session}:{s['ticker']}:{today}"
        if key in sent:
            continue
        text = (f"🔥 PennyGems {session} {s['signal']}\n"
                f"{s['ticker']} ${s['price']:.4f} ({s['percent_change']:.2f}%)\n"
                f"Vol {s['volume']:,} | MktCap {int((s['market_cap'] or 0)/1e6)}M | "
                f"RelVol {s.get('rel_volume') and round(s['rel_volume'],2)}\n"
                f"Score {s['breakout_score']}\n"
                f"https://finance.yahoo.com/quote/{s['ticker']}")
        try:
            requests.get(f"https://api.telegram.org/bot{token}/sendMessage",
                         params={"chat_id": chat_id, "text": text})
            sent.add(key); new += 1; time.sleep(0.2)
        except Exception:
            pass
    try:
        import json as _json
        _json.dump({"sent": list(sent)}, open(state_path,"w"))
    except Exception:
        pass
    return new
