import os
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_fixed
from .config import (
    get_google_api_key,
    get_groq_api_key,
    get_openai_api_key,
    RATE_LIMIT_RPM,
    last_llm_call,
    GROQ_MODEL,
    GEMINI_MODEL,
    OPENAI_MODEL,
)


class LLMClient:
    """Singleton LLM client"""

    _instance = None
    _instances = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_llm(self, provider="gemini"):
        """Get cached LLM instance for the specified provider."""
        if provider not in self._instances:
            if provider == "groq":
                self._instances[provider] = ChatGroq(
                    model=GROQ_MODEL,
                    api_key=get_groq_api_key(),
                    max_retries=0,
                    timeout=30,
                )
            elif provider == "gemini":
                self._instances[provider] = ChatGoogleGenerativeAI(
                    model=GEMINI_MODEL,
                    google_api_key=get_google_api_key(),
                    max_retries=0,
                    timeout=30,
                )
            elif provider == "openai":
                self._instances[provider] = ChatOpenAI(
                    model=OPENAI_MODEL,
                    openai_api_key=get_openai_api_key(),
                    max_retries=0,
                    timeout=30,
                )
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")

        return self._instances[provider]


# Global instance
llm_client = LLMClient()

# Rate limiting
wait_time = 60 / RATE_LIMIT_RPM


def get_llm(provider="gemini"):
    """Get LLM instance for the specified provider."""
    return llm_client.get_llm(provider)


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
