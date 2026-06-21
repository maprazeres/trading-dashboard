from flask import Flask
import requests
from datetime import datetime

app = Flask(__name__)

# ✅ sempre atualize se mudar o ngrok
NGROK_URL = "https://tragedy-evil-praying.ngrok-free.dev"


# ================= SAFE REQUEST =================
def safe_get(url):
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return None
        return res.json()
    except:
        return None


# ================= DADOS =================
def get_data():
    try:
        data = safe_get(f"{NGROK_URL}/data")
        if not data:
            return 0, 0, []

        wallet = data["wallet"]["result"]["list"][0]
        positions = data["positions"]["result"]["list"]

        total = float(wallet["totalWalletBalance"])
        pnl = float(wallet["totalPerpUPL"])

        pos_list = []

        for p in positions:
            if float(p["size"]) == 0:
                continue

            created = int(p["createdTime"])
            entry = datetime.fromtimestamp(created / 1000)
            hours = (datetime.now() - entry).total_seconds() / 3600

            pos_list.append({
                "symbol": p["symbol"],
                "side": p["side"],
                "pnl": float(p["unrealisedPnl"]),
                "time": f"{hours:.1f}h",
                "risk": float(p["positionValue"])
            })

        pos_list.sort(key=lambda x: x["pnl"], reverse=True)

        return total, pnl, pos_list

    except:
        return 0, 0, []


# ================= LINK =================
def tv_link(symbol):
    return f'<a href="https://www.tradingview.com/chart/?symbol=BYBIT:{symbol}&interval=240" target="_blank" style="color:white;text-decoration:none;">'


# ================= OPORTUNIDADES =================
def get_opportunities():
    try:
        data = safe_get("https://api.bybit.com/v5/market/tickers?category=linear")
        if not data:
            return []

        coins = data["result"]["list"]

        coins = sorted(coins, key=lambda x: float(x["turnover24h"]), reverse=True)

        ranking = []

        for c in coins[:40]:
            try:
                change = float(c["price24hPcnt"]) * 100
                volume = float(c["turnover24h"])

                if volume < 5_000_000:
                    continue
                if abs(change) < 2:
                    continue

                ranking.append({
                    "symbol": c["symbol"],
                    "direction": "LONG" if change > 0 else "SHORT",
                    "change": change,
                    "volume": volume
                })

            except:
                continue

        ranking.sort(key=lambda x: abs(x["change"]), reverse=True)
        return ranking[:6]

    except:
        return []


# ================= ALERTA =================
def get_signals_early():
    sinais = []

    try:
        data = safe_get("https://api.bybit.com/v5/market/tickers?category=linear")
        if not data:
            return []

        coins = data["result"]["list"]
        coins = sorted(coins, key=lambda x: float(x["turnover24h"]), reverse=True)

        for c in coins[:25]:
            try:
                volume = float(c["turnover24h"])
                if volume < 5_000_000:
                    continue

                sym = c["symbol"]

                k = safe_get(
                    f"https://api.bybit.com/v5/market/kline?category=linear&symbol={sym}&interval=240&limit=30"
                )

                if not k:
                    continue

                candles = k["result"]["list"]
                closes = [float(x[4]) for x in candles]

                sma8_prev = sum(closes[-9:-1]) / 8
                sma21_prev = sum(closes[-22:-1]) / 21

                sma8_now = sum(closes[-8:]) / 8
                sma21_now = sum(closes[-21:]) / 21

                t = datetime.fromtimestamp(int(candles[-1][0]) / 1000)

                if sma8_prev < sma21_prev and sma8_now > sma21_now:
                    sinais.append({"symbol": sym, "type": "LONG", "time": t})

                elif sma8_prev > sma21_prev and sma8_now < sma21_now:
                    sinais.append({"symbol": sym, "type": "SHORT", "time": t})

            except:
                continue

        return sinais[:5]

    except:
        return []


# ================= APP =================
@app.route("/")
def home():

    total, pnl, pos = get_data()
    ranking = get_opportunities()
    early = get_signals_early()

    html = f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="60">
    </head>

    <body style="background:#0d1117;color:white;font-family:Arial;margin:10px">

    <h2 style="text-align:center;margin-bottom:15px;">
    📊 Trading Dashboard PRO
    </h2>

    <div style="background:#161b22;padding:12px;border-radius:10px;margin-bottom:12px;">
    💰 ${total:.2f} | PnL: ${pnl:.2f}
    </div>

    <h3 style="margin-top:20px;">🚀 Oportunidades</h3>
    """

    for c in ranking:
        html += f"""
        <div style="
        background:#161b22;
        padding:14px;
        margin:10px 0;
        border-radius:12px;
        border-left:6px solid {'#00ff88' if c['direction']=='LONG' else '#ff4d4d'};
        ">

        <div style="display:flex;align-items:center;gap:10px;">

        <div style="font-size:18px;font-weight:bold;">
        {tv_link(c['symbol'])}{c['symbol']}</a>
        </div>

        <div style="
        font-size:12px;
        padding:2px 8px;
        border-radius:6px;
        background:{'#053d2a' if c['direction']=='LONG' else '#3d0505'};
        color:{'#00ff88' if c['direction']=='LONG' else '#ff4d4d'};
        font-weight:bold;
        ">
        {c['direction']}
        </div>

        </div>

        <div style="margin-top:6px;">📈 {c['change']:.2f}%</div>
        <div style="margin-top:4px;color:#aaa;">💰 {c['volume']:,.0f}</div>

        </div>
        """

    html += "<h3>⚡ Alerta Inicial</h3>"

    for s in early:
        html += f"""
        <div>
        {tv_link(s['symbol'])}{s['symbol']} | {s['type']}</a>
        </div>
        """

    html += "<h3>💼 Posições</h3>"

    for p in pos:
        cor = "#00ff88" if p["pnl"] >= 0 else "#ff4d4d"

        html += f"""
        <div style="color:{cor};margin-bottom:5px;">
        {p['symbol']} | {p['side']} | ${p['pnl']:.2f} | {p['time']} | risco ${p['risk']:.0f}
        </div>
        """

    html += "</body></html>"
    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)