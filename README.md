# Stonks: A CS50x 2025 Finance Web App

![Dashboard Screenshot]![dashboard](https://github.com/user-attachments/assets/35caeace-3dcb-4bb0-a4f6-fb2753b7c062)


A Flask-based stock trading simulator and tracker leveraging real-time APIs and a rich feature set, built for educational and portfolio-management purposes.

## 🚀 Overview

**Stonks** is an interactive web application that allows users to:

* **Look up** real-time stock quotes (via AlphaVantage / FinancialModelingPrep)
* **Buy & sell** shares using simulated USD
* **Track holdings** with cost basis, unrealized P/L, and sector data
* **View transaction history** of all trades
* **Monitor market** prices in a refreshable watchlist
* **Read the latest finance news** from reliable RSS feeds and fallback
* **Toggle dark/light mode** with persistent preference
* **Enjoy animated dashboards** (count-ups, sparklines, live ticker)

Built on **Flask**, **Bootstrap 5**, **SQLite**, and **Chart.js**, Stonks demonstrates full-stack skills, API integration, UI/UX polish, and accessibility best practices.

---

## ✨ Key Features

1. **Portfolio Dashboard**

   * Animated count-up for cash & portfolio value
   * 30-day sparkline chart of portfolio performance
   * Live marquee ticker of top holdings
2. **Holdings & P/L**

   * Detailed cost basis, current price, unrealized gain/loss (\$ & %)
   * Sector breakdown via FinancialModelingPrep profiles
3. **Transaction History**

   * Chronological list of all buys and sells with timestamps and sectors
4. **Market Watch**

   * Customizable watchlist with auto-refresh every 15 seconds
   * Green/red badges for gainers and losers
5. **News Feed**

   * Unified output from NewsAPI.org, RSS (Reuters, NYT, BBC), and static demo
   * Responsive card grid with hover animation
6. **Dark/Light Mode**

   * Toggle stored in localStorage, styling via Bootstrap 5.3 themes
7. **Accessibility & Performance**

   * Semantic HTML, ARIA attributes, keyboard focus states
   * Caching for API calls, minimal JS bundle, pagination for history

---

## 📸 Screenshots

![Holdings Page]![holdings](https://github.com/user-attachments/assets/e08c54c9-c073-4b85-a6e0-1421e07c02be)

![History]![history](https://github.com/user-attachments/assets/fc57ad39-f7d6-4e3c-a72c-bb51aa657eed)

![Market Watch]!![market_watch](https://github.com/user-attachments/assets/cf551b2f-397f-4630-b14b-9a26c6fd5db3)


---

## 🛠️ Installation & Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/stonks.git
   cd stonks
   ```
2. **Create & activate a virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```
4. **Configure environment variables**
   Create a `.env` file:

   ```ini
   ALPHAVANTAGE_KEY=your_alpha_vantage_key
   FMP_KEY=your_fmp_key
   FLASK_APP=app.py
   FLASK_ENV=development
   ```
5. **Initialize the database**

   ```bash
   flask db upgrade  # or sqlite3 finance.db < schema.sql
   ```
6. **Run the app**

   ```bash
   flask run
   ```

Open `http://localhost:5000` and register a new account to get started.

---

## 📚 Usage

* **Register & Log In**: Create a user account to track your portfolio.
* **Quote**: Get the latest price and % change for any ticker.
* **Buy / Sell**: Execute market orders against live or paper cash.
* **Dashboard**: View animated summaries, sparklines, live ticker, and news.
* **Holdings**: Analyze positions with sector, cost basis, value, and P/L.
* **History**: Browse all past transactions with filters.
* **Market Watch**: Manage a watchlist for instant updates.
* **Theme Toggle**: Switch between light and dark UI modes.

---

## 🧪 Testing & CI

* Unit tests written with **pytest**, covering core helpers and routes.
* **GitHub Actions** runs linting, tests, and builds on every pull request.

To run tests locally:

```bash
pytest
```

---

## 🔐 Security & Best Practices

* **API Keys** stored in environment variables, never committed.
* **Password Hashing** via `werkzeug.security.generate_password_hash`.
* **CSRF protection** on forms using Flask-WTF.
* **Input Validation** and error handling with custom apology pages.

---

## ⚙️ Deployment

1. **Procfile** for Heroku or **Dockerfile** for containerization included.
2. Use managed database (Postgres) instead of SQLite in production.
3. Set environment variables on your host or CI/CD pipeline.
4. Enable HTTPS with Let’s Encrypt or cloud provider certs.

---

## 🦆 Future Roadmap

* Two-factor authentication (TOTP) for login security
* Real-time order book via WebSockets (Flask-SocketIO)
* Advanced risk metrics: Volatility, Beta, Sharpe Ratio
* Export CSV/PDF reports for holdings and history
* Mobile app companion (React Native or Flutter)

---

## 📄 License & Contributing

This project is licensed under the MIT License. Contributions are welcome—please open issues or pull requests on GitHub.

---

*Happy trading!* 🚀


