from flask import Flask, request
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

    return remaining, daily, days, progress, status


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

                # ✅ menos restritivo
                if abs(strength) < 3 or abs(strength) > 15:
                    continue

                url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={sym}&interval=240&limit=60"
                candles = requests.get(url).json()["result"]["list"]

                df = pd.DataFrame(candles, columns=[
                    "time","open","high","low","close","volume","turnover"
                ]).astype(float)

                df["sma20"] = df["close"].rolling(20).mean()
                df["sma50"] = df["close"].rolling(50).mean()

                cross = detect_sma_cross(df)

                trend_up = df["sma20"].iloc[-1] > df["sma50"].iloc[-1]
                trend_down = df["sma20"].iloc[-1] < df["sma50"].iloc[-1]

                # ✅ lógica flexível (mais sinais)
                if cross == "LONG" or trend_up:
                    direction = "LONG"
                elif cross == "SHORT" or trend_down:
                    direction = "SHORT"
                else:
                    continue

                level = "🔥 FORTE" if abs(strength) > 8 else "⚡ MÉDIO"

                ranking.append({
                    "symbol": sym,
                    "direction": direction,
                    "strength": strength,
                    "level": level
                })

            except:
                continue

        ranking.sort(key=lambda x: abs(x["strength"]), reverse=True)
        return ranking[:6]

    except:
        print("TOTAL COINS ANALISADAS:", len(coins))
        print("OPORTUNIDADES ENCONTRADAS:", len(ranking))
        return []


# ================= DADOS =================
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
        mensagens.append("🚨 Exposição MUITO alta")

    if mmr >= 10:
        mensagens.append("🚨 Risco de liquidação")

    for p in pos:
        if p["pct"] > 20:
            mensagens.append(f"🔥 {p['symbol']} grande")
        if p["days"] > 20:
            mensagens.append(f"⏱️ {p['symbol']} +20 dias")

    if not mensagens:
        mensagens.append("✅ Tudo sob controle")

    return mensagens


# ================= APP =================
@app.route("/")
def home():

    page = request.args.get("page", "main")

    total, pnl, pos, exposure, mmr = get_data()
    ranking = get_opportunities()
    analises = analyze_trades(pos, exposure, mmr)

    remaining, daily, days, progress, status = get_goal(total)

    # ✅ MENU
    html = """
    <html>
    <body style="background:#0d1117;color:white;font-family:Segoe UI">

    <div style="padding:10px;background:#111">
        <a href="/?page=main" style="color:white">📊 Dashboard</a> |
        <a href="/?page=stats" style="color:white">📈 Performance</a>
    </div>
    """

    # ================= DASHBOARD =================
    if page == "main":

        html += f"""
        <div style="display:flex">

        <div style="width:30%;padding:15px;background:#161b22">

        <div>💰 Total: ${total:.2f}</div>
        <div>PnL: ${pnl:.2f}</div><br>

        <div>⚠️ Exposição: {exposure:.1f}%</div>
        <div>🧱 MMR: {mmr:.2f}%</div><br>

        <div>🎯 Falta: ${remaining:.2f}</div>
        <div>Por dia: ${daily:.2f}</div>
        <div>{status}</div><br>

        <div>🤖 IA</div>
        {''.join(f"<div>{m}</div>" for m in analises)}

        <br><b>💼 Posições</b><br>
        {"".join(f"{p['symbol']} {p['side']} ${p['pnl']:.2f} | {p['tempo']}<br>" for p in pos)}

        </div>

        <div style="width:70%;padding:15px">

        <h3>🚀 Oportunidades</h3>
        """

        if not ranking:
            html += "<div>Sem oportunidades no momento</div>"

        for c in ranking:
            html += f"""
            <div style="padding:10px;margin:5px;background:{'#064' if c['direction']=='LONG' else '#600'}">
            {c['symbol']} | {c['direction']} | {c['strength']:.2f}% | {c['level']}
            </div>
            """

        html += "</div></div>"

    # ================= PERFORMANCE =================
    else:
        html += """
        <div style="padding:20px">
        <h2>📈 Performance</h2>
        <p>Em breve gráficos 📊</p>
        </div>
        """

    html += "</body></html>"

    return html


if __name__ == "__main__":
    app.run()