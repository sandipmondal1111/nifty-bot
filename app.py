import requests, os, time, threading
from flask import Flask
app = Flask(__name__)

B = os.getenv("BOT_TOKEN","").strip()
C = os.getenv("CHAT_ID","").strip()

def get_nifty():
    # Yahoo Finance se - sabse stable
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=1d"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=15)
    j = r.json()
    spot = j['chart']['result'][0]['meta']['regularMarketPrice']
    return {"spot": spot}

@app.route('/')
def home():
    try:
        d = get_nifty()
        return f"Bot Working! NIFTY: {d['spot']}"
    except Exception as e:
        return f"Error: {e} - {str(e)[:200]}"

def bg_loop():
    while True:
        try:
            d = get_nifty()
            msg = f"NIFTY Spot: {d['spot']}"
            print(msg)
            if B and C:
                requests.get(f"https://api.telegram.org/bot{B}/sendMessage",
                    params={"chat_id": C, "text": msg}, timeout=10)
        except Exception as e:
            print(f"Loop error: {e}")
        time.sleep(900)

threading.Thread(target=bg_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
