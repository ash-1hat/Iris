"""
LLM client wrapper for Anthropic Claude API
Handles API initialization, error handling, and retries
"""

import os
from typing import Optional
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Global client instance
_llm_client: Optional[Anthropic] = None


def get_llm_client() -> Anthropic:
    """
    Get or create Anthropic client instance
    Singleton pattern to reuse client

    Returns:
        Anthropic client instance

    Raises:
        ValueError: If ANTHROPIC_API_KEY not set in environment
    """
    global _llm_client

    if _llm_client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment variables. "
                "Please set it in .env file or environment."
            )

        _llm_client = Anthropic(api_key=api_key)

    return _llm_client


def call_llm_with_retry(
    prompt: str,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 2000,
    temperature: float = 0.3,
    max_retries: int = 2
) -> str:
    """
    Call Claude API with automatic retry on failure

    Args:
        prompt: The prompt text
        model: Claude model to use
        max_tokens: Maximum tokens in response
        temperature: Temperature for response generation (0.0-1.0)
        max_retries: Maximum number of retry attempts

    Returns:
        Response text from Claude

    Raises:
        Exception: If all retries fail
    """
    client = get_llm_client()

    last_error = None

    for attempt in range(max_retries):
        try:
            message = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )

            return message.content[0].text

        except Exception as e:
            last_error = e

            # If this was the last attempt, raise the error
            if attempt == max_retries - 1:
                break

            # Otherwise, continue to next attempt
            continue

    # If we got here, all retries failed
    raise Exception(f"LLM call failed after {max_retries} attempts: {str(last_error)}")


def estimate_tokens(text: str) -> int:
    """
    Rough estimate of token count
    Claude uses ~3-4 characters per token on average

    Args:
        text: Text to estimate

    Returns:
        Estimated token count
    """
    return len(text) // 4


def validate_api_key() -> bool:
    """
    Validate that API key is set and client can be created

    Returns:
        True if API key is valid and client can be created
    """
    try:
        client = get_llm_client()
        return True
    except ValueError:
        return False
