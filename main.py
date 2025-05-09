import os
import json
import logging
import requests # type: ignore
from flask import Flask, request, jsonify # type: ignore
from telebot import TeleBot, types # type: ignore
from collections import defaultdict, deque

# Configurări de bază
TELEGRAM_TOKEN = "7711949090:AAGXMoHzN66c8WB2hkdmssZU5PZzGgjZmh4"
OPENROUTER_API_KEY = "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"
OPENROUTER_MODEL = "microsoft/mai-ds-r1:free"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://edge-seekr-bot.onrender.com")

# Configurare logging simplificată
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Inițializare Flask și Bot
app = Flask(__name__)
bot = TeleBot(TELEGRAM_TOKEN, threaded=False)

# Stare utilizatori
user_contexts = defaultdict(lambda: {"messages": deque(), "char_count": 0})
user_mode = defaultdict(bool)
MAX_CONTEXT_CHARS = 20000  # Redus pentru eficiență

# Funcții utilitare optimizate
def send_message(chat_id, text, parse_mode=None):
    """Funcție simplificată pentru trimiterea mesajelor"""
    data = {"chat_id": chat_id, "text": text}
    if parse_mode:
        data["parse_mode"] = parse_mode
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json=data)
    except Exception as e:
        logger.error(f"Eroare trimitere mesaj: {e}")
        # Încercare fără parse_mode dacă eșuează
        if parse_mode:
            send_message(chat_id, text)

def add_to_context(user_id, role, content):
    """Adaugă mesaj în context cu management automat al dimensiunii"""
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
    return "Contextul conversației a fost șters."

def delete_messages(chat_id, message_id, num_messages=10):
    """Șterge mesaje din chat (folosit pentru comanda /clean)"""
    success_count = 0
    
    # Încearcă să șteargă ultimele num_messages, inclusiv mesajul curent
    for i in range(message_id, message_id - num_messages, -1):
        if i <= 0:
            break
            
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage",
                json={"chat_id": chat_id, "message_id": i}
            )
            
            if response.status_code == 200:
                success_count += 1
            else:
                logger.warning(f"Nu s-a putut șterge mesajul {i}: {response.text}")
        except Exception as e:
            logger.error(f"Eroare la ștergerea mesajului {i}: {e}")
    
    return success_count

def query_llm(messages):
    """Interogare API OpenRouter optimizată"""
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": WEBHOOK_URL,
            "X-Title": "EdgeSeekr Bot"
        }
        
        data = {"model": OPENROUTER_MODEL, "messages": messages}
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, 
            json=data, 
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and result["choices"]:
                return result["choices"][0]["message"]["content"]
        
        logger.error(f"Eroare API: {response.status_code} - {response.text[:200]}")
        return None
        
    except Exception as e:
        logger.error(f"Excepție API: {e}")
        return None

# Comenzi bot
@bot.message_handler(commands=['start'])
def handle_start(message):
    welcome_text = (
        "👋 Bun venit la *EdgeSeekr Bot*!\n\n"
        "Sunt asistentul tău AI alimentat de modelul MAI DS R1 Microsoft.\n\n"
        "Pentru a începe o conversație, folosește /llm.\n"
        "Pentru mai multe informații, încearcă /help."
    )
    send_message(message.chat.id, welcome_text, "Markdown")

@bot.message_handler(commands=['help'])
def handle_help(message):
    help_text = (
        "*Comenzi disponibile:*\n\n"
        "• /start - Mesaj de bun venit\n"
        "• /help - Arată acest mesaj\n"
        "• /info - Informații despre bot\n"
        "• /llm - Începe conversația cu AI\n"
        "• /clean - Șterge mesajele din chat\n"
        "• /clear - Resetează contextul conversației\n"
        "• /bye - Încheie modul AI"
    )
    send_message(message.chat.id, help_text, "Markdown")

@bot.message_handler(commands=['info'])
def handle_info(message):
    info_text = (
        "*EdgeSeekr Bot* 🤖\n\n"
        "Bot: @edge_seekr_bot\n"
        "Model: MAI DS R1 Microsoft\n"
        "API: OpenRouter\n\n"
        "Bot creat cu TeleBot și Flask."
    )
    send_message(message.chat.id, info_text, "Markdown")

