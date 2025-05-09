import os
import json
import logging
import requests # type: ignore
from flask import Flask, request, jsonify # type: ignore
from telebot import TeleBot, types, apihelper
from collections import defaultdict, deque

# Activează logging detaliat pentru telebot
apihelper.ENABLE_MIDDLEWARE = True
apihelper.SESSION_TIME_TO_LIVE = 5 * 60

# Configurare logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurare bot și API keys
TELEGRAM_TOKEN = "7711949090:AAGXMoHzN66c8WB2hkdmssZU5PZzGgjZmh4"
OPENROUTER_API_KEY = "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"
OPENROUTER_MODEL = "microsoft/MAI-DS-R1"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://your-render-app-url.onrender.com")

# Inițializare Flask și Bot
app = Flask(__name__)
bot = TeleBot(TELEGRAM_TOKEN, threaded=False)

# Configurație request-uri Telegram
apihelper.API_URL = "https://api.telegram.org/bot{0}/{1}"
apihelper.READ_TIMEOUT = 30
apihelper.CONNECT_TIMEOUT = 10

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

# Middleware pentru debugging
def log_update(update_json):
    print(f"Update primit: {json.dumps(update_json, indent=2)}")

# Comenzi bot
@bot.message_handler(commands=['start'])
def handle_start(message):
    """Procesează comanda /start"""
    try:
        print(f"Comanda /start primită de la utilizatorul {message.from_user.id}")
        welcome_text = (
            "👋 Bun venit la *EdgeSeekr Bot*!\n\n"
            "Sunt asistentul tău AI alimentat de modelul MAI DS R1 Microsoft prin OpenRouter.\n\n"
            "Pentru a începe o conversație, folosește comanda /llm.\n"
            "Pentru mai multe informații, încearcă /help sau /info."
        )
        
        # Încearcă direct cu API-ul Telegram în loc de metoda bibliotecii
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": message.chat.id,
                "text": welcome_text,
                "parse_mode": "Markdown"
            }
        )
        
        print(f"Răspuns direct API: {response.status_code}")
        if response.status_code == 200:
            print("Mesaj trimis cu succes prin API direct")
        else:
            print(f"Eroare API: {response.text}")
    except Exception as e:
        print(f"Eroare în handle_start: {str(e)}")
        # Încearcă fără parse_mode și direct prin API
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={
                    "chat_id": message.chat.id,
                    "text": "Bun venit la EdgeSeekr Bot! Folosește /help pentru asistență."
                }
            )
            print("Mesaj simplu trimis cu succes")
        except Exception as e2:
            print(f"A doua încercare eșuată: {str(e2)}")

@bot.message_handler(commands=['help'])
def handle_help(message):
    """Procesează comanda /help"""
    try:
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
        
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": message.chat.id,
                "text": help_text,
                "parse_mode": "Markdown"
            }
        )
    except Exception as e:
        print(f"Eroare în handle_help: {str(e)}")
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": message.chat.id,
                "text": "Eroare la afișarea comenzilor. Te rog încearcă din nou."
            }
        )

@bot.message_handler(commands=['info'])
def handle_info(message):
    """Procesează comanda /info"""
    try:
        info_text = (
            "*EdgeSeekr Bot* 🤖\n\n"
            "Bot: @edge_seekr_bot\n"
            "Model: MAI DS R1 Microsoft\n"
            "API: OpenRouter\n\n"
            "Acest bot utilizează un model avansat de inteligență artificială pentru a purta conversații naturale.\n\n"
            "Bot creat folosind TeleBot și Flask cu hosting pe Render.com."
        )
        
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": message.chat.id,
                "text": info_text,
                "parse_mode": "Markdown"
            }
        )
    except Exception as e:
        print(f"Eroare în handle_info: {str(e)}")

@bot.message_handler(commands=['llm'])
def handle_llm_command(message):
    """Procesează comanda /llm pentru a începe modul LLM"""
    try:
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
        
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": message.chat.id,
                "text": response_text,
                "parse_mode": "Markdown"
            }
        )
    except Exception as e:
        print(f"Eroare în handle_llm_command: {str(e)}")

@bot.message_handler(commands=['clear'])
def handle_clear_command(message):
    """Procesează comanda /clear pentru a reseta contextul"""
    try:
        user_id = message.from_user.id
        response = clear_context(user_id)
        if user_mode[user_id]:
            user_mode[user_id] = True  # Păstrează modul LLM activ
            response += "\nMomentul perfect pentru un nou început! Cu ce te pot ajuta?"
        
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": message.chat.id,
                "text": response
            }
        )
    except Exception as e:
        print(f"Eroare în handle_clear_command: {str(e)}")

@bot.message_handler(commands=['bye'])
def handle_bye_command(message):
    """Procesează comanda /bye pentru a încheia modul LLM"""
    try:
        user_id = message.from_user.id
        
        if user_mode[user_id]:
            user_mode[user_id] = False
            clear_context(user_id)
            
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={
                    "chat_id": message.chat.id,
                    "text": "👋 La revedere! Modul AI a fost dezactivat. Folosește /llm pentru a relua conversația."
                }
            )
        else:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={
                    "chat_id": message.chat.id,
                    "text": "Modul AI nu este activ. Folosește /llm pentru a începe o conversație."
                }
            )
    except Exception as e:
        print(f"Eroare în handle_bye_command: {str(e)}")

