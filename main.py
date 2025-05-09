import requests # type: ignore
import json
import os
from telegram import Update # type: ignore
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext # type: ignore

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def call_llm(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": "EdgeSeekrBot"
    }
    data = {
        "model": "microsoft/mai-ds-r1:free",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.ok:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print(response.text)
        return "Eroare de la modelul MAI DS R1."

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
