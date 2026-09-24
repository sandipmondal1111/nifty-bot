import requests, os, time, socket
from flask import Flask
import urllib3
urllib3.disable_warnings()

app = Flask(__name__)

PROJECT = "kscckhjrasotwejshmr"
SUPA_HOST = f"{PROJECT}.supabase.co"
ANON = os.getenv("SUPABASE_KEY")
EMAIL = os.getenv("ROEIQ_EMAIL")
PASS = os.getenv("ROEIQ_PASS")
BOT = os.getenv("BOT_TOKEN")
CHAT = os.getenv("CHAT_ID")

# DNS fix - IP nikalo Cloudflare se
def get_ip():
    try:
        # Try Google DNS over HTTPS
        r = requests.get(f"https://1.1.1.1/dns-query?name={SUPA_HOST}&type=A",
                         headers={"accept": "application/dns-json"}, timeout=5)
        ip = r.json()['Answer'][0]['data']
        return ip
    except:
        try:
            return socket.gethostbyname(SUPA_HOST)
        except:
            return "104.18.38.10" # fallback supabase ip

SUPA_IP = get_ip()
print(f"SUPABASE IP: {SUPA_IP} for {SUPA_HOST}")

def supa_request(method, path, headers={}, json_data=None):
    # IP se call karo, Host header se original bhejo
    url = f"https://{SUPA_IP}{path}"
    h = headers.copy()
    h["Host"] = SUPA_HOST
    h["apikey"] = ANON
    # SNI ke liye session
    s = requests.Session()
    # verify False karna padta hai IP call pe
    r = s.request(method, url, headers=h, json=json_data, verify=False, timeout=15)
    return r

def get_token():
    path = "/auth/v1/token?grant_type=password"
    headers = {"Content-Type": "application/json"}
    data = {"email": EMAIL, "password": PASS}
    r = supa_request("POST", path, headers, data)
    print("TOKEN RESP:", r.text[:500])
    return r.json().get("access_token")

def get_chain():
    token = get_token()
    if not token:
        raise Exception("Token nahi mila")
    path = "/functions/v1/get-option-chain"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    r = supa_request("POST", path, headers, {"symbol": "NIFTY"})
    print("CHAIN RESP:", r.text[:500])
    return r.json()

def send_telegram(msg):
    if not BOT or not CHAT: return
    try:
        requests.get(f"https://api.telegram.org/bot{BOT}/sendMessage",
                     params={"chat_id": CHAT, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

@app.route('/')
def home():
    try:
        data = get_chain()
        return f"Bot Working! Data: {str(data)[:1000]}"
    except Exception as e:
        return f"Error: {e}"

def loop():
    while True:
        try:
            d = get_chain()
            spot = d.get('spot', 'N/A')
            send_telegram(f"📊 *NIFTY Live* \nSpot: {spot}\n✅ ROEIQ se connected!")
        except Exception as e:
            print("Loop error:", e)
        time.sleep(900)

import threading
threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
