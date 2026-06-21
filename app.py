from flask import Flask, jsonify
from pybit.unified_trading import HTTP
import os
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()

api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")

session = HTTP(testnet=False, api_key=api_key, api_secret=api_secret)


@app.route("/data")
def get_data():
    try:
        wallet = session.get_wallet_balance(accountType="UNIFIED")
        positions = session.get_positions(category="linear", settleCoin="USDT")

        return jsonify({
            "wallet": wallet,
            "positions": positions
        })

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/")
def home():
    return "API ONLINE ✅"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)