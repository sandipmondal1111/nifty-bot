import requests, os, time
from flask import Flask

app = Flask(__name__)

URL = "https://kscckhjrasotwejshmr.supabase.co"
ANON = os.getenv("SUPABASE_KEY")
EMAIL = os.getenv("ROEIQ_EMAIL")
PASS = os.getenv("ROEIQ_PASS")
BOT = os.getenv("BOT_TOKEN")
CHAT = os.getenv("CHAT_ID")

def get_token():
    r = requests.post(f"{URL}/auth/v1/token?grant_type=password",
        headers={"apikey": ANON, "Content-Type": "application/json"},
        json={"email": EMAIL, "password": PASS}, timeout=10)
    return r.json().get("access_token")

def get_chain():
    token = get_token()
    r = requests.post(f"{URL}/functions/v1/get-option-chain",
        headers={"apikey": ANON, "Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"symbol": "NIFTY"}, timeout=15)
    return r.json()

def send_telegram(msg):
    if not BOT or not CHAT: return
    try:
        requests.get(f"https://api.telegram.org/bot{BOT}/sendMessage?chat_id={CHAT}&text={msg}&parse_mode=Markdown")
    except: pass

@app.route('/')
def home():
    try:
        data = get_chain()
        spot = data.get('spot') or data.get('underlying') or 'NIFTY'
        return f"Bot Working! Spot: {spot} | Data OK: {str(data)[:500]}"
    except Exception as e:
        return f"Error: {e}"

# Telegram alert loop - Render pe background me chalega
def start_bot():
    while True:
        try:
            data = get_chain()
            spot = data.get('spot', 0)
            msg = f"📊 *NIFTY Update*\nSpot: {spot}\nBot is Live from ROEIQ ✅\nNSE Block Khatam!"
            send_telegram(msg)
        except Exception as e:
            print(e)
        time.sleep(900) # 15 min

import threading
threading.Thread(target=start_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
