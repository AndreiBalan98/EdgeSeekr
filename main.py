import requests # type: ignore
import json
import os
import logging
from telegram import Update # type: ignore
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, JobQueue # type: ignore
from datetime import datetime

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Set log level for debugging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Stocăm utilizatorii activi
active_users = set()

# Prompt de sistem – stil prietenos, natural
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Comportă-te ca un prieten real. Răspunde ca un om, cu un stil natural, chiar cu mici greșeli, abrevieri, sau exprimări colocviale. "
        "Nu da mesaje lungi, spune doar esența. E ok să suni casual, cald, cu personalitate. Nu fi formal. "
        "Imaginează-ți că ești prietenul bun al persoanei care vorbește cu tine."
    )
}

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
            SYSTEM_PROMPT,
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
    user_id = update.effective_chat.id
    active_users.add(user_id)
    user_text = update.message.text
    response = call_llm(user_text)
    context.bot.send_message(chat_id=user_id, text=response)

def send_reminders(context: CallbackContext):
    for user_id in active_users:
        context.bot.send_message(chat_id=user_id, text="Hei, ce mai faci? 😊 Dacă vrei să mai vorbim, sunt aici!")

def main():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle))

    # JobQueue pentru trimiterea de mesaje automate
    job_queue = updater.job_queue
    job_queue.run_repeating(send_reminders, interval=600, first=600)  # la fiecare 10 minute

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