@bot.message_handler(commands=['llm'])
def handle_llm_command(message):
    user_id = message.from_user.id
    
    # Resetează contextul și activează modul LLM
    clear_context(user_id)
    user_mode[user_id] = True
    
    # Adaugă mesaj de sistem
    system_prompt = (
        "Ești un asistent AI amabil și util, numit EdgeSeekr. "
        "Răspunzi concis și ești alimentat de modelul MAI DS R1 Microsoft."
    )
    add_to_context(user_id, "system", system_prompt)
    
    send_message(
        message.chat.id,
        "🤖 *Modul AI activat*\n\nPoți începe să conversezi cu mine. Ce dorești să discutăm?",
        "Markdown"
    )

@bot.message_handler(commands=['clean'])
def handle_clean_command(message):
    chat_id = message.chat.id
    message_id = message.message_id
    
    # Șterge mesajele din chat
    deleted_count = delete_messages(chat_id, message_id)
    
    # Trimite confirmare (acest mesaj va fi singurul rămas)
    send_message(chat_id, f"Am șters {deleted_count} mesaje din chat.")

@bot.message_handler(commands=['clear'])
def handle_clear_command(message):
    user_id = message.from_user.id
    response = clear_context(user_id)
    
    if user_mode[user_id]:
        response += "\nContextul a fost resetat. Cu ce te pot ajuta acum?"
    
    send_message(message.chat.id, response)

@bot.message_handler(commands=['bye'])
def handle_bye_command(message):
    user_id = message.from_user.id
    
    if user_mode[user_id]:
        user_mode[user_id] = False
        clear_context(user_id)
        send_message(message.chat.id, "👋 La revedere! Modul AI dezactivat.")
    else:
        send_message(message.chat.id, "Modul AI nu este activ. Folosește /llm pentru a începe.")

@bot.message_handler(func=lambda message: user_mode.get(message.from_user.id, False))
def handle_llm_message(message):
    user_id = message.from_user.id
    user_input = message.text
    
    # Ignoră comenzile în modul LLM (cu excepția celor specifice)
    if user_input.startswith('/') and not any(user_input.startswith(cmd) for cmd in ['/bye', '/clear', '/clean', '/llm']):
        return
    
    # Adaugă mesajul în context
    add_to_context(user_id, "user", user_input)
    
    # Indicator de scriere
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction",
        json={"chat_id": message.chat.id, "action": "typing"}
    )
    
    # Obține răspuns de la LLM
    response = query_llm(list(user_contexts[user_id]["messages"]))
    
    if response:
        add_to_context(user_id, "assistant", response)
        send_message(message.chat.id, response)
    else:
        send_message(message.chat.id, "❌ Nu am putut genera un răspuns. Te rog încearcă din nou.")

@bot.message_handler(func=lambda message: True)
def default_handler(message):
    send_message(
        message.chat.id,
        "Pentru a vorbi cu AI, folosește /llm apoi scrie mesajul tău.\n"
        "Pentru comenzi, folosește /help."
    )

# Webhook și endpoint-uri Flask
@app.route('/' + TELEGRAM_TOKEN, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data(as_text=True)
        
        try:
            update = types.Update.de_json(json_string)
            bot.process_new_updates([update])
        except Exception as e:
            logger.error(f"Eroare procesare update: {e}")
        
        return '', 200
    return '', 403

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    webhook_url = f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
    
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
            json={"url": webhook_url}
        )
        
        if response.status_code == 200 and response.json().get('ok'):
            return f"Webhook setat cu succes: {webhook_url}", 200
        return f"Eroare setare webhook: {response.text}", 500
    except Exception as e:
        return f"Excepție: {str(e)}", 500

@app.route('/', methods=['GET'])
def index():
    return "EdgeSeekr Bot Server is running", 200

if __name__ == "__main__":
    # Setează webhook-ul la pornire
    port = int(os.environ.get("PORT", 10000))
    
    if WEBHOOK_URL:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
                json={"url": f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"}
            )
        except Exception as e:
            logger.error(f"Eroare setare webhook: {e}")
    
    app.run(host="0.0.0.0", port=port)