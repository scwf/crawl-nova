"""LLM client for video_scribe."""

import os
from typing import Any, List, Optional
from urllib.parse import urlparse, urlunparse

from openai import OpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from .utils import setup_logger

logger = setup_logger("llm_client")

def normalize_base_url(base_url: str) -> str:
    """Normalize API base URL by ensuring /v1 suffix when needed."""
    url = base_url.strip()
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")

    if not path:
        path = "/v1"

    normalized = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )

    return normalized

_client = None

def get_llm_client(api_key: Optional[str] = None, base_url: Optional[str] = None) -> OpenAI:
    """Get OpenAI client instance.
    
    Args:
        api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var.
        base_url: OpenAI Base URL. If None, reads from OPENAI_BASE_URL env var.
    """
    global _client
    
    # Allow re-initialization if keys are provided
    if api_key or base_url or _client is None:
        final_api_key = api_key or os.getenv("OPENAI_API_KEY", "").strip()
        final_base_url = base_url or os.getenv("OPENAI_BASE_URL", "").strip()
        
        if final_base_url:
            final_base_url = normalize_base_url(final_base_url)

        if not final_api_key:
             # Even if no key is found, we might want to return a client if it works without one (e.g. local LLMs), 
             # but standard OpenAI requires it. We'll warn but proceed.
             logger.warning("OPENAI_API_KEY is not set.")

        _client = OpenAI(
            base_url=final_base_url if final_base_url else None,
            api_key=final_api_key,
        )

    return _client

@retry(
    stop=stop_after_attempt(5),
    wait=wait_random_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(Exception), # Broad retry for network/API issues, can be refined
    reraise=True
)
def call_llm(
    messages: List[dict],
    model: str,
    temperature: float = 0.2,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    """Call LLM API with retry logic."""
    client = get_llm_client(api_key, base_url)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            **kwargs,
        )
        return response
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise
