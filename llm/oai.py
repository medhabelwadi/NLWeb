import os
import json
import re
import logging
import asyncio
from typing import Dict, Any, List

import openai

logger = logging.getLogger(__name__)


class ConfigurationError(RuntimeError):
    """
    Raised when configuration is missing or invalid.
    """
    pass


def get_openai_api_key() -> str:
    """
    Retrieve the OpenAI API key from environment or raise an error.
    """
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ConfigurationError("OPENAI_API_KEY is not set")
    return key


def get_async_client() -> openai.OpenAIAsync:
    """
    Configure and return an asynchronous OpenAI client.
    """
    openai.api_key = get_openai_api_key()
    return openai.OpenAIAsync()


def _build_messages(prompt: str, schema: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Construct the system and user message sequence enforcing a JSON schema.
    """
    return [
        {
            "role": "system",
            "content": (
                f"Provide a valid JSON response matching this schema: "
                f"{json.dumps(schema)}"
            )
        },
        {"role": "user", "content": prompt}
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


async def get_completion(
    prompt: str,
    schema: Dict[str, Any],
    model: str = "gpt-4",
    temperature: float = 0.7,
    max_tokens: int = 2048,
    timeout: float = 30.0
) -> Dict[str, Any]:
    """
    Send an async chat completion request and return parsed JSON output.
    """
    client = get_async_client()
    messages = _build_messages(prompt, schema)

    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ),
            timeout
        )
    except asyncio.TimeoutError:
        logger.error("Completion request timed out after %s seconds", timeout)
        raise

    return clean_response(response.choices[0].message.content)


async def get_embeddings(
    text: str,
    model: str = "text-embedding-3-small",
    timeout: float = 30.0
) -> List[float]:
    """
    Send an async embedding request and return the embedding vector.
    """
    client = get_async_client()

    try:
        response = await asyncio.wait_for(
            client.embeddings.create(input=text, model=model),
            timeout
        )
    except asyncio.TimeoutError:
        logger.error("Embedding request timed out after %s seconds", timeout)
        raise

    return response.data[0].embedding
