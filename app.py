from flask import Flask
import threading, time, os, requests
app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = "1039213382"
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0","Referer": "https://www.nseindia.com/option-chain"})
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
        print(f"Sent: {msg}")
    except Exception as e:
        print(e)
def get_oi_data():
    try:
        session.get("https://www.nseindia.com", timeout=10)
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
        res = session.get(url, timeout=10).json()
        ce_oi = sum(x['CE']['openInterest'] for x in res['records']['data'] if 'CE' in x)
        pe_oi = sum(x['PE']['openInterest'] for x in res['records']['data'] if 'PE' in x)
        pcr = pe_oi/ce_oi if ce_oi else 0
        spot = res['records']['underlyingValue']
        return f"📊 NIFTY OI\nSpot: {spot}\nCE OI: {ce_oi}\nPE OI: {pe_oi}\nPCR: {pcr:.2f}"
    except Exception as e:
        return f"Error: {e}"
def bot_logic():
    send_telegram("✅ Bot Started! Ab OI alert ayega.")
    while True:
        msg = get_oi_data()
        send_telegram(msg)
        time.sleep(300)
@app.route('/')
def home():
    return "Bot is ON - OI Active"
if __name__ == "__main__":
    threading.Thread(target=bot_logic, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
