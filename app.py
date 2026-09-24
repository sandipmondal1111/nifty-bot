import requests, os, time, threading, json
from flask import Flask
app = Flask(__name__)

B = os.getenv("BOT_TOKEN","").strip()
C = os.getenv("CHAT_ID","").strip()

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def get_spot():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=1d"
    r = requests.get(url, headers=HEADERS, timeout=15)
    return r.json()['chart']['result'][0]['meta']['regularMarketPrice']

def get_option_chain():
    spot = get_spot()
    chain = None
    # 3 tarike se try karenge
    urls = [
        "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY",
        "https://api.allorigins.win/raw?url=https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY",
        "https://api.codetabs.com/v1/proxy?quest=https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    ]
    for u in urls:
        try:
            # cookie ke liye pehle main page hit
            if "nseindia.com/api" in u and "allorigins" not in u and "codetabs" not in u:
                requests.get("https://www.nseindia.com/option-chain", headers=HEADERS, timeout=10)
            r = requests.get(u, headers=HEADERS, timeout=20)
            if r.text.startswith("{"):
                chain = r.json()
                break
        except:
            continue

    if not chain:
        return {"spot": spot, "chain": [], "error": "NSE block, sirf spot mila"}

    expiry = chain['records']['expiryDates'][0]
    atm = round(spot/50)*50
    result = []
    for item in chain['records']['data']:
        if item.get('strikePrice') and abs(item['strikePrice'] - atm) <= 200:
            ce = item.get('CE', {})
            pe = item.get('PE', {})
            result.append({
                "strike": item['strikePrice'],
                "ce_ltp": ce.get('lastPrice', 0),
                "pe_ltp": pe.get('lastPrice', 0),
                "ce_oi": ce.get('openInterest', 0),
                "pe_oi": pe.get('openInterest', 0)
            })
    result = sorted(result, key=lambda x: x['strike'])
    return {"spot": spot, "expiry": expiry, "chain": result}

@app.route('/')
def home():
    try:
        d = get_option_chain()
        html = f"<h2>NIFTY: {d['spot']} | Exp: {d.get('expiry','')}</h2><table border=1><tr><th>Strike</th><th>CE LTP</th><th>PE LTP</th><th>CE OI</th><th>PE OI</th></tr>"
        for c in d['chain']:
            html += f"<tr><td>{c['strike']}</td><td>{c['ce_ltp']}</td><td>{c['pe_ltp']}</td><td>{c['ce_oi']}</td><td>{c['pe_oi']}</td></tr>"
        html += "</table>"
        if not d['chain']:
            html += f"<p>{d.get('error','')} - Spot: {d['spot']}</p>"
        return html
    except Exception as e:
        return f"Error: {e}"

def bg_loop():
    while True:
        try:
            d = get_option_chain()
            msg = f"NIFTY: {d['spot']} Exp: {d.get('expiry','')}\n"
            for c in d['chain'][:5]:
                msg += f"{c['strike']} CE:{c['ce_ltp']} PE:{c['pe_ltp']}\n"
            print(msg)
            if B and C and d['chain']:
                requests.get(f"https://api.telegram.org/bot{B}/sendMessage", params={"chat_id": C, "text": msg}, timeout=10)
        except Exception as e:
            print(f"Loop error: {e}")
        time.sleep(900)

threading.Thread(target=bg_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
