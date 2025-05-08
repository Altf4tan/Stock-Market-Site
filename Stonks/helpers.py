import os, requests

from decimal import Decimal, ROUND_HALF_UP
from flask import redirect, render_template, session
from functools import wraps

# Source: https://site.financialmodelingprep.com/
FMP_KEY = os.getenv("9kL9TKTMw97140buG8or4gboW2mNv3fr")

def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

def lookup(symbol):
    """
    Return latest price using FinancialModelingPrep.
    Falls back to a stub price if the API is down.
    """
    from time import time
    s = symbol.upper()

    # ---- tiny 15‑s cache so repeated refreshes don't spam the API ----
    if "_cache" not in lookup.__dict__:
        lookup._cache = {}
    price, ts = lookup._cache.get(s, (None, 0))
    if time() - ts < 15:
        return {"name": s, "price": price, "changePercent": 0.0, "symbol": s}

    url = f"https://financialmodelingprep.com/api/v3/quote-short/{s}?apikey={FMP_KEY}"
    try:
        data = requests.get(url, timeout=6).json()
        price = float(data[0]["price"])
    except Exception:
        # --- stub price if API fails or quota exceeded ---
        stub = {"AAPL": 180.12, "TSLA": 172.44, "IBM": 145.67}.get(s, 100.00)
        price = stub

    lookup._cache[s] = (price, time())
    return {"name": s, "price": price, "changePercent": 0.0, "symbol": s}

def usd_cents(value_cents: int) ->str:
    #Format integer cents as $X,000.00
    return f"${value_cents / 100:,.2f}"
