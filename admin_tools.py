#!/usr/bin/env python3
import logging
from telebot import types
from datetime import datetime

from bot_core import bot, send_message
from database import (
    is_admin, get_users, get_conversation_history, 
    get_conversation_dates, get_scheduled_messages
)
from scheduler import schedule_message
from persona_prompts import get_all_personas

# Configurare logging
logger = logging.getLogger(__name__)

# Stare temporară pentru interacțiuni în mai mulți pași
admin_states = {}

def generate_user_stats():
    """Generează statistici despre utilizatorii botului"""
    users = get_users()
    
    if not users:
        return "Nu există încă date despre utilizatori."
    
    stats = "*📊 Statistici Utilizatori*\n\n"
    for user_id, data in users.items():
        username = data.get("username", "Necunoscut")
        last_active = data.get("last_active", "Necunoscut")
        first_seen = data.get("first_seen", "Necunoscut")
        
        stats += f"*ID:* {user_id}\n"
        stats += f"*Username:* @{username}\n" if username else "*Username:* Necunoscut\n"
        stats += f"*Prima utilizare:* {first_seen}\n"
        stats += f"*Ultima activitate:* {last_active}\n\n"
    
    return stats

def generate_scheduled_messages_info():
    """Generează informații despre mesajele programate"""
    messages = get_scheduled_messages()
    
    if not messages:
        return "Nu există mesaje programate."
    
    info = "*📅 Mesaje Programate*\n\n"
    for msg in messages:
        target = "toți utilizatorii" if msg.get("target_type") == "all" else f"utilizatorul {msg.get('target_id')}"
        persona = msg.get("persona", "joe")
        schedule_time = msg.get("schedule_time", "Necunoscut")
        topic = msg.get("topic", "Necunoscut")
        interval = msg.get("interval")
        recurring = "Da" if interval else "Nu"
        
        info += f"*ID:* `{msg.get('id')[:8]}...`\n"
        info += f"*Destinatar:* {target}\n"
        info += f"*Personaj:* {persona}\n"
        info += f"*Subiect:* {topic}\n"
        info += f"*Programat pentru:* {schedule_time}\n"
        info += f"*Recurent:* {recurring}\n\n"
    
    return info

def handle_admin_panel(message):
    """Afișează panoul de administrare"""
    user_id =