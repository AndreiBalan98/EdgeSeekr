#!/usr/bin/env python3
import logging
from datetime import datetime
from telebot import types

from bot_core import bot, send_message
from database import (get_users, get_conversation_dates, get_conversation_history,
    log_user_activity, get_scheduled_messages, remove_scheduled_message, is_admin)
from scheduler import schedule_message
from persona_prompts import get_all_personas, get_persona_prompt
from llm_service import query_llm

# Setup logging and admin state
logger = logging.getLogger(__name__)
admin_state = {}

def handle_admin_panel(message):
    """Main admin panel handler"""
    user_id, chat_id = message.from_user.id, message.chat.id
    if not is_admin(user_id):
        send_message(chat_id, "❌ Nu ai acces la această comandă.")
        log_user_activity(user_id, None, "admin_panel_denied")
        return
    
    try:
        log_user_activity(user_id, None, "admin_panel")
        admin_state[user_id] = {"mode": "main"}
        
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(*[types.InlineKeyboardButton(btn[0], callback_data=btn[1]) for btn in [
            ("👥 Vezi utilizatori", "admin_users"),
            ("💬 Vezi conversații", "admin_convs"),
            ("📨 Trimite mesaj", "admin_send"),
            ("⏱ Programează mesaje", "admin_schedule"),
            ("🗓 Mesaje programate", "admin_scheduled")
        ]])
        
        send_message(chat_id, "🔐 *Panou de administrare*\n\nSelectează o opțiune:", 
                    parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"Eroare la afișarea panoului admin: {e}")
        send_message(chat_id, "❌ A apărut o eroare. Te rog încearcă din nou.")

def show_users(chat_id):
    """Display user list"""
    try:
        users = get_users()
        if not users:
            send_message(chat_id, "Nu există utilizatori înregistrați.")
            return
        
        message = "👥 *Utilizatori înregistrați:*\n\n"
        for user_id, data in users.items():
            message += (f"ID: `{user_id}`\n"
                      f"Username: @{data.get('username', 'Fără nume') or 'Fără nume'}\n"
                      f"Prima interacțiune: {data.get('first_seen', 'Necunoscut')}\n"
                      f"Ultima activitate: {data.get('last_active', 'Necunoscut')}\n\n")
        
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_back"))
        send_message(chat_id, message, parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"Eroare la afișarea utilizatorilor: {e}")
        send_message(chat_id, "❌ A apărut o eroare la afișarea utilizatorilor.")

