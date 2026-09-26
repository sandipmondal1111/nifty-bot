import os, time, threading, requests
from flask import Flask
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")

# NSE HOLIDAYS 2026
NSE_HOLIDAYS_2026 = [
    "2026-01-26", "2026-03-03", "2026-03-26", "2026-03-31",
    "2026-04-03", "2026-04-14", "2026-05-01", "2026-05-28",
    "2026-06-26", "2026-09-14", "2026-10-02", "2026-10-20",
    "2026-11-10", "2026-11-24", "2026-12-25",
]

error_sent = False
last_error_time = 0

@app.route('/')
def home():
    return "Nifty Bot LIVE"

def get_ist_now():
    return datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

def is_market_closed():
    now = get_ist_now()
    if now.weekday() >= 5:
        return True, f"Weekend {now.strftime('%A')}"
    today = now.strftime("%Y-%m-%d")
    if today in NSE_HOLIDAYS_2026:
        return True, f"NSE Holiday {today}"
    return False, ""

def send_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
    except:
        pass

def bot_loop():
    global error_sent, last_error_time
    from fyers_apiv3 import fyersModel

    # ====== SATURDAY TEST BLOCK ======
    try:
        ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
        FULL_TOKEN = f"{CLIENT_ID}:{ACCESS_TOKEN}" if ACCESS_TOKEN and ":" not in ACCESS_TOKEN else ACCESS_TOKEN
        fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=FULL_TOKEN, is_async=False, log_path="")

        q = fyers.quotes({"symbols": "NSE:NIFTY50-INDEX"})
        if q.get("s") == "ok":
            ltp = q["d"][0]["v"]["lp"]
            chain = fyers.optionchain(data={"symbol": "NSE:NIFTY50-INDEX", "strikecount": 10})
            if chain.get("s") == "ok":
                oc = chain["data"]["optionsChain"]
                atm = int(round(ltp / 50) * 50)
                row = min(oc, key=lambda x: abs(x["strikePrice"] - atm))
                pe_oi = row.get("putOI", row.get("put_oi", 0))
                ce_oi = row.get("callOI", row.get("call_oi", 0))

                send_telegram(
                    f"🧪 <b>SATURDAY TEST OK</b>\n"
                    f"NIFTY {ltp:.0f} | ATM {row['strikePrice']}\n"
                    f"PE OI: {pe_oi/100000:.2f} Lakh\n"
                    f"CE OI: {ce_oi/100000:.2f} Lakh\n\n"
                    f"Ye Friday ka closing OI hai.\n"
                    f"Aaj change 0 hai isliye alert nahi ayega.\n"
                    f"Monday 9:15 se Live alert chalu hoga."
                )
    except Exception as e:
        print(f"Test block error {e}")

    # ====== NORMAL BOT START ======
    closed, reason = is_market_closed()
    if closed:
        print(f"{reason} - No LIVE msg, sleeping 1hr after test")
        time.sleep(3600)
    else:
        send_telegram("✅ <b>Bot LIVE</b>\nTue 1L | Normal 50K | Weekend OFF")

    last_pe, last_ce = 0, 0

    while True:
        try:
            closed, reason = is_market_closed()
            if closed:
                print(f"{reason} - sleeping 1hr")
                time.sleep(3600)
                continue

            ist = get_ist_now()
            if ist.hour < 9 or (ist.hour == 9 and ist.minute < 15) or ist.hour >= 16:
                print(f"Market hours closed {ist.strftime('%H:%M')} - sleep 5min")
                time.sleep(300)
                continue

            ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
            FULL_TOKEN = f"{CLIENT_ID}:{ACCESS_TOKEN}" if ":" not in ACCESS_TOKEN else ACCESS_TOKEN
            fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=FULL_TOKEN, is_async=False, log_path="")

            q = fyers.quotes({"symbols": "NSE:NIFTY50-INDEX"})
            if q.get("s")!= "ok":
                print(f"Quotes fail {q}")
                code = q.get("code", 0)
                txt = str(q.get("message", "")).lower()
                if code in [-8, -11, -21] or "token" in txt or "expire" in txt:
                    if not error_sent or (time.time() - last_error_time > 21600):
                        c, _ = is_market_closed()
                        if not c:
                            send_telegram("❌ <b>ACCESS_TOKEN Expire</b>")
                            error_sent = True
                            last_error_time = time.time()
                time.sleep(300)
                continue

            error_sent = False
            ltp = q["d"][0]["v"]["lp"]
            atm = int(round(ltp / 50) * 50)

            chain = fyers.optionchain(data={"symbol": "NSE:NIFTY50-INDEX", "strikecount": 30})
            if chain.get("s")!= "ok":
                print(f"Chain fail {chain}")
                time.sleep(60)
                continue

            oc = chain["data"]["optionsChain"]
            row = min(oc, key=lambda x: abs(x["strikePrice"] - atm))
            pe_oi = row.get("putOI", row.get("put_oi", row.get("putOi", 0)))
            ce_oi = row.get("callOI", row.get("call_oi", row.get("callOi", 0)))

            print(f"Live {ltp} ATM {row['strikePrice']} PE {pe_oi} CE {ce_oi}")

            if pe_oi == 0 and ce_oi == 0:
                time.sleep(60)
                continue

            if last_pe == 0:
                last_pe, last_ce = pe_oi, ce_oi
                time.sleep(60)
                continue

            pe_diff = pe_oi - last_pe
            ce_diff = ce_oi - last_ce

            is_tue = get_ist_now().weekday() == 1
            thr = 100000 if is_tue else 50000

            if abs(pe_diff) >= thr or abs(ce_diff) >= thr:
                msg = f"🚨 <b>{'TUESDAY EXPIRY' if is_tue else 'OI ALERT'} {row['strikePrice']}</b>\nNIFTY {ltp:.0f}\nPE {last_pe/100000:.2f}L->{pe_oi/100000:.2f}L ({pe_diff/1000:+.0f}k)\nCE {last_ce/100000:.2f}L->{ce_oi/100000:.2f}L ({ce_diff/1000:+.0f}k)"
                send_telegram(msg)

            last_pe, last_ce = pe_oi, ce_oi
            time.sleep(60)

        except Exception as e:
            print(f"Err {e}")
            time.sleep(60)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
