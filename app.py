import os, time, threading
from flask import Flask
import requests
from fyers_apiv3 import fyersModel

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")

@app.route('/')
def home():
    return "Nifty-Bot is LIVE - Fyers Bot Running"

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
    except Exception as e:
        print(e)

def nifty_loop():
    time.sleep(5)
    send_telegram("✅ <b>Nifty-Bot Live on Render!</b>\nhttps://nifty-bot-dm0o.onrender.com")
    fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=ACCESS_TOKEN, is_async=False, log_path="")

    while True:
        try:
            # Nifty LTP
            res = fyers.quotes({"symbols":"NSE:NIFTY50-INDEX"})
            if res.get("s") == "ok":
                ltp = res["d"][0]["v"]["lp"]
                print(f"NIFTY: {ltp}")
                # yaha tum apna strategy logic add kar sakte ho
                # send_telegram(f"NIFTY: {ltp}")
            else:
                print(res)
            time.sleep(60)
        except Exception as e:
            print(f"Loop Error: {e}")
            time.sleep(30)

# Bot ko background me chalao
threading.Thread(target=nifty_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
