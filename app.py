import os, re, hashlib, requests, logging
from flask import Flask, request
import telegram
from datetime import datetime

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# --- ENV ---
BOT_TOKEN = os.getenv("BOT_TOKEN","").strip()
CLIENT_ID = os.getenv("CLIENT_ID","").strip()
SECRET_KEY = os.getenv("FYERS_SECRET_KEY","").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","").strip()
TOKEN_FILE = "fyers_token.txt"

bot = telegram.Bot(token=BOT_TOKEN)

# --- STEP 2 VALIDATION: ENV CHECK ---
def check_env():
    errors = []
    if not BOT_TOKEN: errors.append("BOT_TOKEN khali hai")
    if not CLIENT_ID or "-100" not in CLIENT_ID: errors.append(f"CLIENT_ID galat hai: {CLIENT_ID}")
    if not SECRET_KEY or len(SECRET_KEY) < 15: errors.append("FYERS_SECRET_KEY khali/galat hai")
    if not CHAT_ID: errors.append("TELEGRAM_CHAT_ID khali hai")
    return errors

# --- HELPERS ---
def save_token(t):
    with open(TOKEN_FILE,"w") as f: f.write(t.strip())

def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE,"r") as f: return f.read().strip()
    return ""

def validate_authcode_format(code):
    if len(code) < 100: return False, f"auth_code bahut chhota hai ({len(code)} char), pura copy nahi kiya"
    return True, "OK"

def generate_token(auth_code):
    # STEP 6
    app_id_hash = hashlib.sha256(f"{CLIENT_ID}:{SECRET_KEY}".encode()).hexdigest()
    payload = {"grant_type":"authorization_code", "appIdHash": app_id_hash, "code": auth_code}
    logging.info(f"STEP 6: Token generate req with hash {app_id_hash[:10]}...")
    r = requests.post("https://api.fyers.in/api/v3/validate-authcode", json=payload, timeout=15)
    res = r.json()
    logging.info(f"STEP 6 Response: {res}")
    return res, app_id_hash

def test_profile(token):
    # STEP 7.1
    headers = {"Authorization": f"{CLIENT_ID}:{token}"}
    r = requests.get("https://api.fyers.in/api/v3/profile", headers=headers, timeout=10)
    return r.json()

def test_quotes(token):
    # STEP 7.2
    headers = {"Authorization": f"{CLIENT_ID}:{token}"}
    url = "https://api.fyers.in/data-rest/v2/quotes/?symbols=NSE:NIFTY50-INDEX"
    r = requests.get(url, headers=headers, timeout=10)
    return r.json()

# --- ROUTES ---
@app.route('/')
def home():
    errs = check_env()
    if errs: return f"ENV FAIL: {errs}"
    return f"Bot Live | ENV OK | Token Exists: {bool(load_token())}"

