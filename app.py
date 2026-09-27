import os, time, requests, re, datetime
from flask import Flask
from threading import Thread, Lock
from fyers_apiv3 import fyersModel

app = Flask(__name__)

CLIENT_ID = os.getenv("CLIENT_ID", "").strip()
SECRET_KEY = os.getenv("FYERS_SECRET_KEY", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip().replace('"','').replace("'","")
TOKEN_FILE = "/tmp/fyers_token.txt"
FYERS_TOKEN = ""
LAST_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

DATA_LOCK = Lock()
PREV_DATA = {"ce_ltp": None, "pe_ltp": None, "ce_oich": 0, "pe_oich": 0, "last_scenario": "", "last_alert_time": 0, "last_major_alert": 0}
TOKEN_ALERT_DATE = ""

def save_token(t):
    global FYERS_TOKEN
    FYERS_TOKEN = t.strip()
    try: 
        with open(TOKEN_FILE,"w") as f:
            f.write(FYERS_TOKEN)
    except: pass
    print(f"TOKEN SAVED len={len(FYERS_TOKEN)}", flush=True)

def load_token():
    try:
        if os.path.exists(TOKEN_FILE):
            t = open(TOKEN_FILE,"r").read().strip()
            if t: return t
    except: pass
    return os.getenv("FYERS_ACCESS_TOKEN","").strip()

FYERS_TOKEN = load_token()

@app.route('/')
def home(): 
    return f"Bot Live! Token:{bool(FYERS_TOKEN)} | Last:{PREV_DATA['last_scenario']}"

def run_flask(): 
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))

def send_telegram(chat_id, text):
    if not chat_id: return
    try: 
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text}, timeout=15)
    except Exception as e: 
        print(f"TG ERR {e}", flush=True)

def analyze_all(ce_oich, pe_oich, ce_diff, pe_diff, ce_up, pe_up, nifty, sup, res):
    FAST = 50000
    if abs(nifty-sup) < 60 and ce_diff < -FAST and pe_diff > FAST:
        return f"🔥 SUPPORT BOUNCE @ {sup}\nCE CHOI {ce_diff/1000:.0f}k/min gir raha, PE CHOI +{pe_diff/1000:.0f}k/min badh raha", "Strong Bullish - Support Hold", "CE BUY"
    if abs(nifty-res) < 60 and ce_diff > FAST and pe_diff < -FAST:
        return f"🔥 RESISTANCE REJECTION @ {res}\nCE CHOI +{ce_diff/1000:.0f}k/min badh raha, PE CHOI {pe_diff/1000:.0f}k/min gir raha", "Strong Bearish - Resistance Hold", "PE BUY"
    if nifty > res and ce_diff < -FAST:
        return f"🚀 BREAKOUT @ {res}\nNIFTY {nifty} > Res {res}, CE unwinding {ce_diff/1000:.0f}k/min", "Breakout Bullish", "CE BUY"
    if nifty < sup and pe_diff < -FAST:
        return f"💥 BREAKDOWN @ {sup}\nNIFTY {nifty} < Sup {sup}, PE unwinding {pe_diff/1000:.0f}k/min", "Breakdown Bearish", "PE BUY"
    if ce_oich > 0 and ce_up and pe_oich > 0 and not pe_up:
        return "📈 Bullish Setup", "Bullish Pressure", "CE BUYING SETUP"
    if ce_oich > 0 and not ce_up and pe_oich > 0 and pe_up:
        return "📉 Bearish Setup", "Bearish Pressure", "PE BUYING SETUP"
    if ce_oich < 0 and ce_up and pe_oich < 0 and not pe_up:
        return "🚀 Strong Bullish Setup", "Strong Bullish Pressure", "CE BUY (Continuation)"
    if ce_oich < 0 and not ce_up and pe_oich < 0 and pe_up:
        return "💥 Strong Bearish Setup", "Strong Bearish Pressure", "PE BUY (Continuation)"
    return "⚠️ Sideway Market", "Market se dur raho", "NO ACTION"

