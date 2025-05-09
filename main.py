import os
import json
import logging
import requests  # type: ignore
from telegram import Update  # type: ignore
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters  # type: ignore

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Prompt de sistem – stil prietenos
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Comportă-te ca un prieten real. Răspunde ca un om, cu un stil natural, chiar cu mici greșeli, abrevieri, sau exprimări colocviale. "
        "Nu da mesaje lungi, spune doar esența. E ok să suni casual, cald, cu personalitate. Nu fi formal. "
        "Imaginează-ți că ești prietenul bun al persoanei care vorbește cu tine."
    )
}

# Istoric mesaje
MAX_CHAR_COUNT = 50000
message_history = []  # conține dict-uri: {"role": "...", "content": "..."}


def update_message_history(role: str, content: str):
    global message_history
    message_history.append({"role": role, "content": content})

    # Trunchiem istoria dacă depășim limita de caractere
    total_chars = sum(len(msg["content"]) for msg in message_history)
    while total_chars > MAX_CHAR_COUNT and message_history:
        message_history.pop(0)
        total_chars = sum(len(msg["content"]) for msg in message_history)


def call_llm(prompt: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": "EdgeSeekrBot"
    }

    update_message_history("user", prompt)

    data = {
        "model": "microsoft/mai-ds-r1:free",
        "messages": [SYSTEM_PROMPT] + message_history
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.ok:
        ai_response = response.json()["choices"][0]["message"]["content"]
        update_message_history("assistant", ai_response)
        return ai_response
    else:
        print(response.text)
        return "Oops, ceva n-a mers cu răspunsul 🤷‍♂️"


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    response = call_llm(user_text)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()


if __name__ == "__main__":
    main()
