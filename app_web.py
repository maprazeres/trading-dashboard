from flask import Flask
import requests
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

    if daily < 10:
        status = "✅ NO RITMO"
        color = "#00ff88"
    else:
        status = "⚠️ ATRASADO"
        color = "#ff4d4d"

    return remaining, daily, days, progress, status, color


# ================= DADOS =================
def get_data():

    try:
        res = requests.get(
            f"{NGROK_URL}/data",
            headers={
                "User-Agent": "Mozilla/5.0",
                "ngrok-skip-browser-warning": "true"
            }
        )

        data = res.json()

        wallet = data["wallet"]["result"]["list"][0]
        positions = data["positions"]["result"]["list"]

        total = float(wallet["totalWalletBalance"])
        pnl = float(wallet["totalPerpUPL"])

        # ✅ MMR
        mmr = float(wallet["accountMMRate"]) * 100

        pos_list = []
        exposure = 0

        for p in positions:

            size = float(p["size"])
            if size == 0:
                continue

            pnl_pos = float(p["unrealisedPnl"])
            value = float(p["positionValue"])

            exposure += value

            created = int(p["createdTime"])
            entry = datetime.fromtimestamp(created / 1000)

            seconds = (datetime.now() - entry).total_seconds()
            days = seconds / 86400

            if days < 1:
                tempo = f"{days * 24:.1f}h"
            else:
                tempo = f"{days:.1f}d"

            pct = (value / total * 100) if total > 0 else 0

            pos_list.append({
                "symbol": p["symbol"],
                "side": p["side"],
                "pnl": pnl_pos,
                "tempo": tempo,
                "pct": pct
            })

        exposure_pct = (exposure / total * 100) if total > 0 else 0

        return total, pnl, pos_list, exposure_pct, mmr

    except Exception as e:
        print("ERRO:", e)
        return 0, 0, [], 0, 0


# ================= APP =================
@app.route("/")
def home():

    total, pnl, pos, exposure, mmr = get_data()
    remaining, daily, days, progress, status, cor_meta = get_goal(total)

    pnl_c = "#00ff88" if pnl >= 0 else "#ff4d4d"

    # ================= ALERTA MMR =================
    if mmr > 7:
        mmr_status = "🚨 RISCO DE LIQUIDAÇÃO"
        mmr_color = "#ff0000"
    elif mmr > 5:
        mmr_status = "⚠️ ATENÇÃO"
        mmr_color = "#ffaa00"
    else:
        mmr_status = "✅ SEGURO"
        mmr_color = "#00ff88"

    # ================= ALERTA EXPOSIÇÃO =================
    if exposure > 100:
        exp_status = "🚨 MUITO ALTO"
        exp_color = "#ff0000"
    elif exposure > 60:
        exp_status = "⚠️ ALTO"
        exp_color = "#ffaa00"
    else:
        exp_status = "✅ CONTROLADO"
        exp_color = "#00ff88"

    html = f"""
    <html>
    <body style="background:#0f0f0f;color:white;font-family:Segoe UI;">

    <h2 style="padding:10px;">📊 TRADING DASHBOARD PRO</h2>

    <div style="display:flex">

    <!-- ESQUERDA -->
    <div style="width:35%;padding:15px">

    <div style="background:#1c1c1c;padding:15px;border-radius:8px">
    <h3>💰 Conta</h3>
    Total: ${total:.2f}<br>
    PnL: <span style="color:{pnl_c}">${pnl:.2f}</span>
    </div>

    <div style="background:#1c1c1c;padding:15px;margin-top:10px;border-radius:8px">
    <h3>⚠️ Exposição</h3>
    {exposure:.1f}%<br>
    <b style="color:{exp_color}">{exp_status}</b>
    </div>

    <div style="background:#1c1c1c;padding:15px;margin-top:10px;border-radius:8px">
    <h3>🧱 MMR</h3>
    {mmr:.2f}%<br>
    <b style="color:{mmr_color}">{mmr_status}</b>
    </div>

    <div style="background:#1c1c1c;padding:15px;margin-top:10px;border-radius:8px">
    <h3>🎯 Meta</h3>

    Falta: ${remaining:.2f}<br>
    Dias: {days}<br>
    Por dia: ${daily:.2f}<br>

    <b style="color:{cor_meta}">{status}</b>

    <div style="background:#333;height:10px;margin-top:10px;">
        <div style="width:{progress}%;background:#00ff88;height:10px;"></div>
    </div>

    </div>

    <div style="background:#1c1c1c;padding:15px;margin-top:10px;border-radius:8px">
    <h3>💼 Posições</h3>
    """

    if not pos:
        html += "<p>Nenhuma posição</p>"

    for p in pos:

        cor = "#00ff88" if p["pnl"] >= 0 else "#ff4d4d"
        destaque = "🔥" if p["pct"] > 20 else ""

        html += f"""
        <div style="color:{cor}">
        {p['symbol']} {destaque} | {p['side']} | ${p['pnl']:.2f}
        | {p['tempo']} | {p['pct']:.1f}%
        </div>
        """

    html += "</div></div></div></body></html>"

    return html


if __name__ == "__main__":
    app.run()