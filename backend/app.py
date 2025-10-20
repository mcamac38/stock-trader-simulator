import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import socket

# Optional: psycopg2 for /dbcheck (OK if missing)
try:
    import psycopg2
except Exception:
    psycopg2 = None

app = Flask(__name__)

# Allow your Amplify frontend (set to your exact Amplify URL)
AMPLIFY_ORIGIN = os.getenv("AMPLIFY_ORIGIN", "https://main.d2bmkzvarvu1na.amplifyapp.com")
CORS(app, resources={r"/*": {"origins": [AMPLIFY_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"]}}, supports_credentials=True, allo>

# ---- Demo in-memory "DB" ----
USERS = {}      # username -> {password, full_name, email, role}
BALANCES = {}   # username -> float

USERS["mcamac38"] = {
    "password": "Finishthis",
    "full_name": "Matthew Camacho",
    "email": "mcamac38@asu.edu",
    "role": "admin"
}
BALANCES["mcamac38"] = 10000.0

@app.route("/")
def home():
    return jsonify({
        "message": "Stock Trader API is running",
        "endpoints": ["/health", "/dbcheck", "/auth/register", "/auth/login", "/account", "/cash/deposit"]
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok", "host": socket.gethostname()})

@app.route("/dbcheck")
def dbcheck():
    if psycopg2 is None:
        return jsonify(ok=False, error="psycopg2 not installed"), 500
    try:
        conn = psycopg2.connect(
            host=os.getenv("DATABASE_HOST"),
            port=os.getenv("DATABASE_PORT", "5432"),
            dbname=os.getenv("DATABASE_NAME", "postgres"),
            user=os.getenv("DATABASE_USER"),
            password=os.getenv("DATABASE_PASSWORD"),
            connect_timeout=3,
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                result = cur.fetchone()[0]
                return jsonify(ok=True, result=result)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

# ---- Auth helpers ----
def get_current_user():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    # For this demo, token == username
    if not token or token not in USERS:
	        return None
    u = USERS[token].copy()
    u["username"] = token
    return u

# ---- Auth endpoints ----
@app.route("/auth/register", methods=["POST"])
def register():
    body = request.get_json(force=True) or {}
    full_name = (body.get("full_name") or "").strip()
    username  = (body.get("username")  or "").strip()
    email     = (body.get("email")     or "").strip()
    password  = (body.get("password")  or "")

    if not username or username in USERS:
        return jsonify({"detail": "Username taken or invalid"}), 400

    USERS[username] = {
        "password": password,   # NOTE: plain text for demo only (hash later)
        "full_name": full_name,
        "email": email,
        "role": "user",
    }
    BALANCES[username] = 10000.0  # starter balance

    # For demo, token == username
    return jsonify({"access_token": username, "token_type": "bearer"})

@app.route("/auth/login", methods=["POST"])
def login():
    body = request.get_json(force=True) or {}
    username = (body.get("username") or "").strip()
    password = (body.get("password") or "")
    u = USERS.get(username)
    if not u or u["password"] != password:
        return jsonify({"detail": "Invalid credentials"}), 401
    # demo token == username
    return jsonify({"access_token": username, "token_type": "bearer"})

# ---- Protected endpoints ----
@app.route("/account", methods=["GET"])
def account():
    user = get_current_user()
    if not user:
        return jsonify({"detail": "Not authenticated"}), 401
    return jsonify({
        "username": user["username"],
        "full_name": user["full_name"],
        "email": user["email"],
        "role": user["role"],
        "cash_balance": BALANCES.get(user["username"], 0.0),
    })

@app.route("/cash/deposit", methods=["POST"])
def cash_deposit():
    user = get_current_user()
    if not user:
        return jsonify({"detail": "Not authenticated"}), 401

    body = request.get_json(force=True) or {}
    try:
        amount = float(body.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0.0

    if amount <= 0:
        return jsonify({"detail": "Amount must be > 0"}), 400

    BALANCES[user["username"]] = BALANCES.get(user["username"], 0.0) + amount
    return jsonify({"ok": True, "new_balance": BALANCES[user["username"]]})

@app.route("/cash/withdraw", methods=["POST"])
def cash_withdraw():
    user = get_current_user()
    if not user:
        return jsonify({"detail": "Not Authenticated"}), 401

    body = request.get_json(force=True) or {}
    try:
        amount = float(body.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0.0

    if amount <= 0:
        return jsonify({"detail": "Amount must be > 0"}), 400

    bal = BALANCES.get(user["username"], 0.0)
    if amount > bal:
        return jsonify({"detail": "Insufficient funds"}), 400

    BALANCES[user["username"]] = bal - amount
    return jsonify({"ok": True, "new_balance": BALANCES[user["username"]]})

@app.route("/admin/stocks", methods=["POST"])
def admin_create_stock():
    user = get_current_user()
    if not user:
        return jsonify({"detail": "Not Authenticated"}), 401
    #will restrict to admin only
    #if user.get("role") !="admin":
    #    return jsonify({"detail": "Forbidden"}), 403

    body = request.get_json(force=True) or {}

    #required fields
    ticker = (body.get("ticker") or "").strip().upper()
    company_name = (body.get("company_name") or "").strip()
    try:
        current_price = float(body.get("current_price", 0))
    except (TypeError, ValueError):
        current_price = 0.00

    if not ticker:
        return jsonify({"detail": "ticker is required"}), 400
    if not company_name:
        return jsonify({"detail": "company name required"}), 400
    if current_price <= 0:
        return jsonify({"detail": "current price must be > 0"}), 400

    #Optional fields
    volume = body.get("volume")
    if volume is not None:
        try:
            volume = int(volume)
        except (TypeError, ValueError):
            return jsonify({"detail": "volume must be an integer"}), 400
    sector = (body.get("sector") or "").strip() or None
    is_listed = bool(body.get("is_listed", True))

    #In-memory "DB"
    if "STOCKS" not in globals():
        globals()["STOCKS"] = {}
    if ticker in STOCKS:
        return jsonify({"detail": "ticker already exists"}), 400

    STOCKS[ticker] = {
        "ticker": ticker,
        "company_name": company_name,
        "current_price": float(current_price),
        "volume": volume if volume is not None else 0,
        "sector": sector,
        "is_listed": is_listed,
        "created_by": user["username"],
    }

    return jsonify(STOCKS[ticker]), 201

if __name__ == "__main__":
    # Only used if you run app.py directly; systemd runs gunicorn
    from os import getenv
    app.run(host="0.0.0.0", port=int(getenv("PORT", "8000")))