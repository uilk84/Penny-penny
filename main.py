from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ PennyGems Stock Scanner is running on Render!"

@app.route("/scan")
def scan():
    # Example placeholder for stock scan logic
    results = [
        {"ticker": "ABC", "signal": "BUY"},
        {"ticker": "XYZ", "signal": "SELL"}
    ]
    return jsonify({"status": "success", "results": results})

# Important: No app.run() — Gunicorn will handle running the server
