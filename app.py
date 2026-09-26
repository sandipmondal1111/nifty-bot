import os, time, threading, requests
from flask import Flask
from datetime import datetime

app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")

# Flag ko file ki tarah memory me rakhenge
error_sent = False
last_error_time = 0

@app.route('/')
def home(): return "Nifty Bot LIVE - Manual Token"

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except: pass

def bot_loop():
    global error_sent, last_error_time
    from fyers_apiv3 import fyersModel

    send_telegram("✅ <b>Bot LIVE - Fixed No-Spam</b>\nTuesday 1L | Normal 50K")

    last_pe, last_ce = 0, 0

    while True:
        try:
            # IMPORTANT: Har baar naya token env se padho
            ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
            fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=ACCESS_TOKEN, is_async=False, log_path="")

            q = fyers.quotes({"symbols":"NSE:NIFTY50-INDEX"})
            if q.get("s")!="ok":
                print(f"Token Expire {q}")
                # 6 ghante me sirf 1 baar msg
                if not error_sent or (time.time() - last_error_time > 21600):
                    send_telegram("❌ <b>ACCESS_TOKEN Expire</b>\nFyers se naya token bana ke Render > Environment me daalo\nYe msg ab 6 ghante me 1 baar hi aayega.")
                    error_sent = True
                    last_error_time = time.time()
                time.sleep(300)
                continue

            error_sent = False # Token sahi hote hi flag reset
            ltp = q["d"][0]["v"]["lp"]
            atm = int(round(ltp/50)*50)
            chain = fyers.optionchain(data={"symbol":"NSE:NIFTY50-INDEX","strikecount":30})
            if chain.get("s")!="ok": time.sleep(60); continue

            oc = chain["data"]["optionsChain"]
            row = min(oc, key=lambda x: abs(x["strikePrice"]-atm))
            pe_oi = row.get("putOI",0); ce_oi = row.get("callOI",0)
            if pe_oi==0 and ce_oi==0: time.sleep(60); continue

            if last_pe==0: last_pe,last_ce=pe_oi,ce_oi; time.sleep(60); continue

            pe_diff = pe_oi - last_pe
            ce_diff = ce_oi - last_ce
            is_tue = datetime.now().weekday()==1
            thr = 100000 if is_tue else 50000
            tag = "TUESDAY EXPIRY" if is_tue else "NORMAL DAY"

            if abs(pe_diff)>=thr or abs(ce_diff)>=thr:
                msg = f"🚨 <b>{tag}</b>\nNIFTY {ltp:.0f} | ATM {row['strikePrice']}\nPE {last_pe/100000:.2f}L -> {pe_oi/100000:.2f}L ({pe_diff/1000:+.0f}k)\nCE {last_ce/100000:.2f}L -> {ce_oi/100000:.2f}L ({ce_diff/1000:+.0f}k)"
                send_telegram(msg)

            last_pe,last_ce = pe_oi, ce_oi
            time.sleep(60)
        except Exception as e:
            print(f"Err {e}"); time.sleep(60)

threading.Thread(target=bot_loop, daemon=True).start()
if __name__=="__main__": app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