def get_chain_data():
    global FYERS_TOKEN
    if not FYERS_TOKEN: 
        return None, "NO_TOKEN"
    try:
        fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=FYERS_TOKEN, is_async=False, log_path="")
        resp = fyers.optionchain(data={"symbol":"NSE:NIFTY50-INDEX","strikecount":15})
        # FIX: -15 bhi token error hai
        if resp.get("code") in [-401, -402, -15] or "Invalid token" in str(resp) or "valid token" in str(resp).lower() or "Token has expired" in str(resp):
            return None, "TOKEN_EXPIRE"
        if not resp.get("data",{}).get("optionsChain"):
            return None, f"OC Error: {resp}"
        
        chains = resp["data"]["optionsChain"]
        nifty_ltp = resp["data"].get("lastPrice",0)
        
        max_pe_oi, max_ce_oi = 0,0
        sup, res = 0,0
        for ch in chains:
            pe_oi = ch.get("put",{}).get("oi",0)
            ce_oi = ch.get("call",{}).get("oi",0)
            if pe_oi > max_pe_oi:
                max_pe_oi = pe_oi
                sup = ch["strike_price"]
            if ce_oi > max_ce_oi:
                max_ce_oi = ce_oi
                res = ch["strike_price"]
        
        atm_chain = min(chains, key=lambda x: abs(x["strike_price"]-nifty_ltp))
        return {"nifty":nifty_ltp, "atm":atm_chain, "sup":sup, "res":res, "sup_oi":max_pe_oi, "res_oi":max_ce_oi}, None
    except Exception as e:
        return None, str(e)

def fetch_for_auto():
    global PREV_DATA
    data, err = get_chain_data()
    if err: return err
    if not data: return None
    
    atm = data["atm"]
    ce = atm.get("call",{}); pe = atm.get("put",{})
    ce_ltp, pe_ltp = ce.get('ltp',0), pe.get('ltp',0)
    ce_oich, pe_oich = ce.get('oich',0), pe.get('oich',0)
    
    with DATA_LOCK:
        if PREV_DATA["ce_ltp"] is None:
            PREV_DATA["ce_ltp"]=ce_ltp; PREV_DATA["pe_ltp"]=pe_ltp
            PREV_DATA["ce_oich"]=ce_oich; PREV_DATA["pe_oich"]=pe_oich
            return None
        ce_up = ce_ltp > PREV_DATA["ce_ltp"]
        pe_up = pe_ltp > PREV_DATA["pe_ltp"]
        ce_diff = ce_oich - PREV_DATA["ce_oich"]
        pe_diff = pe_oich - PREV_DATA["pe_oich"]
        PREV_DATA["ce_ltp"]=ce_ltp; PREV_DATA["pe_ltp"]=pe_ltp
        PREV_DATA["ce_oich"]=ce_oich; PREV_DATA["pe_oich"]=pe_oich

    scenario, view, action = analyze_all(ce_oich, pe_oich, ce_diff, pe_diff, ce_up, pe_up, data["nifty"], data["sup"], data["res"])
    
    msg = f"🔔 {scenario}\nNIFTY {data['nifty']} | ATM {atm['strike_price']}\nSup {data['sup']} (PE OI {data['sup_oi']/100000:.1f}L) | Res {data['res']} (CE OI {data['res_oi']/100000:.1f}L)\nCE LTP {ce_ltp} ({'↑' if ce_up else '↓'}) CHOI {ce_oich} [{ce_diff/1000:+.0f}k/m]\nPE LTP {pe_ltp} ({'↑' if pe_up else '↓'}) CHOI {pe_oich} [{pe_diff/1000:+.0f}k/m]\nView: {view}\nAction: {action}"
    return scenario, msg, ce_diff, pe_diff

