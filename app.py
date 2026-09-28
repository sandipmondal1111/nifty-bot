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
LAST_CHAT_ID = os.getenv("CHAT_ID", "").strip() or os.getenv("TELEGRAM_CHAT_ID", "").strip()

def save_token(t):
    global FYERS_TOKEN
    t = t.strip().split(":")[-1] # sirf raw
    FYERS_TOKEN = t
    try:
        with open(TOKEN_FILE,"w") as f:
            f.write(t)
    except: pass
    print(f"TOKEN SAVED len={len(t)}", flush=True)

def load_token():
    try:
        if os.path.exists(TOKEN_FILE):
            t = open(TOKEN_FILE).read().strip().split(":")[-1]
            if t: return t
    except: pass
    return os.getenv("FYERS_ACCESS_TOKEN","").strip().split(":")[-1]

FYERS_TOKEN = load_token()

@app.route('/')
def home():
    return f"Bot Live! Token:{bool(FYERS_TOKEN)}"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))

def send_telegram(chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text}, timeout=15)
    except: pass

def get_chain_data():
    if not FYERS_TOKEN:
        return None, "NO_TOKEN"
    try:
        # Library ko CLIENT_ID:TOKEN chahiye
        token_full = f"{CLIENT_ID}:{FYERS_TOKEN}"
        fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=token_full, is_async=False, log_path="")

        qr = fyers.quotes(data={"symbols":"NSE:NIFTY50-INDEX"})
        print(f"LIB QUOTES: {qr}", flush=True)
        if qr.get("s")!="ok":
            return None, f"TOKEN_EXPIRE / Quotes Error: {qr}"

        nifty = qr["d"][0]["v"]["lp"]

        oc = fyers.optionchain(data={"symbol":"NSE:NIFTY50-INDEX","strikecount":15})
        print(f"LIB OC: s={oc.get('s')} code={oc.get('code')} last={oc.get('data',{}).get('lastPrice')}", flush=True)
        if oc.get("s")!="ok":
            return None, f"OC Error: {oc}"

        chains = oc["data"]["optionsChain"]
        max_pe, max_ce, sup, res = 0,0,0,0
        for ch in chains:
            if ch.get("put",{}).get("oi",0) >= max_pe:
                max_pe = ch["put"]["oi"]; sup = ch["strike_price"]
            if ch.get("call",{}).get("oi",0) >= max_ce:
                max_ce = ch["call"]["oi"]; res = ch["strike_price"]
        atm = min(chains, key=lambda x: abs(x["strike_price"]-nifty))
        return {"nifty":nifty, "atm":atm, "sup":sup, "res":res, "sup_oi":max_pe, "res_oi":max_ce}, None
    except Exception as e:
        import traceback; traceback.print_exc()
        return None, str(e)

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
                chat_id=upd.get("message",{}).get("chat",{}).get("id")
                text=upd.get("message",{}).get("text","")
                if chat_id: LAST_CHAT_ID=str(chat_id)
                if not text: continue

                if "/oi" in text.lower():
                    data, err = get_chain_data()
                    if err and "TOKEN_EXPIRE" in str(err):
                        send_telegram(chat_id,"❌ Token Expire! /token bhejo")
                    elif not data:
                        send_telegram(chat_id,f"Err: {err}")
                    else:
                        send_telegram(chat_id,f"✅ NIFTY {data['nifty']} ATM {data['atm']['strike_price']}\nSup {data['sup']} PE OI {data['sup_oi']/100000:.1f}L\nRes {data['res']} CE OI {data['res_oi']/100000:.1f}L")

                elif "/token" in text.lower():
                    s=fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                    send_telegram(chat_id,f"🔗 Login Link:\n{s.generate_authcode()}\n\nLogin ke baad link paste karo")

                elif "auth_code" in text:
                    m=re.search(r"auth_code=([^&]+)", text)
                    if m:
                        send_telegram(chat_id,"⏳ Token generate...")
                        s=fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html", response_type="code", grant_type="authorization_code")
                        s.set_token(m.group(1))
                        resp=s.generate_token()
                        print(f"GEN RESP: {resp}", flush=True)
                        if "access_token" in resp:
                            save_token(resp['access_token'])
                            FYERS_TOKEN=load_token()
                            data, err = get_chain_data()
                            if err:
                                send_telegram(chat_id,f"⚠️ Token bana par fail: {err}")
                            else:
                                send_telegram(chat_id,f"✅ Token Accepted! NIFTY {data['nifty']} ATM {data['atm']['strike_price']} Sup {data['sup']} Res {data['res']}")
                        else:
                            send_telegram(chat_id,f"❌ Rejected: {resp}")
        except Exception as e:
            print(f"POLL ERR {e}", flush=True)
        time.sleep(1)

if __name__=="__main__":
    Thread(target=run_flask, daemon=True).start()
    telegram_polling()
