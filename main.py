import os
import json
import logging
import requests # type: ignore
from flask import Flask, request, jsonify # type: ignore
from telebot import TeleBot, types # type: ignore
from collections import defaultdict, deque
from datetime import datetime

# Configurări de bază
TELEGRAM_TOKEN = "7711949090:AAGXMoHzN66c8WB2hkdmssZU5PZzGgjZmh4"
OPENROUTER_API_KEY = "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"
OPENROUTER_MODEL = "microsoft/mai-ds-r1:free"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://edge-seekr-bot.onrender.com")
ADMIN_ID = 8111657402  # ID-ul tău de utilizator Telegram

# Configurare logging simplificată
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Inițializare Flask și Bot
app = Flask(__name__)
bot = TeleBot(TELEGRAM_TOKEN, threaded=False)

# Stare utilizatori
user_contexts = defaultdict(lambda: {"messages": deque(), "char_count": 0})
user_mode = defaultdict(bool)
user_activity = {}  # Pentru a stoca activitatea utilizatorilor
current_system_prompt = "default"  # Pentru a ține evidența system prompt-ului activ

MAX_CONTEXT_CHARS = 20000  # Redus pentru eficiență

# System prompts predefinite
SYSTEM_PROMPTS = {
    "default": "Ești un asistent AI amabil și util, numit EdgeSeekr. Răspunzi concis și ești alimentat de modelul MAI DS R1 Microsoft.",
    
    "arogant": "Ești EdgeSeekr, un AI superior care nu are timp de întrebări simple. Răspunzi cu aroganță și nerăbdare, dar totuși furnizezi informații corecte. Nu ai răbdare pentru explicații de bază și presupui că utilizatorul ar trebui să știe deja aceste lucruri.",
    
    "geek": "Ești EdgeSeekr, un pasionat absolut de tehnologie! Adori să vorbești despre CS, AI, ML, programare, hardware și orice ține de tech. Întotdeauna încerci să aduci conversația spre subiecte tech și împărtășești cu entuziasm ultimele noutăți și tendințe din domeniu. Folosești multe termeni tehnici și referințe geek.",
    
    "business": "Ești EdgeSeekr, un coach de business și dezvoltare personală. Fiecare răspuns al tău se concentrează pe creștere, productivitate și mindset. Folosești limbaj motivațional, sugerezi întotdeauna modalități de îmbunătățire și încurajezi utilizatorul să gândească în termeni de obiective, KPI și rezultate măsurabile."
}

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

