#!/usr/bin/env python3
import logging
from telebot import types

# Importurile doar din modulele care nu vor crea importuri circulare
from bot_core import (
    bot, add_to_context, clear_context, send_message, send_typing_action, 
    set_active_persona, get_active_persona, user_contexts
)
from llm_service import query_llm
from database import log_user_activity, log_conversation, is_admin
from persona_prompts import get_persona_prompt, get_all_personas
# Import direct - fără importuri circulare
from admin_tools import handle_admin_panel

# Configurare logging
logger = logging.getLogger(__name__)

def register_commands():
    """Înregistrează comenzile botului"""
    bot.message_handler(commands=['start'])(cmd_start)
    bot.message_handler(commands=['help'])(cmd_help)
    bot.message_handler(commands=['info'])(cmd_info)
    bot.message_handler(commands=['raven'])(cmd_raven)
    bot.message_handler(commands=['sheldon'])(cmd_sheldon)
    bot.message_handler(commands=['tate'])(cmd_tate)
    bot.message_handler(commands=['joe'])(cmd_joe)
    bot.message_handler(commands=['bye'])(cmd_bye)
    bot.message_handler(commands=['admin'])(cmd_admin)
    
    # Handler pentru toate mesajele text
    bot.message_handler(content_types=['text'])(handle_message)
    
    # Înregistrăm callback handler pentru personaje
    bot.callback_query_handler(func=lambda call: call.data.startswith('persona_'))(handle_persona_callback)

def cmd_start(message):
    """Comandă start - întâmpină utilizatorul"""
    user_id = message.from_user.id
    username = message.from_user.username
    log_user_activity(user_id, username, "start")
    
    # Resetează contextul și personajul
    clear_context(user_id)
    
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🦅 Raven", callback_data="persona_raven"),
        types.InlineKeyboardButton("🤓 Sheldon", callback_data="persona_sheldon"),
        types.InlineKeyboardButton("💪 Tate", callback_data="persona_tate"),
        types.InlineKeyboardButton("😊 Joe", callback_data="persona_joe")
    )
    
    welcome_text = (
        "🤖 *Bun venit la EdgeSeekr Bot!*\n\n"
        "Sunt un asistent AI care te poate ajuta cu diverse întrebări. "
        "Alege unul dintre personajele de mai jos pentru a începe o conversație "
        "sau folosește comenzile pentru a interacționa cu mine.\n\n"
        "Scrie /help pentru a vedea lista completă de comenzi."
    )
    
    send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=kb)

def cmd_help(message):
    """Comandă help - afișează lista de comenzi"""
    user_id = message.from_user.id
    username = message.from_user.username
    log_user_activity(user_id, username, "help")
    
    help_text = (
        "🔍 *Comenzi disponibile:*\n\n"
        "/start - Pornește botul și afișează meniul principal\n"
        "/help - Afișează acest mesaj de ajutor\n"
        "/info - Informații despre proiect și creator\n\n"
        "*Personaje disponibile:*\n"
        "/raven - Pornește conversația cu Raven (dark și arogantă)\n"
        "/sheldon - Pornește conversația cu Sheldon (geek entuziast)\n"
        "/tate - Pornește conversația cu Tate (motivațional, business)\n"
        "/joe - Pornește conversația cu Joe (personaj normal)\n"
        "/bye - Încheie conversația curentă\n\n"
    )
    
    # Adaugă comenzile admin pentru administratori
    if is_admin(user_id):
        help_text += (
            "*Comenzi admin:*\n"
            "/admin - Accesează panoul de administrare\n"
        )
    
    send_message(message.chat.id, help_text, parse_mode="Markdown")

def cmd_info(message):
    """Comandă info - afișează informații despre proiect"""
    user_id = message.from_user.id
    username = message.from_user.username
    log_user_activity(user_id, username, "info")
    
    info_text = (
        "ℹ️ *Despre EdgeSeekr Bot*\n\n"
        "EdgeSeekr este un bot Telegram care utilizează modele LLM gratuite "
        "pentru a oferi conversații interactive cu diferite personaje.\n\n"
        "*Creator:* Andrei Balan\n"
        "*GitHub:* [AndreiBalan98/EdgeSeekr](https://github.com/AndreiBalan98/EdgeSeekr)\n\n"
        "Acest bot folosește API-ul OpenRouter pentru a accesa modele de limbaj "
        "gratuite și performante."
    )
    
    send_message(message.chat.id, info_text, parse_mode="Markdown")

