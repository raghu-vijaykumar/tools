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
    limit_website=None,
):
    """Fetch new articles from RSS feeds and scraping sources, then process unsummarized articles sequentially."""
    logging.info("Starting newsletter processing...")

    # Fetch new articles from RSS feeds and scraping sources
    new_articles_count = len(fetch_new_articles(limit_website=limit_website))
    if limit_website:
        logging.info(f"Fetched {new_articles_count} new articles (limited to {limit_website}).")
    else:
        logging.info(f"Fetched {new_articles_count} new articles from all sources.")

    # Get all unsummarized articles (including newly fetched ones)
    from .db import get_unsummarized_articles

    articles_to_process = get_unsummarized_articles()
    logging.info(f"Found {len(articles_to_process)} unsummarized articles to process.")

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
        result = process_article(article, provider)
        if not result:
            logging.error(f"Failed to process article: {article['title']}")
            continue

        # Extract summary data (result is now a dict with summary, categories, full_summary)
        if isinstance(result, dict):
            summary_text = result.get("full_summary", result.get("summary", ""))
            categories = result.get("categories", [])
        else:
            # Backward compatibility for string returns
            summary_text = result
            categories = []

        # Generate audio if not skipping
        if not no_audio:
            try:
                generate_summary_audio(article["id"], summary_text, tts)
                update_article_status(article["id"], "audio_generated")
                log_processing_action(article["id"], "audio_generated")
                logging.info(f"Generated audio for: {article['title']}")
            except Exception as e:
                logging.error(f"Failed to generate audio for {article['title']}: {e}")

        # Send summary via Telegram
        try:
            send_summary_sync(article, summary_text, no_audio=no_audio)
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
                    summary_text,
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


def force_send_existing(limit=None, no_audio=False):
    """Force send all summarized articles to Telegram."""
    logging.info("Starting force send of existing summarized articles...")

    from .db import get_summarized_articles

    articles_to_send = get_summarized_articles(limit=limit)
    logging.info(f"Found {len(articles_to_send)} summarized articles to send.")

    if not articles_to_send:
        logging.info("No summarized articles found to send.")
        return

    # Send each summarized article to Telegram
    sent_count = 0
    for article in articles_to_send:
        try:
            logging.info(f"Sending article {sent_count + 1}/{len(articles_to_send)}: {article['title']}")

            # Send summary via Telegram
            send_summary_sync(article, article["summary"], no_audio=no_audio)
            update_article_status(article["id"], "telegram_sent")
            log_processing_action(article["id"], "telegram_sent")
            logging.info(f"Force sent Telegram message for: {article['title']}")

            sent_count += 1

        except Exception as e:
            logging.error(f"Failed to force send Telegram for {article['title']}: {e}")

    logging.info(f"Force send completed. Sent {sent_count} articles to Telegram.")


@click.group()
def cli():
    """Newsletter automation CLI."""
    pass


@cli.command()
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
@click.option("--limit-website", help="Limit fetching to specific website (e.g., 'uber' for scraping, or 'github' for RSS)")
def run(provider, tts, no_audio, no_linkedin, limit_website):
    """Run the full newsletter processing pipeline."""
    run_newsletter(
        provider=provider, tts=tts, no_audio=no_audio, no_linkedin=no_linkedin, limit_website=limit_website
    )


@cli.command()
@click.option("--limit", type=int, help="Limit number of articles to send (default: all)")
@click.option("--no-audio", is_flag=True, help="Skip audio in Telegram messages")
def send_existing(limit, no_audio):
    """Force send all summarized articles to Telegram."""
    force_send_existing(limit=limit, no_audio=no_audio)


if __name__ == "__main__":
    cli()
