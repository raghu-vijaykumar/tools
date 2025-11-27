import click
import sys
import os
import shutil
import logging
from datetime import datetime, timedelta

# Add src to path for direct execution
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from newsletter.fetcher import fetch_new_articles
from newsletter.summarizer import process_article, generate_linkedin_post_for_summary
from .audio import generate_summary_audio
from .telegram import send_summary_sync
from common.telegram import send_linkedin_post_content_sync
from .db import get_unsummarized_articles, log_processing_action, update_article_status


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
    provider="gemini",
    tts="gtts",
    no_audio=False,
    no_linkedin=False,
):
    """Fetch new articles from RSS feeds and process unsummarized articles sequentially."""
    logging.info("Starting newsletter processing...")

    # Fetch new articles from RSS feeds
    new_articles_count = len(fetch_new_articles())
    logging.info(f"Fetched {new_articles_count} new articles from RSS feeds.")

    # Get all unsummarized articles (including newly fetched ones)
    from .db import get_unsummarized_articles

    articles_to_process = get_unsummarized_articles()
    logging.info(f"Found {len(articles_to_process)} articles to process.")

    if not articles_to_process:
        logging.info("No articles to process. All caught up!")
        return

    # Process each unsummarized article sequentially
    processed_count = 0
    for article in articles_to_process:
        logging.info(
            f"Processing article {processed_count + 1}/{len(articles_to_process)}: {article['title']}"
        )

        # Process article: fetch content and generate summary
        summary = process_article(article, provider)
        if not summary:
            logging.error(f"Failed to process article: {article['title']}")
            continue

        # Generate audio if not skipping
        if not no_audio:
            try:
                generate_summary_audio(article["id"], summary, tts)
                update_article_status(article["id"], "audio_generated")
                log_processing_action(article["id"], "audio_generated")
                logging.info(f"Generated audio for: {article['title']}")
            except Exception as e:
                logging.error(f"Failed to generate audio for {article['title']}: {e}")

        # Send summary via Telegram
        try:
            send_summary_sync(article, summary, no_audio=no_audio)
            update_article_status(article["id"], "telegram_sent")
            log_processing_action(article["id"], "telegram_sent")
            logging.info(f"Sent Telegram message for: {article['title']}")
        except Exception as e:
            logging.error(f"Failed to send Telegram for {article['title']}: {e}")

        # Generate and send LinkedIn post if not skipping
        if not no_linkedin:
            try:
                linkedin_post = generate_linkedin_post_for_summary(
                    article["title"],
                    summary,
                    article["link"],
                    article.get("published", "")[:10],  # date string
                    provider,
                )
                send_linkedin_post_content_sync(article["title"], linkedin_post)
                update_article_status(article["id"], "linkedin_posted")
                log_processing_action(article["id"], "linkedin_posted")
                logging.info(f"Posted to LinkedIn for: {article['title']}")
            except Exception as e:
                logging.error(f"Failed to post LinkedIn for {article['title']}: {e}")
        else:
            logging.info("Skipped LinkedIn posting.")

        processed_count += 1
        logging.info(f"Completed processing article: {article['title']}")

    logging.info(
        f"Newsletter processing completed. Processed {processed_count} articles."
    )


@click.command()
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
@click.option("--no-audio", is_flag=True, help="Skip audio generation")
@click.option("--no-linkedin", is_flag=True, help="Skip LinkedIn posting")
def main(provider, tts, no_audio, no_linkedin):
    run_newsletter(
        provider=provider, tts=tts, no_audio=no_audio, no_linkedin=no_linkedin
    )


if __name__ == "__main__":
    main()
