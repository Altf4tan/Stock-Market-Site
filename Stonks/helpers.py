import os, requests

from decimal import Decimal, ROUND_HALF_UP
from flask import redirect, render_template, session
from functools import wraps

# Source: https://www.alphavantage.co/
AV_KEY = os.getenv("SM923JHIKMXH3NOP")
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
    url = (
        "https://www.alphavantage.co/query"
        f"?function=GLOBAL_QUOTE&symbol={symbol}&apikey={AV_KEY}"
    )
    try:
        data = requests.get(url, timeout=6).json()["Global Quote"]
        price_d = Decimal(data["05. price"])
        prev_d  = Decimal(data["08. previous close"])
        pct     = float((price_d - prev_d) / prev_d) if prev_d else 0
        return {
            "name":  symbol.upper(),            # AV free tier lacks company name
            "price": float(price_d),
            "changePercent": pct,
            "symbol": symbol.upper(),
        }
    except (KeyError, ValueError, requests.RequestException):
        return None
def usd_cents(value_cents: int) ->str:
    #Format integer cents as $X,000.00
    return f"${value_cents / 100:,.2f}"
