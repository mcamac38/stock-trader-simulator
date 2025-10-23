import time, jwt, os
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import socket

#this is a secure way to securely transmit info as JSON
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"

#Helper for JWT
def make_token(username: str) -> str:
    now = int(time.time())
    payload = {"sub": username, "iat": now, "exp": now + 60*60}  # token expires in 1h
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def parse_token(auth_header):
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ",1)[1].strip()
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return data.get("sub")
    except Exception:
        return None

# Optional: psycopg2 for /dbcheck (OK if missing)
try:
    import psycopg2
except Exception:
    psycopg2 = None

# ---- DB Helpers ----
def get_db_connection():
    import psycopg2
    conn = psycopg2.connect(
        host=os.getenv("DATABASE_HOST"),
        port=os.getenv("DATABASE_PORT", "5432"),
        dbname=os.getenv("DATABASE_NAME"),
        user=os.getenv("DATABASE_USER"),
        password=os.getenv("DATABASE_PASSWORD")
    )
    return conn

def db_get_user_by_username(username: str):
    username = (username or "").strip()
    if not username:
        return None
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, username, email, full_name, password_hash, role, created_at
                    FROM users
                    WHERE username = %s
                """, (username,))
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0], "username": row[1], "email": row[2],
                    "full_name": row[3], "password_hash": row[4],
                    "role": row[5], "created_at": row[6]
                }
    finally:
        conn.close()

def db_create_user(full_name: str, username: str, email: str, password: str, role: str = "user"):
    username = (username or "").strip()
    email = (email or "").strip().lower()
    full_name = (full_name or "").strip()

    if not username or not email or not full_name or not password:
        raise ValueError("All fields are required")

    pw_hash = generate_password_hash(password)

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (username, email, full_name, password_hash, role)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, username, email, full_name, role, created_at
                """, (username, email, full_name, pw_hash, role))
                row = cur.fetchone()
                return {
                    "id": row[0], "username": row[1], "email": row[2],
                    "full_name": row[3], "role": row[4], "created_at": row[5]
                }
    except Exception as e:
        msg = str(e)
        if "users_username_key" in msg or "unique constraint" in msg.lower():
            raise ValueError("Username already exists")
        if "users_email_key" in msg:
            raise ValueError("Email already exists")
        raise
    finally:
        conn.close()

def db_deposit(user_id: str, amount: float) -> float:
    """Add to cash_balance; returns new balance."""
    import psycopg2
    conn = get_db_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                   SET cash_balance = cash_balance + %s
                 WHERE id = %s
             RETURNING cash_balance;
            """, (amount, user_id))
            row = cur.fetchone()
            if not row:
                raise ValueError("User not found")
            return float(row[0])

def db_withdraw(user_id: str, amount: float) -> float:
    """
    Subtract from cash_balance; returns new balance.
    Fails if balance would go negative.
    """
    import psycopg2
    conn = get_db_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                   SET cash_balance = cash_balance - %s
                 WHERE id = %s
                   AND cash_balance >= %s
             RETURNING cash_balance;
            """, (amount, user_id, amount))
            row = cur.fetchone()
            if not row:
                # Either user not found or insufficient funds
                raise ValueError("Insufficient funds")
            return float(row[0])

app = Flask(__name__)

