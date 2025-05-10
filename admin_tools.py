#!/usr/bin/env python3
import logging
from datetime import datetime
from telebot import types

from bot_core import bot, send_message
from database import (
    get_users, get_conversation_dates, get_conversation_history,
    log_user_activity, get_scheduled_messages,
    remove_scheduled_message, is_admin
)
from scheduler import schedule_message
from persona_prompts import get_all_personas

# Configurare logging
logger = logging.getLogger(__name__)

# Starea curentă a panoului admin
admin_state = {}

def handle_admin_panel(message):
    """Gestionare panou admin principal"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if not is_admin(user_id):
        send_message(chat_id, "❌ Nu ai acces la această comandă.")
        return
    
    log_user_activity(user_id, None, "admin_panel")
    admin_state[user_id] = {"mode": "main"}
    
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("👥 Vezi utilizatori", callback_data="admin_users"),
        types.InlineKeyboardButton("💬 Vezi conversații", callback_data="admin_convs"),
        types.InlineKeyboardButton("📨 Trimite mesaj", callback_data="admin_send"),
        types.InlineKeyboardButton("⏱ Programează mesaje", callback_data="admin_schedule"),
        types.InlineKeyboardButton("🗓 Mesaje programate", callback_data="admin_scheduled")
    )
    
    send_message(
        chat_id,
        "🔐 *Panou de administrare*\n\nSelectează o opțiune:",
        parse_mode="Markdown",
        reply_markup=kb
    )

def show_users(chat_id):
    """Afișează lista utilizatorilor"""
    users = get_users()
    
    if not users:
        send_message(chat_id, "Nu există utilizatori înregistrați.")
        return
    
    message = "👥 *Utilizatori înregistrați:*\n\n"
    for user_id, data in users.items():
        username = data.get("username", "Fără nume") or "Fără nume"
        first_seen = data.get("first_seen", "Necunoscut")
        last_active = data.get("last_active", "Necunoscut")
        
        message += f"ID: `{user_id}`\n"
        message += f"Username: @{username}\n"
        message += f"Prima interacțiune: {first_seen}\n"
        message += f"Ultima activitate: {last_active}\n\n"
    
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_back"))
    
    send_message(chat_id, message, parse_mode="Markdown", reply_markup=kb)

def show_user_list(chat_id, mode):
    """Afișează lista utilizatorilor cu butoane pentru acțiuni"""
    users = get_users()
    
    if not users:
        send_message(chat_id, "Nu există utilizatori înregistrați.")
        return
    
    message = "👥 *Selectează un utilizator:*\n\n"
    
    kb = types.InlineKeyboardMarkup(row_width=1)
    for user_id, data in users.items():
        username = data.get("username", "Fără nume") or "Fără nume"
        kb.add(types.InlineKeyboardButton(
            f"@{username} ({user_id})", 
            callback_data=f"admin_{mode}_user_{user_id}"
        ))
    
    kb.add(types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_back"))
    send_message(chat_id, message, parse_mode="Markdown", reply_markup=kb)

def show_conversation_dates(chat_id, user_id):
    """Afișează datele conversațiilor unui utilizator"""
    dates = get_conversation_dates(user_id)
    
    if not dates:
        send_message(chat_id, f"Utilizatorul {user_id} nu are conversații salvate.")
        return
    
    message = f"📅 *Conversații pentru utilizatorul {user_id}:*\n\nSelectează o dată:"
    
    kb = types.InlineKeyboardMarkup(row_width=2)
    for date in dates[:10]:  # Limităm la primele 10 zile
        kb.add(types.InlineKeyboardButton(
            date, 
            callback_data=f"admin_view_conv_{user_id}_{date}"
        ))
    
    kb.add(types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_convs"))
    send_message(chat_id, message, parse_mode="Markdown", reply_markup=kb)

def show_conversation(chat_id, user_id, date):
    """Afișează conversația unui utilizator din data specificată"""
    conversation = get_conversation_history(user_id, date)
    
    if not conversation:
        send_message(chat_id, f"Nu există conversații pentru {user_id} în data {date}.")
        return
    
    message = f"💬 *Conversație {user_id} - {date}:*\n\n"
    
    for msg in conversation:
        role = msg.get("role", "")
        time = msg.get("time", "")
        content = msg.get("message", "")
        
        role_icon = "👤" if role == "user" else "🤖"
        message += f"{role_icon} *{role.upper()}* ({time}):\n{content}\n\n"
        
        # Limităm mesajul pentru a evita depășirea limitei Telegram
        if len(message) > 3500:
            message += "...(mesaj trunchiat din cauza dimensiunii)"
            break
    
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "🔙 Înapoi", 
        callback_data=f"admin_view_dates_{user_id}"
    ))
    
    send_message(chat_id, message, parse_mode="Markdown", reply_markup=kb)

def ask_message_target(chat_id):
    """Întreabă utilizatorul cui vrea să trimită mesajul"""
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("👤 Un utilizator specific", callback_data="admin_send_one"),
        types.InlineKeyboardButton("👥 Toți utilizatorii", callback_data="admin_send_all"),
        types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_back")
    )
    
    send_message(
        chat_id,
        "📨 *Trimite mesaj*\n\nCui vrei să trimiți mesajul?",
        parse_mode="Markdown",
        reply_markup=kb
    )

def ask_persona(chat_id, command, target_id=None):
    """Întreabă utilizatorul ce personaj să folosească"""
    personas = get_all_personas()
    
    kb = types.InlineKeyboardMarkup(row_width=2)
    for key, persona in personas.items():
        kb.add(types.InlineKeyboardButton(
            f"{persona['name']}", 
            callback_data=f"admin_{command}_persona_{key}" + (f"_{target_id}" if target_id else "")
        ))
    
    kb.add(types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_back"))
    
    send_message(
        chat_id,
        "🎭 *Selectează personajul:*\n\nCe personaj vrei să folosești pentru acest mesaj?",
        parse_mode="Markdown",
        reply_markup=kb
    )

def start_message_input(message, mode, persona, target_id=None):
    """Începe procesul de introducere a mesajului de către admin"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    admin_state[user_id] = {
        "mode": mode,
        "persona": persona,
        "target_id": target_id
    }
    
    send_message(
        chat_id,
        "✏️ Introdu tema mesajului sau spune despre ce vrei să vorbească LLM-ul:",
        parse_mode="Markdown"
    )
    
    # Setăm handler pentru următorul mesaj
    bot.register_next_step_handler(message, process_message_content)

def process_message_content(message):
    """Procesează conținutul mesajului de la admin"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    content = message.text
    
    if not content:
        send_message(chat_id, "❌ Conținut invalid. Încearcă din nou.")
        return
    
    state = admin_state.get(user_id, {})
    mode = state.get("mode", "")
    persona = state.get("persona", "joe")
    target_id = state.get("target_id")
    
    if mode == "send":
        # Trimite imediat mesajul
        if target_id:
            # Trimite către un utilizator specific
            from llm_service import query_llm
            from persona_prompts import get_persona_prompt
            
            system_prompt = get_persona_prompt(persona)
            llm_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generează un mesaj despre următorul subiect: {content}"}
            ]
            
            response = query_llm(llm_messages)
            if response:
                send_message(int(target_id), response)
                send_message(
                    chat_id, 
                    f"✅ Mesaj trimis către utilizatorul {target_id} folosind personajul {persona}."
                )
            else:
                send_message(chat_id, "❌ Eroare la generarea mesajului.")
        else:
            # Trimite către toți utilizatorii
            users = get_users()
            from llm_service import query_llm
            from persona_prompts import get_persona_prompt
            
            system_prompt = get_persona_prompt(persona)
            llm_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generează un mesaj despre următorul subiect: {content}"}
            ]
            
            response = query_llm(llm_messages)
            if response:
                success_count = 0
                for uid in users:
                    try:
                        send_message(int(uid), response)
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Eroare la trimiterea mesajului către {uid}: {e}")
                
                send_message(
                    chat_id, 
                    f"✅ Mesaj trimis către {success_count} utilizatori folosind personajul {persona}."
                )
            else:
                send_message(chat_id, "❌ Eroare la generarea mesajului.")
    
    elif mode == "schedule":
        # Continuă cu programarea
        admin_state[user_id]["topic"] = content
        
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton("📆 Introduce data/ora", callback_data="admin_schedule_datetime"),
            types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_back")
        )
        
        send_message(
            chat_id,
            "⏱ *Programare mesaj*\n\nMesajul va fi despre: " + content + "\n\nIntroduce data și ora:",
            parse_mode="Markdown",
            reply_markup=kb
        )

def start_datetime_input(message):
    """Începe procesul de introducere a datei și orei"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    send_message(
        chat_id,
        "📅 Introdu data și ora în format YYYY-MM-DD HH:MM:SS\n"
        "Exemplu: 2025-01-01 12:00:00",
        parse_mode="Markdown"
    )
    
    # Setăm handler pentru următorul mesaj
    bot.register_next_step_handler(message, process_datetime_input)

def process_datetime_input(message):
    """Procesează inputul de dată și oră"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    datetime_str = message.text
    
    try:
        # Verificăm formatul
        scheduled_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        
        # Verificăm dacă e în viitor
        if scheduled_time <= datetime.now():
            send_message(chat_id, "❌ Data și ora trebuie să fie în viitor. Încearcă din nou.")
            start_datetime_input(message)
            return
        
        # Salvăm în stare
        admin_state[user_id]["schedule_time"] = datetime_str
        
        # Întrebăm despre interval
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("O singură dată", callback_data="admin_schedule_once"),
            types.InlineKeyboardButton("Zilnic", callback_data="admin_schedule_interval_24"),
            types.InlineKeyboardButton("Săptămânal", callback_data="admin_schedule_interval_168"),
            types.InlineKeyboardButton("Lunar", callback_data="admin_schedule_interval_720"),
            types.InlineKeyboardButton("Personalizat", callback_data="admin_schedule_custom"),
            types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_back")
        )
        
        send_message(
            chat_id,
            f"🔄 *Recurență*\n\nMesajul va fi trimis la: {datetime_str}\n\nAlege frecvența repetării:",
            parse_mode="Markdown",
            reply_markup=kb
        )
        
    except ValueError:
        send_message(
            chat_id, 
            "❌ Format invalid. Te rog folosește formatul YYYY-MM-DD HH:MM:SS.\n"
            "Exemplu: 2025-01-01 12:00:00"
        )
        start_datetime_input(message)

def start_custom_interval_input(message):
    """Începe procesul de introducere a intervalului personalizat"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    send_message(
        chat_id,
        "⏱ Introdu intervalul în ore\n"
        "Exemplu: 12 (pentru un mesaj la fiecare 12 ore)",
        parse_mode="Markdown"
    )
    
    # Setăm handler pentru următorul mesaj
    bot.register_next_step_handler(message, process_interval_input)

