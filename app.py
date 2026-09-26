import os, threading, time, requests, re
from flask import Flask
from fyers_apiv3 import fyersModel

app = Flask(__name__)

CLIENT_ID = os.getenv("CLIENT_ID", "").strip()
SECRET_KEY = os.getenv("FYERS_SECRET_KEY", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip().replace('"','').replace("'","")
CHAT_ID = os.getenv("CHAT_ID", "").strip()
ACCESS_TOKEN = os.getenv("FYERS_ACCESS_TOKEN", "").strip()

print(f"STARTUP CHECK: CLIENT_ID={'OK' if CLIENT_ID else 'MISSING'} BOT_TOKEN={'OK '+BOT_TOKEN[:10] if BOT_TOKEN else 'MISSING'} CHAT_ID={CHAT_ID}")

def send_telegram(msg):
    try:
        if not BOT_TOKEN or not CHAT_ID:
            print(f"Cannot send TG: BOT_TOKEN missing={not BOT_TOKEN} CHAT_ID missing={not CHAT_ID}")
            return
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        print(f"TG Send: {r.status_code} {r.text[:100]}")
    except Exception as e:
        print(f"Telegram error: {e}")

def get_fyers():
    full_token = f"{CLIENT_ID}:{ACCESS_TOKEN}" if ACCESS_TOKEN and ":" not in ACCESS_TOKEN else ACCESS_TOKEN
    return fyersModel.FyersModel(client_id=CLIENT_ID, token=full_token, log_path="", is_async=False)

@app.route('/')
def home():
    return f"Bot Live! BOT={'OK' if BOT_TOKEN else 'MISSING'} CHAT={CHAT_ID} Token={'OK' if ACCESS_TOKEN else 'MISSING'} <br><a href='/delete-webhook'>Click to Fix Telegram</a>"

@app.route('/delete-webhook')
def del_hook():
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True"
        r = requests.get(url, timeout=10).json()
        return f"Webhook delete: {r} <br>Now send /token on telegram"
    except Exception as e:
        return str(e)

@app.route('/token')
def gen_token_link():
    session = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
    link = session.generate_authcode()
    send_telegram(f"🔗 *Login Link:*\n{link}")
    return f"<a href='{link}'>Login</a>"

def telegram_polling():
    print("Telegram listener started...")
    # delete webhook on start
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=10)
        print("Webhook deleted on startup")
    except: pass

    last_update = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update+1}&timeout=20"
            r = requests.get(url, timeout=25).json()
            print(f"Polling tick: ok={r.get('ok')} result_len={len(r.get('result',[]))}")
            if r.get("ok"):
                for upd in r.get("result", []):
                    last_update = upd["update_id"]
                    msg = upd.get("message", {})
                    text = msg.get("text", "")
                    print(f"Got: {text}")
                    #... (baki tumhara same code)
                    if "/token" in text.lower():
                        session = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                        link = session.generate_authcode()
                        send_telegram(f"🔗 *Fyers Login Link:*\n{link}")
                    elif "auth_code" in text:
                        m = re.search(r"auth_code=([^&]+)", text)
                        if m:
                            code = m.group(1)
                            session = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                            session.set_token(code)
                            resp = session.generate_token()
                            if "access_token" in resp:
                                token = resp["access_token"]
                                os.environ["FYERS_ACCESS_TOKEN"] = token
                                global ACCESS_TOKEN
                                ACCESS_TOKEN = token
                                send_telegram(f"✅ *Token Updated!*\nAb bot LIVE hai.\n`{token}`")
                            else:
                                send_telegram(f"❌ Token Error: {resp}")
                    elif "/status" in text.lower():
                        try:
                            fy = get_fyers()
                            res = fy.quotes({"symbols":"NSE:NIFTY50-INDEX"})
                            if res.get("s") == "ok":
                                price = res["d"][0]["v"]["lp"]
                                send_telegram(f"📊 *NIFTY: {price}*\n✅ Data LIVE hai")
                            else:
                                send_telegram(f"⚠️ Fyers Error: {res}")
                        except Exception as e:
                            send_telegram(f"❌ Data Error: {e}")
            time.sleep(2)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

threading.Thread(target=telegram_polling, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
