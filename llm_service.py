#!/usr/bin/env python3
import os
import logging
import requests
from bot_core import WEBHOOK_URL

# Configurare logging
logger = logging.getLogger(__name__)

# Configurări OpenRouter - standardizare nume variabile
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "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")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "microsoft/mai-ds-r1:free")

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