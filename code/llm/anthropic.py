# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
Anthropic wrapper  

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.

"""

import os
import json
import re
import logging
import asyncio
from typing import Dict, Any, List

from anthropic import AsyncAnthropic
from config.config import CONFIG
import threading

logger = logging.getLogger(__name__)


class ConfigurationError(RuntimeError):
    """Raised when configuration is missing or invalid."""
    pass


def get_anthropic_api_key() -> str:
    """Retrieve the Anthropic API key from the environment or raise an error."""
    # Get the API key from the preferred provider config
    preferred_provider = CONFIG.preferred_provider
    provider_config = CONFIG.providers[preferred_provider]
    api_key_env_var = provider_config.api_key_env
    
    key = os.getenv(api_key_env_var)
    if not key:
        raise ConfigurationError(f"{api_key_env_var} is not set")
    return key

_client_lock = threading.Lock()
anthropic_client = None

def get_async_client() -> AsyncAnthropic:
    """
    Configure and return an async Anthropic client.
    """
    global anthropic_client
    with _client_lock:  # Thread-safe client initialization
        if anthropic_client is None:
            api_key = get_anthropic_api_key()
            anthropic_client = AsyncAnthropic(api_key=api_key)
    return anthropic_client


def _build_messages(prompt: str, schema: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Construct the message sequence for JSON-schema enforcement.
    """
    return [
        {
            "role": "assistant",
            "content": f"I'll provide a JSON response matching this schema: {json.dumps(schema)}"
        },
        {
            "role": "user",
            "content": prompt
        }
    ]


def clean_response(content: str) -> Dict[str, Any]:
    """
    Strip markdown fences and extract the first JSON object.
    """
    cleaned = re.sub(r"```(?:json)?\s*", "", content).strip()
    match = re.search(r"(\{.*\})", cleaned, re.S)
    if not match:
        logger.error("Failed to parse JSON from content: %r", content)
        raise ValueError("No JSON object found in response")
    return json.loads(match.group(1))


async def get_anthropic_completion(
    prompt: str,
    schema: Dict[str, Any],
    model: str = None,  # Make model optional
    temperature: float = 1.0,
    max_tokens: int = 2048,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    Send an async chat completion request to Anthropic and return parsed JSON.
    """
    # If model not provided, get it from config
    if model is None:
        preferred_provider = CONFIG.preferred_provider
        provider_config = CONFIG.providers[preferred_provider]
        # Use the 'high' model for completions by default
        model = provider_config.models.high
    
    client = get_async_client()
    messages = _build_messages(prompt, schema)

    try:
        response = await asyncio.wait_for(
            client.messages.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                system=f"You are a helpful assistant that always responds with valid JSON matching the provided schema."
            ),
            timeout
        )
    except asyncio.TimeoutError:
        logger.error("Completion request timed out after %s seconds", timeout)
        raise

    # Extract the response content
    content = response.content[0].text
    return clean_response(content)
