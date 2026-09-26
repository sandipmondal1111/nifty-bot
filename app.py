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
LAST_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
PREV_DATA = {"ce_ltp": None, "pe_ltp": None, "last_scenario": ""}

def save_token(token):
    global FYERS_TOKEN
    FYERS_TOKEN = token
    try:
        with open(TOKEN_FILE, "w") as f:
            f.write(token)
    except:
        pass
    print("TOKEN SAVED", flush=True)

def load_token():
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                t = f.read().strip()
                if t:
                    return t
    except:
        pass
    return os.getenv("FYERS_ACCESS_TOKEN", "").strip()

FYERS_TOKEN = load_token()

@app.route('/')
def home():
    return f"Bot Live! Token: {bool(FYERS_TOKEN)} | Auto Alert ON"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

def send_telegram(chat_id, text):
    if not chat_id:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      json={"chat_id": chat_id, "text": text}, timeout=15)
    except Exception as e:
        print(f"TG SEND ERR {e}", flush=True)

# --- TUMHARA SCREENSHOT WALA 4 CONDITION LOGIC ---
def analyze_logic(ce_oich, ce_prem_up, pe_oich, pe_prem_up):
    # 1. Bullish Setup: CE COI UP + Premium UP and PE COI UP + Premium DOWN
    if ce_oich > 0 and ce_prem_up == True and pe_oich > 0 and pe_prem_up == False:
        return "📈 Bullish Setup", "Bullish Pressure", "CE BUYING SETUP"

    # 2. Bearish Setup: CE COI UP + Premium DOWN and PE COI UP + Premium UP
    elif ce_oich > 0 and ce_prem_up == False and pe_oich > 0 and pe_prem_up == True:
        return "📉 Bearish Setup", "Bearish Pressure", "PE BUYING SETUP"

    # 3. Strong Bullish Setup: CE COI DOWN + Premium UP and PE COI DOWN + Premium DOWN
    elif ce_oich < 0 and ce_prem_up == True and pe_oich < 0 and pe_prem_up == False:
        return "🚀 Strong Bullish Setup", "Strong Bullish Pressure", "CE BUYING SETUP (Continuation)"

    # 4. Strong Bearish Setup: CE COI DOWN + Premium DOWN and PE COI DOWN + Premium UP
    elif ce_oich < 0 and ce_prem_up == False and pe_oich < 0 and pe_prem_up == True:
        return "💥 Strong Bearish Setup", "Strong Bearish Pressure", "PE BUYING SETUP (Continuation)"

    # 5. Sideway
    else:
        return "⚠️ Sideway Market", "Market se dur raho!!!!!!", "NO ACTION"

def fetch_analysis():
    global PREV_DATA, FYERS_TOKEN
    if not FYERS_TOKEN:
        return None
    try:
        fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=FYERS_TOKEN, is_async=False, log_path="")
        oc_resp = fyers.optionchain(data={"symbol": "NSE:NIFTY50-INDEX", "strikecount": 1})

        if not oc_resp.get("data", {}).get("optionsChain"):
            print(f"OC RESP ERROR: {oc_resp}", flush=True)
            return None

        chain = oc_resp["data"]["optionsChain"][0]
        strike = chain["strike_price"]
        ce = chain.get("call", {})
        pe = chain.get("put", {})
        nifty_ltp = oc_resp["data"].get("lastPrice", 0)

        ce_ltp = ce.get('ltp', 0)
        pe_ltp = pe.get('ltp', 0)
        ce_oi = ce.get('oi', 0)
        pe_oi = pe.get('oi', 0)
        ce_oich = ce.get('oich', 0) # CHOI
        pe_oich = pe.get('oich', 0) # CHOI

        # First time data collect
        if PREV_DATA["ce_ltp"] is None:
            PREV_DATA["ce_ltp"] = ce_ltp
            PREV_DATA["pe_ltp"] = pe_ltp
            return None

        ce_prem_up = ce_ltp > PREV_DATA["ce_ltp"]
        pe_prem_up = pe_ltp > PREV_DATA["pe_ltp"]

        PREV_DATA["ce_ltp"] = ce_ltp
        PREV_DATA["pe_ltp"] = pe_ltp

        scenario, view, action = analyze_logic(ce_oich, ce_prem_up, pe_oich, pe_prem_up)

        msg = f"🔔 AUTO ALERT\n"
        msg += f"NIFTY {nifty_ltp} | ATM {strike}\n"
        msg += f"CE: LTP {ce_ltp} ({'↑' if ce_prem_up else '↓'}) | OI {ce_oi} | CHOI {ce_oich} ({'↑' if ce_oich>0 else '↓'})\n"
        msg += f"PE: LTP {pe_ltp} ({'↑' if pe_prem_up else '↓'}) | OI {pe_oi} | CHOI {pe_oich} ({'↑' if pe_oich>0 else '↓'})\n"
        msg += f"------------------------\n"
        msg += f"Scenario: {scenario}\n"
        msg += f"Market View: {view}\n"
        msg += f"Action: {action}"

        return scenario, msg, ce_oich, pe_oich

    except Exception as e:
        print(f"FETCH ERR {e}", flush=True)
        return None

