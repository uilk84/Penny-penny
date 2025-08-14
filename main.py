
import os, threading, time
from flask import Flask, jsonify, request, render_template_string
from screener import load_universe, scan, DEFAULTS, send_telegram_alerts

APP_DIR = os.path.dirname(os.path.abspath(__file__))
UNIVERSE = load_universe(os.path.join(APP_DIR, "symbols.csv"))

app = Flask(__name__)

INDEX_HTML = """<!doctype html>
<html>
  <head>
    <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
    <title>PennyGems Screener</title>
    <style>
      :root { color-scheme: dark; }
      body { font-family: -apple-system, system-ui, Arial; background: #0d0f14; color: #e6e6e6; margin:0; }
      header { position: sticky; top:0; background:#0d0f14; padding:12px 16px; border-bottom:1px solid #222; }
      .row { display:flex; gap:8px; align-items:center; flex-wrap: wrap; }
      select, input, button { background:#151821; color:#e6e6e6; border:1px solid #333; border-radius:8px; padding:8px; }
      table { width:100%; border-collapse: collapse; }
      th, td { padding:8px; border-bottom:1px solid #222; text-align:left; font-size:14px; }
      .chip { padding:4px 8px; border-radius:999px; font-weight:600; font-size:12px;}
      .BUY { background:#164; color:#bfffc4; }
      .WATCH { background:#443; color:#f6e6a6; }
      .IGNORE { background:#333; color:#aaa; }
      .muted { color:#aaa; }
      .footer { padding:10px; text-align:center; color:#888; }
      a { color:#7fb3ff; text-decoration:none; }
    </style>
  </head>
  <body>
    <header>
      <div class="row">
        <strong>📊 PennyGems Screener</strong>
        <label>Session
          <select id="session">
            <option value="AUTO">Auto</option>
            <option value="PRE">Pre-Market</option>
            <option value="REG">Regular</option>
            <option value="POST">After Hours</option>
          </select>
        </label>
        <label>Price ≥ <input id="price_min" type="number" step="0.01" value="0.50" style="width:80px"></label>
        <label>Price ≤ <input id="price_max" type="number" step="0.01" value="3.00" style="width:80px"></label>
        <label>Pct ≥ REG<input id="pct_reg" type="number" step="0.1" value="10" style="width:60px"></label>
        <label>Pct ≥ PRE/POST<input id="pct_pre" type="number" step="0.1" value="5" style="width:60px"></label>
        <button onclick="refresh()">Run</button>
      </div>
    </header>
    <div style="padding:12px 16px">
      <table id="tbl"><thead>
        <tr><th>Ticker</th><th>Price</th><th>%</th><th>Vol</th><th>MktCap</th><th>RelVol</th><th>Score</th><th>Signal</th></tr>
      </thead><tbody></tbody></table>
      <div class="footer muted">Auto-refreshing every 30s · <a href="/api/screener" target="_blank">JSON API</a></div>
    </div>

    <script>
      async function refresh(){
        const session = document.getElementById('session').value;
        const price_min = document.getElementById('price_min').value;
        const price_max = document.getElementById('price_max').value;
        const pct_reg = document.getElementById('pct_reg').value;
        const pct_pre = document.getElementById('pct_pre').value;
        const url = `/api/screener?session=${session}&price_min=${price_min}&price_max=${price_max}&pct_min_regular=${pct_reg}&pct_min_premarket=${pct_pre}`;
        const res = await fetch(url);
        const data = await res.json();
        const tbody = document.querySelector('#tbl tbody');
        tbody.innerHTML = '';
        data.forEach(r => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td><a href="https://finance.yahoo.com/quote/${r.ticker}" target="_blank">${r.ticker}</a></td>
            <td>${(r.price ?? '').toFixed ? r.price.toFixed(4) : '-'}</td>
            <td>${(r.percent_change ?? '').toFixed ? r.percent_change.toFixed(2) : '-'}%</td>
            <td>${r.volume ? r.volume.toLocaleString() : '-'}</td>
            <td>${r.market_cap ? Math.round(r.market_cap/1e6) + 'M' : '-'}</td>
            <td>${r.rel_volume ? r.rel_volume.toFixed(2) : '-'}</td>
            <td>${r.breakout_score ?? '-'}</td>
            <td><span class="chip ${r.signal}">${r.signal}</span></td>
          `;
          tbody.appendChild(tr);
        });
      }
      refresh();
      setInterval(refresh, 30000);
    </script>
  </body>
</html>"""

@app.get("/")
def index():
    return render_template_string(INDEX_HTML)

@app.get("/api/screener")
def api_screener():
    session = request.args.get("session", "AUTO")
    params = dict(DEFAULTS)
    for p in ["price_min","price_max","pct_min_regular","pct_min_premarket","vol_min_regular","vol_min_premarket","mktcap_max"]:
        v = request.args.get(p)
        if v is not None:
            try: params[p] = float(v)
            except: pass
    data = scan(UNIVERSE, session=session, limits=params)
    return jsonify(data)

@app.get("/health")
def health():
    return {"ok": True}

def _alerts_loop():
    enable = os.getenv("ENABLE_ALERTS", "0") == "1"
    if not enable:
        return
    session = "AUTO"
    while True:
        try:
            results = scan(UNIVERSE, session=session)
            send_telegram_alerts(results, session=session)
        except Exception:
            pass
        time.sleep(60)

def _start_background():
    t = threading.Thread(target=_alerts_loop, daemon=True)
    t.start()

_start_background()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
