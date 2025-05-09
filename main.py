#!/usr/bin/env python3
import os
from flask import Flask, request
from telebot import types
import logging

from bot_core import bot, setup_webhook
from database import init_db, ADMIN_ID
from commands import register_commands

# Configurare logging simplă
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Inițializare Flask
app = Flask(__name__)

# Endpoint-uri Flask
@app.route(f'/{os.environ.get("TELEGRAM_TOKEN", "")}', methods=['POST'])
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

if __name__ == "__main__":
    # Inițializează baza de date
    init_db()
    
    # Înregistrează comenzile botului
    register_commands()
    
    # Setează webhook la pornire și pornește serverul
    port = int(os.environ.get("PORT", 10000))
    setup_webhook()
    app.run(host="0.0.0.0", port=port)