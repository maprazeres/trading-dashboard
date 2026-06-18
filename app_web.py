from flask import Flask
import requests
import pandas as pd
from datetime import datetime

app = Flask(__name__)

NGROK_URL = "https://tragedy-evil-praying.ngrok-free.dev"

# 🎯 META
TARGET = 500
TARGET_DATE = datetime(2026, 6, 30)
START_BALANCE = 364


# ================= META =================
def get_goal(current):

    days = max((TARGET_DATE - datetime.now()).days, 1)
    remaining = TARGET - current
    daily = remaining / days

    progress = ((current - START_BALANCE) / (TARGET - START_BALANCE)) * 100
    progress = max(0, min(progress, 100))

    status = "✅ NO RITMO" if daily < 10 else "⚠️ ATRASADO"
    color = "#00ff88" if daily < 10 else "#ff4d4d"

    return remaining, daily, days, progress, status, color


# ================= SUPERTREND =================
def supertrend(df, period=10, multiplier=3):

    hl2 = (df['high'] + df['low']) / 2
    atr = (df['high'] - df['low']).rolling(period).mean()

    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr

    trend = [True]

    for i in range(1, len(df)):
        if df['close'].iloc[i] > upper.iloc[i - 1]:
            trend.append(True)
        elif df['close'].iloc[i] < lower.iloc[i - 1]:
            trend.append(False)
        else:
            trend.append(trend[i - 1])

    return trend[-1]


# ================= SMA CROSS =================
def detect_sma_cross(df):

    sma20_prev = df["sma20"].iloc[-2]
    sma50_prev = df["sma50"].iloc[-2]

    sma20_now = df["sma20"].iloc[-1]
    sma50_now = df["sma50"].iloc[-1]

    if sma20_prev < sma50_prev and sma20_now > sma50_now:
        return "LONG"

    if sma20_prev > sma50_prev and sma20_now < sma50_now:
        return "SHORT"

    return None


# ================= OPPORTUNITIES =================
def get_opportunities():
    try:
        coins = requests.get(
            "https://api.bybit.com/v5/market/tickers?category=linear",
            timeout=10,
        ).json()["result"]["list"]

        btc = next(
            (float(c["price24hPcnt"]) * 100 for c in coins if c["symbol"] == "BTCUSDT"),
            0,
        )

        ranking = []

        for c in coins:
            try:
                sym = c["symbol"]
                change = float(c["price24hPcnt"]) * 100
                vol = float(c["turnover24h"])
                price = float(c["lastPrice"])

                if sym == "BTCUSDT":
                    continue

                if price < 0.01 or vol < 5_000_000:
                    continue

                strength = change - btc

                if abs(strength) < 3 or abs(strength) > 15:
                    continue

                url = (
                    f"https://api.bybit.com/v5/market/kline?category=linear&"
                    f"symbol={sym}&interval=240&limit=60"
                )
                candles = requests.get(url, timeout=10).json()["result"]["list"]

                df = pd.DataFrame(
                    candles,
                    columns=[
                        "time", "open", "high", "low", "close",
                        "volume", "turnover",
                    ],
                )
                df = df.astype(float)

                if len(df) < 60:
                    continue

                df["sma20"] = df["close"].rolling(20).mean()
                df["sma50"] = df["close"].rolling(50).mean()

                cross = detect_sma_cross(df)
                st = supertrend(df)

                if cross == "LONG" and st:
                    direction = "LONG"
                elif cross == "SHORT" and not st:
                    direction = "SHORT"
                else:
                    continue

                level = "🔥 FORTE" if abs(strength) > 8 else "⚡ MÉDIO"

                ranking.append(
                    {
                        "symbol": sym,
                        "direction": direction,
                        "strength": strength,
                        "level": level,
                    }
                )

            except Exception:
                continue

        ranking.sort(key=lambda x: abs(x["strength"]), reverse=True)
        return ranking[:6]

    except Exception:
        return []


