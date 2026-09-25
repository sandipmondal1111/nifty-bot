import os, time, threading, hashlib, requests
from flask import Flask
from datetime import datetime

app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN") # ye add karo Render pe
SECRET_ID = os.environ.get("SECRET_ID") # FYERS secret
FYERS_PIN = os.environ.get("FYERS_PIN")

ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")

@app.route('/')
def home(): return "Nifty Expiry Bot LIVE - Fixed"

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
        print("TG SENT")
    except Exception as e:
        print(f"TG Err {e}")

def refresh_fyers_token():
    global ACCESS_TOKEN
    try:
        h = hashlib.sha256(f"{CLIENT_ID}:{SECRET_ID}".encode()).hexdigest()
        r = requests.post("https://api-t1.fyers.in/api/v3/validate-refresh-token", json={
            "grant_type": "refresh_token",
            "appIdHash": h,
            "refresh_token": REFRESH_TOKEN,
            "pin": FYERS_PIN
        }, timeout=10).json()
        print(f"Refresh Response: {r}")
        if r.get('s') == 'ok':
            ACCESS_TOKEN = r['access_token']
            send_telegram(f"🔄 FYERS Token Auto-Refresh OK: {ACCESS_TOKEN[:10]}...")
            return True
        else:
            send_telegram(f"❌ Refresh FAIL: {r}")
            return False
    except Exception as e:
        print(f"Refresh Exc: {e}")
        return False

def bot_loop():
    from fyers_apiv3 import fyersModel

    send_telegram("✅ <b>Bot Restart - Fixed Version</b>\n1 Min Check | Auto Refresh ON")

    if not refresh_fyers_token():
        time.sleep(10)

    fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=ACCESS_TOKEN, is_async=False, log_path="")
    last_pe, last_ce = 0, 0

    while True:
        try:
            # Agar token expire to refresh
            q = fyers.quotes({"symbols":"NSE:NIFTY50-INDEX"})
            if q.get("s")!= "ok" or q.get("code") == 401:
                print(f"Quotes fail {q}, refreshing...")
                if refresh_fyers_token():
                    fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=ACCESS_TOKEN, is_async=False, log_path="")
                time.sleep(60); continue

            ltp = q["d"][0]["v"]["lp"]
            atm = int(round(ltp/50)*50)

            chain = fyers.optionchain(data={"symbol":"NSE:NIFTY50-INDEX","strikecount":30})
            if chain.get("s")!= "ok":
                print(f"Chain fail {chain}")
                time.sleep(60); continue

            oc = chain["data"]["optionsChain"]
            row = min(oc, key=lambda x: abs(x["strikePrice"]-atm))

            # FYERS v3 me ye field hai
            ce_oi = row.get("callOI", 0)
            pe_oi = row.get("putOI", 0)
            print(f"LTP {ltp} ATM {row['strikePrice']} PE {pe_oi} CE {ce_oi} last {last_pe}/{last_ce}")

            if ce_oi==0 and pe_oi==0: time.sleep(60); continue

            if last_pe == 0:
                last_pe, last_ce = pe_oi, ce_oi
                print("First OI set")
                time.sleep(60); continue

            pe_diff = pe_oi - last_pe
            ce_diff = ce_oi - last_ce

            # FIX: Har baar update karo taaki diff sahi rahe
            is_tuesday = datetime.now().weekday() == 1
            threshold = 100000 if is_tuesday else 50000

            if abs(pe_diff) >= threshold or abs(ce_diff) >= threshold:
                # tumhara wala title/action logic yahi rahega...
                #...
                msg = f"🚨 {'TUESDAY' if is_tuesday else 'NORMAL'} {row['strikePrice']} | NIFTY {ltp:.0f}\nPE {last_pe/100000:.2f}L -> {pe_oi/100000:.2f}L ({pe_diff/1000:.0f}k)\nCE {last_ce/100000:.2f}L -> {ce_oi/100000:.2f}L ({ce_diff/1000:.0f}k)"
                send_telegram(msg)
                last_pe, last_ce = pe_oi, ce_oi
            else:
                # FIX: Threshold na mile to bhi 5 min me baseline update karo
                # Nahi to diff bahut bada ho jayega
                last_pe, last_ce = pe_oi, ce_oi

            time.sleep(60)
        except Exception as e:
            print(f"Err {e}"); time.sleep(60)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
