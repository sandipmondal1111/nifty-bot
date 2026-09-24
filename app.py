import os, time, threading
from flask import Flask
import requests
from datetime import datetime

app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")

@app.route('/')
def home(): return "Nifty Expiry Bot LIVE"

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(e)

def bot_loop():
    from fyers_apiv3 import fyersModel
    fyers = fyersModel.FyersModel(client_id=CLIENT_ID, token=ACCESS_TOKEN, is_async=False, log_path="")
    send_telegram("✅ <b>Nifty Expiry Bot LIVE</b>\nTuesday 1L | Normal 50K | 1 Min Check")

    last_pe, last_ce = 0, 0

    while True:
        try:
            q = fyers.quotes({"symbols":"NSE:NIFTY50-INDEX"})
            if q.get("s")!="ok": time.sleep(60); continue
            ltp = q["d"][0]["v"]["lp"]
            atm = int(round(ltp/50)*50)

            chain = fyers.optionchain(data={"symbol":"NSE:NIFTY50-INDEX","strikecount":30})
            if chain.get("s")!="ok": time.sleep(60); continue

            oc = chain["data"]["optionsChain"]
            row = min(oc, key=lambda x: abs(x["strikePrice"]-atm))

            ce_oi = row.get("callOI",0) or (row.get("call",{}).get("oi",0) if isinstance(row.get("call"), dict) else 0)
            pe_oi = row.get("putOI",0) or (row.get("put",{}).get("oi",0) if isinstance(row.get("put"), dict) else 0)
            if ce_oi==0 and pe_oi==0: time.sleep(60); continue

            if last_pe == 0:
                last_pe, last_ce = pe_oi, ce_oi
                time.sleep(60); continue

            pe_diff = pe_oi - last_pe
            ce_diff = ce_oi - last_ce

            today = datetime.now().weekday()
            is_tuesday = today == 1
            threshold = 100000 if is_tuesday else 50000
            day_tag = "TUESDAY EXPIRY" if is_tuesday else "NORMAL DAY"

            if abs(pe_diff) >= threshold or abs(ce_diff) >= threshold:

                # CLEAR ACTION LOGIC
                if pe_diff > threshold and ce_diff < 0:
                    title = "🟢 BULLISH BREAKOUT"
                    reason = f"ATM PE me {pe_diff/1000:.0f}k Fresh Buying, CE me {abs(ce_diff)/1000:.0f}k Short Covering"
                    action = f"👉 ACTION: BUY karo\n1. Nifty ATM {row['strikePrice']} PE BUY\n2. Ya Nifty Futures BUY\nSL: {row['strikePrice']-50} ke niche\nTarget: 80-100 points"

                elif ce_diff > threshold and pe_diff < 0:
                    title = "🔴 BEARISH BREAKDOWN"
                    reason = f"ATM CE me {ce_diff/1000:.0f}k Fresh Selling, PE me {abs(pe_diff)/1000:.0f}k Exit"
                    action = f"👉 ACTION: SELL karo\n1. Nifty ATM {row['strikePrice']} CE BUY\n2. Ya Nifty Futures SELL\nSL: {row['strikePrice']+50} ke upar\nTarget: 80-100 points"

                elif pe_diff > threshold:
                    title = "🟢 SUPPORT BAN RAHA HAI"
                    reason = f"PE OI +{pe_diff/1000:.0f}k bada (Strong Support)"
                    action = "👉 ACTION: WAIT FOR DIP & BUY\nDip pe PE BUY karo, CE SELL mat karo abhi"

                elif ce_diff > threshold:
                    title = "🔴 RESISTANCE BAN RAHA HAI"
                    reason = f"CE OI +{ce_diff/1000:.0f}k bada (Strong Resistance)"
                    action = "👉 ACTION: RISE PE SELL\nUpar aate hi CE BUY karo, PE me Profit Book karo"

                elif pe_diff < -threshold:
                    title = "⚠️ SUPPORT TOOT RAHA HAI"
                    reason = f"PE OI -{abs(pe_diff)/1000:.0f}k kam (Support Weak)"
                    action = "👉 ACTION: EXIT LONG / CAUTION\nPE wale nikal rahe hai, apna PE BUY exit karo"

                else:
                    title = "⚠️ RESISTANCE TOOT RAHA HAI"
                    reason = f"CE OI -{abs(ce_diff)/1000:.0f}k kam (Resistance Weak)"
                    action = "👉 ACTION: EXIT SHORT / CAUTION\nCE wale nikal rahe hai, apna CE BUY exit karo"

                msg = f"""🚨 <b>{title} | {day_tag}</b>
NIFTY {ltp:.0f} | ATM {row['strikePrice']}

{reason}

PE OI: {last_pe/100000:.2f}L → {pe_oi/100000:.2f}L ({'+' if pe_diff>0 else ''}{pe_diff/1000:.0f}k)
CE OI: {last_ce/100000:.2f}L → {ce_oi/100000:.2f}L ({'+' if ce_diff>0 else ''}{ce_diff/1000:.0f}k)

{action}"""

                send_telegram(msg)
                last_pe, last_ce = pe_oi, ce_oi

            time.sleep(60)
        except Exception as e:
            print(f"Err {e}"); time.sleep(60)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
