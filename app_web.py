from flask import Flask, request
import requests
from pybit.unified_trading import HTTP
from dotenv import load_dotenv
import os
import json
from datetime import datetime, timedelta
import time

load_dotenv()

api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")

# ✅ TESTNET para não bloquear
session = HTTP(testnet=True, api_key=api_key, api_secret=api_secret)

app = Flask(__name__)

HISTORY_FILE = "history.json"


# =========================
# HISTÓRICO
# =========================
def save_history(balance):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    data = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)

    data.append({"date": now, "balance": balance})
    data = data[-200:]

    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f)


def get_performance():
    if not os.path.exists(HISTORY_FILE):
        return 0, 0

    with open(HISTORY_FILE, "r") as f:
        data = json.load(f)

    if len(data) < 2:
        return 0, 0

    last = data[-1]["balance"]

    cutoff = datetime.now() - timedelta(days=7)
    old = data[0]["balance"]

    for d in data:
        dt = datetime.strptime(d["date"], "%Y-%m-%d %H:%M")
        if dt < cutoff:
            old = d["balance"]

    growth = last - old
    pct = (growth / old * 100) if old != 0 else 0

    return growth, pct


# =========================
# CONTA (COM PROTEÇÃO ⛑️)
# =========================
def get_account_data():
    try:
        time.sleep(1)
        positions_resp = session.get_positions(category="linear", settleCoin="USDT")

        time.sleep(1)
        wallet_resp = session.get_wallet_balance(accountType="UNIFIED")

        positions = positions_resp['result']['list']
        wallet = wallet_resp['result']['list'][0]

        total_wallet = float(wallet['totalWalletBalance'])
        available = float(wallet['totalAvailableBalance'])

        total_pnl = 0
        results = []

        for pos in positions:
            size = float(pos['size'])
            if size == 0:
                continue

            pnl = float(pos['unrealisedPnl'])
            total_pnl += pnl

            results.append({
                "symbol": pos['symbol'],
                "tipo": pos['side'],
                "pnl": pnl
            })

        im_rate = float(wallet.get("accountIMRate", 0))
        used = im_rate * 100
        mmr = im_rate * 0.3 * 100

        return results, total_wallet, available, total_pnl, used, mmr

    except Exception as e:
        print("ERRO BYBIT:", e)
        return [], 0, 0, 0, 0, 0


# =========================
# MERCADO
# =========================
def get_market():
    try:
        coins = requests.get(
            "https://api.bybit.com/v5/market/tickers?category=linear"
        ).json()['result']['list']

        btc = next(
            (float(c['price24hPcnt']) * 100 for c in coins if c['symbol'] == "BTCUSDT"),
            0
        )

        ranking = []

        for c in coins:
            try:
                sym = c['symbol']
                change = float(c['price24hPcnt']) * 100
                vol = float(c['turnover24h'])
                price = float(c['lastPrice'])

                if sym == "BTCUSDT":
                    continue

                if price < 0.01 or vol < 10_000_000:
                    continue

                strength = change - btc

                if abs(strength) < 2 or abs(strength) > 15:
                    continue

                score = 1 + (abs(strength) > 5) + (abs(strength) > 10)

                if score < 3:
                    continue

                ranking.append({
                    "symbol": sym,
                    "direction": "LONG" if strength > 0 else "SHORT",
                    "strength": strength,
                    "score": score
                })

            except:
                continue

        ranking.sort(key=lambda x: abs(x["strength"]), reverse=True)

        return ranking[:5]

    except Exception as e:
        print("ERRO MARKET:", e)
        return []


# =========================
# APP
# =========================
@app.route("/")
def home():

    page = request.args.get("page", "main")

    pos, total, avail, pnl, used, mmr = get_account_data()
    ranking = get_market()

    save_history(total)
    growth, pct = get_performance()

    pnl_c = "#00ff88" if pnl >= 0 else "#ff4d4d"

    html = f"""
    <html>
    <body style="background:#0f0f0f;color:white;font-family:Segoe UI;">

    <div style="padding:10px;background:#111;">
        <a href="/?page=main">📊 Dashboard</a> |
        <a href="/?page=stats">📈 Performance</a>
    </div>
    """

    # ================= DASHBOARD =================
    if page == "main":

        html += f"""
        <div style="display:flex">

        <div style="width:30%;padding:15px">

        <div style="background:#1c1c1c;padding:15px">
        <h3>Conta</h3>
        ${total:.2f}<br>
        PnL: <span style="color:{pnl_c}">${pnl:.2f}</span><br>
        Uso {used:.2f}% | Risco {mmr:.2f}%
        </div>

        <div style="background:#1c1c1c;padding:15px;margin-top:10px">
        <h3>Posições</h3>
        """

        for p in pos:
            cor = "#00ff88" if p["pnl"] >= 0 else "#ff4d4d"

            html += f"""
            <div style="color:{cor}; font-size:13px;">
            {p['symbol']} | {p['tipo']} | ${p['pnl']:.2f}
            </div><br>
            """

        html += "</div></div>"

        # ========= oportunidades =========
        html += """
        <div style="width:70%;padding:15px">
        <h3>TOP 5 OPORTUNIDADES</h3>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;">
        """

        for c in ranking:
            cor = "#064" if c["direction"] == "LONG" else "#600"

            link = f"https://www.tradingview.com/chart/?symbol=BYBIT:{c['symbol']}&interval=240"

            html += f"""
            <div style="background:{cor};padding:10px">
            <a href="{link}" target="_blank">
            <b>{c['symbol']}</b>
            </a><br>

            {c['direction']} {c['strength']:.2f}%<br>
            Score {c['score']}
            </div>
            """

        html += "</div></div></div>"

    # ================= PERFORMANCE =================
    else:

        cor = "#00ff88" if growth >= 0 else "#ff4d4d"

        html += f"""
        <div style="padding:20px">
        <h2>Performance 7 dias</h2>

        <span style="color:{cor}">
        ${growth:.2f} ({pct:.2f}%)
        </span>
        </div>
        """

    html += "</body></html>"

    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)