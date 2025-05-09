import os
import json
import logging
import requests # type: ignore
from flask import Flask, request, jsonify # type: ignore
from telebot import TeleBot, types # type: ignore
from collections import defaultdict, deque

# Configurare logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurare bot și API keys
TELEGRAM_TOKEN = "7711949090:AAGXMoHzN66c8WB2hkdmssZU5PZzGgjZmh4"
OPENROUTER_API_KEY = "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"
OPENROUTER_MODEL = "microsoft/MAI-DS-R1"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://edge-seekr-bot.onrender.com")

# Inițializare Flask și Bot
app = Flask(__name__)
bot = TeleBot(TELEGRAM_TOKEN)

# Gestionare context conversațional
user_contexts = defaultdict(dict)
MAX_CONTEXT_CHARS = 50000
user_mode = defaultdict(bool)  # Tracking dacă utilizatorul este în modul LLM

# Funcții de utilitate pentru gestionarea contextului
def init_user_context(user_id):
    """Inițializează contextul pentru un utilizator."""
    user_contexts[user_id] = {
        "messages": deque(),
        "char_count": 0
    }

def add_to_context(user_id, role, content):
    """Adaugă un mesaj în contextul utilizatorului, eliminând mesaje vechi dacă se depășește limita."""
    if user_id not in user_contexts:
        init_user_context(user_id)
    
    message = {"role": role, "content": content}
    message_chars = len(content)
    
    # Adaugă mesajul la context
    user_contexts[user_id]["messages"].append(message)
    user_contexts[user_id]["char_count"] += message_chars
    
    # Elimină mesaje vechi până când contextul este sub limită
    while user_contexts[user_id]["char_count"] > MAX_CONTEXT_CHARS and user_contexts[user_id]["messages"]:
        old_message = user_contexts[user_id]["messages"].popleft()
        user_contexts[user_id]["char_count"] -= len(old_message["content"])

def clear_context(user_id):
    """Curăță contextul unui utilizator."""
    if user_id in user_contexts:
        init_user_context(user_id)
    user_mode[user_id] = False
    return "Contextul conversației a fost șters."

# Comenzi bot
@bot.message_handler(commands=['start'])
def handle_start(message):
    """Procesează comanda /start"""
    welcome_text = (
        "👋 Bun venit la *EdgeSeekr Bot*!\n\n"
        "Sunt asistentul tău AI alimentat de modelul MAI DS R1 Microsoft prin OpenRouter.\n\n"
        "Pentru a începe o conversație, folosește comanda /llm.\n"
        "Pentru mai multe informații, încearcă /help sau /info."
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def handle_help(message):
    """Procesează comanda /help"""
    help_text = (
        "*Comenzi disponibile:*\n\n"
        "• /start - Mesaj de bun venit\n"
        "• /help - Arată acest mesaj de ajutor\n"
        "• /info - Informații despre bot și dezvoltator\n"
        "• /llm - Începe o conversație cu modelul AI\n"
        "• /clear - Resetează contextul conversației curente\n"
        "• /bye - Încheie modul de conversație AI\n\n"
        "Pentru a vorbi cu AI, folosește /llm apoi scrie mesajul tău."
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['info'])
def handle_info(message):
    """Procesează comanda /info"""
    info_text = (
        "*EdgeSeekr Bot* 🤖\n\n"
        "Bot: @edge_seekr_bot\n"
        "Model: MAI DS R1 Microsoft\n"
        "API: OpenRouter\n\n"
        "Acest bot utilizează un model avansat de inteligență artificială pentru a purta conversații naturale.\n\n"
        "Bot creat folosind TeleBot și Flask cu hosting pe Render.com."
    )
    bot.send_message(message.chat.id, info_text, parse_mode="Markdown")

@bot.message_handler(commands=['llm'])
def handle_llm_command(message):
    """Procesează comanda /llm pentru a începe modul LLM"""
    user_id = message.from_user.id
    
    # Curăță contextul vechi și inițializează unul nou
    clear_context(user_id)
    
    # Setează utilizatorul în modul LLM
    user_mode[user_id] = True
    
    # Adaugă un mesaj de sistem în context
    system_message = (
        "Ești un asistent AI amabil și util, numit EdgeSeekr. "
        "Răspunzi concis și ești alimentat de modelul MAI DS R1 Microsoft prin API-ul OpenRouter."
    )
    add_to_context(user_id, "system", system_message)
    
    response_text = (
        "🤖 *Modul AI activat*\n\n"
        "Poți începe să conversezi cu mine acum. Contextul conversației va fi păstrat "
        "până la comanda /bye sau /clear.\n\n"
        "Ce dorești să discutăm?"
    )
    bot.send_message(message.chat.id, response_text, parse_mode="Markdown")

@bot.message_handler(commands=['clear'])
def handle_clear_command(message):
    """Procesează comanda /clear pentru a reseta contextul"""
    user_id = message.from_user.id
    response = clear_context(user_id)
    if user_mode[user_id]:
        user_mode[user_id] = True  # Păstrează modul LLM activ
        response += "\nMomentul perfect pentru un nou început! Cu ce te pot ajuta?"
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['bye'])
def handle_bye_command(message):
    """Procesează comanda /bye pentru a încheia modul LLM"""
    user_id = message.from_user.id
    
    if user_mode[user_id]:
        user_mode[user_id] = False
        clear_context(user_id)
        bot.send_message(message.chat.id, "👋 La revedere! Modul AI a fost dezactivat. Folosește /llm pentru a relua conversația.")
    else:
        bot.send_message(message.chat.id, "Modul AI nu este activ. Folosește /llm pentru a începe o conversație.")

