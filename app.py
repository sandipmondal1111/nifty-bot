import requests, os, time, threading
from flask import Flask
app = Flask(__name__)

B = os.getenv("BOT_TOKEN","").strip()
C = os.getenv("CHAT_ID","").strip()

# NSE se direct option chain
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "application/json"
})

def get_nifty():
    # pehle cookie lena padta hai
    try:
        session.get("https://www.nseindia.com/option-chain", timeout=10, verify=False)
    except:
        pass
    r = session.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY", timeout=15, verify=False)
    j = r.json()
    spot = j['records']['underlyingValue']
    expiry = j['records']['expiryDates'][0]
    # ATM ke aas paas ke data
    data = j['records']['data'][:5]
    return {"spot": spot, "expiry": expiry, "raw": j}

@app.route('/')
def home():
    try:
        d = get_nifty()
        return f"Bot Working! NIFTY: {d['spot']} Expiry: {d['expiry']}"
    except Exception as e:
        return f"Error: {e}"

def bg_loop():
    while True:
        try:
            d = get_nifty()
            text = f"NIFTY Spot: {d['spot']}\nExpiry: {d['expiry']}"
            print(text)
            if B and C:
                requests.get(f"https://api.telegram.org/bot{B}/sendMessage",
                    params={"chat_id": C, "text": text}, timeout=10, verify=False)
        except Exception as e:
            print(f"Loop error: {e}")
        time.sleep(900) # 15 min

threading.Thread(target=bg_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
