# app.py — Flask trading simulator (±5–8% moves every 15 minutes)
from flask import Flask, request, jsonify
from flask_cors import CORS
import datetime, random

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["*"]}}, supports_credentials=False)

# --- Config ---
MIN_PRICE = 1.00
STEP_MIN = 0.05        # 5%
STEP_MAX = 0.08        # 8%
INTERVAL_MINUTES = 15  # how often prices are allowed to change

# Your tickers + starting prices
START_PRICES = {
    "AAPL": 268.90,
    "ACME": 37.80,
    "DIS": 111.88,
    "HD": 377.80,
    "LWS": 203.75,
    "NKI": 19.90,
    "NV": 206.88,
    "SMG": 384.70,
}

# Optional company display names (use ticker if not listed)
COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "DIS": "The Walt Disney Company",
    "HD": "The Home Depot, Inc.",
}

# --- In-memory state (resets on server restart) ---
_prices = START_PRICES.copy()
_last_update_time = {sym: None for sym in START_PRICES.keys()}
_cash_balance = 10_000.00


def apply_step_if_due(sym: str) -> None:
    """
    If at least INTERVAL_MINUTES have passed since the last update
    for this symbol, apply ONE random move (±5–8%).
    """
    now = datetime.datetime.utcnow()
    last = _last_update_time[sym]

    # First time: just mark timestamp, don't move yet (or do; your choice)
    if last is None:
        _last_update_time[sym] = now
        return

    elapsed_minutes = (now - last).total_seconds() / 60.0
    if elapsed_minutes < INTERVAL_MINUTES:
        # Too soon: no change
        return

    # Time to move: one hop between -8% and -5% OR +5% and +8%
    magnitude = random.uniform(STEP_MIN, STEP_MAX)
    direction = 1 if random.random() < 0.5 else -1
    pct = direction * magnitude

    new_price = _prices[sym] * (1 + pct)
    _prices[sym] = round(max(MIN_PRICE, new_price), 2)
    _last_update_time[sym] = now


@app.route("/market/tickers", methods=["GET"])
def list_tickers():
    """
    Returns current prices.
    Each symbol is allowed to move at most once per 15 minutes by ±5–8%.
    If you hit this endpoint multiple times within the same 15-min window,
    you'll see the same prices.
    """
    ts = datetime.datetime.utcnow().isoformat()
    rows = []
    for sym in list(_prices.keys()):
        apply_step_if_due(sym)
        rows.append({
            "ticker": sym,
            "company_name": COMPANY_NAMES.get(sym, sym),
            "current_price": _prices[sym],
            "ts": ts
        })
    return jsonify(rows)


# --- Minimal cash account ---
@app.route("/account", methods=["GET"])
def get_account():
    return jsonify({"cash_balance": round(_cash_balance, 2)})


@app.route("/cash/deposit", methods=["POST"])
def deposit():
    global _cash_balance
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0
    if amount <= 0:
        return jsonify({"error": "Amount must be greater than 0."}), 400
    _cash_balance = round(_cash_balance + amount, 2)
    return jsonify({"cash_balance": _cash_balance})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    # Run locally: python app.py
    app.run(host="0.0.0.0", port=8000, debug=True)
    
    
# ------------------------ Adjustments to you randomizer code to get it to work with our stack ------------------------    
# NOTE: keeping your constants exactly

def apply_step_if_due(sym, price, last_ts, now):
    if last_ts is None or (now - last_ts).total_seconds()/60.0 >= INTERVAL_MINUTES:
        magnitude = random.uniform(STEP_MIN, STEP_MAX)
        direction = 1 if random.random() < 0.5 else -1
        pct = direction * magnitude  # (you can insert a "none" branch here)
        new_price = round(max(MIN_PRICE, price * (1 + pct)), 2)
        return new_price, now
    return price, last_ts

def tick_due_prices_via_kayla():
    now = datetime.datetime.utcnow()
    with conn:
      cur.execute("""
        SELECT ticker, current_price, last_price_update
        FROM stocks
        WHERE is_listed = TRUE
        FOR UPDATE SKIP LOCKED
      """)
      for tkr, price, last_ts in cur.fetchall():
          new_price, new_ts = apply_step_if_due(tkr, float(price), last_ts, now)
          if new_price != price or last_ts is None:
              cur.execute("""
                UPDATE stocks
                SET current_price=%s, last_price_update=%s
                WHERE ticker=%s
              """, (new_price, now, tkr))
              

#Cons: Still need DB timestamps for durability; you can add a loop over all stocks each tick (fine for hundreds, less ideal for tens of thousands without filtering “due” first).