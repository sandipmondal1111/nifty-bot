import requests, os, socket, time, threading
from flask import Flask
app = Flask(__name__)

P = "kscckhjrasotwejshmr"
H = f"{P}.supabase.co"
K = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtzY2NraGpyYXNvdHdlamRzaG1yIiwicm9sZSI6ImFub24iLCJpYXQiOjE3N2YzNTU1MTc5ImV4cCI6MjAxMzkzMTU3N30.2KUybzVBJ97NzGA99OrMnNxvFs1P04cdHyyyl--dqs"
E = os.getenv("ROEIQ_EMAIL","").strip()
PW = os.getenv("ROEIQ_PASS","").strip()
B = os.getenv("BOT_TOKEN","").strip()
C = os.getenv("CHAT_ID","").strip()

# DNS fix - Render ka DNS fail hota hai isliye
def get_ips():
    try:
        r = requests.get(f"https://dns.google/resolve?name={H}&type=A", timeout=5).json()
        return [a['data'] for a in r.get('Answer', []) if '.' in a.get('data','')]
    except:
        return ["104.21.33.34"]
IPS = get_ips() or ["104.21.33.34"]
IP = IPS[0]
print(f"Using IP: {IP}")

orig = socket.getaddrinfo
def patched(h,p,f=0,t=0,pr=0,fl=0):
    if h == H:
        return [(2,1,6,'',(IP,p))]
    return orig(h,p,f,t,pr,fl)
socket.getaddrinfo = patched

def get_chain_direct():
    url = f"https://{H}/functions/v1/get-option-chain"
    # Bina user token ke, sirf anon key se
    headers = {
        "apikey": K,
        "Authorization": f"Bearer {K}",
        "Content-Type": "application/json",
        "x-client-info": "supabase-js/2.0.0"
    }
    r = requests.post(url, headers=headers, json={"symbol": "NIFTY"}, timeout=20, verify=False)
    print(f"Direct call: {r.status_code} {r.text[:500]}")
    if r.status_code == 200:
        return r.json()
    raise Exception(f"Direct fail {r.status_code}: {r.text[:500]}")

@app.route('/')
def home():
    try:
        d = get_chain_direct()
        return f"Bot Working! {d}"
    except Exception as e:
        return f"Error: {e}"

def bg_loop():
    while True:
        try:
            d = get_chain_direct()
            spot = d.get('spot','N/A')
            if B and C:
                requests.get(f"https://api.telegram.org/bot{B}/sendMessage", params={"chat_id": C, "text": f"NIFTY Spot: {spot}"}, timeout=10, verify=False)
            print(f"Loop OK: {spot}")
        except Exception as e:
            print(f"Loop err: {e}")
        time.sleep(900)

threading.Thread(target=bg_loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
