import os, time, requests, re
from flask import Flask
from threading import Thread
from fyers_apiv3 import fyersModel

app = Flask(__name__)

CLIENT_ID = os.getenv("CLIENT_ID", "").strip()
SECRET_KEY = os.getenv("FYERS_SECRET_KEY", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip().replace('"','').replace("'","")

TOKEN_FILE = "/tmp/fyers_token.txt"
FYERS_TOKEN = ""

def save_token(token):
    global FYERS_TOKEN
    FYERS_TOKEN = token
    try:
        with open(TOKEN_FILE, "w") as f:
            f.write(token)
    except: pass
    print(f"TOKEN SAVED", flush=True)

def load_token():
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                t = f.read().strip()
                if t: return t
    except: pass
    return os.getenv("FYERS_ACCESS_TOKEN", "").strip()

FYERS_TOKEN = load_token()

@app.route('/')
def home():
    return f"Bot Live! Token Loaded: {bool(FYERS_TOKEN)}"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

def telegram_polling():
    print("Telegram STARTED...", flush=True)
    last_update = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update+1}&timeout=10"
            r = requests.get(url, timeout=15).json()
            if not r.get("ok"):
                time.sleep(2)
                continue
            for upd in r.get("result", []):
                last_update = upd["update_id"]
                msg = upd.get("message",{})
                text = msg.get("text","")
                chat_id = msg.get("chat",{}).get("id")
                if not text: continue
                print(f"GOT {text[:80]}", flush=True)
                low = text.lower()

                if "/status" in low:
                    status = f"✅ Bot Online\nToken Loaded: {bool(FYERS_TOKEN)}\nFile Exists: {os.path.exists(TOKEN_FILE)}"
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":status}, timeout=10)

                elif "/token" in low:
                    s = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                    link = s.generate_authcode()
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"🔗 Login Link:\n{link}"}, timeout=10)

                elif "auth_code" in text:
                    m = re.search(r"auth_code=([^&]+)", text)
                    if m:
                        code=m.group(1)
                        s = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                        s.set_token(code)
                        resp=s.generate_token()
                        print(f"RESP {resp}", flush=True)
                        if "access_token" in resp:
                            save_token(resp['access_token'])
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"✅ Token Auto-Saved! Ab Render me paste karne ki zarurat nahi hai. Trading shuru!"}, timeout=10)
                        else:
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"❌ Error: {resp}"}, timeout=10)
        except Exception as e:
            print(f"ERR {e}", flush=True)
        time.sleep(1)

if __name__=="__main__":
    Thread(target=run_flask, daemon=True).start()
    telegram_polling()
