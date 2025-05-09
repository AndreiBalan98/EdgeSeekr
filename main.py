import requests
import os
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def call_llm(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "microsoft/phi-2",  # sau alt model OpenRouter
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    res = requests.post(url, headers=headers, json=data)
    if res.ok:
        return res.json()["choices"][0]["message"]["content"]
    else:
        return "Eroare de la LLM."

def handle(update: Update, context: CallbackContext):
    user_text = update.message.text
    response = call_llm(user_text)
    context.bot.send_message(chat_id=update.effective_chat.id, text=response)

def main():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
