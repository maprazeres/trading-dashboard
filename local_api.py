# local_api.py

from flask import Flask, jsonify
from pybit.unified_trading import HTTP
import os

app = Flask(__name__)

session = HTTP(
    testnet=False,
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET")
)

@app.route("/data")
def get_data():
    try:
        positions = session.get_positions(category="linear", settleCoin="USDT")
        wallet = session.get_wallet_balance(accountType="UNIFIED")

        return jsonify({
            "positions": positions,
            "wallet": wallet
        })

    except Exception as e:
        return jsonify({"error": str(e)})

app.run(port=5001)