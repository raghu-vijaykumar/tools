import os
from common.audio import generate_audio as common_generate_audio, clean_text_for_audio
from common.config import DATA_DIR
from .db import get_summary_by_article_id


def generate_summaries_audio(date_str, tts_provider="microsoft"):
    """Generate combined audio for all article summaries."""
    import json

    date_dir = os.path.join(DATA_DIR, date_str)
    summaries_file = os.path.join(date_dir, "summaries.json")
    audio_file = os.path.join(date_dir, "summaries.mp3")

    if not os.path.exists(summaries_file):
        print(f"No summaries found for {date_str}")
        return

    with open(summaries_file, "r") as f:
        summaries = json.load(f)

    if not summaries:
        print(f"No summaries to generate audio for {date_str}")
        return

    # Combine all summaries into one text
    combined_text = f"Tech News Summary for {date_str}\n\n"
    for summary in summaries:
        combined_text += f"Article: {summary['title']}\n"
        combined_text += f"Summary: {summary['summary']}\n\n"

    # Clean the text for plain audio
    clean_text = clean_text_for_audio(combined_text)

    common_generate_audio(clean_text, audio_file, tts_provider)


def generate_summary_audio(article_id, summary, tts_provider="gtts"):
    """Generate audio for a single article summary."""
    # Get summary from DB if not provided
    if not summary:
        summary_data = get_summary_by_article_id(article_id)
        if summary_data:
            summary = summary_data["summary"]
        else:
            print(f"No summary found for article {article_id}")
            return

    # Create audio text
    audio_text = f"Tech News Summary: {summary}"

    # Clean the text for audio
    clean_text = clean_text_for_audio(audio_text)

    # Create audio directory if needed
    audio_dir = os.path.join(DATA_DIR, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    # Generate filename
    audio_file = os.path.join(audio_dir, f"summary_{article_id}.mp3")

    # Generate audio
    common_generate_audio(clean_text, audio_file, tts_provider)
    print(f"Generated audio: {audio_file}")
    return audio_file


def generate_article_audio(date_str, title, link):
    """Generate audio for a specific article."""
    # For simplicity, assume we have the content; in reality, might need to scrape
    # Here, just use the title and link as text, or fetch content
    # Since RSS may not have full content, perhaps just TTS the title and summary
    # But for now, placeholder
    text = f"Article: {title}. Link: {link}"
    # Clean the text for plain audio
    clean_text = clean_text_for_audio(text)
    safe_title = "".join(
        c for c in title if c.isalnum() or c in (" ", "-", "_")
    ).rstrip()
    audio_file = os.path.join(DATA_DIR, date_str, f"{safe_title}.mp3")
    common_generate_audio(clean_text, audio_file)
    return audio_file
