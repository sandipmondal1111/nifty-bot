import os, time, requests, re
from flask import Flask
from threading import Thread
from fyers_apiv3 import fyersModel

app = Flask(__name__)

CLIENT_ID = os.getenv("CLIENT_ID", "").strip()
SECRET_KEY = os.getenv("FYERS_SECRET_KEY", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip().replace('"','').replace("'","")
CHAT_ID = os.getenv("CHAT_ID", "").strip()

@app.route('/')
def home():
    return "Bot Live! Telegram Polling Active"

@app.route('/delete-webhook')
def del_hook():
    r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=10).json()
    return f"Deleted: {r}"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

def telegram_polling():
    print("Telegram listener STARTED...", flush=True)
    last_update = 0
    while True:
        try:
            print("Polling telegram...", flush=True)
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update+1}&timeout=10"
            r = requests.get(url, timeout=15).json()
            print(f"POLL: {r.get('ok')} len={len(r.get('result',[]))}", flush=True)
            if r.get("ok"):
                for upd in r.get("result", []):
                    last_update = upd["update_id"]
                    msg = upd.get("message", {})
                    text = msg.get("text","")
                    chat_id = msg.get("chat",{}).get("id")
                    print(f"GOT: {text} from {chat_id}", flush=True)
                    if "/token" in text.lower():
                        session = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                        link = session.generate_authcode()
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": f"🔗 Login Link:\n{link}"}, timeout=10)
                        print("LINK SENT", flush=True)
        except Exception as e:
            print(f"Poll error: {e}", flush=True)
        time.sleep(2)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    telegram_polling()
