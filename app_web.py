from flask import Flask
import requests
import pandas as pd
from datetime import datetime

app = Flask(__name__)

NGROK_URL = "https://tragedy-evil-praying.ngrok-free.dev"

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
    df['atr'] = (df['high'] - df['low']).rolling(period).mean()

    upper = hl2 + (multiplier * df['atr'])
    lower = hl2 - (multiplier * df['atr'])

    trend = [True]

    for i in range(1, len(df)):
        if df['close'][i] > upper[i-1]:
            trend.append(True)
        elif df['close'][i] < lower[i-1]:
            trend.append(False)
        else:
            trend.append(trend[i-1])

    df['st'] = trend
    return trend[-1]


# ================= DETECTAR CRUZAMENTO SMA =================
def detect_sma_cross(df):

    sma20_prev = df["sma20"].iloc[-2]
    sma50_prev = df["sma50"].iloc[-2]

    sma20_now = df["sma20"].iloc[-1]
    sma50_now = df["sma50"].iloc[-1]

    # ✅ CRUZAMENTO PRA CIMA
    if sma20_prev < sma50_prev and sma20_now > sma50_now:
        return "LONG"

    # ✅ CRUZAMENTO PRA BAIXO
    if sma20_prev > sma50_prev and sma20_now < sma50_now:
        return "SHORT"

    return None


# ================= SCANNER =================
def get_opportunities():

    try:
        coins = requests.get(
            "https://api.bybit.com/v5/market/tickers?category=linear"
        ).json()["result"]["list"]

        btc = next(
            (float(c["price24hPcnt"]) * 100 for c in coins if c["symbol"] == "BTCUSDT"),
            0
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

                # ✅ MOMENTUM + EVITAR TOPO
                if abs(strength) < 5 or abs(strength) > 15:
                    continue

                # ✅ CANDLES
                url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={sym}&interval=240&limit=60"
                candles = requests.get(url).json()["result"]["list"]

                df = pd.DataFrame(candles, columns=[
                    "time", "open", "high", "low", "close",
                    "volume", "turnover"
                ])

                df = df.astype(float)

                # ✅ SMA
                df["sma20"] = df["close"].rolling(20).mean()
                df["sma50"] = df["close"].rolling(50).mean()

                # ✅ CRUZAMENTO REAL
                cross = detect_sma_cross(df)

                # ✅ SUPERTREND
                st = supertrend(df)

                if not cross:
                    continue

                # ✅ VALIDAR DIREÇÃO
                if cross == "LONG" and st:
                    direction = "LONG"
                elif cross == "SHORT" and not st:
                    direction = "SHORT"
                else:
                    continue

                ranking.append({
                    "symbol": sym,
                    "direction": direction,
                    "strength": strength
                })

            except:
                continue

        ranking.sort(key=lambda x: abs(x["strength"]), reverse=True)

        return ranking[:6]

    except:
        return []


# ================= APP =================
@app.route("/")
def home():

    ranking = get_opportunities()

    html = """
    <html>
    <body style='background:#0f0f0f;color:white;font-family:Segoe UI;'>

    <h2>🚀 SCANNER PROFISSIONAL (SMA CROSS + SUPERTREND)</h2>
    """

    if not ranking:
        html += "<p>Sem oportunidades no momento</p>"

    for c in ranking:

        cor = "#064" if c["direction"] == "LONG" else "#600"

        html += f"""
        <div style="background:{cor};padding:10px;margin:10px">
        {c['symbol']} | {c['direction']} | {c['strength']:.2f}%
        </div>
        """

    html += "</body></html>"

    return html


if __name__ == "__main__":
    app.run()