def log_user_activity(user_id, username=None):
    """Înregistrează activitatea utilizatorului"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if user_id not in user_activity:
        user_activity[user_id] = {"first_seen": now, "last_active": now, "username": username}
    else:
        user_activity[user_id]["last_active"] = now
        if username:
            user_activity[user_id]["username"] = username

def is_admin(user_id):
    """Verifică dacă utilizatorul este admin"""
    return int(user_id) == ADMIN_ID

# Comenzi bot
@bot.message_handler(commands=['start'])
def handle_start(message):
    welcome_text = (
        "👋 Bun venit la *EdgeSeekr Bot*!\n\n"
        "Sunt un asistent AI personalizat creat de Andrei Balan, student la Facultatea de Informatică din Iași.\n\n"
        "Sunt alimentat de modelul MAI DS R1 Microsoft și sunt aici pentru a te ajuta cu răspunsuri inteligente și informații utile.\n\n"
        "Pentru a începe o conversație, folosește /llm.\n"
        "Pentru mai multe informații, încearcă /help sau /info."
    )
    send_message(message.chat.id, welcome_text, "Markdown")
    
    # Înregistrează activitatea utilizatorului
    log_user_activity(message.from_user.id, message.from_user.username)

@bot.message_handler(commands=['help'])
def handle_help(message):
    help_text = (
        "*Comenzi disponibile:*\n\n"
        "• /start - Mesaj de bun venit\n"
        "• /help - Arată acest mesaj\n"
        "• /info - Informații despre bot și dezvoltator\n"
        "• /llm - Începe conversația cu AI\n"
        "• /clean - Șterge mesajele din chat\n"
        "• /bye - Încheie modul AI"
    )
    
    # Adaugă comenzile admin pentru admin
    if is_admin(message.from_user.id):
        help_text += (
            "\n\n*Comenzi Admin:*\n"
            "• /admin - Accesează funcțiile de administrare"
        )
    
    send_message(message.chat.id, help_text, "Markdown")
    
    # Înregistrează activitatea utilizatorului
    log_user_activity(message.from_user.id, message.from_user.username)

@bot.message_handler(commands=['info'])
def handle_info(message):
    info_text = (
        "*EdgeSeekr Bot* 🤖\n\n"
        "Bot: @edge_seekr_bot\n"
        "Model: MAI DS R1 Microsoft\n"
        "API: OpenRouter\n\n"
        "*Dezvoltator:*\n"
        "Andrei Balan\n"
        "Student la Facultatea de Informatică, Iași\n"
        "GitHub: [github.com/andreibalan](https://github.com/andreibalan)\n\n"
        "Bot creat cu TeleBot și Flask pentru a explora capacitățile modelelor LLM în interacțiunile conversaționale."
    )
    send_message(message.chat.id, info_text, "Markdown")
    
    # Înregistrează activitatea utilizatorului
    log_user_activity(message.from_user.id, message.from_user.username)

@bot.message_handler(commands=['llm'])
def handle_llm_command(message):
    user_id = message.from_user.id
    
    # Resetează contextul și activează modul LLM
    clear_context(user_id)
    user_mode[user_id] = True
    
    # Adaugă mesaj de sistem conform cu mode-ul curent
    add_to_context(user_id, "system", SYSTEM_PROMPTS[current_system_prompt])
    
    send_message(
        message.chat.id,
        "🤖 *Modul AI activat*\n\nPoți începe să conversezi cu mine. Ce dorești să discutăm?",
        "Markdown"
    )
    
    # Înregistrează activitatea utilizatorului
    log_user_activity(message.from_user.id, message.from_user.username)

@bot.message_handler(commands=['clean'])
def handle_clean_command(message):
    chat_id = message.chat.id
    message_id = message.message_id
    
    # Șterge mesajele din chat
    deleted_count = delete_messages(chat_id, message_id)
    
    # Trimite confirmare (acest mesaj va fi singurul rămas)
    send_message(chat_id, f"Am șters {deleted_count} mesaje din chat.")
    
    # Înregistrează activitatea utilizatorului
    log_user_activity(message.from_user.id, message.from_user.username)

@bot.message_handler(commands=['bye'])
def handle_bye_command(message):
    user_id = message.from_user.id
    
    if user_mode[user_id]:
        user_mode[user_id] = False
        clear_context(user_id)
        send_message(message.chat.id, "👋 La revedere! Modul AI dezactivat.")
    else:
        send_message(message,chat.id, "Modul AI nu este activ. Folosește /llm pentru a începe.")
    
    # Înregistrează activitatea utilizatorului
    log_user_activity(message.from_user.id, message.from_user.username)

@bot.message_handler(commands=['admin'])
def handle_admin_command(message):
    user_id = message.from_user.id
    
    # Verifică dacă utilizatorul este admin
    if not is_admin(user_id):
        send_message(message.chat.id, "❌ Nu ai permisiunea de a accesa această comandă.")
        return
    
    # Crează tastatura inline cu opțiunile admin
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # Butoane pentru funcțiile admin
    user_stats_btn = types.InlineKeyboardButton("📊 Statistici utilizatori", callback_data="admin_users")
    change_mode_btn = types.InlineKeyboardButton("🔄 Schimbă system prompt", callback_data="admin_mode")
    
    markup.add(user_stats_btn, change_mode_btn)
    
    send_message(
        message.chat.id,
        "🔐 *Panou Admin*\n\nSelectează o opțiune:",
        "Markdown"
    )
    
    # Trimite butoanele
    bot.send_message(message.chat.id, "Alege o funcție:", reply_markup=markup)

# Handler pentru callback-urile butoanelor
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_callback_handler(call):
    user_id = call.from_user.id
    
    # Verifică din nou dacă utilizatorul este admin
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "Nu ai permisiunea de a accesa această funcție.")
        return
    
    # Procesează diferite acțiuni admin
    if call.data == "admin_users":
        # Generează statisticile utilizatorilor
        stats = "📊 *Statistici Utilizatori*\n\n"
        
        if not user_activity:
            stats += "Nu există încă date despre utilizatori."
        else:
            for uid, data in user_activity.items():
                username = data.get("username", "Necunoscut")
                last_active = data.get("last_active", "Necunoscut")
                first_seen = data.get("first_seen", "Necunoscut")
                
                stats += f"*ID:* {uid}\n"
                stats += f"*Username:* {username}\n"
                stats += f"*Prima utilizare:* {first_seen}\n"
                stats += f"*Ultima activitate:* {last_active}\n\n"
        
        # Trimite statisticile
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=stats,
            parse_mode="Markdown"
        )
        
        # Adaugă buton de întoarcere
        markup = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_back")
        markup.add(back_btn)
        
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
        
    elif call.data == "admin_mode":
        # Crează butoane pentru schimbarea modului
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # Butoane pentru diferite moduri
        default_btn = types.InlineKeyboardButton("Normal", callback_data="mode_default")
        arogant_btn = types.InlineKeyboardButton("Arogant", callback_data="mode_arogant")
        geek_btn = types.InlineKeyboardButton("Geek Tech", callback_data="mode_geek")
        business_btn = types.InlineKeyboardButton("Business", callback_data="mode_business")
        back_btn = types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_back")
        
        markup.add(default_btn, arogant_btn, geek_btn, business_btn, back_btn)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🔄 *Schimbă System Prompt*\n\nMod actual: *{current_system_prompt}*\n\nSelectează un nou mod:",
            parse_mode="Markdown",
            reply_markup=markup
        )
        
    elif call.data == "admin_back":
        # Întoarcere la meniul principal admin
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        user_stats_btn = types.InlineKeyboardButton("📊 Statistici utilizatori", callback_data="admin_users")
        change_mode_btn = types.InlineKeyboardButton("🔄 Schimbă system prompt", callback_data="admin_mode")
        
        markup.add(user_stats_btn, change_mode_btn)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🔐 *Panou Admin*\n\nSelectează o opțiune:",
            parse_mode="Markdown",
            reply_markup=markup
        )

# Handler pentru callback-urile de schimbare a modului
@bot.callback_query_handler(func=lambda call: call.data.startswith('mode_'))
def mode_callback_handler(call):
    global current_system_prompt
    user_id = call.from_user.id
    
    # Verifică din nou dacă utilizatorul este admin
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "Nu ai permisiunea de a accesa această funcție.")
        return
    
    # Extrage noul mod din callback_data
    mode = call.data.split('_')[1]
    
    if mode in SYSTEM_PROMPTS:
        current_system_prompt = mode
        bot.answer_callback_query(call.id, f"System prompt schimbat la: {mode}")
        
        # Actualizează mesajul
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # Butoane pentru diferite moduri
        default_btn = types.InlineKeyboardButton("Normal", callback_data="mode_default")
        arogant_btn = types.InlineKeyboardButton("Arogant", callback_data="mode_arogant")
        geek_btn = types.InlineKeyboardButton("Geek Tech", callback_data="mode_geek")
        business_btn = types.InlineKeyboardButton("Business", callback_data="mode_business")
        back_btn = types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_back")
        
        markup.add(default_btn, arogant_btn, geek_btn, business_btn, back_btn)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🔄 *Schimbă System Prompt*\n\nMod actual: *{current_system_prompt}*\n\nSelectează un nou mod:",
            parse_mode="Markdown",
            reply_markup=markup
        )
    else:
        bot.answer_callback_query(call.id, "Mod necunoscut!")

@bot.message_handler(func=lambda message: user_mode.get(message.from_user.id, False))
def handle_llm_message(message):
    user_id = message.from_user.id
    user_input = message.text
    
    # Ignoră comenzile în modul LLM (cu excepția celor specifice)
    if user_input.startswith('/') and not any(user_input.startswith(cmd) for cmd in ['/bye', '/clean', '/llm']):
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
    
    # Înregistrează activitatea utilizatorului
    log_user_activity(message.from_user.id, message.from_user.username)

@bot.message_handler(func=lambda message: True)
def default_handler(message):
    send_message(
        message.chat.id,
        "Pentru a vorbi cu AI, folosește /llm apoi scrie mesajul tău.\n"
        "Pentru comenzi, folosește /help."
    )
    
    # Înregistrează activitatea utilizatorului
    log_user_activity(message.from_user.id, message.from_user.username)

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