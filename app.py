from flask import Flask
import threading
import time
import os

app = Flask(__name__)

def bot_logic():
    while True:
        print("Bot Running...")
        time.sleep(120)

@app.route('/')
def home():
    return "Bot is ON"

if __name__ == "__main__":
    threading.Thread(target=bot_logic).start()
    app.run(host='0.0.0.0', port=10000)