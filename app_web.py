from flask import Flask, request
import requests
from datetime import datetime

app = Flask(__name__)

NGROK_URL = "https://tragedy-evil-praying.ngrok-free.dev"

# ===== META =====
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


# ================= DADOS =================
def get_data():
    try:
        res = requests.get(
            f"{NGROK_URL}/data",
            headers={"ngrok-skip-browser-warning": "true"}
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

    except:
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
            mensagens.append(f"🔥 {p['symbol']} posição grande")
        if p["days"] > 20:
            mensagens.append(f"⏱️ {p['symbol']} +20 dias")

    if not mensagens:
        mensagens.append("✅ Tudo sob controle")

    return mensagens


# ================= SCANNER =================
def get_opportunities():
    try:
        coins = requests.get(
            "https://api.bybit.com/v5/market/tickers?category=linear"
        ).json()["result"]["list"]

        ranking = []

        for c in coins:
            try:
                change = float(c["price24hPcnt"]) * 100

                if abs(change) < 1:  # mais sinais
                    continue

                direction = "LONG" if change > 0 else "SHORT"

                level = "🔥 FORTE" if abs(change) > 5 else "⚡ MÉDIO"

                ranking.append({
                    "symbol": c["symbol"],
                    "direction": direction,
                    "change": change,
                    "level": level
                })

            except:
                continue

        ranking.sort(key=lambda x: abs(x["change"]), reverse=True)
        return ranking[:6]

    except:
        return []


# ================= APP =================
@app.route("/")
def home():

    page = request.args.get("page", "main")

    total, pnl, pos, exposure, mmr = get_data()
    ranking = get_opportunities()
    analises = analyze_trades(pos, exposure, mmr)

    remaining, daily, days, progress, status = get_goal(total)

    html = f"""
    <html>
    <body style="background:#0d1117;color:white;font-family:Segoe UI;margin:0">

    <!-- MENU -->
    <div style="background:#111;padding:12px;display:flex;gap:20px">
        <a href="/?page=main" style="color:#00ff88;text-decoration:none">📊 Dashboard</a>
        <a href="/?page=stats" style="color:#aaa;text-decoration:none">📈 Performance</a>
    </div>

    """

    # ===== DASHBOARD =====
    if page == "main":

        html += f"""
        <h2 style="padding:10px">📊 Trading Dashboard PRO</h2>

        <div style="display:flex">

        <!-- LEFT -->
        <div style="width:30%;padding:15px">

        <div style="background:#1f2933;padding:15px;margin-bottom:10px;border-radius:10px">
        💰 ${total:.2f}<br>
        PnL: <span style="color:{'#00ff88' if pnl>=0 else '#ff4d4d'}">${pnl:.2f}</span>
        </div>

        <div style="background:#1f2933;padding:15px;margin-bottom:10px;border-radius:10px">
        ⚠️ Exposição: {exposure:.1f}%
        </div>

        <div style="background:#1f2933;padding:15px;margin-bottom:10px;border-radius:10px">
        🧱 MMR: {mmr:.2f}%
        </div>

        <div style="background:#1f2933;padding:15px;margin-bottom:10px;border-radius:10px">
        🎯 Falta: ${remaining:.2f}<br>
        Dias: {days}<br>
        Por dia: ${daily:.2f}<br>
        {status}
        </div>

        <div style="background:#1f2933;padding:15px;border-radius:10px">
        🤖 IA<br>
        {''.join(f"<div>{m}</div>" for m in analises)}
        </div>

        </div>

        <!-- RIGHT -->
        <div style="width:70%;padding:15px">

        <div style="background:#1f2933;padding:15px;margin-bottom:10px;border-radius:10px">
        🚀 Oportunidades
        """

        if not ranking:
            html += "<div>Sem sinais</div>"

        for c in ranking:
            html += f"""
            <div style="padding:10px;margin:5px;background:{'#064' if c['direction']=='LONG' else '#600'}">
            {c['symbol']} | {c['direction']} | {c['change']:.2f}% | {c['level']}
            </div>
            """

        html += "</div>"

        html += "<div style='background:#1f2933;padding:15px;border-radius:10px'>💼 Posições<br>"

        for p in pos:
            cor = "#00ff88" if p["pnl"] >= 0 else "#ff4d4d"

            html += f"""
            <div>
            {p['symbol']} | {p['side']} |
            <span style="color:{cor}">${p['pnl']:.2f}</span> |
            {p['tempo']} | {p['pct']:.1f}%
            </div>
            """

        html += "</div></div></div>"

    else:
        html += """
        <div style="padding:20px">
        <h2>📈 Performance</h2>
        <p>Em breve gráficos</p>
        </div>
        """

    html += "</body></html>"

    return html


if __name__ == "__main__":
    app.run()