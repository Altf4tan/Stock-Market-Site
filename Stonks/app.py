import json, time
from dotenv import load_dotenv
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify, g, Response, stream_with_context
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_wtf import CSRFProtect
from decimal import Decimal, ROUND_HALF_UP
from helpers import apology, login_required, lookup, usd_cents, sector, get_finance_news

def positive_int(field: str, label: str):
    # Validate and convert input to positive integer
    try:
        n = int(field.strip())
        if n < 1:
            raise ValueError
        return n
    except ValueError:
        return apology(f"{label} must be a positive integer")

load_dotenv()
# Configure application
app = Flask(__name__)

# extra layer of protection for our website
app.config["SECRET_KEY"] = "e7c2d5b4c10f4fa89d7ba4355cfc84f9c04d2751b2f6d4d4e3c5a1be2f2a9dc5"
csrf = CSRFProtect(app)

# Custom filter
app.jinja_env.filters["usd"] = usd_cents

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.before_request
def load_user():
    # Store user id (or None) on flask.g for this request
    g.uid = session.get("user_id")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
@login_required
def index():
    news = get_finance_news(limit=5)
    return render_template("index.html", news=news)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        return render_template("buy.html")
    # validate symbol
    symbol = request.form.get("symbol").upper().strip()
    if not symbol:
        return apology("must provide symbol")

    shares_text = request.form.get("shares","")
    shares = positive_int(shares_text,"shares")

    # If positive_int() already returned an apology() Response,
    # it'll be a Response object, not an int ➜ just return it
    if not isinstance(shares, int):
        return shares

    # lookup current price
    quote = lookup(symbol)
    if quote is None:
        return apology("invalid symbol")
    price_d = Decimal(str(quote["price"]))
    price_c = int((price_d * 100).to_integral_value(ROUND_HALF_UP))
    total_c = shares * price_c

    # check if the user has enough cash
    cash_row = db.execute("SELECT cash FROM users WHERE id = ?", g.uid)
    cash = cash_row[0]["cash"]
    if total_c > cash:
        return apology("can't afford")

    # deduct cash
    db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", total_c, g.uid)

    # record the purchase
    db.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)", g.uid, symbol, shares, price_c)

    # let the user know and go back to portfolio
    flash("Bought!")
    return redirect("/")

@app.route("/history")
@login_required
def history():
    # Fetch all transactions for this user, newest first
    rows = db.execute("""SELECT symbol, shares, price, timestamp
                         FROM transactions
                         WHERE user_id = ?
                         ORDER BY timestamp DESC""", g.uid)

    # Augment each row with its sector
    history = []
    for tx in rows:
        history.append({
            "symbol":    tx["symbol"],
            "shares":    tx["shares"],
            "price":     tx["price"],
            "timestamp": tx["timestamp"],
            "sector":    sector(tx["symbol"])
        })

    return render_template("history.html", rows=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    # Forget any user_id
    session.clear()
    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":

        # Get the symbol the user typed
        symbol = request.form.get("symbol")

        # Check if user didn't type anything
        if not symbol:
            return apology("must provide symbol")

        # Look up the stock symbol
        stock = lookup(symbol)

        # Check if lookup failed
        if stock is None:
            return apology("invalid symbol")

        # If everything OK, show the user the price
        return render_template("quoted.html", stock=stock)
    else:
        # If GET(user just clicks Quote button), show the form
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # Get users data for submitting it to server
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Make sure user enters every field and has matching passwords
        if not username or not password or not confirmation:
            return apology("missing fields")
        if password != confirmation:
            return apology("passwords must match")

        # Generate a hash for password to store it into server
        hash_pw = generate_password_hash(password)

        # Store users information to server for recognizing the same user
        # and make sure the username is not taken
        try:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash_pw)
        except:
            return apology("username already taken")
        # Log the new user in
        rows = db.execute("SELECT id FROM users WHERE username = ?", username)
        session["user_id"] = rows[0]["id"]
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    # Show form with symbols
    if request.method == "GET":
        rows = db.execute("SELECT symbol, SUM(shares) AS total FROM transactions WHERE user_id = ? GROUP BY symbol HAVING total > 0", g.uid)
        symbols = [row["symbol"] for row in rows]
        return render_template("sell.html", symbols=symbols)

    # Handle submission (POST)
    symbol = request.form.get("symbol", "").upper().strip()
    if not symbol:
        return apology("must choose symbol")

    shares_text = request.form.get("shares", "")
    shares = positive_int(shares_text, "shares")
    if not isinstance(shares, int):
        return shares       # positive_int already returned apology()

    # How many shares does the user own?
    row = db.execute("SELECT SUM(shares) AS total FROM transactions WHERE user_id = ? AND symbol = ?", g.uid, symbol)
    owned = row[0]["total"] or 0
    if shares > owned:
        return apology("too many shares")

    # Current price
    quote = lookup(symbol)
    if quote is None:
        return apology("invalid symbol")
    price = quote["price"]          # swap to Decimal later
    price_d = Decimal(str(quote["price"]))
    price_c = int((price_d * 100).to_integral_value(ROUND_HALF_UP))
    proceeds_c = price_c * shares

    # Update portfolio and record sale
    db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", proceeds_c, g.uid)
    db.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)", g.uid, symbol, -shares, price_c)
    flash("Sold!")
    return redirect("/")