def auto_alert_loop():
    global TOKEN_ALERT_DATE
    while True:
        try:
            now = datetime.datetime.now()
            today = now.strftime("%Y-%m-%d")
            if now.hour==8 and TOKEN_ALERT_DATE!=today:
                _, err = get_chain_data()
                if err in ["TOKEN_EXPIRE", "NO_TOKEN"] and LAST_CHAT_ID:
                    send_telegram(LAST_CHAT_ID,"❌ Token Expire / Missing hai! /token bhejo login karne ke liye.")
                    TOKEN_ALERT_DATE=today
            
            if now.weekday()<5 and 9 <= now.hour < 16:
                res = fetch_for_auto()
                if res in ["TOKEN_EXPIRE", "NO_TOKEN"]:
                    if TOKEN_ALERT_DATE!=today and LAST_CHAT_ID:
                        send_telegram(LAST_CHAT_ID,"❌ Token Expire! /token bhejo")
                        TOKEN_ALERT_DATE=today
                elif res and isinstance(res, tuple):
                    scenario, msg, ce_diff, pe_diff = res
                    with DATA_LOCK:
                        last_sc = PREV_DATA["last_scenario"]
                        last_major = PREV_DATA["last_major_alert"]
                    is_fast = abs(ce_diff)>50000 or abs(pe_diff)>50000
                    now_ts = time.time()
                    should=False
                    if scenario!=last_sc and "Sideway" not in scenario: 
                        should=True
                    elif is_fast and (now_ts-last_major)>300 and "Sideway" not in scenario:
                        should=True
                        with DATA_LOCK: 
                            PREV_DATA["last_major_alert"]=now_ts
                    if should and LAST_CHAT_ID:
                        send_telegram(LAST_CHAT_ID, msg)
                        with DATA_LOCK:
                            PREV_DATA["last_scenario"]=scenario
                            PREV_DATA["last_alert_time"]=now_ts
        except Exception as e: 
            print(f"AUTO ERR {e}", flush=True)
        time.sleep(60)

def telegram_polling():
    global FYERS_TOKEN, LAST_CHAT_ID
    last_update=0
    while True:
        try:
            r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update+1}&timeout=10", timeout=15).json()
            if not r.get("ok"): 
                time.sleep(2); continue
            for upd in r.get("result",[]):
                last_update=upd["update_id"]
                msg_obj=upd.get("message",{})
                chat_id=msg_obj.get("chat",{}).get("id")
                text=msg_obj.get("text","")
                if chat_id: LAST_CHAT_ID=str(chat_id)
                if not text: continue
                low=text.lower()
                if "/status" in low:
                    with DATA_LOCK: sc=PREV_DATA["last_scenario"]
                    send_telegram(chat_id, f"✅ Bot Online\nTime:{datetime.datetime.now().strftime('%H:%M:%S')}\nToken:{bool(FYERS_TOKEN)}\nLast:{sc}\nAuto ON 9-16 | Sup/Res 15 strikes")
                elif "/oi" in low:
                    data, err = get_chain_data()
                    if err in ["TOKEN_EXPIRE","NO_TOKEN"]: 
                        send_telegram(chat_id,"❌ Token Expire! /token bhejo")
                    elif not data: 
                        send_telegram(chat_id, f"Err: {err}")
                    else:
                        atm=data["atm"]; ce=atm.get("call",{}); pe=atm.get("put",{})
                        send_telegram(chat_id, f"NIFTY {data['nifty']} ATM {atm['strike_price']}\nSup {data['sup']} PE OI {data['sup_oi']/100000:.1f}L\nRes {data['res']} CE OI {data['res_oi']/100000:.1f}L\nCE CHOI {ce.get('oich',0)} PE CHOI {pe.get('oich',0)}")
                elif "/token" in low:
                    s=fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                    send_telegram(chat_id, f"🔗 Login Link:\n{s.generate_authcode()}\n\nLogin ke baad jo link mile usko yahin paste karo")
                elif "auth_code" in text:
                    m=re.search(r"auth_code=([^&]+)", text)
                    if m:
                        s=fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                        s.set_token(m.group(1))
                        resp=s.generate_token()
                        if "access_token" in resp:
                            save_token(resp['access_token']); FYERS_TOKEN=resp['access_token']
                            send_telegram(chat_id,"✅ Token Saved! Auto Alert ON hai.")
                        else: 
                            send_telegram(chat_id, f"❌ {resp}")
        except Exception as e: 
            print(f"POLL ERR {e}", flush=True)
        time.sleep(1)

if __name__=="__main__":
    Thread(target=run_flask, daemon=True).start()
    Thread(target=auto_alert_loop, daemon=True).start()
    telegram_polling()