@app.route('/telegram', methods=['POST'])
def webhook():
    try:
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        if not update.message: return "ok"
        text = update.message.text or ""
        chat_id = update.message.chat.id
        logging.info(f"Msg: {text[:200]}")

        # /start - STEP 3 Validation
        if text == "/start":
            errs = check_env()
            if errs:
                bot.send_message(chat_id=chat_id, text=f"❌ STEP 2 FAIL - ENV Error:\n" + "\n".join(errs))
            else:
                bot.send_message(chat_id=chat_id, text=f"✅ STEP 2 PASS - ENV OK\nSTEP 3 PASS - Telegram Connected\n\nCommands:\n/token - Fyers Login\n/status - System Check\n/check - Token Test")

        # /status - Full system check
        elif text == "/status":
            errs = check_env()
            msg = f"📊 STATUS CHECK - {datetime.now()}\n\n"
            msg += f"STEP 2 ENV: {'✅ PASS' if not errs else '❌ FAIL - '+str(errs)}\n"
            token = load_token()
            msg += f"STEP 5 Token File: {'✅ Exists' if token else '❌ Not Found'}\n"
            if token:
                prof = test_profile(token)
                msg += f"STEP 7.1 Profile: {prof.get('s','fail')} - {prof.get('message','')}\n"
                if prof.get('s') == 'ok':
                    q = test_quotes(token)
                    msg += f"STEP 7.2 Quotes: {q.get('s','fail')}\n"
                    if q.get('s') == 'ok':
                        ltp = q['d'][0]['v']['lp']
                        msg += f"✅ ALL PASS - NIFTY {ltp}"
            bot.send_message(chat_id=chat_id, text=msg[:4000])

        # /token - STEP 4
        elif text == "/token":
            errs = check_env()
            if errs:
                bot.send_message(chat_id=chat_id, text=f"❌ Cannot generate login - ENV FAIL: {errs}")
            else:
                url = f"https://api.fyers.in/api/v3/generate-authcode?client_id={CLIENT_ID}&redirect_uri=https://trade.fyers.in/api-login/redirect-uri/index.html&response_type=code&state=None"
                bot.send_message(chat_id=chat_id, text=f"🔗 STEP 4 - Login Link Generated:\n{url}\n\nLogin karo, fir jo redirect link aaye usko pura yaha paste karo.")

        # /check - STEP 7 Test
        elif text == "/check":
            token = load_token()
            if not token:
                bot.send_message(chat_id=chat_id, text="❌ STEP 7 FAIL - Token file khali hai. Pehle /token se login karo.")
            else:
                bot.send_message(chat_id=chat_id, text=f"⏳ STEP 7 Testing token len={len(token)}...")
                prof = test_profile(token)
                if prof.get('s')!= 'ok':
                    bot.send_message(chat_id=chat_id, text=f"❌ STEP 7.1 FAIL - Profile Test Fail:\n{prof}\n\nReason: Token expire / CLIENT_ID galat / App Draft me hai")
                else:
                    q = test_quotes(token)
                    if q.get('s')!= 'ok':
                        bot.send_message(chat_id=chat_id, text=f"❌ STEP 7.2 FAIL - Quotes Fail:\n{q}")
                    else:
                        ltp = q['d'][0]['v']['lp']
                        bot.send_message(chat_id=chat_id, text=f"✅ STEP 7 PASS - ALL OK!\nProfile: {prof['data']['name']}\nNIFTY: {ltp}\n\nAb Fyers <> Telegram Linked hai!")

        # Fyers Redirect Link - STEP 5 & 6
        elif "auth_code=" in text:
            m = re.search(r"auth_code=([^&]+)", text)
            if not m:
                bot.send_message(chat_id=chat_id, text="❌ STEP 5 FAIL - Link me auth_code nahi mila")
                return "ok"
            auth_code = m.group(1)
            valid, reason = validate_authcode_format(auth_code)
            if not valid:
                bot.send_message(chat_id=chat_id, text=f"❌ STEP 5 FAIL - {reason}")
                return "ok"

            bot.send_message(chat_id=chat_id, text=f"✅ STEP 5 PASS - auth_code mila (len={len(auth_code)})\n⏳ STEP 6 - Token generate kar raha hu...")

            try:
                res, hash_used = generate_token(auth_code)
                if res.get("s") == "ok" and "access_token" in res:
                    save_token(res["access_token"])
                    bot.send_message(chat_id=chat_id, text=f"✅ STEP 6 PASS - Token Generated!\nHash: {hash_used[:15]}...\n⏳ STEP 7 Testing...")

                    prof = test_profile(res["access_token"])
                    if prof.get('s')!= 'ok':
                        bot.send_message(chat_id=chat_id, text=f"❌ STEP 7.1 FAIL - Token bana par valid nahi:\n{prof}\n\nIska matlab: App abhi bhi Draft me hai ya CLIENT_ID galat hai")
                    else:
                        q = test_quotes(res["access_token"])
                        bot.send_message(chat_id=chat_id, text=f"✅ LINK SUCCESS!\n👤 {prof['data']['name']}\n📈 NIFTY {q['d'][0]['v']['lp'] if q.get('s')=='ok' else q}\n\nAb /status bhejo")
                else:
                    bot.send_message(chat_id=chat_id, text=f"❌ STEP 6 FAIL - Token Generation Fail:\n{res}\n\nCommon Reasons:\n1. auth_code 2 min me expire - naya login karo\n2. SECRET_KEY galat hai\n3. App Draft me hai")
            except Exception as e:
                bot.send_message(chat_id=chat_id, text=f"❌ STEP 6 EXCEPTION: {e}")

    except Exception as e:
        logging.error(f"Webhook error {e}")
    return "ok"

if __name__ == "__main__":
    errs = check_env()
    print(f"ENV CHECK: {errs if errs else 'OK'}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
