import os
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from gtts import gTTS
from pydub import AudioSegment
from tenacity import retry, stop_after_attempt, wait_fixed
from .config import (
    get_google_api_key,
    get_groq_api_key,
    AUDIO_LANG,
    AUDIO_SPEED,
    RATE_LIMIT_RPM,
    TTS_RATE_LIMIT_RPM,
    last_llm_call,
    GROQ_MODEL,
    GEMINI_MODEL,
)

# Rate limiting
wait_time = 60 / RATE_LIMIT_RPM
tts_wait_time = 60 / TTS_RATE_LIMIT_RPM

# Singleton GTTS rate limiting
last_tts_call = 0


def get_llm(provider="gemini"):
    """Get LLM instance for the specified provider."""
    if provider == "groq":
        return ChatGroq(
            model=GROQ_MODEL, api_key=get_groq_api_key(), max_retries=0, timeout=30
        )
    elif provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=get_google_api_key(),
            max_retries=0,
            timeout=30,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(wait_time),
)
def summarize_article(article, provider="gemini"):
    """Summarize a single article."""
    global last_llm_call
    current_time = time.time()
    time_since_last = current_time - last_llm_call
    if time_since_last < wait_time:
        time.sleep(wait_time - time_since_last)

    llm = get_llm(provider)
    from langchain_core.prompts import PromptTemplate

    # Get content
    content = ""
    content_path = article.get("content_path")
    if content_path and os.path.exists(content_path):
        with open(content_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = article.get("summary", "")

    prompt = PromptTemplate.from_template(
        "Provide a deeper summary of the following article in 3-5 sentences, addressing key questions like what the article is about, why it matters, and how it works or what it achieves:\n\nTitle: {title}\n\nContent: {content}\n\nSummary:"
    )
    chain = prompt | llm
    response = chain.invoke(
        {
            "title": article["title"],
            "content": content,
        }
    )
    last_llm_call = time.time()
    return response.content.strip()


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
