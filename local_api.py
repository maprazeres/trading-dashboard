# local_api.py

from flask import Flask, jsonify
from pybit.unified_trading import HTTP
from dotenv import load_dotenv
import os
import requests

# ✅ CARREGA ENV
load_dotenv()

# ✅ PEGA CHAVES
api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")

print("API_KEY:", "OK" if api_key else "NÃO CARREGOU")
print("API_SECRET:", "OK" if api_secret else "NÃO CARREGOU")

app = Flask(__name__)

@app.route("/tickers")
def tickers():
    try:
        data = requests.get(
            "https://api.bybit.com/v5/market/tickers?category=linear"
        ).json()

        return data

    except Exception as e:
        return {"error": str(e)}

# ✅ CONEXÃO REAL BYBIT
session = HTTP(
    testnet=False,
    api_key=api_key,
    api_secret=api_secret
)

@app.route("/data")
def get_data():
    try:
        # ✅ POSIÇÕES
        positions = session.get_positions(
            category="linear",
            settleCoin="USDT"
        )

        # ✅ WALLET (TESTAR CONTRACT se necessário)
        wallet = session.get_wallet_balance(accountType="UNIFIED")

        print("WALLET:", wallet)

        return jsonify({
            "positions": positions,
            "wallet": wallet
        })

    except Exception as e:
        print("ERRO:", e)
        return jsonify({"error": str(e)})

# ✅ IMPORTANTE
if __name__ == "__main__":
    app.run(port=5001)