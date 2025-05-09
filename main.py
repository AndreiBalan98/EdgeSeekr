import os
import json
import logging
import requests  # type: ignore
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

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


def call_llm(prompt: str) -> str:
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
