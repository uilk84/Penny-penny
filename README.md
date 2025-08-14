
# PennyGems Screener — iPhone-ready (Yahoo + Telegram)

**Your settings:** Price $0.50–$3.00 • Yahoo Finance (free) • Pre‑market + All‑day • Telegram alerts.

## Run locally
```bash
pip install -r requirements.txt
export ENABLE_ALERTS=1
export TG_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
export TG_CHAT_ID=YOUR_CHAT_ID_HERE
python main.py
```
Open http://localhost:7860 — save to iPhone Home Screen.

## Deploy to Render
1) Create a new **Blueprint** service and point it at this folder (or a GitHub repo with these files).  
2) Set env vars:
   - `ENABLE_ALERTS=1`
   - `TG_BOT_TOKEN`
   - `TG_CHAT_ID`
3) Deploy. Copy the public URL and open it on your iPhone. It auto-refreshes and sends alerts every 60s.

## Customize
- Edit `symbols.csv` for your universe.
- Change thresholds from the UI header or via `/api/screener` params.
