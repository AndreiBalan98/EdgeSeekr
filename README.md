# 🤖 Telegram Bot cu LLM (OpenRouter)

Un bot simplu de Telegram care răspunde cu ajutorul unui LLM gratuit de la [OpenRouter.ai](https://openrouter.ai).

## 🔧 Ce ai nevoie

- Python 3.10+
- Un bot token de la @BotFather
- Un API key de la OpenRouter.ai

## 🛠️ Setup rapid

1. Instalează dependențele:
```bash
pip install -r requirements.txt
```

2. Creează un fișier `.env`:
```
TELEGRAM_BOT_TOKEN=xxx
OPENROUTER_API_KEY=xxx
MODEL=meta-llama/llama-3-8b-instruct
```

3. Rulează botul:
```bash
python bot.py
```

## 🚀 Deploy

Poți hosta pe [Render.com](https://render.com) sau orice alt serviciu care suportă Python.

---

Fă-l cum vrei, adaptează-l, și distrează-te cu AI 🤖✨