def process_interval_input(message):
    """Procesează inputul pentru interval personalizat"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    try:
        interval = int(message.text)
        if interval <= 0:
            send_message(chat_id, "❌ Intervalul trebuie să fie un număr pozitiv. Încearcă din nou.")
            start_custom_interval_input(message)
            return
        
        finalize_schedule(user_id, chat_id, interval)
        
    except ValueError:
        send_message(chat_id, "❌ Trebuie să introduci un număr. Încearcă din nou.")
        start_custom_interval_input(message)

def finalize_schedule(user_id, chat_id, interval=None):
    """Finalizează procesul de programare a mesajului"""
    state = admin_state.get(user_id, {})
    
    if not all(k in state for k in ["persona", "topic", "schedule_time"]):
        send_message(chat_id, "❌ Date incomplete pentru programare. Începe din nou.")
        return
    
    target_type = "user" if state.get("target_id") else "all"
    target_id = state.get("target_id")
    persona = state.get("persona")
    topic = state.get("topic")
    schedule_time = state.get("schedule_time")
    
    # Programează mesajul
    message_id = schedule_message(
        target_type=target_type,
        target_id=target_id,
        persona=persona,
        topic=topic,
        schedule_time=schedule_time,
        interval=interval
    )
    
    # Confirmă programarea
    interval_str = f" și se va repeta la fiecare {interval} ore" if interval else ""
    target_str = f"utilizatorul {target_id}" if target_id else "toți utilizatorii"
    
    send_message(
        chat_id,
        f"✅ *Mesaj programat cu succes!*\n\n"
        f"📆 Data/ora: {schedule_time}{interval_str}\n"
        f"👤 Destinatar: {target_str}\n"
        f"🎭 Personaj: {persona}\n"
        f"📝 Subiect: {topic}\n\n"
        f"ID programare: `{message_id}`",
        parse_mode="Markdown"
    )
    
    # Resetează starea
    admin_state[user_id] = {"mode": "main"}

def show_scheduled_messages(chat_id):
    """Afișează toate mesajele programate"""
    messages = get_scheduled_messages()
    
    if not messages:
        send_message(chat_id, "Nu există mesaje programate.")
        return
    
    response = "📅 *Mesaje programate:*\n\n"
    
    for idx, msg in enumerate(messages, 1):
        target = msg.get("target_id", "toți utilizatorii") or "toți utilizatorii"
        schedule_time = msg.get("schedule_time", "necunoscut")
        persona = msg.get("persona", "necunoscut")
        topic = msg.get("topic", "")
        interval = msg.get("interval")
        message_id = msg.get("id", "")
        
        interval_str = f", repetare la {interval//3600}h" if interval else ""
        
        response += f"*{idx}.* 📆 {schedule_time}{interval_str}\n"
        response += f"👤 Către: {target}\n"
        response += f"🎭 Personaj: {persona}\n"
        response += f"📝 Subiect: {topic}\n"
        response += f"🆔 ID: `{message_id}`\n\n"
    
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("❌ Șterge un mesaj programat", callback_data="admin_delete_scheduled"),
        types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_back")
    )
    
    send_message(chat_id, response, parse_mode="Markdown", reply_markup=kb)

def show_delete_scheduled(chat_id):
    """Afișează lista de mesaje programate pentru ștergere"""
    messages = get_scheduled_messages()
    
    if not messages:
        send_message(chat_id, "Nu există mesaje programate.")
        return
    
    kb = types.InlineKeyboardMarkup(row_width=1)
    
    for idx, msg in enumerate(messages, 1):
        schedule_time = msg.get("schedule_time", "necunoscut")
        topic = msg.get("topic", "")
        message_id = msg.get("id", "")
        
        kb.add(types.InlineKeyboardButton(
            f"{idx}. {schedule_time} - {topic[:20]}...",
            callback_data=f"admin_delete_msg_{message_id}"
        ))
    
    kb.add(types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_scheduled"))
    
    send_message(
        chat_id,
        "❌ *Șterge mesaj programat*\n\nSelectează mesajul pe care vrei să îl ștergi:",
        parse_mode="Markdown",
        reply_markup=kb
    )

# Înregistrăm callback-urile pentru butoanele din panoul admin
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_callback_handler(call):
    """Gestionează callback-urile butoanelor admin"""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "Nu ai acces la această funcție.")
        return

    parts = call.data.split('_')
    action = parts[1] if len(parts) > 1 else ""
    
    try:
        # Acțiuni principale
        if action == "back":
            handle_admin_panel(call.message)
        
        elif action == "users":
            show_users(chat_id)
        
        elif action == "convs":
            show_user_list(chat_id, "view")
        
        elif action == "view" and len(parts) > 2:
            if parts[2] == "user":
                user_id_to_view = parts[3]
                show_conversation_dates(chat_id, user_id_to_view)
            elif parts[2] == "dates":
                user_id_to_view = parts[3]
                show_conversation_dates(chat_id, user_id_to_view)
            elif parts[2] == "conv" and len(parts) > 4:
                user_id_to_view = parts[3]
                date_to_view = parts[4]
                show_conversation(chat_id, user_id_to_view, date_to_view)
        
        elif action == "send":
            if len(parts) > 2:
                if parts[2] == "one":
                    show_user_list(chat_id, "send")
                elif parts[2] == "all":
                    ask_persona(chat_id, "send")
                elif parts[2] == "user" and len(parts) > 3:
                    target_id = parts[3]
                    ask_persona(chat_id, "send", target_id)
                elif parts[2] == "persona" and len(parts) > 3:
                    persona = parts[3]
                    target_id = parts[4] if len(parts) > 4 else None
                    start_message_input(call.message, "send", persona, target_id)
            else:
                ask_message_target(chat_id)
        
        elif action == "schedule":
            if len(parts) > 2:
                if parts[2] == "one":
                    show_user_list(chat_id, "schedule")
                elif parts[2] == "all":
                    ask_persona(chat_id, "schedule")
                elif parts[2] == "user" and len(parts) > 3:
                    target_id = parts[3]
                    ask_persona(chat_id, "schedule", target_id)
                elif parts[2] == "persona" and len(parts) > 3:
                    persona = parts[3]
                    target_id = parts[4] if len(parts) > 4 else None
                    start_message_input(call.message, "schedule", persona, target_id)
                elif parts[2] == "datetime":
                    start_datetime_input(call.message)
                elif parts[2] == "once":
                    finalize_schedule(user_id, chat_id)
                elif parts[2] == "interval" and len(parts) > 3:
                    interval = int(parts[3])
                    finalize_schedule(user_id, chat_id, interval)
                elif parts[2] == "custom":
                    start_custom_interval_input(call.message)
            else:
                ask_message_target(chat_id)
        
        elif action == "scheduled":
            show_scheduled_messages(chat_id)
        
        elif action == "delete":
            if parts[2] == "scheduled":
                show_delete_scheduled(chat_id)
            elif parts[2] == "msg" and len(parts) > 3:
                message_id = parts[3]
                remove_scheduled_message(message_id)
                bot.answer_callback_query(call.id, "Mesaj programat șters cu succes!")
                show_scheduled_messages(chat_id)
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Eroare la procesarea callback-ului admin: {e}")
        bot.answer_callback_query(call.id, "A apărut o eroare. Te rog încearcă din nou.")