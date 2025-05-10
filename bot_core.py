#!/usr/bin/env python3
import os
import logging
import requests
from telebot import TeleBot
from collections import defaultdict, deque

# Configurare logging
logger = logging.getLogger(__name__)

# Configurări de bază - STANDARDIZAREA VARIABILELOR DE MEDIU
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7711949090:AAGXMoHzN66c8WB2hkdmssZU5PZzGgjZmh4")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://edge-seekr-bot.onrender.com")

# Inițializare Bot
bot = TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)

# Stare utilizatori
user_contexts = defaultdict(lambda: {"messages": deque(), "char_count": 0})
user_active_persona = defaultdict(lambda: None)  # Pentru a ține evidența personajului activ
MAX_CONTEXT_CHARS = 16000  # Limita de caractere pentru context

def setup_webhook():
    """Setează webhook-ul pentru bot"""
    webhook_url = f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}"
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
            json={"url": webhook_url}
        )
        if response.status_code == 200 and response.json().get('ok'):
            return f"Webhook setat cu succes: {webhook_url}"
        return f"Eroare setare webhook: {response.text}"
    except Exception as e:
        logger.error(f"Eroare setare webhook: {e}")
        return f"Excepție: {str(e)}"

def send_message(chat_id, text, parse_mode=None, reply_markup=None):
    """Trimite mesaj către un chat"""
    data = {"chat_id": chat_id, "text": text}
    if parse_mode:
        data["parse_mode"] = parse_mode
    if reply_markup:
        data["reply_markup"] = reply_markup.to_json()
    
    try:
        return requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
            json=data
        )
    except Exception as e:
        logger.error(f"Eroare trimitere mesaj: {e}")
        # Încercare fără parse_mode dacă eșuează
        if parse_mode:
            send_message(chat_id, text)

def add_to_context(user_id, role, content):
    """Adaugă mesaj în context cu gestionare automată a dimensiunii"""
    ctx = user_contexts[user_id]
    message = {"role": role, "content": content}
    msg_len = len(content)
    
    ctx["messages"].append(message)
    ctx["char_count"] += msg_len
    
    # Curăță contextul dacă depășește limita
    while ctx["char_count"] > MAX_CONTEXT_CHARS and ctx["messages"]:
        old_msg = ctx["messages"].popleft()
        ctx["char_count"] -= len(old_msg["content"])

def clear_context(user_id):
    """Resetează contextul conversațional"""
    if user_id in user_contexts:
        user_contexts[user_id] = {"messages": deque(), "char_count": 0}
    if user_id in user_active_persona:
        user_active_persona[user_id] = None
    return True

def get_active_persona(user_id):
    """Returnează personajul activ al unui utilizator"""
    return user_active_persona.get(user_id)

def set_active_persona(user_id, persona):
    """Setează personajul activ pentru un utilizator"""
    user_active_persona[user_id] = persona
    return True

def delete_messages(chat_id, message_id, num_messages=10):
    """Șterge mesaje din chat"""
    success_count = 0
    for i in range(message_id, message_id - num_messages, -1):
        if i <= 0:
            break
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteMessage",
                json={"chat_id": chat_id, "message_id": i}
            )
            if response.status_code == 200:
                success_count += 1
        except Exception as e:
            logger.error(f"Eroare la ștergerea mesajului {i}: {e}")
    return success_count

def send_typing_action(chat_id):
    """Trimite indicatorul de scriere"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendChatAction",
            json={"chat_id": chat_id, "action": "typing"}
        )
    except Exception as e:
        logger.error(f"Eroare la trimiterea acțiunii de scriere: {e}")