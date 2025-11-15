import os
import asyncio
import json
from telegram import Bot
from telegram.error import TelegramError
from .config import get_telegram_bot_token, get_telegram_chat_id, DATA_DIR


async def _send_message_with_fallback(bot, chat_id, text, parse_mode):
    """Send a message with markdown parsing, fallback to plain text if it fails."""
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
        )
    except TelegramError as e:
        if "BadRequest" in str(e) or "can't parse" in str(e).lower():
            # Fallback to plain text if markdown parsing fails
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=None,
            )
        else:
            raise


async def _send_text_in_chunks(bot, chat_id, text, max_length):
    """Split text into chunks and send each chunk, preferring paragraph breaks."""
    paragraphs = text.split("\n\n")
    current_chunk = ""

    for paragraph in paragraphs:
        # If adding this paragraph would exceed the limit, send current chunk
        if len(current_chunk) + len(paragraph) + 2 > max_length:  # +2 for \n\n
            if current_chunk:
                await _send_message_with_fallback(
                    bot, chat_id, current_chunk.strip(), "Markdown"
                )
                current_chunk = ""

        # Add paragraph to current chunk
        if current_chunk:
            current_chunk += "\n\n" + paragraph
        else:
            current_chunk = paragraph

    # Send remaining chunk
    if current_chunk:
        await _send_message_with_fallback(
            bot, chat_id, current_chunk.strip(), "Markdown"
        )


async def send_digest_via_telegram(date_str):
    """Send daily digest text and audio via Telegram."""
    try:
        bot_token = get_telegram_bot_token()
        chat_id = get_telegram_chat_id()

        # Check if credentials are set (not placeholder values)
        if (
            bot_token == "your_telegram_bot_token_here"
            or chat_id == "your_telegram_chat_id_here"
        ):
            print(
                f"Telegram credentials not configured. Skipping Telegram send for {date_str}"
            )
            print(
                "Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in your .env file"
            )
            return

        bot = Bot(token=bot_token)

        date_dir = os.path.join(DATA_DIR, date_str)
        digest_file = os.path.join(date_dir, "digest.txt")
        audio_file = os.path.join(date_dir, "digest.mp3")

        # Check if files exist
        if not os.path.exists(digest_file):
            print(f"No digest file found for {date_str}")
            return

        if not os.path.exists(audio_file):
            print(f"No audio file found for {date_str}")
            return

        # Read digest text with encoding fallback
        try:
            with open(digest_file, "r", encoding="utf-8") as f:
                digest_text = f.read()
        except UnicodeDecodeError:
            # Fallback to Windows-1252 encoding for files with Windows-specific characters
            with open(digest_file, "r", encoding="cp1252") as f:
                digest_text = f.read()

        # Send digest text as message, try Markdown first, fallback to None
        header = f"📅 Daily Tech Digest - {date_str}\n\n"
        full_text = header + digest_text

        # Split message if too long (Telegram limit is 4096 chars)
        max_length = 4000
        if len(full_text) > max_length:
            # Send header first
            await _send_message_with_fallback(bot, chat_id, header.strip(), "Markdown")

            # Split content into chunks, preferring paragraph breaks
            await _send_text_in_chunks(bot, chat_id, digest_text, max_length)
        else:
            await _send_message_with_fallback(bot, chat_id, full_text, "Markdown")

        # Send audio file as attachment
        with open(audio_file, "rb") as audio:
            await bot.send_audio(
                chat_id=chat_id,
                audio=audio,
                title=f"Tech Digest Audio - {date_str}",
                caption=f"🎧 Audio version of the {date_str} tech digest",
            )

        print(f"Successfully sent digest for {date_str} via Telegram")

    except TelegramError as e:
        print(f"Telegram error: {e}")
    except Exception as e:
        print(f"Error sending digest via Telegram: {e}")


async def send_articles_via_telegram(date_str):
    """Send individual article messages and combined summaries audio via Telegram."""
    try:
        bot_token = get_telegram_bot_token()
        chat_id = get_telegram_chat_id()

        # Check if credentials are set (not placeholder values)
        if (
            bot_token == "your_telegram_bot_token_here"
            or chat_id == "your_telegram_chat_id_here"
        ):
            print(
                f"Telegram credentials not configured. Skipping Telegram send for {date_str}"
            )
            print(
                "Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in your .env file"
            )
            return

        bot = Bot(token=bot_token)

        date_dir = os.path.join(DATA_DIR, date_str)
        summaries_file = os.path.join(date_dir, "summaries.json")
        audio_file = os.path.join(date_dir, "summaries.mp3")

        # Check if files exist
        if not os.path.exists(summaries_file):
            print(f"No summaries file found for {date_str}")
            return

        with open(summaries_file, "r") as f:
            summaries = json.load(f)

        if not summaries:
            print(f"No summaries to send for {date_str}")
            return

        # Send header message
        header = f"📰 Tech News Articles - {date_str}\n\nHere are today's articles:"
        await _send_message_with_fallback(bot, chat_id, header, "Markdown")

        # Send each article individually with throttling (10 msg/s = 100ms delay)
        for summary in summaries:
            message = f"**{summary['title']}**\n\n{summary['summary']}\n\n[Read more]({summary['link']})"
            await _send_message_with_fallback(bot, chat_id, message, "Markdown")
            await asyncio.sleep(0.1)  # 100ms delay for throttling

        # Send combined summaries audio at the end
        if os.path.exists(audio_file):
            with open(audio_file, "rb") as audio:
                await bot.send_audio(
                    chat_id=chat_id,
                    audio=audio,
                    title=f"Tech News Audio Summary - {date_str}",
                    caption=f"🎧 Combined audio summary of all {len(summaries)} articles for {date_str}",
                )
        else:
            print(f"No audio file found for {date_str}")

        print(
            f"Successfully sent {len(summaries)} articles and audio for {date_str} via Telegram"
        )

    except TelegramError as e:
        print(f"Telegram error: {e}")
    except Exception as e:
        print(f"Error sending articles via Telegram: {e}")


def send_articles_sync(date_str):
    """Synchronous wrapper for sending articles via Telegram."""
    asyncio.run(send_articles_via_telegram(date_str))


def send_digest_sync(date_str):
    """Synchronous wrapper for sending digest via Telegram."""
    import asyncio

    asyncio.run(send_digest_via_telegram(date_str))