@bot.message_handler(func=lambda message: user_mode.get(message.from_user.id, False))
def handle_llm_message(message):
    """Procesează mesaje în modul LLM și le trimite către OpenRouter API"""
    try:
        user_id = message.from_user.id
        user_input = message.text
        
        # Ignoră comenzile în modul LLM (cu excepția celor gestionate explicit)
        if user_input.startswith('/') and not any(user_input.startswith(cmd) for cmd in ['/bye', '/clear', '/llm']):
            return
        
        # Adaugă mesajul utilizatorului în context
        add_to_context(user_id, "user", user_input)
        
        # Indicator de scriere
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction",
            json={
                "chat_id": message.chat.id,
                "action": "typing"
            }
        )
        
        try:
            # Pregătește contextul pentru trimitere la API
            messages = list(user_contexts[user_id]["messages"])
            
            # Apelează OpenRouter API
            response = query_llm(messages)
            
            if response:
                # Adaugă răspunsul la context
                add_to_context(user_id, "assistant", response)
                
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json={
                        "chat_id": message.chat.id,
                        "text": response
                    }
                )
            else:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json={
                        "chat_id": message.chat.id,
                        "text": "❌ Nu am putut genera un răspuns. Te rog încearcă din nou."
                    }
                )
        
        except Exception as e:
            logger.error(f"Eroare în procesarea mesajului LLM: {e}")
            
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={
                    "chat_id": message.chat.id,
                    "text": f"❌ A apărut o eroare: {str(e)}"
                }
            )
    except Exception as e:
        print(f"Eroare globală în handle_llm_message: {str(e)}")

@bot.message_handler(func=lambda message: True)
def default_handler(message):
    """Handler implicit pentru mesaje care nu corespund altor criterii"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": message.chat.id,
                "text": "Pentru a vorbi cu AI, folosește comanda /llm apoi scrie mesajul tău.\n"
                       "Pentru lista completă de comenzi, folosește /help."
            }
        )
    except Exception as e:
        print(f"Eroare în default_handler: {str(e)}")

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
        response = requests.post(url, headers=headers, json=data, timeout=60)
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
        json_string = request.get_data(as_text=True)
        update_json = json.loads(json_string)
        
        # Log pentru debugging
        print(f"Update primit: {json.dumps(update_json, indent=2)}")
        
        try:
            update = types.Update.de_json(json_string)
            bot.process_new_updates([update])
            print("Update procesat cu succes")
        except Exception as e:
            print(f"Eroare la procesarea update-ului: {e}")
            # Încercare manuală de a procesa comanda
            try:
                if 'message' in update_json and 'text' in update_json['message']:
                    chat_id = update_json['message']['chat']['id']
                    text = update_json['message']['text']
                    
                    # Procesare manuală a comenzilor
                    if text == '/start':
                        welcome_text = "👋 Bun venit la EdgeSeekr Bot! Pentru a începe o conversație, folosește /llm."
                        requests.post(
                            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                            json={"chat_id": chat_id, "text": welcome_text}
                        )
                    # Adaugă alte comenzi dacă e nevoie
            except Exception as e2:
                print(f"Și procesarea manuală a eșuat: {e2}")
        
        return '', 200
    else:
        print(f"Content-type nevalid: {request.headers.get('content-type')}")
        return '', 403

@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    """Setează webhook-ul pentru bot."""
    webhook_url = f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
    try:
        print(f"Încercare setare webhook la: {webhook_url}")
        
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
            json={"url": webhook_url}
        )
        
        status = response.status_code
        content = response.json()
        
        print(f"Răspuns setWebhook: Status {status}, Content: {content}")
        
        if status == 200 and content.get('ok'):
            return f"Webhook setat cu succes la: {webhook_url}", 200
        else:
            return f"Eroare la setarea webhook-ului: {content}", 500
    except Exception as e:
        return f"Excepție la setarea webhook-ului: {str(e)}", 500

@app.route('/', methods=['GET'])
def index():
    """Endpoint simplu pentru verificarea stării serverului."""
    return "EdgeSeekr Bot Server is running", 200

@app.route('/debug', methods=['GET'])
def debug():
    """Endpoint pentru verificarea stării botului și a webhook-ului."""
    try:
        # Test direct al API-ului Telegram
        getme_response = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe")
        webhook_info_response = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getWebhookInfo")
        
        bot_info = getme_response.json()
        webhook_info = webhook_info_response.json()
        
        debug_info = {
            "bot_api_response": bot_info,
            "webhook_info": webhook_info,
            "environment": {
                "webhook_url": WEBHOOK_URL,
                "telegram_token_prefix": TELEGRAM_TOKEN[:5],
                "openrouter_model": OPENROUTER_MODEL,
            }
        }
        
        return jsonify(debug_info), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Setează webhook-ul la pornire și rulează serverul
    port = int(os.environ.get("PORT", 10000))
    
    # În Render.com nu există 'DYNO', așa că vom configura direct webhook-ul
    if WEBHOOK_URL != "https://your-render-app-url.onrender.com":  # Verifică dacă avem un URL valid
        print(f"Setare webhook la pornire către: {WEBHOOK_URL}/{TELEGRAM_TOKEN}")
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
                json={"url": f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"}
            )
            print(f"Răspuns setWebhook: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Eroare la setarea webhook-ului: {e}")
    
    app.run(host="0.0.0.0", port=port)