import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify, g
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_wtf import CSRFProtect
from decimal import Decimal, ROUND_HALF_UP
from helpers import apology, login_required, lookup, usd_cents

def positive_int(field: str, label: str):
    try:
        n = int(field.strip())
        if n < 1:
            raise ValueError
        return n
    except ValueError:
        return apology(f"{label} must be a positive integer")

# Configure application
app = Flask(__name__)

# extra layer of protection for our website
csrf = CSRFProtect(app)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

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
    # current cash in integer cents
    cash_c = db.execute(
        "SELECT cash FROM users WHERE id = ?", g.uid)[0]["cash"]

    # all symbols the user owns (>0 shares)
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

    positions = []
    grand_total_c = cash_c        # start with cash balance

    for h in holdings:
        quote = lookup(h["symbol"])
        if not quote:
            continue
        price_c = int((Decimal(str(quote["price"])) * 100).to_integral_value(ROUND_HALF_UP))
        value_c = price_c * h["total_shares"]
        positions.append(
            {
                "symbol": h["symbol"],
                "shares": h["total_shares"],
                "price": price_c,
                "total": value_c,
            }
        )
        grand_total_c += value_c

    return render_template(
        "index.html",
    rows=[{
        "symbol": p["symbol"],
        "shares": p["shares"],
        "price":  p["price"],        # cents
        "value":  p["total"]         # cents
        } for p in positions],
        cash=cash_c,
        grand_total=grand_total_c
    )

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
    # query all transactions for this user, newest first
    rows = db.execute("SELECT symbol, shares, price, timestamp FROM transactions WHERE user_id = ? ORDER BY timestamp DESC", g.uid)
    # render history template with that list
    return render_template("history.html", rows=rows)


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
    row = db.execute("SELECT symbol FROM watchlist WHERE user_id = ?", g.uid)
    data = {}
    for r in row:
        q = lookup(r["symbol"])
        if q:
            data[r["symbol"]] = {
                "price": q["price"],
                "change": q["changePercent"]
            }
    return jsonify(data)

@app.route("/watch", methods=["POST"])
@login_required
def watch():
    symbol = request.form.get("symbol", "").upper().strip()
    if not lookup(symbol):
        return apology("invalid symbol")
    db.execute("INSERT OR IGNORE INTO watchlist (user_id, symbol) VALUES(?, ?)", g.uid, symbol)
    return redirect("/market")

@app.route("/unwatch", methods=["POST"])
@login_required
def unwatch():
    db.execute("DELETE FROM watchlist WHERE user_id = ? AND symbol = ?", g.uid, request.form.get("symbol"))
    return redirect("/market")

@app.route("/market")
@login_required
def market():
    rows = db.execute("SELECT symbol FROM watchlist WHERE user_id = ?", g.uid)
    quotes = []
    for r in rows:
        q = lookup(r["symbol"])
        if q:
            quotes.append({
                "symbol": r["symbol"],
                "price": int((Decimal(str(q["price"])) * 100).to_integral_value(ROUND_HALF_UP)),
                "change": q["changePercent"]
            })
    return render_template("market.html",quotes=quotes)

