import os
import json
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Încarcă variabilele din .env
load_dotenv()

# Configurare logging
logger = logging.getLogger(__name__)

# ID administrator - fără default hard-codat
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))  # Default la 0 = niciun admin

if ADMIN_ID == 0:
    logger.warning("ADMIN_ID nu este setat! Funcționalitățile admin nu vor fi disponibile.")

# Calea către directorul de date
DATA_DIR = Path("data")
USER_DATA_FILE = DATA_DIR / "users.json"
CONVERSATIONS_DIR = DATA_DIR / "conversations"
SCHEDULED_MESSAGES_FILE = DATA_DIR / "scheduled_messages.json"

def init_db():
    """Inițializează structura de fișiere pentru baza de date"""
    # Creează directoarele dacă nu există
    DATA_DIR.mkdir(exist_ok=True)
    CONVERSATIONS_DIR.mkdir(exist_ok=True)
    
    # Inițializează fișierul utilizatorilor dacă nu există
    if not USER_DATA_FILE.exists():
        with open(USER_DATA_FILE, 'w') as f:
            json.dump({}, f)
    
    # Inițializează fișierul cu mesaje programate dacă nu există
    if not SCHEDULED_MESSAGES_FILE.exists():
        with open(SCHEDULED_MESSAGES_FILE, 'w') as f:
            json.dump([], f)

def get_users():
    """Obține toți utilizatorii înregistrați"""
    try:
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_users(users_data):
    """Salvează datele utilizatorilor"""
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(users_data, f, indent=2)

def log_user_activity(user_id, username=None, action=None):
    """Înregistrează activitatea unui utilizator"""
    user_id = str(user_id)  # Convertim la string pentru a fi folosit ca cheie JSON
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    users = get_users()
    
    if user_id not in users:
        users[user_id] = {
            "first_seen": now,
            "last_active": now,
            "username": username,
            "actions": []
        }
    else:
        users[user_id]["last_active"] = now
        if username:
            users[user_id]["username"] = username
    
    # Adaugă acțiunea curentă dacă este specificată
    if action:
        actions = users[user_id].get("actions", [])
        actions.append({"time": now, "action": action})
        users[user_id]["actions"] = actions[-100:]  # Păstrează doar ultimele 100 de acțiuni
    
    save_users(users)

def log_conversation(user_id, role, message):
    """Salvează un mesaj din conversație"""
    user_id = str(user_id)
    now = datetime.now().strftime("%Y-%m-%d")
    
    # Numele fișierului pentru conversația din ziua curentă
    conv_file = CONVERSATIONS_DIR / f"{user_id}_{now}.json"
    
    try:
        if conv_file.exists():
            with open(conv_file, 'r') as f:
                conversation = json.load(f)
        else:
            conversation = []
        
        # Adaugă mesajul cu timestamp
        conversation.append({
            "role": role,
            "message": message,
            "time": datetime.now().strftime("%H:%M:%S")
        })
        
        # Salvează conversația
        with open(conv_file, 'w') as f:
            json.dump(conversation, f, indent=2)
            
    except Exception as e:
        logger.error(f"Eroare la salvarea conversației: {e}")

def get_conversation_history(user_id, date=None):
    """Obține istoricul conversațiilor pentru un utilizator"""
    user_id = str(user_id)
    
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    
    conv_file = CONVERSATIONS_DIR / f"{user_id}_{date}.json"
    
    try:
        if conv_file.exists():
            with open(conv_file, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Eroare la citirea conversației: {e}")
        return []

def get_conversation_dates(user_id):
    """Obține datele la care un utilizator a avut conversații"""
    user_id = str(user_id)
    dates = []
    
    try:
        prefix = f"{user_id}_"
        for file in CONVERSATIONS_DIR.glob(f"{prefix}*.json"):
            date_part = file.name[len(prefix):-5]  # Elimină prefixul și extensia
            dates.append(date_part)
        return sorted(dates, reverse=True)
    except Exception as e:
        logger.error(f"Eroare la obținerea datelor conversațiilor: {e}")
        return []

def is_admin(user_id):
    """Verifică dacă un utilizator este administrator"""
    return int(user_id) == ADMIN_ID

def save_scheduled_message(schedule_data):
    """Salvează un mesaj programat"""
    try:
        with open(SCHEDULED_MESSAGES_FILE, 'r') as f:
            scheduled = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        scheduled = []
    
    scheduled.append(schedule_data)
    
    with open(SCHEDULED_MESSAGES_FILE, 'w') as f:
        json.dump(scheduled, f, indent=2)

def get_scheduled_messages():
    """Obține toate mesajele programate"""
    try:
        with open(SCHEDULED_MESSAGES_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def remove_scheduled_message(message_id):
    """Elimină un mesaj programat"""
    scheduled = get_scheduled_messages()
    scheduled = [msg for msg in scheduled if msg.get("id") != message_id]
    
    with open(SCHEDULED_MESSAGES_FILE, 'w') as f:
        json.dump(scheduled, f, indent=2)