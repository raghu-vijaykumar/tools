import os
import re
import tempfile
from .llm import generate_audio_chunk
from .config import AUDIO_SPEED, DATA_DIR


def clean_text_for_audio(text):
    """Clean text to make it suitable for audio generation."""
    # Remove markdown links but keep the text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Remove markdown headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove markdown bold/italic
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"_(.*?)_", r"\1", text)
    # Remove code blocks
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Clean up extra whitespace
    text = re.sub(r"\n\n+", "\n\n", text)
    text = text.strip()
    return text


def generate_audio(text, filename):
    """Generate audio from text and save to file."""
    # Split into chunks of ~5000 characters (roughly 500-1000 words)
    max_chunk_length = 5000
    words = text.split()
    chunks = []
    current_chunk = []

    for word in words:
        if len(" ".join(current_chunk)) + len(word) < max_chunk_length:
            current_chunk.append(word)
        else:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    audio_files = []
    for i, chunk in enumerate(chunks):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            generate_audio_chunk(chunk, temp_file.name)
            audio_files.append(temp_file.name)

    # Combine all audio files
    from pydub import AudioSegment

    combined = AudioSegment.empty()
    for audio_file in audio_files:
        segment = AudioSegment.from_mp3(audio_file)
        combined += segment

    # Export the combined audio
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    combined.export(filename, format="mp3")

    # Clean up temporary files
    for audio_file in audio_files:
        os.unlink(audio_file)


def generate_summaries_audio(date_str):
    """Generate audio for the summaries of the given date."""
    summaries_file = os.path.join(DATA_DIR, date_str, "summaries.json")
    if not os.path.exists(summaries_file):
        raise FileNotFoundError(f"Summaries file not found: {summaries_file}")

    import json

    with open(summaries_file, "r") as f:
        summaries = json.load(f)

    text = f"Daily Tech Newsletter Digest Audio for {date_str}\n\n"
    for summary in summaries:
        if isinstance(summary, dict):
            summary_text = summary.get("summary", "")
        else:
            summary_text = str(summary)
        text += summary_text + "\n\n"

    audio_filename = os.path.join(DATA_DIR, "audio", "summaries", f"{date_str}.mp3")
    generate_audio(text, audio_filename)


def generate_article_audio(date_str, title, link):
    """Generate audio for a specific article."""
    articles_file = os.path.join(DATA_DIR, "articles", f"{date_str}.md")
    if not os.path.exists(articles_file):
        raise FileNotFoundError(f"Articles file not found: {articles_file}")

    with open(articles_file, "r") as f:
        content = f.read()

    # Find the article section
    article_marker = f"## [{title}]({link})"
    start_idx = content.find(article_marker)
    if start_idx == -1:
        raise ValueError(f"Article not found in file: {title}")

    # Find the next article or end
    next_marker = "\n## ["
    end_idx = content.find(next_marker, start_idx + len(article_marker))
    if end_idx == -1:
        end_idx = len(content)
    article_content = content[start_idx:end_idx]

    text = clean_text_for_audio(article_content)
    audio_filename = os.path.join(
        DATA_DIR,
        "audio",
        "articles",
        f"{date_str}_{title.replace('/', '_').replace(' ', '_')}.mp3",
    )
    generate_audio(text, audio_filename)
