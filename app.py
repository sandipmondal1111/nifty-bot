import requests, os, time, threading
from flask import Flask
app = Flask(__name__)

P = "kscckhjrasotwejshmr"
H = f"{P}.supabase.co"
K = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtzY2NraGpyYXNvdHdlamRzaG1yIiwicm9sZSI6ImFub24iLCJpYXQiOjE3N2YzNTU1MTc5ImV4cCI6MjAxMzkzMTU3N30.2KUybzVBJ97NzGA99OrMnNxvFs1P04cdHyyyl--dqs"
E = os.getenv("ROEIQ_EMAIL","").strip()
PW = os.getenv("ROEIQ_PASS","").strip()
B = os.getenv("BOT_TOKEN","").strip()
C = os.getenv("CHAT_ID","").strip()

def get_token():
    url = f"https://{H}/auth/v1/token?grant_type=password"
    headers = {"apikey": K, "Authorization": f"Bearer {K}", "Content-Type": "application/json"}
    # verify=False SSL error ko bypass karega
    r = requests.post(url, headers=headers, json={"email": E, "password": PW}, timeout=20, verify=False)
    if r.status_code != 200:
        raise Exception(f"Auth {r.status_code}: {r.text[:500]}")
    return r.json()["access_token"]

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
        return f"Bot Working! Spot: {d.get('spot')} - OK"
    except Exception as e:
        return f"Error: {e}"

def bg_loop():
    while True:
        try:
            d = get_chain()
            if B and C:
                requests.get(f"https://api.telegram.org/bot{B}/sendMessage", params={"chat_id": C, "text": f"NIFTY: {d.get('spot')}"}, timeout=10, verify=False)
        except Exception as e:
            print(e)
        time.sleep(900)

threading.Thread(target=bg_loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
