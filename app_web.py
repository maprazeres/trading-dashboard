from flask import Flask
import requests
from datetime import datetime

app = Flask(__name__)

NGROK_URL = "https://tragedy-evil-praying.ngrok-free.dev"

# TELEGRAM
BOT_TOKEN = "SEU_TOKEN"
CHAT_ID = "SEU_CHAT_ID"

# CONFIG
MIN_VOLUME = 5_000_000
MAX_SIGNALS = 5
MAX_AGE_HOURS = 16

# META
TARGET = 400
START_BALANCE = 364
TARGET_DATE = datetime(2026, 6, 30)

sent_signals = set()


def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass


# ================= META =================
def get_goal(current):
    days = max((TARGET_DATE - datetime.now()).days, 1)
    remaining = TARGET - current
    daily = remaining / days

    progress = ((current - START_BALANCE) / (TARGET - START_BALANCE)) * 100
    progress = max(0, min(progress, 100))

    return remaining, daily, progress


# ================= DADOS =================
def get_data():
    try:
        data = requests.get(f"{NGROK_URL}/data").json()

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

            risco = float(p["positionValue"])

            pos_list.append({
                "symbol": p["symbol"],
                "side": p["side"],
                "pnl": float(p["unrealisedPnl"]),
                "time": f"{hours:.1f}h",
                "risk": risco
            })

        pos_list.sort(key=lambda x: x["pnl"], reverse=True)

        return total, pnl, pos_list

    except:
        return 0, 0, []


# ================= LINK TRADINGVIEW =================
def tv_link(symbol):
    return f"https://www.tradingview.com/chart/?symbol=BYBIT:{symbol}&interval=240"


# ================= OPORTUNIDADES =================
def get_opportunities():
    coins = requests.get(
        "https://api.bybit.com/v5/market/tickers?category=linear"
    ).json()["result"]["list"]

    ranking = []

    for c in coins[:40]:
        try:
            change = float(c["price24hPcnt"]) * 100
            volume = float(c["turnover24h"])

            if volume < MIN_VOLUME:
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


# ================= ALERTA 8/21 =================
def get_signals_early():
    sinais = []

    coins = requests.get(
        "https://api.bybit.com/v5/market/tickers?category=linear"
    ).json()["result"]["list"]

    for c in coins[:25]:
        try:
            volume = float(c["turnover24h"])
            if volume < MIN_VOLUME:
                continue

            sym = c["symbol"]

            candles = requests.get(
                f"https://api.bybit.com/v5/market/kline?category=linear&symbol={sym}&interval=240&limit=30"
            ).json()["result"]["list"]

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


# ================= ELITE =================
def get_signals_elite():
    import pandas as pd

    sinais = []

    coins = requests.get(
        "https://api.bybit.com/v5/market/tickers?category=linear"
    ).json()["result"]["list"]

    for c in coins[:25]:
        try:
            volume = float(c["turnover24h"])
            if volume < MIN_VOLUME:
                continue

            sym = c["symbol"]

            candles = requests.get(
                f"https://api.bybit.com/v5/market/kline?category=linear&symbol={sym}&interval=240&limit=100"
            ).json()["result"]["list"]

            df = pd.DataFrame(candles, columns=["time","open","high","low","close","volume","turnover"]).astype(float)

            df["sma8"] = df["close"].rolling(8).mean()
            df["sma21"] = df["close"].rolling(21).mean()
            df["sma20"] = df["close"].rolling(20).mean()
            df["sma50"] = df["close"].rolling(50).mean()

            last = df.iloc[-1]
            prev = df.iloc[-2]

            t = datetime.fromtimestamp(last["time"]/1000)

            age = (datetime.now() - t).total_seconds()/3600
            if age > MAX_AGE_HOURS:
                continue

            if prev.sma8 < prev.sma21 and last.sma8 > last.sma21 and last.sma20 > last.sma50:
                sinais.append({"symbol": sym, "type": "LONG", "time": t})

            elif prev.sma8 > prev.sma21 and last.sma8 < last.sma21 and last.sma20 < last.sma50:
                sinais.append({"symbol": sym, "type": "SHORT", "time": t})

        except:
            continue

    return sinais[:MAX_SIGNALS]


# ================= APP =================
@app.route("/")
def home():

    total, pnl, pos = get_data()
    ranking = get_opportunities()
    early = get_signals_early()
    elite = get_signals_elite()

    faltando, por_dia, progresso = get_goal(total)

    # TELEGRAM
    for s in elite:
        key = f"{s['symbol']}_{s['type']}_{s['time']}"
        if key not in sent_signals:
            send_telegram(f"🎯 {s['symbol']} | {s['type']} | {s['time'].strftime('%H:%M')}")
            sent_signals.add(key)

    html = f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="60">
    </head>

    <body style="background:#0d1117;color:white;font-family:Arial;margin:10px">

    <<h2 style="text-align:center;margin-bottom:15px">
📊 Trading Dashboard PRO
</h2>

    <div style="
background:#161b22;
padding:12px;
margin-bottom:12px;
border-radius:10px;
">

<div style="font-size:16px;font-weight:bold;">
💰 Saldo: ${total:.2f}
</div>

<div style="margin-top:4px;">
📊 PnL: ${pnl:.2f}
</div>

<div style="margin-top:8px;border-top:1px solid #333;padding-top:6px;">
🎯 Falta: ${faltando:.2f}<br>
📅 ${por_dia:.2f}/dia<br>
📈 Progresso: {progresso:.1f}%
</div>

</div>


    
<h3 style="margin-top:20px;margin-bottom:10px;">
🚀 Oportunidades
</h3>

    """

    for c in ranking:
        html += f"""
    
    
<div style="
background:#161b22;
padding:14px;
margin:10px 0;
border-radius:12px;
border-left:6px solid {'#00ff88' if c['direction']=='LONG' else '#ff4d4d'};
box-shadow:0 0 10px rgba(0,0,0,0.4);
">

<div style="display:flex;align-items:center;gap:10px;">


<div style="font-size:18px;font-weight:bold;letter-spacing:0.5px;">
<a href="{tv_link(c['symbol'])}" target="_blank" style="color:white;text-decoration:none;">
{c['symbol']}
</a>
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


    <div style="margin-top:6px;font-size:14px;">
📈 {c['change']:.2f}%
</div>

<div style="margin-top:4px;color:#aaa;font-size:13px;">
💰 {c['volume']:,.0f}
</div>


    </div>
    """


    html += "<h3>⚡ Alerta Inicial</h3>"
    for s in early:
        html += f"<div><a href='{tv_link(s['symbol'])}'>{s['symbol']} | {s['type']}</a></div>"

    html += "<h3>🎯 Sinais Elite</h3>"
    for s in elite:
        html += f"<div><a href='{tv_link(s['symbol'])}'>{s['symbol']} | {s['type']} | {s['time'].strftime('%H:%M')}</a></div>"

    html += "<h3>💼 Posições</h3>"
    for p in pos:
        cor = "#0f0" if p["pnl"] >= 0 else "#f00"
        html += f"<div style='color:{cor}'>{p['symbol']} | {p['side']} | {p['pnl']:.2f} | {p['time']} | risco ${p['risk']:.0f}</div>"

    html += "</body></html>"

    return html


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