def activate_persona(message, persona_key):
    """Activează un personaj pentru utilizator"""
    user_id = message.from_user.id
    username = message.from_user.username
    personas = get_all_personas()
    
    if persona_key not in personas:
        send_message(message.chat.id, "Personaj invalid. Încearcă din nou.")
        return False
    
    persona = personas[persona_key]
    log_user_activity(user_id, username, f"activate_{persona_key}")
    
    # Resetează contextul și setează noul personaj
    clear_context(user_id)
    set_active_persona(user_id, persona_key)
    
    # Adaugă system prompt la context
    system_prompt = get_persona_prompt(persona_key)
    add_to_context(user_id, "system", system_prompt)
    
    activation_text = f"🎭 *Personaj activat: {persona['name']}*\n\n{persona['description']}\n\nScrie un mesaj pentru a începe conversația."
    send_message(message.chat.id, activation_text, parse_mode="Markdown")
    return True

def cmd_raven(message):
    """Comandă raven - activează personajul Raven"""
    activate_persona(message, "raven")

def cmd_sheldon(message):
    """Comandă sheldon - activează personajul Sheldon"""
    activate_persona(message, "sheldon")

def cmd_tate(message):
    """Comandă tate - activează personajul Tate"""
    activate_persona(message, "tate")

def cmd_joe(message):
    """Comandă joe - activează personajul Joe (normal)"""
    activate_persona(message, "joe")

def cmd_bye(message):
    """Comandă bye - încheie conversația curentă"""
    user_id = message.from_user.id
    username = message.from_user.username
    
    active_persona = get_active_persona(user_id)
    if active_persona:
        log_user_activity(user_id, username, "bye")
        clear_context(user_id)
        send_message(message.chat.id, "👋 Conversația s-a încheiat. Folosește /start pentru a începe o nouă conversație.")
    else:
        send_message(message.chat.id, "Nu ești într-o conversație activă. Folosește /start pentru a începe una.")

def cmd_admin(message):
    """Comandă admin - accesează panoul de administrare"""
    user_id = message.from_user.id
    
    if is_admin(user_id):
        handle_admin_panel(message)
    else:
        send_message(message.chat.id, "❌ Nu ai acces la această comandă.")

def handle_message(message):
    """Gestionează mesajele text primite"""
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Verifică dacă există un personaj activ
    active_persona = get_active_persona(user_id)
    if not active_persona:
        # Sugerează comenzi disponibile dacă nu există un personaj activ
        send_message(
            message.chat.id, 
            "Nu ai un personaj activ. Folosește una din comenzile:\n/raven\n/sheldon\n/tate\n/joe\n\nSau apasă /help pentru ajutor."
        )
        return
    
    # Înregistrează activitatea și mesajul
    log_user_activity(user_id, username, "message")
    log_conversation(user_id, "user", message.text)
    
    # Adaugă mesajul la context
    add_to_context(user_id, "user", message.text)
    
    # Trimite indicatorul de scriere
    send_typing_action(message.chat.id)
    
    try:
        # Obține contextul conversației pentru utilizator
        messages = list(user_contexts[user_id]["messages"])
        
        # Interogare LLM pentru răspuns
        response = query_llm(messages)
        
        if response:
            # Adaugă răspunsul la context
            add_to_context(user_id, "assistant", response)
            log_conversation(user_id, "assistant", response)
            
            # Trimite răspunsul
            send_message(message.chat.id, response)
        else:
            send_message(message.chat.id, "❌ Nu am putut genera un răspuns. Te rog încearcă din nou.")
    
    except Exception as e:
        logger.error(f"Eroare la procesarea mesajului: {e}")
        send_message(message.chat.id, "❌ A apărut o eroare. Te rog încearcă din nou.")

# Callback pentru butoanele inline
def handle_persona_callback(call):
    """Gestionează apăsările pe butoanele pentru personaje"""
    try:
        persona_key = call.data.split('_')[1]
        activate_persona(call.message, persona_key)
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Eroare la procesarea callback-ului: {e}")
        bot.answer_callback_query(call.id, "A apărut o eroare. Te rog încearcă din nou.")