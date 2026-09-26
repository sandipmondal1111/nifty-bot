import os, time, requests, re, datetime
from flask import Flask
from threading import Thread
from fyers_apiv3 import fyersModel

app = Flask(__name__)

CLIENT_ID = os.getenv("CLIENT_ID", "").strip()
SECRET_KEY = os.getenv("FYERS_SECRET_KEY", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip().replace('"','').replace("'","")

TOKEN_FILE = "/tmp/fyers_token.txt"
FYERS_TOKEN = ""
LAST_CHAT_ID = None

def save_token(token):
    global FYERS_TOKEN
    FYERS_TOKEN = token
    try:
        with open(TOKEN_FILE, "w") as f: f.write(token)
    except: pass

def load_token():
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                t = f.read().strip()
                if t: return t
        except: pass
    return os.getenv("FYERS_ACCESS_TOKEN", "").strip()

FYERS_TOKEN = load_token()

@app.route('/')
def home(): return "ATM OI Bot Live"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

def send_telegram(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text}, timeout=10)
    except: pass

def get_atm_oi():
    global FYERS_TOKEN
    if not FYERS_TOKEN: return "Token nahi hai, /token karo"

    try:
        fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=FYERS_TOKEN, is_async=False, log_path="")

        # Nifty LTP
        nifty_resp = fyers.quotes(data={"symbols":"NSE:NIFTY50-INDEX"})
        ltp = nifty_resp['d'][0]['v']['lp']
        atm = round(ltp / 50) * 50

        # Expiry - Is Thursday ki expiry auto nikale
        today = datetime.date.today()
        # Next Thursday
        days_ahead = 3 - today.weekday() # Thursday = 3
        if days_ahead <= 0: days_ahead += 7
        next_thu = today + datetime.timedelta(days_ahead)
        expiry_str = next_thu.strftime("%y%b").upper() # jaise 26SEP26 -> 26SEP
        # Fyers format: 26OCT30 = 2026 ke liye? Fyers me 2 digit year
        expiry_fyers = f"{next_thu.strftime('%y')}{next_thu.strftime('%b').upper()[:3]}" # check
        # Simplest: Tumhe Fyers me symbol dekhna padega. Hum 2 format try karenge

        # Tumhare Fyers me symbol aise hota hai: NSE:NIFTY26OCT{STRIKE}CE
        # Isliye hum direct try karte hain
        yy = next_thu.strftime("%y")
        mmm = next_thu.strftime("%b").upper()
        dd = next_thu.strftime("%d")

        # Try 1: NSE:NIFTY26OCT0215000CE (common format)
        # Fyers latest format: NSE:NIFTY25O1624500CE type bhi hota hai

        # Isliye hum NSE ka option chain API use nahi kar rahe, direct symbol
        # Tum ek baar apne Fyers app me ATM CE ka symbol copy karke mujhe bhejo to mai 100% fix kar dunga

        # Abhi ke liye ye format use karo jo sabse zyada chalta hai:
        ce_sym = f"NSE:NIFTY{yy}{mmm}{atm}CE"
        pe_sym = f"NSE:NIFTY{yy}{mmm}{atm}PE"

        resp = fyers.quotes(data={"symbols": f"{ce_sym},{pe_sym}"})

        if not resp.get("d"):
            return f"Symbol Error\nTry kiye: {ce_sym}\nResp: {resp}\nApna Fyers ka ek CE symbol bhejo"

        out = f"NIFTY {ltp} | ATM {atm}\n"
        for d in resp['d']:
            oi = d['v'].get('oi',0)
            ltp_opt = d['v'].get('lp',0)
            out += f"{d['n'].split(':')[-1]}: LTP {ltp_opt} | OI {oi}\n"

        return out

    except Exception as e:
        return f"OI Error: {e}"

def telegram_polling():
    global LAST_CHAT_ID, FYERS_TOKEN
    last_update = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update+1}&timeout=10"
            r = requests.get(url, timeout=15).json()
            for upd in r.get("result", []):
                last_update = upd["update_id"]
                msg = upd.get("message",{})
                text = msg.get("text","")
                chat_id = msg.get("chat",{}).get("id")
                LAST_CHAT_ID = chat_id
                if not text: continue
                low = text.lower()

                if "/status" in low:
                    send_telegram(chat_id, f"✅ Bot Online\nATM: {get_atm_oi()}")

                elif "/oi" in low or "/atm" in low:
                    data = get_atm_oi()
                    send_telegram(chat_id, data)

                elif "/token" in low:
                    s = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                    link = s.generate_authcode()
                    send_telegram(chat_id, f"🔗 Login Link:\n{link}")

                elif "auth_code" in text:
                    m = re.search(r"auth_code=([^&]+)", text)
                    if m:
                        s = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                        s.set_token(m.group(1))
                        resp=s.generate_token()
                        if "access_token" in resp:
                            save_token(resp['access_token'])
                            FYERS_TOKEN = resp['access_token']
                            send_telegram(chat_id, f"✅ Token Saved!\nAb /oi bhejo ATM OI ke liye")
                        else:
                            send_telegram(chat_id, f"❌ {resp}")
        except Exception as e:
            print(f"ERR {e}", flush=True)
        time.sleep(1)

if __name__=="__main__":
    Thread(target=run_flask, daemon=True).start()
    telegram_polling()
