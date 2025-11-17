import os
from common.audio import generate_audio as common_generate_audio, clean_text_for_audio
from .config import DATA_DIR


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
