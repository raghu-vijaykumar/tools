import click
import sys
import os
import shutil
from datetime import datetime, timedelta

# Add src to path for direct execution
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from newsletter.fetcher import fetch_articles
from newsletter.summarizer import (
    summarize_articles_for_date,
    generate_combined_articles_markdown,
)
from .audio import generate_summaries_audio
from common.telegram import send_summaries_sync
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
                print(f"Failed to delete {file_path}. Reason: {e}")


def run_newsletter(days=1, provider="gemini", tts="gtts", cleanup=True):
    """Fetch, summarize, and generate audio for daily tech newsletters."""
    print(f"Processing last {days} days...")

    # Fetch articles
    articles_by_date = fetch_articles(days)
    print(f"Fetched articles for {len(articles_by_date)} dates.")

    # Process each date
    for date_str in sorted(articles_by_date.keys()):
        print(f"Processing {date_str}...")

        # Summarize and generate markdown articles
        summaries = summarize_articles_for_date(date_str, provider)
        print(f"Summarized {len(summaries)} articles and generated markdown articles.")

        # Generate combined articles markdown
        generate_combined_articles_markdown(date_str)

        if summaries:
            # Generate combined summaries audio
            generate_summaries_audio(date_str, tts)
            print("Generated summaries audio.")

            # Send summaries via Telegram
            send_summaries_sync(date_str)
            print("Sent summaries via Telegram.")

    # Clean up data directory if requested
    if cleanup:
        cleanup_data_directory()
        print("Cleaned up data directory.")
    else:
        print("Skipped data directory cleanup.")

    print("Done!")


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
def main(days, provider, tts, cleanup):
    run_newsletter(days, provider, tts, cleanup)


if __name__ == "__main__":
    main()
