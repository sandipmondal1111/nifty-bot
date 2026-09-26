import os, threading, time, requests, re
from flask import Flask
from fyers_apiv3 import fyersModel

app = Flask(__name__)

CLIENT_ID = os.getenv("CLIENT_ID", "").strip()
SECRET_KEY = os.getenv("FYERS_SECRET_KEY", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip().replace('"','').replace("'","")
CHAT_ID = os.getenv("CHAT_ID", "").strip()
ACCESS_TOKEN = os.getenv("FYERS_ACCESS_TOKEN", "").strip()

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        print(f"TG SENT: {msg[:50]}")
    except Exception as e:
        print(f"TG Error: {e}")

def get_fyers():
    full_token = f"{CLIENT_ID}:{ACCESS_TOKEN}" if ACCESS_TOKEN and ":" not in ACCESS_TOKEN else ACCESS_TOKEN
    return fyersModel.FyersModel(client_id=CLIENT_ID, token=full_token, log_path="", is_async=False)

@app.route('/')
def home():
    return f"Bot Live! BOT={'OK' if BOT_TOKEN else 'NO'} CHAT={CHAT_ID} Token={'OK' if ACCESS_TOKEN else 'NO'} <br><a href='/delete-webhook'>Fix Telegram</a>"

@app.route('/delete-webhook')
def del_hook():
    r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=10).json()
    return f"Deleted: {r}"

def telegram_polling():
    print("Telegram listener STARTED...")
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=10)
        print("Webhook cleared")
    except Exception as e:
        print(f"Clear webhook error: {e}")

    last_update = 0
    while True:
        try:
            print("Polling telegram...")
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update+1}&timeout=10"
            r = requests.get(url, timeout=15).json()
            if r.get("ok"):
                for upd in r.get("result", []):
                    last_update = upd["update_id"]
                    text = upd.get("message", {}).get("text", "")
                    print(f"GOT MSG: {text}")
                    if "/token" in text.lower():
                        session = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                        link = session.generate_authcode()
                        send_telegram(f"🔗 *Login Link:*\n{link}")
                    elif "auth_code" in text:
                        m = re.search(r"auth_code=([^&]+)", text)
                        if m:
                            code = m.group(1)
                            session = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                            session.set_token(code)
                            resp = session.generate_token()
                            if "access_token" in resp:
                                ACCESS_TOKEN_NEW = resp["access_token"]
                                os.environ["FYERS_ACCESS_TOKEN"] = ACCESS_TOKEN_NEW
                                global ACCESS_TOKEN
                                ACCESS_TOKEN = ACCESS_TOKEN_NEW
                                send_telegram(f"✅ *Token Updated!*\nBot ab LIVE hai")
                            else:
                                send_telegram(f"❌ Error: {resp}")
                    elif "/status" in text.lower():
                        try:
                            fy = get_fyers()
                            res = fy.quotes({"symbols":"NSE:NIFTY50-INDEX"})
                            price = res["d"][0]["v"]["lp"] if res.get("s")=="ok" else res
                            send_telegram(f"📊 *NIFTY: {price}*")
                        except Exception as e:
                            send_telegram(f"Error: {e}")
        except Exception as e:
            print(f"Polling loop error: {e}")
        time.sleep(3)

threading.Thread(target=telegram_polling, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
