import os, threading, time, requests
from flask import Flask
from fyers_apiv3 import fyersModel

app = Flask(__name__)

CLIENT_ID = os.getenv("CLIENT_ID")
SECRET_KEY = os.getenv("FYERS_SECRET_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
ACCESS_TOKEN = os.getenv("FYERS_ACCESS_TOKEN", "")

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def get_fyers():
    return fyersModel.FyersModel(client_id=CLIENT_ID, token=ACCESS_TOKEN, log_path="")

@app.route('/')
def home():
    return f"Bot Live! Token: {'OK' if ACCESS_TOKEN else 'MISSING'}"

@app.route('/token')
def gen_token_link():
    from fyers_apiv3 import fyersModel
    session = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
    link = session.generate_authcode()
    send_telegram(f"🔗 Login Link:\n{link}")
    return f"<a href='{link}'>Login to Fyers</a>"

def telegram_polling():
    print("Telegram listener started...")
    last_update = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update+1}&timeout=20"
            r = requests.get(url, timeout=25).json()
            if r.get("ok"):
                for upd in r.get("result", []):
                    last_update = upd["update_id"]
                    msg = upd.get("message", {})
                    text = msg.get("text", "")
                    print(f"Got: {text}")

                    if "/token" in text.lower():
                        from fyers_apiv3 import fyersModel
                        session = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                        link = session.generate_authcode()
                        send_telegram(f"🔗 *Fyers Login Link:*\n{link}")

                    elif "auth_code" in text:
                        # extract code
                        import re
                        m = re.search(r"auth_code=([^&]+)", text)
                        if m:
                            code = m.group(1)
                            from fyers_apiv3 import fyersModel
                            session = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                            session.set_token(code)
                            resp = session.generate_token()
                            if "access_token" in resp:
                                token = resp["access_token"]
                                os.environ["FYERS_ACCESS_TOKEN"] = token
                                send_telegram(f"✅ *Token Updated!*\nAb bot LIVE hai.\n`{token[:30]}...`")
                                print(f"Token saved: {token[:20]}")
                                global ACCESS_TOKEN
                                ACCESS_TOKEN = token
                            else:
                                send_telegram(f"❌ Token Error: {resp}")

                    elif "/status" in text.lower() or "/check" in text.lower():
                        try:
                            fy = get_fyers()
                            res = fy.quotes({"symbols":"NSE:NIFTY50-INDEX"})
                            if res.get("s") == "ok":
                                price = res["d"][0]["v"]["lp"]
                                send_telegram(f"📊 *NIFTY: {price}*\n✅ Data LIVE hai\nToken: OK\nTime: Saturday Test Mode")
                            else:
                                send_telegram(f"⚠️ Fyers Error: {res}\nToken expire? /token bhejo")
                        except Exception as e:
                            send_telegram(f"❌ Data Error: {e}")

            time.sleep(2)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

threading.Thread(target=telegram_polling, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
