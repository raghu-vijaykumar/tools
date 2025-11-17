import os
import re
import tempfile
import time
import torch
from gtts import gTTS
from transformers import pipeline
from pydub import AudioSegment
import numpy as np
import soundfile as sf
from tenacity import retry, stop_after_attempt, wait_fixed
from .config import AUDIO_SPEED, DATA_DIR, AUDIO_LANG, TTS_RATE_LIMIT_RPM

# Text chunk size for TTS processing
TEXT_CHUNK_SIZE = 400


# Singleton GTTS rate limiting
last_tts_call = 0

# Rate limiting
tts_wait_time = 60 / TTS_RATE_LIMIT_RPM


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(tts_wait_time),
)
def generate_audio_chunk(text_chunk, temp_file):
    """Generate audio for a text chunk."""
    global last_tts_call
    current_time = time.time()
    time_since_last = current_time - last_tts_call
    if time_since_last < tts_wait_time:
        time.sleep(tts_wait_time - time_since_last)
    tts = gTTS(text=text_chunk, lang=AUDIO_LANG, slow=False)
    tts.save(temp_file)

    # Apply speed adjustment if needed
    if AUDIO_SPEED != 1.0:
        audio = AudioSegment.from_mp3(temp_file)
        # Speed up the audio (higher speed = shorter duration)
        sped_up_audio = audio.speedup(playback_speed=AUDIO_SPEED)
        sped_up_audio.export(temp_file, format="mp3")

    last_tts_call = time.time()


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


def generate_audio(text, filename, tts_provider="gtts"):
    """Generate audio from text using the specified TTS model or provider."""
    if os.path.exists(filename):
        print(f"Audio already exists: {filename}")
        return

    if tts_provider == "gtts":
        print("Using TTS provider: gTTS (Google Text-to-Speech API)")
        # Split into chunks of ~5000 characters (roughly 500-1000 words) for API calls
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

    else:
        print(f"Using TTS model: {tts_provider}")
        # Hugging Face TTS model (local models)
        # Split text into chunks at word boundaries
        chunks = []
        start = 0
        while start < len(text):
            end = start + TEXT_CHUNK_SIZE
            if end >= len(text):
                chunks.append(text[start:])
                break
            # Find the nearest space after or before end
            if text[end] == " ":
                chunks.append(text[start:end])
                start = end
            else:
                space_before = text.rfind(" ", start, end)
                if space_before != -1:
                    chunks.append(text[start:space_before])
                    start = space_before + 1  # Skip space
                else:
                    # No space found, find next space after
                    space_after = text.find(" ", end, end + 50)
                    if space_after != -1:
                        chunks.append(text[start:space_after])
                        start = space_after + 1
                    else:
                        # Force cut
                        chunks.append(text[start:end])
                        start = end

        # Set device
        device = "cuda" if torch.cuda.is_available() else "cpu"

        # Initialize pipeline
        try:
            synthesizer = pipeline("text-to-speech", tts_provider, device=device)
            print(f"Using TTS model: {tts_provider} on device: {device}")
        except Exception as e:
            print(f"Error loading TTS model '{tts_provider}': {e}")
            return

        # Use a default speaker embedding (zeros) - adjust size if needed for different models
        speaker_embedding = torch.zeros(1, 512, dtype=torch.float32)

        # Generate audio for each chunk
        audio_arrays = []
        sample_rates = []

        for i, chunk in enumerate(chunks, 1):
            if not chunk.strip():
                continue
            try:
                print(f"Processing TTS chunk {i}/{len(chunks)} ({len(chunk)} chars)")
                speech = synthesizer(
                    chunk, forward_params={"speaker_embeddings": speaker_embedding}
                )
                audio_arrays.append(np.array(speech["audio"]))
                sample_rates.append(speech["sampling_rate"])
            except Exception as e:
                print(f"Error generating audio for chunk {i}: {e}")
                continue

        if not audio_arrays:
            print("Error: No audio generated.")
            return

        # All chunks should have same sample rate
        target_rate = sample_rates[0] if sample_rates else 16000

        # Concatenate all audio chunks
        concatenated = np.concatenate(audio_arrays, axis=0)
        audio_data = concatenated.squeeze()
        sampling_rate = target_rate

        # Save audio
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".wav":
            sf.write(filename, audio_data, sampling_rate)
        else:
            # Default to mp3 via pydub
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            temp_wav = filename.rsplit(".", 1)[0] + "_temp.wav"
            sf.write(temp_wav, audio_data, sampling_rate)
            audio = AudioSegment.from_wav(temp_wav)
            audio.export(filename, format="mp3")
            os.remove(temp_wav)
