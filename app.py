import requests, os, time, socket
from flask import Flask
app = Flask(__name__)
PROJECT = "kscckhjrasotwejshmr"
SUPA_HOST = f"{PROJECT}.supabase.co"
ANON = os.getenv("SUPABASE_KEY")
EMAIL = os.getenv("ROEIQ_EMAIL")
PASS = os.getenv("ROEIQ_PASS")
BOT = os.getenv("BOT_TOKEN")
CHAT = os.getenv("CHAT_ID")
def get_ip():
    try:
        r = requests.get(f"https://1.1.1.1/dns-query?name={SUPA_HOST}&type=A", headers={"accept": "application/dns-json"}, timeout=5)
        return r.json()['Answer'][0]['data']
    except: return "104.18.38.10"
SUPA_IP = get_ip()
orig = socket.getaddrinfo
def patched(h,p,f=0,t=0,pr=0,fl=0):
    if h==SUPA_HOST: return [(2,1,6,'',(SUPA_IP,p))]
    return orig(h,p,f,t,pr,fl)
socket.getaddrinfo = patched
def get_token():
    url=f"https://{SUPA_HOST}/auth/v1/token?grant_type=password"
    print(f"Calling {url}")
    r=requests.post(url, headers={"apikey": ANON, "Content-Type": "application/json"}, json={"email": EMAIL, "password": PASS}, timeout=15)
    print(f"STATUS: {r.status_code}")
    print(f"BODY: {r.text[:1000]}")
    if r.status_code != 200:
        raise Exception(f"Auth fail {r.status_code}: {r.text[:500]}")
    return r.json().get("access_token")
def get_chain():
    token=get_token()
    url=f"https://{SUPA_HOST}/functions/v1/get-option-chain"
    headers={"apikey": ANON, "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r=requests.post(url, headers=headers, json={"symbol": "NIFTY"}, timeout=15)
    return r.json()
def send_telegram(m):
    try: requests.get(f"https://api.telegram.org/bot{BOT}/sendMessage", params={"chat_id": CHAT, "text": m, "parse_mode": "Markdown"}, timeout=10)
    except: pass
@app.route('/')
def home():
    try:
        d=get_chain()
        return f"Bot Working! {str(d)[:1000]}"
    except Exception as e: return f"Error: {e}"
def loop():
    while True:
        try:
            d=get_chain()
            send_telegram(f"NIFTY Spot: {d.get('spot','OK')} - Connected!")
        except: pass
        time.sleep(900)
import threading; threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__": app.run(host='0.0.0.0', port=10000)
