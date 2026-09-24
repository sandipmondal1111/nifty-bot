import os, time, threading, math
from datetime import datetime, timedelta
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
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"TG Error: {e}")

def get_next_expiry():
    # Nifty ka next Thursday expiry nikalo
    today = datetime.now()
    days_ahead = 3 - today.weekday() # Thursday = 3
    if days_ahead < 0: days_ahead += 7
    exp = today + timedelta(days=days_ahead)
    # Fyers ko YYYY-MM-DD format chahiye optionchain me nahi, but symbol me YYMMM
    return exp

def oi_loop():
    time.sleep(5)
    send_telegram("✅ <b>OI Bot Live!</b>\nAb har 5 min me ATM OI ayega")
    fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=ACCESS_TOKEN, is_async=False, log_path="")

    while True:
        try:
            # 1. Nifty Spot
            res = fyers.quotes({"symbols":"NSE:NIFTY50-INDEX"})
            if res.get("s")!= "ok":
                print(f"Fyers Error: {res}")
                time.sleep(60)
                continue

            nifty_ltp = res["d"][0]["v"]["lp"]
            atm = int(round(nifty_ltp / 50) * 50)
            print(f"NIFTY {nifty_ltp} ATM {atm}")

            # 2. ATM CE & PE ka OI nikalo - Current week expiry
            # Fyers symbol: NSE:NIFTY24XXX23050CE
            # Better: optionchain API use karo
            data = {"symbol":"NSE:NIFTY50-INDEX", "strikecount":1}
            chain = fyers.optionchain(data=data)

            if chain.get("s") == "ok":
                # ATM ke aas pass ka data
                options = chain["data"]["optionsChain"]
                atm_data = None
                for opt in options:
                    if opt["strikePrice"] == atm:
                        atm_data = opt
                        break
                if not atm_data:
                    atm_data = options[len(options)//2]

                ce_oi = atm_data["ceLongBuildup"] if "ceLongBuildup" in str(atm_data) else atm_data.get("ceOI",0) if "ceOI" in atm_data else atm_data["callOI"]
                # Simple fallback - agar structure alag ho to quotes se lo
                raise Exception("Use Quotes fallback")

            else:
                raise Exception("Chain fail, use quotes")

        except Exception as e:
            # Fallback: Direct Quotes se ATM CE/PE ka OI lo - Ye sabse stable hai
            try:
                # Expiry auto detect karne ke liye hum next expiry ka symbol banayenge
                # Format: NSE:NIFTY25930... 26 = year, 930 = 30 Sep
                # Easy way: Nifty ki monthly chain se 0 symbol lo
                today = datetime.now()
                # Current month expiry try karo - Fyers format NSE:NIFTY25SEP23050CE
                month_str = today.strftime("%y%b").upper() # 25SEP
                # Is saal ke Thursdays try karenge
                ce_sym = f"NSE:NIFTY{month_str}{atm}CE"
                pe_sym = f"NSE:NIFTY{month_str}{atm}PE"

                # Agar monthly fail to weekly: NSE:NIFTY25916... type
                q = fyers.quotes({"symbols": f"{ce_sym},{pe_sym}"})
                print(f"OI Quotes: {q}")
                if q.get("s") == "ok" and len(q["d"]) >= 2:
                    ce_d = q["d"][0]["v"] if "CE" in q["d"][0]["n"] else q["d"][1]["v"]
                    pe_d = q["d"][1]["v"] if "PE" in q["d"][1]["n"] else q["d"][0]["v"]

                    ce_oi = ce_d.get("oi",0)
                    ce_coi = ce_d.get("coi", ce_d.get("oiChange",0))
                    pe_oi = pe_d.get("oi",0)
                    pe_coi = pe_d.get("coi", pe_d.get("oiChange",0))

                    # Lakh me convert
                    def fmt(n): return f"{n/100000:.1f}L" if n>1000 else str(n)

                    if pe_oi > ce_oi:
                        side = "PE Heavy (Support)"
                        bias = "🟢"
                    elif ce_oi > pe_oi:
                        side = "CE Heavy (Resistance)"
                        bias = "🔴"
                    else:
                        side = "Balanced"
                        bias = "⚪"

                    msg = f"""{bias} <b>NIFTY {nifty_ltp:.0f} | ATM {atm}</b>

PE: OI {fmt(pe_oi)} | CH {fmt(pe_coi)}
CE: OI {fmt(ce_oi)} | CH {fmt(ce_coi)}

👉 {side}
Diff: {fmt(abs(pe_oi-ce_oi))}"""
                    send_telegram(msg)
                else:
                    # Last LTP hi bhej do taaki pata chale bot live hai
                    send_telegram(f"📊 <b>NIFTY {nifty_ltp:.0f} ATM {atm}</b> | Bot Live (OI data wait for market)")
            except Exception as e2:
                print(f"OI Error: {e2}")
                # Market band hai to bhi live proof ke liye Nifty bhej do
                try:
                    send_telegram(f"📈 <b>NIFTY Spot {nifty_ltp:.0f} ATM {atm}</b> - Bot Live | OI market hours me ayega")
                except: pass

        time.sleep(300) # 5 min

threading.Thread(target=oi_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
