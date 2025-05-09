import requests # type: ignore
import os
import json

# Variabile
TELEGRAM_TOKEN = "7711949090:AAGXMoHzN66c8WB2hkdmssZU5PZzGgjZmh4"
CHAT_ID = "8111657402"  # ID-ul tău de chat

def test_telegram_api():
    """Testează direct API-ul Telegram pentru a verifica dacă token-ul funcționează."""
    print("Testare getMe...")
    response = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\nToken-ul este valid!")
    else:
        print("\nToken-ul NU este valid!")
        return
    
    # Testează trimiterea unui mesaj
    print("\nTestare sendMessage...")
    message_data = {
        "chat_id": CHAT_ID,
        "text": "Test direct către API-ul Telegram. Dacă vezi acest mesaj, problema este în codul Flask/pyTelegramBotAPI."
    }
    
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
        json=message_data
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\nMesajul a fost trimis cu succes!")
    else:
        print("\nEroare la trimiterea mesajului.")

if __name__ == "__main__":
    test_telegram_api()