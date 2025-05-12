import requests, time

from dotenv import load_dotenv
from decimal import Decimal
from flask import redirect, render_template, session
from functools import wraps
import xml.etree.ElementTree as ET

load_dotenv()

# Source: https://site.financialmodelingprep.com/
FMP_KEY = os.environ["9kL9TKTMw97140buG8or4gboW2mNv3fr"]
# Source https://newsapi.org
NEWSAPI_KEY = os.environ["0260f85285a54f17a11f63a677b2f4f6"]

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
    Decorator that ensures a user is logged in before accessing a route.
    Redirects to login page if not authenticated.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f) # Preserves original function's metadata (name, docstring, etc)
    def decorated_function(*args, **kwargs):
        # Check if user_id exists in the session (Flask's encrypted cookie storage)
        if session.get("user_id") is None:
            # User not logged in - redirect to login page
            return redirect("/login")
        # User is authenticated - execute original route function
        return f(*args, **kwargs)

    return decorated_function

def lookup(symbol):
    """
    Return latest price *and* day‑percent change using
    FinancialModelingPrep’s /quote endpoint.
    Falls back to a stub price if the API is down.
    """
    from time import time
    s = symbol.upper()

    # ---- 15‑s in‑memory cache ----
    # Initialize cache if it doesn't exist on the function object
    if "_cache" not in lookup.__dict__:
        lookup._cache = {}

    # Check for valid cached entry
    cached = lookup._cache.get(s)
    if cached and time() - cached["ts"] < 15:
        return cached["data"]

    url = f"https://financialmodelingprep.com/api/v3/quote/{s}?apikey={FMP_KEY}"
    try:
        # Attempt API request with timeout
        data = requests.get(url, timeout=6).json()[0]
        price = float(data["price"])
        # FMP returns raw percent already, e.g. 1.23 (not 0.0123)
        pct   = float(data["changesPercentage"]) / 100
    except Exception:
        # --- stub fallback ---
        stub_prices = {"AAPL": 180.12, "TSLA": 172.44, "IBM": 145.67}

        # Use stub price if available, otherwise default to $100.00
        price = stub_prices.get(s, 100.00)
        pct   = 0.0  # No percentage change in fallback mode

    # Prepare Result & Update Cache
    result = {
        "name": s,
        "price": price,
        "changePercent": pct,
        "symbol": s
    }
    
    # Store result in cache with current timestamp
    lookup._cache[s] = {"data": result, "ts": time()}
    return result

def usd_cents(value_cents: int) ->str:
    #Format integer cents as $X,000.00
    return f"${value_cents / 100:,.2f}"

# in-memory cache: symbol → (sector, timestamp)
_sector_cache = {}

def sector(symbol):
    # return company's sector, caching results for 24 h
    s = symbol.upper()
    # if we fetched this symbol less than 24 h ago, return the cached sector
    cached = _sector_cache.get(s)
    if cached and time.time() - cached[1] < 24 * 3600:
        return cached[0]
    # otherwise fetch from FMP
    try:
        url = f"https://financialmodelingprep.com/api/v3/profile/{s}?apikey={FMP_KEY}"
        data = requests.get(url, timeout=6).json()
        sector_name = data[0].get("sector", "—") if data else "—"
    except Exception:
        sector_name = "—"

    # cache & return
    _sector_cache[s] = (sector_name, time.time())
    return sector_name

def get_finance_news(limit=5):
    """
    Try NewsAPI.org (if you have a key), then Reuters RSS,
    then NYT RSS, then finally a static demo list.
    Returns a list of dicts with: title, url, site, publishedDate.
    """
    # 1) NewsAPI.org (JSON) ––– requires NEWSAPI_KEY in your helpers
    try:
        url = (
            "https://newsapi.org/v2/top-headlines"
            "?category=business"
            f"&pageSize={limit}"
            f"&apiKey={NEWSAPI_KEY}"
        )
        # Make API request with timeout
        res = requests.get(url, timeout=6)
        res.raise_for_status() # Raise exception for HTTP errors
        # Extract articles from JSON response
        articles = res.json().get("articles", [])
        if articles:
            # Transform NewsAPI format to our standard format
            return [
                {
                    "title":         art.get("title", "No title"),
                    "url":           art.get("url", "#"),
                    "site":          art.get("source", {}).get("name", "NewsAPI"),
                    "publishedDate": art.get("publishedAt", "")[:10]
                }
                for art in articles
            ]
    except Exception:
        pass # Silent failure to attempt fallback sources

    # 2) RSS fallbacks
    feeds = [
        ("Reuters",      "https://feeds.reuters.com/reuters/businessNews"),
        ("NYTimes",      "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"),
        ("BBC Business","http://feeds.bbci.co.uk/news/business/rss.xml"),
    ]
    for source, rss_url in feeds:
        try:
            # Fetch RSS feed
            r = requests.get(rss_url, timeout=6)
            r.raise_for_status()

            # Parse XML response
            root = ET.fromstring(r.content)
            # Find all items and limit to requested count
            items = root.findall(".//item")[:limit]
            if items:
                # Convert RSS items to standard format
                return [
                    {
                        "title":         it.findtext("title",        default="No title"),
                        "url":           it.findtext("link",         default="#"),
                        "site":          source,
                        "publishedDate": it.findtext("pubDate",       default="")[:16]
                    }
                    for it in items
                ]
        except Exception:
            continue # Try next feed if this one fails

    # Final fallback
    return [
        {
            "title":         "Markets open mixed amid economic worries",
            "url":           "#",
            "site":          "Demo",
            "publishedDate": "2025-05-12"
        },
        {
            "title":         "Tech stocks rally as earnings beat estimates",
            "url":           "#",
            "site":          "Demo",
            "publishedDate": "2025-05-11"
        },
        # … up to `limit` items …
    ][:limit]