# ================= DATA REAL =================
def get_data():

    try:
        res = requests.get(
            f"{NGROK_URL}/data",
            headers={
                "ngrok-skip-browser-warning": "true",
                "User-Agent": "Mozilla/5.0"
            }
        )

        data = res.json()

        wallet = data["wallet"]["result"]["list"][0]
        positions = data["positions"]["result"]["list"]

        total = float(wallet["totalWalletBalance"])
        pnl = float(wallet["totalPerpUPL"])
        mmr = float(wallet["accountMMRate"]) * 100

        pos_list = []
        exposure = 0

        for p in positions:

            if float(p["size"]) == 0:
                continue

            value = float(p["positionValue"])
            exposure += value

            created = int(p["createdTime"])
            entry = datetime.fromtimestamp(created / 1000)

            days = (datetime.now() - entry).total_seconds() / 86400
            tempo = f"{days:.1f}d" if days >= 1 else f"{days*24:.1f}h"

            pct = (value / total * 100) if total > 0 else 0

            pos_list.append({
                "symbol": p["symbol"],
                "side": p["side"],
                "pnl": float(p["unrealisedPnl"]),
                "tempo": tempo,
                "pct": pct,
                "days": days
            })

        exposure_pct = (exposure / total * 100) if total > 0 else 0

        return total, pnl, pos_list, exposure_pct, mmr

    except Exception as e:
        print("ERRO:", e)
        return 0, 0, [], 0, 0


# ================= IA =================
def analyze_trades(pos, exposure, mmr):

    mensagens = []

    if exposure > 150:
        mensagens.append("🚨 Exposição MUITO alta (>150%)")

    if mmr >= 10:
        mensagens.append("🚨 Risco de liquidação (MMR >=10%)")

    for p in pos:
        if p["pct"] > 20:
            mensagens.append(f"🔥 {p['symbol']} grande ({p['pct']:.1f}%)")
        if p["days"] > 20:
            mensagens.append(f"⏱️ {p['symbol']} +20 dias aberta")

    if not mensagens:
        mensagens.append("✅ Tudo sob controle")

    return mensagens


# ================= APP =================
@app.route("/")
def home():

    total, pnl, pos, exposure, mmr = get_data()
    ranking = get_opportunities()
    analises = analyze_trades(pos, exposure, mmr)

    remaining, daily, days, progress, status, _ = get_goal(total)

    html = f"""
    <html>
    <body style="background:#0d1117;color:white;font-family:Segoe UI;margin:0">

    <h2 style="padding:10px">📊 Trading Dashboard PRO</h2>

    <div style="display:flex">

    <div style="width:30%;padding:15px;background:#161b22">

        <div style="background:#1f2933;padding:15px;margin-bottom:10px;border-radius:8px">
        💰 ${total:.2f}<br>
        PnL: <span style="color:{'#00ff88' if pnl>=0 else '#ff4d4d'}">${pnl:.2f}</span>
        </div>

        <div style="background:#1f2933;padding:15px;margin-bottom:10px;border-radius:8px">
        ⚠️ Exposição: {exposure:.1f}%
        </div>

        <div style="background:#1f2933;padding:15px;margin-bottom:10px;border-radius:8px">
        🧱 MMR: {mmr:.2f}%
        </div>

        <div style="background:#1f2933;padding:15px;margin-bottom:10px;border-radius:8px">
        🎯 Meta<br>
        Falta: ${remaining:.2f}<br>
        Dias: {days}<br>
        Por dia: ${daily:.2f}
        <div style="height:8px;background:#333;margin-top:5px">
            <div style="width:{progress}%;background:#00ff88;height:8px"></div>
        </div>
        </div>

        <div style="background:#1f2933;padding:15px;border-radius:8px">
        🤖 IA<br>
        {''.join(f"<div>{m}</div>" for m in analises)}
        </div>

    </div>

    <div style="width:70%;padding:15px">

        <div style="background:#1f2933;padding:15px;margin-bottom:10px;border-radius:8px">
        🚀 Oportunidades
    """

    if not ranking:
        html += "<p>Sem sinais</p>"

    for c in ranking:
        cor = "#064" if c["direction"] == "LONG" else "#600"
        html += f"""
        <div style="background:{cor};padding:10px;margin:5px">
        {c['symbol']} | {c['direction']} | {c['strength']:.2f}% | {c['level']}
        </div>
        """

    html += "</div>"

    html += """
        <div style="background:#1f2933;padding:15px;border-radius:8px">
        💼 Posições
    """

    for p in pos:
        cor = "#00ff88" if p["pnl"] >= 0 else "#ff4d4d"
        html += f"""
        <div>
        {p['symbol']} | {p['side']} |
        <span style="color:{cor}">${p['pnl']:.2f}</span> |
        {p['tempo']} | {p['pct']:.1f}%
        </div>
        """

    html += "</div></div></div></body></html>"

    return html


if __name__ == "__main__":
    app.run()