def show_user_list(chat_id, mode):
    """Display user list with action buttons"""
    try:
        users = get_users()
        if not users:
            send_message(chat_id, "Nu există utilizatori înregistrați.")
            return
        
        kb = types.InlineKeyboardMarkup(row_width=1)
        for user_id, data in users.items():
            username = data.get("username", "Fără nume") or "Fără nume"
            kb.add(types.InlineKeyboardButton(f"@{username} ({user_id})", 
                                             callback_data=f"admin_{mode}_user_{user_id}"))
        kb.add(types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_back"))
        send_message(chat_id, "👥 *Selectează un utilizator:*\n\n", parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"Eroare la afișarea listei de utilizatori: {e}")
        send_message(chat_id, "❌ A apărut o eroare la afișarea listei de utilizatori.")

def show_conversation_dates(chat_id, user_id):
    """Show conversation dates for a user"""
    try:
        dates = get_conversation_dates(user_id)
        if not dates:
            send_message(chat_id, f"Utilizatorul {user_id} nu are conversații salvate.")
            return
        
        kb = types.InlineKeyboardMarkup(row_width=2)
        for date in dates[:10]:  # Limită de 10 date pentru a evita butoane prea multe
            kb.add(types.InlineKeyboardButton(date, callback_data=f"admin_view_conv_{user_id}_{date}"))
        kb.add(types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_convs"))
        send_message(chat_id, f"📅 *Conversații pentru utilizatorul {user_id}:*\n\nSelectează o dată:", 
                    parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"Eroare la afișarea datelor conversațiilor: {e}")
        send_message(chat_id, "❌ A apărut o eroare la afișarea datelor conversațiilor.")

def show_conversation(chat_id, user_id, date):
    """Show conversation for a user on specified date"""
    try:
        conversation = get_conversation_history(user_id, date)
        if not conversation:
            send_message(chat_id, f"Nu există conversații pentru {user_id} în data {date}.")
            return
        
        message = f"💬 *Conversație {user_id} - {date}:*\n\n"
        for msg in conversation:
            role = msg.get('role', '')
            time = msg.get('time', '')
            content = msg.get('message', '')
            
            role_icon = "👤" if role == "user" else "🤖"
            message += f"{role_icon} *{role.upper()}* ({time}):\n{content}\n\n"
            
            if len(message) > 3500:
                message += "...(mesaj trunchiat din cauza dimensiunii)"
                break
        
        kb = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Înapoi", callback_data=f"admin_view_dates_{user_id}")
        )
        send_message(chat_id, message, parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"Eroare la afișarea conversației: {e}")
        send_message(chat_id, "❌ A apărut o eroare la afișarea conversației.")

def ask_message_target(chat_id):
    """Ask admin who to send the message to"""
    try:
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(*[types.InlineKeyboardButton(btn[0], callback_data=btn[1]) for btn in [
            ("👤 Un utilizator specific", "admin_send_one"),
            ("👥 Toți utilizatorii", "admin_send_all"),
            ("🔙 Înapoi", "admin_back")
        ]])
        send_message(chat_id, "📨 *Trimite mesaj*\n\nCui vrei să trimiți mesajul?", 
                    parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"Eroare la selectarea destinatarului: {e}")
        send_message(chat_id, "❌ A apărut o eroare la selectarea destinatarului.")

def ask_persona(chat_id, command, target_id=None):
    """Ask admin which persona to use"""
    try:
        personas = get_all_personas()
        kb = types.InlineKeyboardMarkup(row_width=2)
        for key, persona in personas.items():
            callback = f"admin_{command}_persona_{key}" + (f"_{target_id}" if target_id else "")
            kb.add(types.InlineKeyboardButton(f"{persona['name']}", callback_data=callback))
        kb.add(types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_back"))
        send_message(chat_id, "🎭 *Selectează personajul:*\n\nCe personaj vrei să folosești pentru acest mesaj?",
                    parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"Eroare la selectarea personajului: {e}")
        send_message(chat_id, "❌ A apărut o eroare la selectarea personajului.")

def start_message_input(message, mode, persona, target_id=None):
    """Start message input process"""
    try:
        user_id, chat_id = message.from_user.id, message.chat.id
        if not is_admin(user_id):
            send_message(chat_id, "❌ Nu ai acces la această comandă.")
            return
            
        admin_state[user_id] = {"mode": mode, "persona": persona, "target_id": target_id}
        send_message(chat_id, "✏️ Introdu tema mesajului sau spune despre ce vrei să vorbească LLM-ul:", 
                    parse_mode="Markdown")
        bot.register_next_step_handler(message, process_message_content)
    except Exception as e:
        logger.error(f"Eroare la începerea introducerii mesajului: {e}")
        send_message(message.chat.id, "❌ A apărut o eroare. Te rog încearcă din nou.")

def process_message_content(message):
    """Process message content from admin"""
    user_id, chat_id, content = message.from_user.id, message.chat.id, message.text
    
    if not is_admin(user_id):
        send_message(chat_id, "❌ Nu ai acces la această comandă.")
        return
        
    if not content:
        send_message(chat_id, "❌ Conținut invalid. Încearcă din nou.")
        return
    
    try:
        state = admin_state.get(user_id, {})
        mode = state.get("mode", "")
        persona = state.get("persona", "joe")
        target_id = state.get("target_id")
        
        if mode == "send":
            system_prompt = get_persona_prompt(persona)
            llm_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generează un mesaj despre următorul subiect: {content}"}
            ]
            response = query_llm(llm_messages)
            
            if response:
                if target_id:
                    try:
                        send_message(int(target_id), response)
                        send_message(chat_id, f"✅ Mesaj trimis către utilizatorul {target_id} folosind personajul {persona}.")
                        log_user_activity(user_id, None, f"send_message_to_{target_id}")
                    except Exception as e:
                        logger.error(f"Eroare la trimiterea mesajului către {target_id}: {e}")
                        send_message(chat_id, f"❌ Nu s-a putut trimite mesajul către {target_id}.")
                else:
                    users, success_count = get_users(), 0
                    for uid in users:
                        try:
                            send_message(int(uid), response)
                            success_count += 1
                        except Exception as e:
                            logger.error(f"Eroare la trimiterea mesajului către {uid}: {e}")
                    send_message(chat_id, f"✅ Mesaj trimis către {success_count} utilizatori folosind personajul {persona}.")
                    log_user_activity(user_id, None, "send_message_to_all")
            else:
                send_message(chat_id, "❌ Eroare la generarea mesajului.")
        
        elif mode == "schedule":
            admin_state[user_id]["topic"] = content
            kb = types.InlineKeyboardMarkup(row_width=1)
            kb.add(
                types.InlineKeyboardButton("📆 Introduce data/ora", callback_data="admin_schedule_datetime"),
                types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_back")
            )
            send_message(chat_id, f"⏱ *Programare mesaj*\n\nMesajul va fi despre: {content}\n\nIntroduce data și ora:",
                        parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"Eroare la procesarea conținutului mesajului: {e}")
        send_message(chat_id, "❌ A apărut o eroare la procesarea mesajului. Te rog încearcă din nou.")

def start_datetime_input(message):
    """Start date/time input process"""
    user_id, chat_id = message.from_user.id, message.chat.id
    
    if not is_admin(user_id):
        send_message(chat_id, "❌ Nu ai acces la această comandă.")
        return
        
    send_message(chat_id, "📅 Introdu data și ora în format YYYY-MM-DD HH:MM:SS\n"
                         "Exemplu: 2025-01-01 12:00:00", parse_mode="Markdown")
    bot.register_next_step_handler(message, process_datetime_input)

def process_datetime_input(message):
    """Process date/time input"""
    user_id, chat_id, datetime_str = message.from_user.id, message.chat.id, message.text
    
    if not is_admin(user_id):
        send_message(chat_id, "❌ Nu ai acces la această comandă.")
        return
        
    try:
        scheduled_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        if scheduled_time <= datetime.now():
            send_message(chat_id, "❌ Data și ora trebuie să fie în viitor. Încearcă din nou.")
            start_datetime_input(message)
            return
        
        admin_state[user_id]["schedule_time"] = datetime_str
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(*[types.InlineKeyboardButton(btn[0], callback_data=btn[1]) for btn in [
            ("O singură dată", "admin_schedule_once"),
            ("Zilnic", "admin_schedule_interval_24"),
            ("Săptămânal", "admin_schedule_interval_168"),
            ("Lunar", "admin_schedule_interval_720"),
            ("Personalizat", "admin_schedule_custom"),
            ("🔙 Înapoi", "admin_back")
        ]])
        send_message(chat_id, f"🔄 *Recurență*\n\nMesajul va fi trimis la: {datetime_str}\n\nAlege frecvența repetării:",
                    parse_mode="Markdown", reply_markup=kb)
    except ValueError:
        send_message(chat_id, "❌ Format invalid. Te rog folosește formatul YYYY-MM-DD HH:MM:SS.\n"
                            "Exemplu: 2025-01-01 12:00:00")
        start_datetime_input(message)
    except Exception as e:
        logger.error(f"Eroare la procesarea datei/orei: {e}")
        send_message(chat_id, "❌ A apărut o eroare la procesarea datei. Te rog încearcă din nou.")

def start_custom_interval_input(message):
    """Start custom interval input process"""
    user_id, chat_id = message.from_user.id, message.chat.id
    
    if not is_admin(user_id):
        send_message(chat_id, "❌ Nu ai acces la această comandă.")
        return
        
    send_message(chat_id, "⏱ Introdu intervalul în ore\nExemplu: 12 (pentru un mesaj la fiecare 12 ore)",
                parse_mode="Markdown")
    bot.register_next_step_handler(message, process_interval_input)

def process_interval_input(message):
    """Process custom interval input"""
    user_id, chat_id = message.from_user.id, message.chat.id
    
    if not is_admin(user_id):
        send_message(chat_id, "❌ Nu ai acces la această comandă.")
        return
        
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
    except Exception as e:
        logger.error(f"Eroare la procesarea intervalului: {e}")
        send_message(chat_id, "❌ A apărut o eroare la procesarea intervalului. Te rog încearcă din nou.")

def finalize_schedule(user_id, chat_id, interval=None):
    """Finalize message scheduling"""
    if not is_admin(user_id):
        send_message(chat_id, "❌ Nu ai acces la această comandă.")
        return
        
    try:
        state = admin_state.get(user_id, {})
        if not all(k in state for k in ["persona", "topic", "schedule_time"]):
            send_message(chat_id, "❌ Date incomplete pentru programare. Începe din nou.")
            return
        
        target_type = "user" if state.get("target_id") else "all"
        target_id = state.get("target_id")
        persona = state.get("persona")
        topic = state.get("topic")
        schedule_time = state.get("schedule_time")
        
        message_id = schedule_message(target_type=target_type, target_id=target_id, persona=persona,
                                    topic=topic, schedule_time=schedule_time, interval=interval)
        
        interval_str = f" și se va repeta la fiecare {interval} ore" if interval else ""
        target_str = f"utilizatorul {target_id}" if target_id else "toți utilizatorii"
        
        send_message(chat_id, f"✅ *Mesaj programat cu succes!*\n\n"
                            f"📆 Data/ora: {schedule_time}{interval_str}\n"
                            f"👤 Destinatar: {target_str}\n"
                            f"🎭 Personaj: {persona}\n"
                            f"📝 Subiect: {topic}\n\n"
                            f"ID programare: `{message_id}`", parse_mode="Markdown")
        
        log_user_activity(user_id, None, "schedule_message")
        admin_state[user_id] = {"mode": "main"}
    except Exception as e:
        logger.error(f"Eroare la finalizarea programării: {e}")
        send_message(chat_id, "❌ A apărut o eroare la finalizarea programării. Te rog încearcă din nou.")

def show_scheduled_messages(chat_id):
    """Show all scheduled messages"""
    try:
        messages = get_scheduled_messages()
        if not messages:
            send_message(chat_id, "Nu există mesaje programate.")
            return
        
        response = "📅 *Mesaje programate:*\n\n"
        for idx, msg in enumerate(messages, 1):
            interval_text = f", repetare la {msg.get('interval')//3600}h" if msg.get('interval') else ''
            target_id = msg.get('target_id', 'toți utilizatorii') or 'toți utilizatorii'
            
            response += (f"*{idx}.* 📆 {msg.get('schedule_time', 'necunoscut')}{interval_text}\n"
                        f"👤 Către: {target_id}\n"
                        f"🎭 Personaj: {msg.get('persona', 'necunoscut')}\n"
                        f"📝 Subiect: {msg.get('topic', '')}\n"
                        f"🆔 ID: `{msg.get('id', '')}`\n\n")
        
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton("❌ Șterge un mesaj programat", callback_data="admin_delete_scheduled"),
            types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_back")
        )
        send_message(chat_id, response, parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"Eroare la afișarea mesajelor programate: {e}")
        send_message(chat_id, "❌ A apărut o eroare la afișarea mesajelor programate.")

