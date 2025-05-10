import os
import logging
import requests
from dotenv import load_dotenv
from bot_core import WEBHOOK_URL  # Importăm doar ce avem nevoie pentru a evita circular imports

# Încarcă variabilele din .env
load_dotenv()

# Configurare logging
logger = logging.getLogger(__name__)

# Configurări OpenRouter - fără credențiale hard-codate
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "microsoft/mai-ds-r1:free")  # Default model e ok

# Verificare API key
if not OPENROUTER_API_KEY:
    logger.critical("OPENROUTER_API_KEY nu este setat! Verifică variabilele de mediu sau .env")
    raise EnvironmentError("OPENROUTER_API_KEY lipsește")

def query_llm(messages):
    """Interogare API OpenRouter"""
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": WEBHOOK_URL,
            "X-Title": "EdgeSeekr Bot"
        }
        
        data = {
            "model": OPENROUTER_MODEL, 
            "messages": messages
        }
        
        logger.info(f"Trimitere cerere către OpenRouter: {OPENROUTER_MODEL}")
        
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
            else:
                logger.error(f"Răspuns invalid de la API: {result}")
        else:
            logger.error(f"Eroare API: {response.status_code} - {response.text[:200]}")
        
        return None
        
    except Exception as e:
        logger.error(f"Excepție API: {e}")
        return None