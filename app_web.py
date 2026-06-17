from flask import Flask, request
import requests
import os
import json
from datetime import datetime, timedelta

app = Flask(__name__)

HISTORY_FILE = "history.json"

# ✅ CONFIG DA META
TARGET = 500
TARGET_DATE = datetime(2026, 6, 30)
START_BALANCE = 364  # ajuste se quiser

NGROK_URL = "https://tragedy-evil-praying.ngrok-free.dev"


# =========================
# 🎯 META
# =========================
def get_goal_status(current_balance):

    now = datetime.now()
    days_left = (TARGET_DATE - now).days
    days_left = max(days_left, 1)

    remaining = TARGET - current_balance
    daily = remaining / days_left

    progress = ((current_balance - START_BALANCE) / (TARGET - START_BALANCE)) * 100
    progress = max(0, min(progress, 100))

    status = "✅ NO RITMO" if daily < 10 else "⚠️ ATRASADO"
    cor = "#00ff88" if daily < 10 else "#ff4d4d"

    return {
        "target": TARGET,
        "remaining": remaining,
        "daily": daily,
        "days_left": days_left,
        "progress": progress,
        "status": status,
        "cor": cor
    }


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


# =========================
# DADOS REAIS
# =========================
def get_account_data():
    try:
        response = requests.get(
            f"{NGROK_URL}/data",
            headers={
                "ngrok-skip-browser-warning": "true",
                "User-Agent": "Mozilla/5.0"
            }
        )

        data = response.json()

        wallet = data["wallet"]["result"]["list"][0]
        positions = data["positions"]["result"]["list"]

        total_wallet = float(wallet['totalWalletBalance'])
        total_pnl = 0

        results = []

        for pos in positions:
            if float(pos['size']) == 0:
                continue

            pnl = float(pos['unrealisedPnl'])
            total_pnl += pnl

            # ✅ TEMPO DA POSIÇÃO
            created_time = int(pos['createdTime'])
            entry_date = datetime.fromtimestamp(created_time / 1000)

            seconds = (datetime.now() - entry_date).total_seconds()
            days = seconds / 86400

            tempo = f"{days*24:.1f}h" if days < 1 else f"{days:.1f}d"

            results.append({
                "symbol": pos['symbol'],
                "tipo": pos['side'],
                "pnl": pnl,
                "tempo": tempo
            })

        return results, total_wallet, total_pnl

    except Exception as e:
        print("ERRO:", e)
        return [], 0, 0


# =========================
# APP
# =========================
@app.route("/")
def home():

    pos, total, pnl = get_account_data()
    goal = get_goal_status(total)

    pnl_c = "#00ff88" if pnl >= 0 else "#ff4d4d"

    html = f"""
    <html>
    <body style="background:#0f0f0f;color:white;font-family:Segoe UI;">

    <div style="padding:10px;background:#111;">
        📊 Dashboard
    </div>

    <div style="display:flex">

    <!-- ESQUERDA -->
    <div style="width:30%;padding:15px">

    <div style="background:#1c1c1c;padding:15px;border-radius:8px">
    <h3>💰 Conta</h3>
    Total: ${total:.2f}<br>
    PnL: <span style="color:{pnl_c}">${pnl:.2f}</span>
    </div>

    <!-- META PRO -->
    <div style="background:#1c1c1c;padding:15px;margin-top:10px;border-radius:8px">
    <h3>🎯 Meta</h3>

    Meta: ${goal['target']}<br>
    Falta: ${goal['remaining']:.2f}<br>
    Dias: {goal['days_left']}<br>
    Por dia: ${goal['daily']:.2f}<br>

    <b style="color:{goal['cor']}">{goal['status']}</b>

    <div style="background:#333;height:10px;margin-top:10px;">
        <div style="width:{goal['progress']}%;background:#00ff88;height:10px;"></div>
    </div>

    Progresso: {goal['progress']:.1f}%
    </div>

    <!-- POSIÇÕES -->
    <div style="background:#1c1c1c;padding:15px;margin-top:10px;border-radius:8px">
    <h3>💼 Posições</h3>
    """

    if not pos:
        html += "<p>Nenhuma posição ativa</p>"

    for p in pos:
        cor = "#00ff88" if p["pnl"] >= 0 else "#ff4d4d"

        html += f"""
        <div style="color:{cor}">
        {p['symbol']} | {p['tipo']} | ${p['pnl']:.2f} | {p['tempo']}
        </div>
        """

    html += "</div></div>"

    html += """
    <div style="width:70%;padding:15px">
    <h3>🚀 OPORTUNIDADES</h3>
    <p>Em breve melhorias aqui...</p>
    </div>
    </div>

    </body></html>
    """

    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)