def show_delete_scheduled(chat_id):
    """Show scheduled messages list for deletion"""
    try:
        messages = get_scheduled_messages()
        if not messages:
            send_message(chat_id, "Nu există mesaje programate.")
            return
        
        kb = types.InlineKeyboardMarkup(row_width=1)
        for idx, msg in enumerate(messages, 1):
            topic = msg.get('topic', '')
            topic_short = topic[:20] + "..." if len(topic) > 20 else topic
            
            kb.add(types.InlineKeyboardButton(
                f"{idx}. {msg.get('schedule_time', 'necunoscut')} - {topic_short}",
                callback_data=f"admin_delete_msg_{msg.get('id', '')}"
            ))
        kb.add(types.InlineKeyboardButton("🔙 Înapoi", callback_data="admin_scheduled"))
        send_message(chat_id, "❌ *Șterge mesaj programat*\n\nSelectează mesajul pe care vrei să îl ștergi:",
                    parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"Eroare la afișarea mesajelor pentru ștergere: {e}")
        send_message(chat_id, "❌ A apărut o eroare la afișarea mesajelor pentru ștergere.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_callback_handler(call):
    """Handle admin callback buttons"""
    user_id, chat_id = call.from_user.id, call.message.chat.id
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "Nu ai acces la această funcție.")
        return

    parts = call.data.split('_')
    action = parts[1] if len(parts) > 1 else ""
    
    try:
        # Main actions
        if action == "back":
            handle_admin_panel(call.message)
        elif action == "users":
            show_users(chat_id)
        elif action == "convs":
            show_user_list(chat_id, "view")
        elif action == "view" and len(parts) > 2:
            if parts[2] == "user":
                show_conversation_dates(chat_id, parts[3])
            elif parts[2] == "dates":
                show_conversation_dates(chat_id, parts[3])
            elif parts[2] == "conv" and len(parts) > 4:
                show_conversation(chat_id, parts[3], parts[4])
        elif action == "send":
            if len(parts) > 2:
                if parts[2] == "one":
                    show_user_list(chat_id, "send")
                elif parts[2] == "all":
                    ask_persona(chat_id, "send")
                elif parts[2] == "user" and len(parts) > 3:
                    ask_persona(chat_id, "send", parts[3])
                elif parts[2] == "persona" and len(parts) > 3:
                    start_message_input(call.message, "send", parts[3], parts[4] if len(parts) > 4 else None)
            else:
                ask_message_target(chat_id)
        elif action == "schedule":
            if len(parts) > 2:
                if parts[2] == "one":
                    show_user_list(chat_id, "schedule")
                elif parts[2] == "all":
                    ask_persona(chat_id, "schedule")
                elif parts[2] == "user" and len(parts) > 3:
                    ask_persona(chat_id, "schedule", parts[3])
                elif parts[2] == "persona" and len(parts) > 3:
                    start_message_input(call.message, "schedule", parts[3], parts[4] if len(parts) > 4 else None)
                elif parts[2] == "datetime":
                    start_datetime_input(call.message)
                elif parts[2] == "once":
                    finalize_schedule(user_id, chat_id)
                elif parts[2] == "interval" and len(parts) > 3:
                    finalize_schedule(user_id, chat_id, int(parts[3]))
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
                msg_id = parts[3]
                if remove_scheduled_message(msg_id):
                    bot.answer_callback_query(call.id, "Mesaj programat șters cu succes!")
                    log_user_activity(user_id, None, f"delete_scheduled_msg_{msg_id}")
                else:
                    bot.answer_callback_query(call.id, "Nu s-a putut șterge mesajul programat.")
                show_scheduled_messages(chat_id)
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Eroare la procesarea callback-ului admin: {e}")
        bot.answer_callback_query(call.id, "A apărut o eroare. Te rog încearcă din nou.")