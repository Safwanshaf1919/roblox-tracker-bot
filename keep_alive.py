from discord.audit_logs import F
from flask import Flask,render_template
from threading import Thread
import os
print(f"Your app should be accessible at https://{os.environ['REPL_SLUG']}.{os.environ['REPL_OWNER']}.repl.co")

app = Flask(__name__)
@app.route('/')
def index():
    return "Alive"
def run():
    app.run(host="0.0.0.0",port=3000)
def keep_alive():
    t=Thread(target=run)
    t.start()