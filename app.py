import os, time, hashlib, requests
from datetime import datetime
from fyers_apiv3 import fyersModel

CLIENT_ID = os.environ.get("CLIENT_ID", "XS45486")
SECRET_ID = os.environ.get("SECRET_ID", "QDCP2NLBMS") # Tumhara secret
FYERS_PIN = os.environ.get("FYERS_PIN", "1234") # Tumhara Fyers 4 digit PIN
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN") # my_token.py wala refresh_token
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode":"HTML"}, timeout=10)
    except: pass

def get_new_access_token():
    try:
        # 1. APP_ID_HASH banao
        app_hash = hashlib.sha256(f"{CLIENT_ID}:{SECRET_ID}".encode()).hexdigest()

        # 2. Refresh API call
        url = "https://api-t1.fyers.in/api/v3/validate-refresh-token"
        payload = {
            "grant_type": "refresh_token",
            "appIdHash": app_hash,
            "refresh_token": REFRESH_TOKEN,
            "pin": FYERS_PIN
        }
        r = requests.post(url, json=payload, timeout=10).json()
        print(f"Refresh Response: {r}")

        if r.get('s')=='ok' or 'access_token' in r:
            access = r.get('data',{}).get('access_token') or r.get('access_token')
            print("New Access Token Mil Gaya!")
            return f"{CLIENT_ID}:{access}"
        else:
            # Fallback - ENV wala access token
            print("Refresh fail, ENV token use kar raha hu")
            at = os.environ.get("ACCESS_TOKEN")
            return f"{CLIENT_ID}:{at}" if at and not at.startswith(CLIENT_ID) else at

    except Exception as e:
        print(f"Token Refresh Error {e}")
        at = os.environ.get("ACCESS_TOKEN")
        return f"{CLIENT_ID}:{at}" if at else None

# Startup pe ek baar token refresh
ACCESS_TOKEN_FULL = get_new_access_token()
fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=ACCESS_TOKEN_FULL, log_path="")
send_tg(f"✅ <b>Bot ON - Auto Token Active</b>\nHash: {hashlib.sha256(f'{CLIENT_ID}:{SECRET_ID}'.encode()).hexdigest()[:10]}...")

prev_call = None
prev_put = None

while True:
    try:
        res = fyers.optionchain(data={"symbol":"NSE:NIFTY50-INDEX","strikecount":15})
        if res.get('s')!='ok':
            print(f"API Error, Token Refresh kar raha hu {res}")
            ACCESS_TOKEN_FULL = get_new_access_token()
            fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=ACCESS_TOKEN_FULL, log_path="")
            time.sleep(10)
            continue

        chain = res['data']['optionsChain']
        ltp = chain[0].get('ltp',0)
        atm = round(ltp/50)*50

        call_choi = put_choi = 0
        for opt in chain:
            sp = opt.get('strike_price',0)
            if sp>0 and abs(sp-atm) <=150:
                ch = opt.get('oich',{}).get('ch',0)
                sym = opt.get('symbol','')
                if 'CE' in sym: call_choi+=ch
                elif 'PE' in sym: put_choi+=ch

        call_l = call_choi/100000
        put_l = put_choi/100000

        if prev_call is None:
            chg_c, chg_p = call_l, put_l
        else:
            chg_c = call_l - prev_call
            chg_p = put_l - prev_put

        # --- 3 LEVEL SENTIMENT ---
        if chg_c>=20 and chg_p<=-5:
            senti="🔴 BEARISH - Call Writing"; sugg="Sell on Rise"
        elif chg_p>=20 and chg_c<=-5:
            senti="🟢 BULLISH - Put Writing"; sugg="Buy on Dip"
        elif chg_c<=-15 and chg_p<=-15:
            senti="⚡ BOTH UNWIND - Big Move"; sugg="Straddle Buy"
        elif chg_c<=-15:
            senti="🟢 Call Unwinding"; sugg="Short Covering"
        elif chg_p<=-15:
            senti="🔴 Put Unwinding"; sugg="Long Unwinding"
        else:
            senti="🟡 MIXED"; sugg="Wait & Watch"

        print(f"{datetime.now().strftime('%H:%M:%S')} LTP:{ltp} C:{chg_c:+.1f} P:{chg_p:+.1f} {senti}")

        # Alert
        if prev_call is not None and (abs(chg_c)>=20 or abs(chg_p)>=20 or datetime.now().minute%15==0):
            msg = f"🚨 <b>NIFTY {datetime.now().strftime('%H:%M:%S')}</b>\nLTP:{ltp} ATM:{atm}\nC:{call_l:.1f}L ({chg_c:+.1f}L)\nP:{put_l:.1f}L ({chg_p:+.1f}L)\n\n{senti}\n💡{sugg}"
            send_tg(msg)

        prev_call, prev_put = call_l, put_l
        time.sleep(60)

    except Exception as e:
        print(e)
        time.sleep(10)
