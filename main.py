#!/usr/bin/env python3
import os
from flask import Flask, request
from telebot import types
import logging
from dotenv import load_dotenv

# Încarcă variabilele din .env
load_dotenv()

# Inițializare baza de date înaintea altor importuri pentru a evita importuri circulare
from database import init_db, ADMIN_ID

# Acum putem importa modulele care depind de database
from bot_core import bot, setup_webhook, TELEGRAM_BOT_TOKEN
from commands import register_commands
from admin_tools import admin_callback_handler
from scheduler import start_scheduler  # Importăm start_scheduler

# Configurare logging simplă
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Inițializare Flask
app = Flask(__name__)

# Endpoint-uri Flask
@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def webhook():
    """Primește actualizări de la Telegram"""
    if request.headers.get('content-type') == 'application/json':
        try:
            update = types.Update.de_json(request.get_data(as_text=True))
            bot.process_new_updates([update])
        except Exception as e:
            logger.error(f"Eroare procesare update: {e}")
        return '', 200
    return '', 403

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    """Setează webhook-ul manual"""
    return setup_webhook(), 200

@app.route('/', methods=['GET'])
def index():
    """Pagina de status"""
    return "EdgeSeekr Bot Server is running", 200

def initialize_app():
    """Inițializează aplicația"""
    # Inițializează baza de date
    init_db()
    
    # Înregistrează comenzile botului
    register_commands()
    
    # Înregistrează callback handler pentru admin
    bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))(admin_callback_handler)
    
    # Setează webhook la pornire
    setup_webhook()
    
    # Pornește scheduler-ul
    start_scheduler()  # Adaugă această linie
    
    return app

if __name__ == "__main__":
    # Inițializează aplicația și pornește serverul
    app = initialize_app()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
else:
    # Pentru WSGI servers (Gunicorn)
    app = initialize_app()