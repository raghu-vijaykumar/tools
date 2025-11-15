"""
Embedding utilities for the AI tools.
Supports multiple embedding providers including local and cloud options.
"""

from typing import List, Optional
import os

from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Local embeddings
try:
    from langchain_community.embeddings import HuggingFaceEmbeddings

    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from .config import get_openai_api_key, get_google_api_key


def get_embeddings(provider: str = "openai", model: Optional[str] = None):
    """
    Get embeddings instance for the specified provider and model.

    Args:
        provider: 'openai', 'gemini', 'huggingface', 'sentence-transformers'
        model: Specific model name (optional, uses defaults if not provided)
    """
    if provider == "openai":
        model_name = model or "text-embedding-3-small"
        return OpenAIEmbeddings(
            model=model_name, api_key=get_openai_api_key(), max_retries=3, timeout=30
        )

    elif provider == "gemini":
        model_name = model or "models/embedding-001"
        return GoogleGenerativeAIEmbeddings(
            model=model_name, google_api_key=get_google_api_key()
        )

    elif provider == "huggingface":
        if not HUGGINGFACE_AVAILABLE:
            raise ImportError(
                "langchain-community not installed. Run: pip install langchain-community"
            )

        model_name = model or "sentence-transformers/all-MiniLM-L6-v2"
        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

    elif provider == "sentence-transformers":
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers not installed. Run: pip install sentence-transformers"
            )

        model_name = model or "all-MiniLM-L6-v2"

        class SentenceTransformersEmbeddings:
            """Custom wrapper for sentence-transformers to match LangChain interface."""

            def __init__(self, model_name: str):
                self.model = SentenceTransformer(model_name)

            def embed_documents(self, texts: List[str]) -> List[List[float]]:
                """Embed a list of documents."""
                return self.model.encode(texts, convert_to_numpy=False).tolist()

            def embed_query(self, text: str) -> List[float]:
                """Embed a single query."""
                return self.model.encode(text, convert_to_numpy=False).tolist()

        return SentenceTransformersEmbeddings(model_name)

    else:
        available_providers = ["openai", "gemini"]
        if HUGGINGFACE_AVAILABLE:
            available_providers.append("huggingface")
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            available_providers.append("sentence-transformers")

        raise ValueError(
            f"Unsupported embedding provider: {provider}. "
            f"Available: {', '.join(available_providers)}"
        )


def get_available_providers():
    """Get list of available embedding providers."""
    providers = ["openai", "gemini"]

    if HUGGINGFACE_AVAILABLE:
        providers.append("huggingface")
    if SENTENCE_TRANSFORMERS_AVAILABLE:
        providers.append("sentence-transformers")

    return providers


def get_default_models():
    """Get default model names for each provider."""
    return {
        "openai": "text-embedding-3-small",
        "gemini": "models/embedding-001",
        "huggingface": "sentence-transformers/all-MiniLM-L6-v2",
        "sentence-transformers": "all-MiniLM-L6-v2",
    }