# Allow your Amplify frontend (set to your exact Amplify URL)
AMPLIFY_ORIGIN = os.getenv("AMPLIFY_ORIGIN", "https://main.d2bmkzvarvu1na.amplifyapp.com")
CORS(app, resources={r"/*": {"origins": [AMPLIFY_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"]}}, supports_credentials=True, allow_headers=["Content-Type", "Authorization"], expose_headers=["Content-Type", "Authorization"], methods=["GET>

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
    """Extract current user from Authorization: Bearer <token>.
       Supports JWT (preferred) and legacy 'username as token' fallback."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    raw = auth.split(" ", 1)[1].strip()
    if not raw:
        return None

    # Try JWT first
    try:
        payload = jwt.decode(raw, JWT_SECRET, algorithms=[JWT_ALG])
        username = payload.get("sub")
        if not username:
            return None
        u = db_get_user_by_username(username)
        if not u:
            return None
        return {
            "id": u["id"],
            "username": u["username"],
            "email": u["email"],
            "full_name": u["full_name"],
            "role": u["role"],
        }
    except Exception:
        # Fallback: legacy demo token == username
        username = raw
        u = db_get_user_by_username(username)
        if not u:
            return None
        return {
            "id": u["id"],
            "username": u["username"],
            "email": u["email"],
            "full_name": u["full_name"],
            "role": u["role"],
        }

#def ensure_account(conn, user_id):
#   with conn.cursor() as cur:
#        cur.execute("""
#           INSERT INTO accounts (user_id, cash_balance)
#            VALUES (%s, 0)
#            ON CONFLICT (user_id) DO NOTHING;
#        """, (user_id,))

#def get_balance_db(conn, user_id):
#    with conn.cursor() as cur:
#        cur.execute("SELECT cash_balance FROM accounts WHERE user_id = %s;", (user_id,))
#        row = cur.fetchone()
#        return float(row[0]) if row else 0.0

#def deposit_db(conn, user_id, amount):
#    with conn.cursor() as cur:
#        # ensure row exists
#        cur.execute("""
#            INSERT INTO accounts (user_id, cash_balance)
#            VALUES (%s, 0)
#            ON CONFLICT (user_id) DO NOTHING;
#        """, (user_id,))
#        # add amount
#        cur.execute("""
#            UPDATE accounts
#            SET cash_balance = cash_balance + %s
#            WHERE user_id = %s
#            RETURNING cash_balance;
#        """, (amount, user_id))
#       return float(cur.fetchone()[0])

#def withdraw_db(conn, user_id, amount):
#    with conn.cursor() as cur:
#        # ensure row exists
#        cur.execute("""
#            INSERT INTO accounts (user_id, cash_balance)
#            VALUES (%s, 0)
#            ON CONFLICT (user_id) DO NOTHING;
#        """, (user_id,))
#        # subtract only if enough funds
#        cur.execute("""
#           UPDATE accounts
#            SET cash_balance = cash_balance - %s
#           WHERE user_id = %s AND cash_balance >= %s
#            RETURNING cash_balance;
#       """, (amount, user_id, amount))
#        row = cur.fetchone()
#        if not row:
#            return None  # insufficient funds
#        return float(row[0])

# ---- Auth endpoints ----
@app.route("/auth/register", methods=["POST"])
def register():
    body = request.get_json(force=True) or {}
    full_name = (body.get("full_name") or "").strip()
    username  = (body.get("username")  or "").strip()
    email     = (body.get("email")     or "").strip()
    password  = (body.get("password")  or "")

    if not username or not username or not email or not password:
        return jsonify({"detail": "All fields are required"}), 400

    try:
        user =db_create_user(full_name, username, email, password, role="user")
        token = make_token(user["username"])
        return jsonify({"access_token": token, "token_type": "bearer"}), 201
    except ValueError as ve:
        return jsonify({"detail": str(ve)}), 400
    except Exception as e:
        return jsonify({"detail": f"Registration failed: {e}"}), 500

@app.route("/auth/login", methods=["POST"])
def login():
    body = request.get_json(force=True) or {}
    username = (body.get("username") or "").strip()
    password = (body.get("password") or "")
    u = db_get_user_by_username(username)
    if not u:
        return jsonify({"detail": "Invalid credentials"}), 401

    if not check_password_hash(u["password_hash"], password):
        return jsonify({"detail": "Invalid credentials"}), 401

    token = make_token(username)
    return jsonify({"access_token": token, "token_type": "bearer"})

# ---- Protected endpoints ----
@app.route("/account", methods=["GET"])
def account():
    user = get_current_user()
    if not user:
        return jsonify({"detail": "Not authenticated"}), 401
    try:
        conn = get_db_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT cash_balance FROM users WHERE id = %s LIMIT 1;",
                    (user["id"],)
                )
                row = cur.fetchone()
                balance = float(row[0]) if row and row[0] is not None else 0.0
        return jsonify({
            "username":  user["username"],
            "full_name": user["full_name"],
            "email":     user["email"],
            "role":      user["role"],
            "cash_balance": balance,
        })
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@app.route("/cash/deposit", methods=["POST"])
def cash_deposit():
    user = get_current_user()
    if not user:
        return jsonify({"detail": "Not authenticated"}), 401

    body = request.get_json(force=True) or {}
    try:
        amount = float(body.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0.00

    if amount <= 0:
        return jsonify({"detail": "Amount must be > 0"}), 400

    try:
        new_balance = db_deposit(user["id"], amount)  # <-- use users-table helper
        return jsonify({"ok": True, "new_balance": new_balance})
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@app.route("/cash/withdraw", methods=["POST"])
def cash_withdraw():
    user = get_current_user()
    if not user:
        return jsonify({"detail": "Not Authenticated"}), 401

    body = request.get_json(force=True) or {}
    try:
        amount = float(body.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0.00

    if amount <= 0:
        return jsonify({"detail": "Amount must be > 0"}), 400

    try:
        new_balance = db_withdraw(user["id"], amount)  # <-- use users-table helper
        return jsonify({"ok": True, "new_balance": new_balance})
    except ValueError as ve:
        # raised by db_withdraw on insufficient funds
        return jsonify({"detail": str(ve)}), 400
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@app.route("/admin/stocks", methods=["POST"])
def admin_create_stock():
    user = get_current_user()
    if not user:
        return jsonify({"detail": "Not Authenticated"}), 401

    # restrict to admin
    role = (user.get("role") or "").strip().lower()
    if role != "admin":
        return jsonify({"detail": "Forbidden"}), 403

    body = request.get_json(force=True) or {}

    # required fields
    ticker = (body.get("ticker") or "").strip().upper()
    company_name = (body.get("company_name") or "").strip()
    try:
        current_price = float(body.get("current_price"))
    except (TypeError, ValueError):
        current_price = 0.0
    volume = body.get("volume")
    sector = (body.get("sector") or "").strip() or None
    is_listed = bool(body.get("is_listed", True))

    if not ticker or not company_name or current_price <= 0:
        return jsonify({"detail": "Ticker, company name, and positive current price required"}), 400

    try:
        conn = get_db_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO stocks (ticker, company_name, current_price, volume, sector, is_listed, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ticker) DO UPDATE
                      SET company_name = EXCLUDED.company_name,
                          current_price = EXCLUDED.current_price,
                          volume = COALESCE(EXCLUDED.volume, stocks.volume),
                          sector = COALESCE(EXCLUDED.sector, stocks.sector),
                          is_listed = EXCLUDED.is_listed,
                          created_by = EXCLUDED.created_by
                    RETURNING ticker, company_name, current_price, volume, sector, is_listed;
                """, (ticker, company_name, float(current_price), volume, sector, is_listed, user["id"]))
                t = cur.fetchone()

        return jsonify({
            "ticker": t[0],
            "company_name": t[1],
            "current_price": float(t[2]),
            "volume": t[3],
            "sector": t[4],
            "is_listed": t[5],
            "created_by": user["username"]
        }), 201
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@app.route("/market/tickers", methods=["GET"])
def list_tickers():
    """
    Returns a simple list of tradable tickers.
    Example item:
    { "ticker":"ACME", "company_name":"Acme Corp", "current_price": 99.99 }
    """
    try:
        conn = get_db_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ticker, company_name, current_price
                    FROM stocks
                    WHERE is_listed = TRUE
                    ORDER BY ticker ASC
                    LIMIT 500
                """)
                rows = cur.fetchall()
        conn.close()

        data = [
            {"ticker": r[0], "company_name": r[1], "current_price": float(r[2])}
            for r in rows
        ]
        return jsonify(data)
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@app.route("/market/tickers/<ticker>", methods=["GET"])
def get_ticker(ticker):
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return jsonify({"detail": "ticker required"}), 400
    try:
        conn = get_db_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ticker, company_name, current_price, volume, sector, is_listed, created_by, created_at
                    FROM stocks
                    WHERE ticker = %s
                """, (ticker,))
                row = cur.fetchone()
        conn.close()

        if not row:
            return jsonify({"detail": "Not found"}), 404

        return jsonify({
            "ticker": row[0],
            "company_name": row[1],
            "current_price": float(row[2]),
            "volume": row[3],
            "sector": row[4],
            "is_listed": row[5],
            "created_by": row[6],
            "created_at": row[7].isoformat() if row[7] else None
        })
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

if __name__ == "__main__":
    # Only used if you run app.py directly; systemd runs gunicorn
    from os import getenv
    app.run(host="0.0.0.0", port=int(getenv("PORT", "8000")))