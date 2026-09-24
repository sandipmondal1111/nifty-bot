import requests, os, socket, time, threading
from flask import Flask
app = Flask(__name__)

P = "kscckhjrasotwejshmr"
H = f"{P}.supabase.co"
K = os.getenv("SUPABASE_KEY","").strip()
E = os.getenv("ROEIQ_EMAIL","").strip()
PW = os.getenv("ROEIQ_PASS","").strip()
B = os.getenv("BOT_TOKEN","").strip()
C = os.getenv("CHAT_ID","").strip()

# DNS fix - yehi SSL error fix karta hai
def get_ip():
    try:
        r = requests.get(f"https://1.1.1.1/dns-query?name={H}&type=A", headers={"accept": "application/dns-json"}, timeout=5)
        return r.json()['Answer'][0]['data']
    except:
        return "104.18.38.10"
IP = get_ip()
orig = socket.getaddrinfo
def patched(host,port,f=0,t=0,pr=0,fl=0):
    if host == H:
        return [(2,1,6,'',(IP,port))]
    return orig(host,port,f,t,pr,fl)
socket.getaddrinfo = patched

def get_token():
    url = f"https://{H}/auth/v1/token?grant_type=password"
    r = requests.post(url, headers={"apikey": K, "Authorization": f"Bearer {K}", "Content-Type": "application/json"}, json={"email": E, "password": PW}, timeout=20)
    if r.status_code!= 200:
        raise Exception(f"Auth {r.status_code}: {r.text[:300]}")
    return r.json()["access_token"]

def get_chain():
    t = get_token()
    url = f"https://{H}/functions/v1/get-option-chain"
    r = requests.post(url, headers={"apikey": K, "Authorization": f"Bearer {t}", "Content-Type": "application/json"}, json={"symbol": "NIFTY"}, timeout=20)
    return r.json()

@app.route('/')
def home():
    try:
        d = get_chain()
        return f"Bot Working! Spot: {d.get('spot')} - OK"
    except Exception as e:
        return f"Error: {e}"

def bg_loop():
    while True:
        try:
            d = get_chain()
            spot = d.get('spot','N/A')
            if B and C:
                requests.get(f"https://api.telegram.org/bot{B}/sendMessage", params={"chat_id": C, "text": f"NIFTY: {spot} ✅ Connected"}, timeout=10)
            print(f"Sent: {spot}")
        except Exception as e:
            print(f"Loop error: {e}")
        time.sleep(900) # 15 min

threading.Thread(target=bg_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
