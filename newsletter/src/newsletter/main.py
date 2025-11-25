import click
import sys
import os
import shutil
import logging
from datetime import datetime, timedelta

# Add src to path for direct execution
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from newsletter.fetcher import fetch_articles
from newsletter.summarizer import (
    summarize_articles_for_date,
    generate_combined_articles_markdown,
    generate_linkedin_post_for_date,
)
from .audio import generate_summaries_audio
from common.telegram import send_summaries_sync, send_linkedin_post_sync
from common.config import get_date_str, get_days_ago


def cleanup_data_directory():
    """Clean up the data directory by removing all contents."""
    data_dir = "data"
    if os.path.exists(data_dir):
        for filename in os.listdir(data_dir):
            file_path = os.path.join(data_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logging.error(f"Failed to delete {file_path}. Reason: {e}")


def run_newsletter(
    days=1, dates_list=None, provider="gemini", tts="gtts", cleanup=True, no_audio=False
):
    """Fetch, summarize, and generate audio for daily tech newsletters."""
    if dates_list:
        logging.info(f"Processing specific dates: {dates_list}...")
        # Fetch articles for specific dates
        articles_by_date = {}
        for date_str in dates_list:
            articles_for_date = fetch_articles(None, target_dates=[date_str])
            articles_by_date.update(articles_for_date)
    else:
        logging.info(f"Processing last {days} days...")
        articles_by_date = fetch_articles(days)

    logging.info(f"Fetched articles for {len(articles_by_date)} dates.")

    # Process each date
    for date_str in sorted(articles_by_date.keys()):
        logging.info(f"Processing {date_str}...")

        # Summarize and generate markdown articles
        summaries = summarize_articles_for_date(date_str, provider)
        logging.info(
            f"Summarized {len(summaries)} articles and generated markdown articles."
        )

        # Generate combined articles markdown
        generate_combined_articles_markdown(date_str)

        # Generate LinkedIn post
        generate_linkedin_post_for_date(date_str, provider)

        if summaries:
            # Generate combined summaries audio if not skipping
            if not no_audio:
                generate_summaries_audio(date_str, tts)
                logging.info("Generated summaries audio.")

            # Send summaries via Telegram
            send_summaries_sync(date_str, no_audio=no_audio)
            logging.info("Sent summaries via Telegram.")

            # Send LinkedIn post via Telegram
            send_linkedin_post_sync(date_str)
            logging.info("Sent LinkedIn post via Telegram.")

    # Clean up data directory if requested
    if cleanup:
        cleanup_data_directory()
        logging.info("Cleaned up data directory.")
    else:
        logging.info("Skipped data directory cleanup.")

    logging.info("Newsletter processing completed successfully.")


@click.command()
@click.option("--days", default=1, help="Number of days to fetch (default: 1)")
@click.option(
    "--provider",
    default="gemini",
    type=click.Choice(["gemini", "groq", "openai"]),
    help="LLM provider to use (default: gemini)",
)
@click.option(
    "--tts",
    default="gtts",
    help="TTS model or provider to use (default: gtts, use 'microsoft/speecht5_tts' for local model)",
)
@click.option(
    "--cleanup/--no-cleanup",
    default=True,
    help="Clean up data directory after processing (default: cleanup)",
)
@click.option("--no-audio", is_flag=True, help="Skip audio generation")
def main(days, provider, tts, cleanup, no_audio):
    run_newsletter(days, provider, tts, cleanup, no_audio=no_audio)


if __name__ == "__main__":
    main()
