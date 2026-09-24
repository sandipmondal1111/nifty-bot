import os, time, threading
from flask import Flask
import requests
from fyers_apiv3 import fyersModel

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
SECRET_ID = os.environ.get("SECRET_ID")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")

app_flask = Flask(__name__)
@app_flask.route('/')
def home():
    return "Nifty-Bot Live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port)

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except: pass

def start_bot():
    send_telegram("✅ Bot ON - Render Live")
    while True:
        print("Bot Running... Market Closed Time")
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    start_bot()
