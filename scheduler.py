#!/usr/bin/env python3
import uuid
import logging
import threading
import time
from datetime import datetime, timedelta

from bot_core import bot, send_message
from database import get_scheduled_messages, remove_scheduled_message, get_users
from llm_service import query_llm
from persona_prompts import get_persona_prompt

# Configurare logging
logger = logging.getLogger(__name__)

def parse_schedule_time(time_str):
    """Convertește un string de timp în datetime"""
    try:
        return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        logger.error(f"Format de timp invalid: {time_str}")
        return None

def schedule_message(target_type, target_id, persona, topic, schedule_time, interval=None):
    """
    Programează un mesaj
    
    Args:
        target_type: 'user' sau 'all'
        target_id: ID-ul utilizatorului sau None pentru 'all'
        persona: Cheia personajului
        topic: Subiectul mesajului
        schedule_time: Timpul programat (string "%Y-%m-%d %H:%M:%S")
        interval: Interval de repetiție în ore sau None
    
    Returns:
        ID-ul mesajului programat
    """
    # Generează un ID unic pentru acest mesaj programat
    message_id = str(uuid.uuid4())
    
    # Converteste intervalul în secunde dacă e specificat
    interval_seconds = None
    if interval:
        try:
            interval_seconds = int(interval) * 3600  # ore în secunde
        except (ValueError, TypeError):
            logger.error(f"Interval invalid: {interval}")
    
    # Creează datele programării
    schedule_data = {
        "id": message_id,
        "target_type": target_type,
        "target_id": target_id,
        "persona": persona,
        "topic": topic,
        "schedule_time": schedule_time,
        "interval": interval_seconds,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    from database import save_scheduled_message
    save_scheduled_message(schedule_data)
    
    return message_id

def process_scheduled_messages():
    """Procesează mesajele programate și le trimite dacă e momentul"""
    messages = get_scheduled_messages()
    now = datetime.now()
    
    for message in messages:
        schedule_time = parse_schedule_time(message.get("schedule_time"))
        if not schedule_time:
            continue
        
        # Verifică dacă e timpul să trimitem mesajul
        if schedule_time <= now:
            try:
                # Obține detaliile personajului și pregătește mesajul
                persona = message.get("persona", "joe")
                topic = message.get("topic", "")
                system_prompt = get_persona_prompt(persona)
                
                # Creează contextul pentru LLM
                llm_messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generează un mesaj despre următorul subiect: {topic}"}
                ]
                
                # Generează răspunsul
                response = query_llm(llm_messages)
                
                if response:
                    # Trimite către destinatarii specificați
                    target_type = message.get("target_type")
                    target_id = message.get("target_id")
                    
                    if target_type == "user" and target_id:
                        # Trimite către utilizatorul specificat
                        send_message(target_id, response)
                        logger.info(f"Mesaj programat trimis către utilizatorul {target_id}")
                    
                    elif target_type == "all":
                        # Trimite către toți utilizatorii
                        users = get_users()
                        for user_id in users:
                            try:
                                send_message(user_id, response)
                            except Exception as e:
                                logger.error(f"Eroare la trimiterea mesajului către {user_id}: {e}")
                        logger.info(f"Mesaj programat trimis către toți utilizatorii")
                
                # Verifică dacă mesajul trebuie reprogramat
                interval = message.get("interval")
                if interval:
                    # Calculează următorul timp programat
                    next_time = schedule_time + timedelta(seconds=interval)
                    message["schedule_time"] = next_time.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Salvează mesajul actualizat
                    remove_scheduled_message(message["id"])
                    from database import save_scheduled_message
                    save_scheduled_message(message)
                else:
                    # Șterge mesajul dacă nu este recurent
                    remove_scheduled_message(message["id"])
                    
            except Exception as e:
                logger.error(f"Eroare la procesarea mesajului programat {message.get('id')}: {e}")

def start_scheduler():
    """Pornește programatorul în fundal"""
    def scheduler_loop():
        while True:
            try:
                process_scheduled_messages()
            except Exception as e:
                logger.error(f"Eroare în bucla programatorului: {e}")
            
            # Așteaptă un minut până la următoarea verificare
            time.sleep(60)
    
    # Pornește thread-ul programatorului
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()
    logger.info("Programator de mesaje pornit")