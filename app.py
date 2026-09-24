import os
import time
import threading
from flask import Flask
import requests
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws

# --- ENV VARIABLES (Render se ayenge) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
SECRET_ID = os.environ.get("SECRET_ID")
FYERS_PIN = os.environ.get("FYERS_PIN")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Nifty-Bot is Running! Live"

def run_flask():
    # Render 10000 port expect karta hai
    app_flask.run(host='0.0.0.0', port=10000)

# --- Telegram Send Function ---
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
    except Exception as e:
        print(f"Telegram Error: {e}")

# --- Token Refresh ---
def get_new_access_token():
    global ACCESS_TOKEN
    try:
        # Refresh token se naya access token
        session = fyersModel.SessionModel(
            client_id=CLIENT_ID,
            secret_key=SECRET_ID,
            redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html",
            response_type="code",
            grant_type="refresh_token"
        )
        session.set_token(REFRESH_TOKEN)
        # FYERS me pin bhi chahiye hota hai kuch cases me
        response = session.generate_token()
        if "access_token" in response:
            ACCESS_TOKEN = response["access_token"]
            print("New Access Token Mil Gaya!")
            send_telegram("✅ Bot ON - Auto Token Active")
            return ACCESS_TOKEN
        else:
            print(f"Token Refresh Failed: {response}")
            return None
    except Exception as e:
        print(f"Token Error: {e}")
        return None

# --- Main Bot Logic ---
def start_nifty_bot():
    token = ACCESS_TOKEN
    if not token:
        token = get_new_access_token()

    if not token:
        print("No Token Found!")
        time.sleep(10)
        return

    fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=token, is_async=False, log_path="")

    print("Bot Started, Waiting for Market...")
    send_telegram("🤖 Nifty-Bot Started on Render")

    # Simple LTP Loop - Market Hours me chalega
    while True:
        try:
            # NIFTY 50
            data = {"symbols":"NSE:NIFTY50-INDEX"}
            resp = fyers.quotes(data)

            if resp.get("s") == "ok":
                ltp = resp["d"][0]["v"]["lp"]
                msg = f"📊 NIFTY: {ltp}\nTime: {time.strftime('%H:%M:%S')}"
                print(msg)
                # Har 15 min me bhejo (testing ke liye har 2 min)
                # send_telegram(msg)
            else:
                print(f"API Response: {resp}")
                # Token expire hua to refresh
                if "token" in str(resp).lower() or resp.get("code") == -16:
                    print("Token Expired, Refreshing...")
                    get_new_access_token()

            time.sleep(60) # 1 min wait

        except Exception as e:
            print(f"Loop Error: {e}")
            time.sleep(30)

# --- Start Both ---
if __name__ == "__main__":
    # Flask ko alag thread pe chalao taaki Render ko port mile
    threading.Thread(target=run_flask, daemon=True).start()

    # Bot ko main thread pe chalao
    start_nifty_bot()