@bot.message_handler(func=lambda message: user_mode.get(message.from_user.id, False))
def handle_llm_message(message):
    """Procesează mesaje în modul LLM și le trimite către OpenRouter API"""
    user_id = message.from_user.id
    user_input = message.text
    
    # Ignoră comenzile în modul LLM (cu excepția celor gestionate explicit)
    if user_input.startswith('/') and not any(user_input.startswith(cmd) for cmd in ['/bye', '/clear', '/llm']):
        return
    
    # Adaugă mesajul utilizatorului în context
    add_to_context(user_id, "user", user_input)
    
    # Indicator de scriere
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        # Pregătește contextul pentru trimitere la API
        messages = list(user_contexts[user_id]["messages"])
        
        # Apelează OpenRouter API
        response = query_llm(messages)
        
        if response:
            # Adaugă răspunsul la context
            add_to_context(user_id, "assistant", response)
            bot.send_message(message.chat.id, response)
        else:
            bot.send_message(message.chat.id, "❌ Nu am putut genera un răspuns. Te rog încearcă din nou.")
    
    except Exception as e:
        logger.error(f"Eroare în procesarea mesajului LLM: {e}")
        bot.send_message(message.chat.id, f"❌ A apărut o eroare: {str(e)}")

@bot.message_handler(func=lambda message: True)
def default_handler(message):
    """Handler implicit pentru mesaje care nu corespund altor criterii"""
    bot.send_message(
        message.chat.id,
        "Pentru a vorbi cu AI, folosește comanda /llm apoi scrie mesajul tău.\n"
        "Pentru lista completă de comenzi, folosește /help."
    )

def query_llm(messages):
    """Trimite cerere către OpenRouter API și primește răspunsul."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://edge-seekr-bot.onrender.com",  # înlocuiește cu URL-ul aplicației tale
        "X-Title": "EdgeSeekr Bot"
    }
    
    data = {
        "model": OPENROUTER_MODEL,
        "messages": messages
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            logger.error(f"Răspuns neașteptat de la API: {result}")
            return None
    
    except Exception as e:
        logger.error(f"Eroare în apelul API OpenRouter: {e}")
        raise

# Webhook și endpoint-uri Flask
@app.route('/' + TELEGRAM_TOKEN, methods=['POST'])
def webhook():
    """Procesează update-uri primite de la Telegram."""
    if request.headers.get('content-type') == 'application/json':
        update = types.Update.de_json(request.get_data(as_text=True))
        bot.process_new_updates([update])
        return '', 200
    else:
        return '', 403

@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    """Setează webhook-ul pentru bot."""
    webhook_url = f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
    response = bot.set_webhook(url=webhook_url)
    if response:
        return f"Webhook setat la: {webhook_url}", 200
    else:
        return "Eroare la setarea webhook-ului", 500

@app.route('/', methods=['GET'])
def index():
    """Endpoint simplu pentru verificarea stării serverului."""
    return "EdgeSeekr Bot Server is running", 200

if __name__ == "__main__":
    # Setează webhook-ul la pornire și rulează serverul
    port = int(os.environ.get("PORT", 5000))
    
    # Asigură-te că webhook-ul este setat când aplicația este în producție
    if 'DYNO' in os.environ:  # Verifică dacă rulăm pe un server (Render)
        bot.remove_webhook()
        bot.set_webhook(url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}")
    
    app.run(host="0.0.0.0", port=port)