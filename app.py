import os, time, threading
from flask import Flask
import requests
from fyers_apiv3 import fyersModel

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")

@app.route('/')
def home():
    return "Nifty-Bot is LIVE - OI Bot Running"

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(e)

def oi_loop():
    time.sleep(3)
    fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=ACCESS_TOKEN, is_async=False, log_path="")
    send_telegram("✅ <b>OI Bot Live!</b> Market open me ATM OI ayega")

    while True:
        try:
            # Nifty LTP
            nifty = fyers.quotes({"symbols":"NSE:NIFTY50-INDEX"})
            if nifty.get("s")!= "ok":
                time.sleep(60); continue
            ltp = nifty["d"][0]["v"]["lp"]
            atm = int(round(ltp/50)*50)

            # Option Chain se ATM ka OI
            chain = fyers.optionchain(data={"symbol":"NSE:NIFTY50-INDEX","strikecount":20})
            if chain.get("s") == "ok":
                oc = chain["data"]["optionsChain"]
                atm_row = min(oc, key=lambda x: abs(x["strikePrice"]-atm))
                # Fyers chain keys alag-alag ho sakte hai, sab handle kiya
                ce_oi = atm_row.get("callOI", atm_row.get("oI",0) if "call" not in str(atm_row).lower() else 0)
                pe_oi = atm_row.get("putOI",0)
                ce_ch = atm_row.get("callOIChange", atm_row.get("callOICh",0))
                pe_ch = atm_row.get("putOIChange", atm_row.get("putOICh",0))

                # agar nested structure ho
                if ce_oi == 0 and "call" in atm_row:
                    ce_oi = atm_row["call"].get("oi",0)
                    ce_ch = atm_row["call"].get("oiChange",0)
                    pe_oi = atm_row["put"].get("oi",0)
                    pe_ch = atm_row["put"].get("oiChange",0)

                # Agar abhi bhi 0 hai to quotes se try karo weekly symbols ke liye
                if ce_oi == 0 and pe_oi == 0:
                    # Expiry data se symbol lo
                    expiry = chain["data"]["expiryData"][0]["expiry"] if "expiryData" in chain["data"] else None
                    print(f"Expiry: {expiry} Row: {atm_row}")

                def fmt(n):
                    try:
                        n=int(n)
                        return f"{n/100000:.1f}L" if n>=100000 else f"{n/1000:.1f}k" if n>=1000 else str(n)
                    except: return str(n)

                side = "PE Heavy 🟢" if pe_oi>ce_oi else "CE Heavy 🔴" if ce_oi>pe_oi else "Balanced ⚪"

                msg = f"""⚪ <b>NIFTY {ltp:.0f} | ATM {atm_row['strikePrice']}</b>

PE: OI {fmt(pe_oi)} | CH {fmt(pe_ch)}
CE: OI {fmt(ce_oi)} | CH {fmt(ce_ch)}

👉 {side}
Diff: {fmt(abs(pe_oi-ce_oi))}"""

                # Raat me 0 hai to spam mat karo, market time pe hi bhejo
                from datetime import datetime
                now = datetime.now()
                if 9 <= now.hour <= 15 and ce_oi!=0:
                    send_telegram(msg)
                else:
                    print(msg)
                    # Raat me live proof ke liye ek hi baar
                    if now.minute % 30 == 0:
                        send_telegram(f"📈 NIFTY {ltp:.0f} ATM {atm} - Bot Live | OI subah 9:15 se ayega")

            time.sleep(300) # 5 min
        except Exception as e:
            print(f"Loop err: {e}")
            time.sleep(60)

threading.Thread(target=oi_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
