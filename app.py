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

# Sahi IP nikalne ka function
def get_all_ips():
    ips = []
    try:
        # Google DNS se
        r = requests.get(f"https://dns.google/resolve?name={H}&type=A", timeout=5).json()
        for a in r.get('Answer', []):
            if 'data' in a and '.' in a['data']:
                ips.append(a['data'])
    except: pass
    try:
        # Cloudflare DNS se
        r = requests.get(f"https://1.1.1.1/dns-query?name={H}&type=A", headers={"accept": "application/dns-json"}, timeout=5).json()
        for a in r.get('Answer', []):
            if 'data' in a and '.' in a['data']:
                ips.append(a['data'])
    except: pass
    # fallback IPs
    ips += ["104.21.33.34", "104.18.38.10", "172.67.158.15"]
    return list(dict.fromkeys(ips)) # unique

IPS = get_all_ips()
print(f"Trying IPs: {IPS}")

orig_getaddrinfo = socket.getaddrinfo
current_ip = [IPS[0] if IPS else "104.21.33.34"]

def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == H:
        return [(2, 1, 6, '', (current_ip[0], port))]
    return orig_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = patched_getaddrinfo

def get_token():
    url = f"https://{H}/auth/v1/token?grant_type=password"
    headers = {"apikey": K, "Authorization": f"Bearer {K}", "Content-Type": "application/json"}
    last_err = ""
    for ip in IPS:
        current_ip[0] = ip
        try:
            print(f"Trying IP {ip} for auth...")
            r = requests.post(url, headers=headers, json={"email": E, "password": PW}, timeout=15, verify=False)
            print(f"IP {ip} -> {r.status_code} {r.text[:200]}")
            if "Project not specified" in r.text:
                last_err = r.text
                continue # next IP try karo
            if r.status_code == 200:
                return r.json()["access_token"]
            last_err = r.text
        except Exception as e:
            print(f"IP {ip} failed: {e}")
            last_err = str(e)
            continue
    raise Exception(f"Auth fail: {last_err[:500]}")

def get_chain():
    t = get_token()
    url = f"https://{H}/functions/v1/get-option-chain"
    headers = {"apikey": K, "Authorization": f"Bearer {t}", "Content-Type": "application/json"}
    r = requests.post(url, headers=headers, json={"symbol": "NIFTY"}, timeout=20, verify=False)
    return r.json()

@app.route('/')
def home():
    try:
        d = get_chain()
        return f"Bot Working! Spot: {d.get('spot')} IP: {current_ip[0]}"
    except Exception as e:
        return f"Error: {e} | Tried IPs: {IPS}"

def bg_loop():
    while True:
        try:
            d = get_chain()
            if B and C:
                requests.get(f"https://api.telegram.org/bot{B}/sendMessage", params={"chat_id": C, "text": f"NIFTY: {d.get('spot')}"}, timeout=10, verify=False)
        except Exception as e:
            print(f"Loop: {e}")
        time.sleep(900)

threading.Thread(target=bg_loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
