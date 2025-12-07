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
                # Gemini doesn't support max_retries parameter in the same way
                self._instances[provider] = ChatGoogleGenerativeAI(
                    model=GEMINI_MODEL,
                    google_api_key=get_google_api_key(),
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
def classify_and_summarize_article(article, provider="gemini"):
    """Classify if an article is software engineering related and summarize if it is."""
    global last_llm_call
    current_time = time.time()
    time_since_last = current_time - last_llm_call
    if time_since_last < wait_time:
        time.sleep(wait_time - time_since_last)

    try:
        llm = get_llm(provider)
        from langchain_core.prompts import PromptTemplate

        # Get content
        content = ""
        content_path = article.get("content_path")
        if content_path and os.path.exists(content_path):
            with open(content_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = article.get("content", article.get("summary", ""))

        # Log request details for debugging
        print(f"LLM Request - Provider: {provider}, Title: {article['title'][:50]}..., Content length: {len(content)}")

        # Truncate content if too long (Gemini has token limits)
        if len(content) > 10000:  # Conservative limit
            content = content[:10000] + "..."
            print(f"Content truncated to 10000 chars for API limits")

        prompt = PromptTemplate.from_template(
            "First, determine if the following article is primarily about software engineering, AI, DevOps, security, or networking. Technical topics include: system design, architecture, programming, algorithms, data structures, development tools, frameworks, databases, APIs, DevOps, cloud infrastructure, AI/ML, cybersecurity, network architecture, and technical implementation details.\n\nTitle: {title}\n\nContent: {content}\n\nIf it's NOT related to these technical areas (e.g., business, product, HR, marketing, research papers, etc.), respond with only: SKIP\n\nIf it IS related, provide a response in the following format:\n\nCATEGORIES: [list 2-4 relevant categories/tags, separated by commas]\n\nSUMMARY: [provide a deeper summary in 3-5 sentences addressing key questions like what the article is about, why it matters, and how it works or what it achieves]"
        )
        chain = prompt | llm

        print(f"Sending request to {provider} API...")
        response = chain.invoke(
            {
                "title": article["title"],
                "content": content,
            }
        )
        last_llm_call = time.time()
        result = response.content.strip()

        print(f"LLM Response received, length: {len(result)}")

        if result.upper() == "SKIP":
            print("Article classified as non-technical, skipping")
            return None  # Not tech-related

        # Parse the response to extract categories and summary
        try:
            if "CATEGORIES:" in result and "SUMMARY:" in result:
                categories_part = result.split("CATEGORIES:")[1].split("SUMMARY:")[0].strip()
                summary_part = result.split("SUMMARY:")[1].strip()

                # Clean up categories (remove brackets if present and split by comma)
                categories = [cat.strip().strip('[]') for cat in categories_part.split(',') if cat.strip()]

                print(f"Successfully parsed categories: {categories}")
                return {
                    "summary": summary_part,
                    "categories": categories
                }
            else:
                # Fallback: treat the entire response as summary with empty categories
                print("Response format unexpected, using fallback parsing")
                return {
                    "summary": result,
                    "categories": []
                }
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            # If parsing fails, return the entire result as summary
            return {
                "summary": result,
                "categories": []
            }

    except Exception as e:
        print(f"LLM API Error for article '{article.get('title', 'Unknown')}': {type(e).__name__}: {e}")

        # Check for specific API errors
        if "ResourceExhausted" in str(e):
            print("ERROR: API quota exceeded or rate limited. Check your API key quota and billing.")
            print("Try switching to a different provider: --provider groq or --provider openai")
        elif "InvalidArgument" in str(e):
            print("ERROR: Invalid request. Content might be too long or malformed.")
        elif "PermissionDenied" in str(e):
            print("ERROR: API key invalid or insufficient permissions.")
        elif "NotFound" in str(e):
            print("ERROR: Model not found. Check model configuration.")

        # Re-raise to trigger retry logic
        raise


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
        # Check for content field first, then fall back to summary
        content = article.get("content", article.get("summary", ""))

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
