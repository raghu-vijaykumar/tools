import asyncio
import logging
from telegram import Bot
from telegram.constants import ParseMode
from .config import get_telegram_bot_token, get_telegram_chat_id

logger = logging.getLogger(__name__)


async def _send_message_with_fallback(bot, chat_id, text, parse_mode):
    """Send a message with fallback to plain text if parsing fails."""
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
    except Exception as e:
        logger.warning(f"Failed to send with parse_mode {parse_mode}: {e}")
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)


async def _send_text_in_chunks(bot, chat_id, text, max_length):
    """Send long text in chunks to avoid Telegram message length limit."""
    chunks = [text[i : i + max_length] for i in range(0, len(text), max_length)]
    for chunk in chunks:
        await bot.send_message(chat_id=chat_id, text=chunk, parse_mode=ParseMode.HTML)


async def send_digest_via_telegram(date_str):
    """Send the digest for the given date via Telegram."""
    bot_token = get_telegram_bot_token()
    chat_id = get_telegram_chat_id()
    bot = Bot(token=bot_token)

    digest_path = f"data/digests/{date_str}.md"
    try:
        with open(digest_path, "r", encoding="utf-8") as f:
            digest_content = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Digest file not found: {digest_path}")

    await _send_message_with_fallback(
        bot,
        chat_id,
        f"*Daily Tech Newsletter Digest - {date_str}*\n\n",
        ParseMode.MARKDOWN,
    )
    await _send_text_in_chunks(bot, chat_id, digest_content, 4096)


async def send_articles_via_telegram(date_str):
    """Send articles markdown for the given date via Telegram."""
    bot_token = get_telegram_bot_token()
    chat_id = get_telegram_chat_id()
    bot = Bot(token=bot_token)

    articles_path = f"data/articles/{date_str}.md"
    try:
        with open(articles_path, "r", encoding="utf-8") as f:
            articles_content = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Articles file not found: {articles_path}")

    await _send_message_with_fallback(
        bot, chat_id, f"*Daily Tech Articles - {date_str}*\n\n", ParseMode.MARKDOWN
    )
    await _send_text_in_chunks(bot, chat_id, articles_content, 4096)


def send_articles_sync(date_str):
    """Synchronous wrapper for sending articles."""
    asyncio.run(send_articles_via_telegram(date_str))


async def send_summaries_via_telegram(date_str):
    """Send article summaries with links via Telegram."""
    import json
    import os

    bot_token = get_telegram_bot_token()
    chat_id = get_telegram_chat_id()
    bot = Bot(token=bot_token)

    # Load summaries
    summaries_path = f"data/{date_str}/summaries.json"
    try:
        with open(summaries_path, "r", encoding="utf-8") as f:
            summaries = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Summaries file not found: {summaries_path}")

    # Check for audio file
    audio_path = f"data/{date_str}/summaries.mp3"
    audio_exists = os.path.exists(audio_path)

    # Send header
    await _send_message_with_fallback(
        bot, chat_id, f"*📰 Tech News Summary - {date_str}*\n\n", ParseMode.MARKDOWN
    )

    # Send each summary as a separate message
    for summary in summaries:
        title = summary["title"]
        link = summary["link"]
        summary_text = summary["summary"]

        # Send individual article summary
        message = f"*📌 {title}*\n\n{summary_text}\n\n🔗 {link}"

        # If message is too long for Telegram (4000 chars), truncate with ellipsis
        if len(message) > 3950:
            # Leave room for ellipsis and some buffer
            message = message[:3950] + "..."

        await _send_message_with_fallback(bot, chat_id, message, ParseMode.MARKDOWN)

    # Send footer with audio status
    if audio_exists:
        footer = "*🎧 Combined Audio Summary Available*"
    else:
        footer = "*❌ Audio summary not generated*"

    await _send_message_with_fallback(bot, chat_id, footer, ParseMode.MARKDOWN)

    # Send audio file if it exists
    if audio_exists:
        try:
            with open(audio_path, "rb") as audio_file:
                await bot.send_audio(
                    chat_id=chat_id,
                    audio=audio_file,
                    title=f"Tech News Audio Summary - {date_str}",
                    caption="🎵 Combined audio summary of today's tech news",
                )
                logger.info(f"Sent audio file for {date_str}")
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")


def send_summaries_sync(date_str):
    """Synchronous wrapper for sending summaries."""
    asyncio.run(send_summaries_via_telegram(date_str))


def send_digest_sync(date_str):
    """Synchronous wrapper for sending digest."""
    asyncio.run(send_digest_via_telegram(date_str))
