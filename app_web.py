from flask import Flask
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

# ================= META =================
TARGET = 500
TARGET_DATE = datetime(2026, 6, 30)
START_BALANCE = 364

NGROK_URL = "https://tragedy-evil-praying.ngrok-free.dev"


# ================= META =================
def get_goal(current):

    now = datetime.now()
    days = max((TARGET_DATE - now).days, 1)

    remaining = TARGET - current
    daily = remaining / days

    progress = ((current - START_BALANCE) / (TARGET - START_BALANCE)) * 100
    progress = max(0, min(progress, 100))

    status = "✅ NO RITMO" if daily < 10 else "⚠️ ATRASADO"
    cor = "#00ff88" if daily < 10 else "#ff4d4d"

    return remaining, daily, days, progress, status, cor


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

        pos_list = []
        total_pnl = 0
        total_exposure = 0

        for p in positions:

            size = float(p["size"])
            if size == 0:
                continue

            pnl = float(p["unrealisedPnl"])
            total_pnl += pnl

            value = float(p["positionValue"])
            total_exposure += value

            created = int(p["createdTime"])
            entry = datetime.fromtimestamp(created / 1000)

            sec = (datetime.now() - entry).total_seconds()
            days = sec / 86400

            tempo = f"{days*24:.1f}h" if days < 1 else f"{days:.1f}d"

            pct = (value / total) * 100

            pos_list.append({
                "symbol": p["symbol"],
                "side": p["side"],
                "pnl": pnl,
                "tempo": tempo,
                "pct": pct
            })

        return total, total_pnl, pos_list, total_exposure

    except Exception as e:
        print(e)
        return 0, 0, [], 0


# ================= APP =================
@app.route("/")
def home():

    total, pnl, pos, exposure = get_data()
    remaining, daily, days, progress, status, cor_meta = get_goal(total)

    pnl_c = "#00ff88" if pnl >= 0 else "#ff4d4d"

    exposure_pct = (exposure / total * 100) if total > 0 else 0

    # ⚠️ ALERTA DE RISCO
    if exposure_pct > 60:
        risk_status = "🚨 RISCO MUITO ALTO"
        risk_color = "#ff0000"
    elif exposure_pct > 40:
        risk_status = "⚠️ RISCO MODERADO"
        risk_color = "#ffaa00"
    else:
        risk_status = "✅ RISCO CONTROLADO"
        risk_color = "#00ff88"

    html = f"""
    <html>
    <body style="background:#0f0f0f;color:white;font-family:Segoe UI;">

    <h2>📊 Dashboard Pro</h2>

    <div style="display:flex">

    <!-- ESQUERDA -->
    <div style="width:30%;padding:15px">

    <div style="background:#1c1c1c;padding:15px">
    <h3>💰 Conta</h3>
    ${total:.2f}<br>
    PnL: <span style="color:{pnl_c}">${pnl:.2f}</span>
    </div>

    <div style="background:#1c1c1c;padding:15px;margin-top:10px">
    <h3>⚠️ Risco</h3>

    Exposição: {exposure_pct:.1f}%<br>

    <b style="color:{risk_color}">
    {risk_status}
    </b>
    </div>

    <div style="background:#1c1c1c;padding:15px;margin-top:10px">
    <h3>🎯 Meta</h3>

    Falta: ${remaining:.2f}<br>
    Dias: {days}<br>
    Por dia: ${daily:.2f}<br>

    <b style="color:{cor_meta}">
    {status}
    </b>

    <div style="background:#333;height:10px;margin-top:10px;">
        <div style="width:{progress}%;background:#00ff88;height:10px;"></div>
    </div>
    </div>

    <div style="background:#1c1c1c;padding:15px;margin-top:10px">
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

    html += "</div></div>"

    html += """
    <div style="width:70%;padding:15px">
    <h3>🚀 Evolução</h3>
    <p>Próximo nível: gráfico 📈</p>
    </div>
    </div>

    </body></html>
    """

    return html


if __name__ == "__main__":
    app.run()