# --- AUTO ALERT LOOP (BINA /oi BHEJE ALERT AAYEGA) ---
def auto_alert_loop():
    print("Auto Alert Loop Started", flush=True)
    while True:
        try:
            now = datetime.datetime.now()
            # Market time: Mon-Fri 9:15 to 15:30
            if now.weekday() < 5 and 9 <= now.hour < 16:
                res = fetch_analysis()
                if res:
                    scenario, msg, ce_oich, pe_oich = res
                    is_major_change = abs(ce_oich) > 100000 or abs(pe_oich) > 100000

                    # Alert tabhi jab scenario change ho ya bada OI change ho
                    if scenario!= PREV_DATA["last_scenario"] or is_major_change:
                        # Sideway ko ignore karo jab tak bada change na ho
                        if "Sideway" not in scenario or is_major_change:
                            if LAST_CHAT_ID:
                                send_telegram(LAST_CHAT_ID, msg)
                                print(f"ALERT SENT: {scenario}", flush=True)
                            PREV_DATA["last_scenario"] = scenario
        except Exception as e:
            print(f"AUTO ERR {e}", flush=True)
        time.sleep(60) # Har 60 sec check

def telegram_polling():
    global FYERS_TOKEN, LAST_CHAT_ID
    print("Telegram STARTED...", flush=True)
    last_update = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update+1}&timeout=10"
            r = requests.get(url, timeout=15).json()
            if not r.get("ok"):
                time.sleep(2)
                continue

            for upd in r.get("result", []):
                last_update = upd["update_id"]
                msg_obj = upd.get("message", {})
                text = msg_obj.get("text", "")
                chat_id = msg_obj.get("chat", {}).get("id")

                if chat_id:
                    LAST_CHAT_ID = str(chat_id)

                if not text:
                    continue

                print(f"GOT {text[:80]}", flush=True)
                low = text.lower()

                if "/status" in low:
                    status = f"✅ Bot Online\nToken: {bool(FYERS_TOKEN)}\nAuto Alert: ON\nLast Scenario: {PREV_DATA['last_scenario']}\nFile Exists: {os.path.exists(TOKEN_FILE)}"
                    send_telegram(chat_id, status)

                elif "/oi" in low or "/analysis" in low:
                    res = fetch_analysis()
                    if res:
                        send_telegram(chat_id, res[1])
                    else:
                        send_telegram(chat_id, "Data Collect ho raha hai, 1 min baad fir /oi bhejo\n(Market band hai to data nahi aayega)")

                elif "/auto_on" in low:
                    send_telegram(chat_id, f"✅ Auto Alert ON hai!\nAb se {LAST_CHAT_ID} pe bina bole alert aayega.\nHar 60 sec me check hoga.")

                elif "/token" in low:
                    s = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                    link = s.generate_authcode()
                    send_telegram(chat_id, f"🔗 Login Link:\n{link}")

                elif "auth_code" in text:
                    m = re.search(r"auth_code=([^&]+)", text)
                    if m:
                        code = m.group(1)
                        s = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                        s.set_token(code)
                        resp = s.generate_token()
                        print(f"RESP {resp}", flush=True)
                        if "access_token" in resp:
                            save_token(resp['access_token'])
                            FYERS_TOKEN = resp['access_token']
                            send_telegram(chat_id, "✅ Token Auto-Saved! Auto Alert chalu ho gaya. /auto_on bhejo confirm karne ke liye")
                        else:
                            send_telegram(chat_id, f"❌ Error: {resp}")
        except Exception as e:
            print(f"ERR {e}", flush=True)
        time.sleep(1)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    Thread(target=auto_alert_loop, daemon=True).start()
    telegram_polling()
