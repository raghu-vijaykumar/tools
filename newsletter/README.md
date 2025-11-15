# Newsletter Daily Digest

A Python CLI tool to fetch daily newsletters from tech blogs, summarize them using Gemini LLM, and generate audio digests.

## Features

- Fetches articles from RSS feeds of reputed tech blogs
- Summarizes articles using LangChain and Google Gemini
- Generates daily digests
- Creates audio versions using Google Text-to-Speech
- Sends digests via Telegram bot (text + audio attachment)
- Rate limiting for LLM calls
- Skips already processed data on reruns
- Configurable number of days to fetch

## Setup

1. Install uv if not already installed.
2. Clone or download the project.
3. Install dependencies: `uv sync`
4. Set up environment variables: Copy `.env.example` to `.env` and add your API keys.

### Telegram Bot Setup (Optional)

To receive digests via Telegram:

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow instructions to create your bot
3. Copy the bot token provided by BotFather
4. Message your bot to start a chat and get your chat ID
5. Add to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```

The bot will send digest text as a message and audio as an attachment.

## Usage

Run the CLI:

```bash
uv run python main.py --days 7
```

This will fetch articles from the last 7 days, summarize them, generate digests, and create audio files.

Data is stored in the `data/` directory, organized by date.

## Requirements

- Python 3.12+
- Google API key for Gemini
- Internet connection for fetching RSS and API calls
