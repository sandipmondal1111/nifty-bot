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
    time.sleep(2)
    last_update = 0
    while True:
        try:
            print("Polling telegram...")
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update+1}&timeout=10"
            r = requests.get(url, timeout=15).json()
            print(f"POLL RESULT: ok={r.get('ok')} count={len(r.get('result',[]))}")
            if r.get("ok"):
                for upd in r.get("result", []):
                    last_update = upd["update_id"]
                    msg_obj = upd.get("message", {})
                    text = msg_obj.get("text", "")
                    from_chat = msg_obj.get("chat", {}).get("id", CHAT_ID)
                    print(f"GOT MSG: {text} from {from_chat}")
                    # yahan direct send karenge same chat pe
                    def send_to_chat(m):
                        try:
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": from_chat, "text": m, "parse_mode": "Markdown"}, timeout=10)
                            print(f"SENT to {from_chat}")
                        except Exception as e:
                            print(f"SEND ERR {e}")

                    if "/token" in text.lower():
                        session = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                        link = session.generate_authcode()
                        send_to_chat(f"🔗 *Login Link:*\n{link}")
                    elif "auth_code" in text:
                        import re
                        m = re.search(r"auth_code=([^&]+)", text)
                        if m:
                            code = m.group(1)
                            session = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                            session.set_token(code)
                            resp = session.generate_token()
                            if "access_token" in resp:
                                send_to_chat(f"✅ *Token Updated!*\n`{resp['access_token'][:20]}...`")
                            else:
                                send_to_chat(f"❌ Error: {resp}")
        except Exception as e:
            print(f"Polling error: {e}")
        time.sleep(3)

threading.Thread(target=telegram_polling, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
