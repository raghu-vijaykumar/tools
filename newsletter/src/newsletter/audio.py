import os
import re
import tempfile
from pydub import AudioSegment
from .clients import generate_audio_chunk
from .config import DATA_DIR

# gTTS text limit
TEXT_CHUNK_SIZE = 4000


def clean_text_for_audio(text):
    """Clean text for audio generation: remove markdown formatting and links."""
    # Remove markdown bold: **text** -> text
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    # Remove markdown italics: *text* -> text
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    # Remove markdown links: [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove any remaining * or ** that might be standalone
    text = re.sub(r"\*+", "", text)
    # Clean up extra whitespace
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()


def generate_audio(text, filename):
    """Generate audio from text and save to file, handling long text by chunking."""
    if os.path.exists(filename):
        print(f"Audio already exists: {filename}")
        return

    # Split text into chunks
    chunks = [
        text[i : i + TEXT_CHUNK_SIZE] for i in range(0, len(text), TEXT_CHUNK_SIZE)
    ]

    if len(chunks) == 1:
        # Single chunk
        print(f"processing chunk 1/1 using gtts")
        generate_audio_chunk(chunks[0], filename)
    else:
        # Multiple chunks, concatenate
        combined = AudioSegment.empty()
        for i, chunk in enumerate(chunks, 1):
            print(f"Processing audio chunk {i}/{len(chunks)} using gtts")
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_filename = temp_file.name
            generate_audio_chunk(chunk, temp_filename)
            audio_segment = AudioSegment.from_mp3(temp_filename)
            combined += audio_segment
            os.unlink(temp_filename)  # Clean up temp file
        combined.export(filename, format="mp3")

    print(f"Audio saved: {filename}")


def generate_summaries_audio(date_str):
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

    generate_audio(clean_text, audio_file)


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
    generate_audio(clean_text, audio_file)
    return audio_file