@app.route("/api/quotes")
@login_required
def api_quotes():
    """Return latest price & change% for the caller’s watchlist."""
    # Get watchlist symbols from database
    rows = db.execute("SELECT symbol FROM watchlist WHERE user_id = ?", g.uid)
    data = {}
    for row in rows:
        # Fetch current quote data for       each symbol
        quote = lookup(row["symbol"])
        if quote:
            # Structure response data
            data[row["symbol"]] = {
                "price": quote["price"], # Current price in dollars
                "change": quote["changePercent"] # Percentage change
            }
    return jsonify(data) # Return JSON for API consumers

@app.route("/watch", methods=["POST"])
@login_required
def watch():
    # Add a stock symbol to user's watchlist
    symbol = request.form.get("symbol", "").upper().strip()

    # Validate symbol exists
    if not lookup(symbol):
        return apology("invalid symbol")

    # Insert symbol if not already in watchlist
    db.execute("INSERT OR IGNORE INTO watchlist (user_id, symbol) VALUES(?, ?)", g.uid, symbol)
    return redirect("/market")

@app.route("/unwatch", methods=["POST"])
@login_required
def unwatch():
    # Remove a stock symbol from user's watchlist
    db.execute("DELETE FROM watchlist WHERE user_id = ? AND symbol = ?", g.uid, request.form.get("symbol"))
    return redirect("/market")

@app.route("/market")
@login_required
def market():
    # Display market data for user's watchlist

    # Retrieve watchlist symbols from database
    rows = db.execute("SELECT symbol FROM watchlist WHERE user_id = ?", g.uid)
    quotes = []
    for r in rows:
        # Get current quote for each symbol
        q = lookup(r["symbol"])
        if q:
            # Convert price to cents using decimal precision
            quotes.append({
                "symbol": r["symbol"],
                "price": int((Decimal(str(q["price"])) * 100).to_integral_value(ROUND_HALF_UP)),
                "change": q["changePercent"]
            })
    # Render market page with formatted quotes
    return render_template("market.html",quotes=quotes)

@app.route("/holdings")
@login_required
def holdings():
    # Get current user's cash balance in cents from database
    cash_c = db.execute(
        "SELECT cash FROM users WHERE id = ?", g.uid
    )[0]["cash"]

    # Retrieve all stock symbols where user has a positive share balance
    holdings = db.execute(
        """
        SELECT symbol, SUM(shares) AS total_shares
          FROM transactions
         WHERE user_id = ?
      GROUP BY symbol
        HAVING total_shares > 0
        """,
        g.uid,
    )

    positions = [] # List to hold processed position data
    grand_total_c = cash_c # Total portfolio value (cash + stocks) in cents

    # Process each holding to get current market data
    for h in holdings:
        symbol = h["symbol"]
        quote = lookup(symbol) # Get real-time stock data via API
        if not quote: # Skip if symbol lookup fails (e.g., delisted)
            continue

        # Convert price to cents using precise decimal arithmetic
        # Avoids floating point inaccuracies by using Decimal type
        price_c = int(
            (Decimal(str(quote["price"])) * 100)
            .to_integral_value(ROUND_HALF_UP)
        )
        value_c = price_c * h["total_shares"]

        # Build position dictionary with formatted data
        positions.append({
            "symbol":        symbol,
            "shares":        h["total_shares"],
            "price":         price_c,
            "value":         value_c,
            "changePercent": quote["changePercent"],
            "sector":        sector(symbol)
        })

        grand_total_c += value_c

    # Render template
    return render_template(
        "holdings.html",
        rows=[{
            "symbol":        p["symbol"],
            "shares":        p["shares"],
            "sector":        p["sector"],
            "price":         p["price"],        # in cents
            "value":         p["value"],        # in cents
            "changePercent": p["changePercent"]
        } for p in positions],
        cash= cash_c, # Cash balance in cents
        grand_total= grand_total_c # Total portfolio value in cents
    )

@app.route("/stream")
@login_required
def stream():
    def event_stream():
        # infinite loop: push updates every 10 seconds
        while True:
            time.sleep(10)
            # get all symbols the user owns
            rows = db.execute("""SELECT DISTINCT symbol
                              FROM transactions
                              WHERE user_id = ?""", g.uid)
            # lookup each symbol
            quotes = []
            for r in rows:
                q = lookup(r["symbol"])
                if q:
                    quotes.append({
                        "symbol": q["symbol"],
                        "changePercent": q["changePercent"]
                        })
            # send as SSE data
            yield f"data: {json.dumps(quotes)}\n\n"
    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream"
    )
