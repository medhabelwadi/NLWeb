import os
import json
import re
import logging
import asyncio
from typing import Dict, Any, List

import anthropic

logger = logging.getLogger(__name__)


class ConfigurationError(RuntimeError):
    """Raised when configuration is missing or invalid."""
    pass


def get_anthropic_api_key() -> str:
    """Retrieve the Anthropic API key from the environment or raise an error."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise ConfigurationError("ANTHROPIC_API_KEY is not set")
    return key


def get_async_client() -> anthropic.Client:
    """
    Configure and return an Anthropic client.

    Note: Anthropic's Python client uses sync I/O under the hood;
    we wrap calls in asyncio.to_thread for async behavior.
    """
    return anthropic.Client(api_key=get_anthropic_api_key())


def _build_prompt(prompt: str, schema: Dict[str, Any]) -> str:
    """
    Construct the combined prompt with system and user roles
    for JSON-schema enforcement.
    """
    system = (
        f"{anthropic.AI_PROMPT}"
        f"Provide a valid JSON response matching this schema: {json.dumps(schema)}"
    )
    user = f"{anthropic.HUMAN_PROMPT} {prompt}"
    # End with AI_PROMPT so the model knows to generate the response
    return f"{system}{user}{anthropic.AI_PROMPT}"


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
    model: str = "claude-2",
    temperature: float = 1.0,
    max_tokens_to_sample: int = 2048,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    Send an async chat completion request to Anthropic and return parsed JSON.
    """
    client = get_async_client()
    anthropic_prompt = _build_prompt(prompt, schema)

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                lambda: client.completions.create(
                    model=model,
                    prompt=anthropic_prompt,
                    max_tokens_to_sample=max_tokens_to_sample,
                    temperature=temperature,
                )
            ),
            timeout,
        )
    except asyncio.TimeoutError:
        logger.error("Completion request timed out after %s seconds", timeout)
        raise

    # response.completion contains the generated text
    return clean_response(response.completion)


async def get_embeddings(
    text: str,
    model: str = "embeddings-cl100k",
    timeout: float = 30.0,
) -> List[float]:
    """
    Send an async embedding request to Anthropic and return the embedding vector.
    """
    client = get_async_client()

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                lambda: client.embeddings.create(model=model, input=text)
            ),
            timeout,
        )
    except asyncio.TimeoutError:
        logger.error("Embedding request timed out after %s seconds", timeout)
        raise

    # Assuming response.data[0]['embedding'] holds the vector
    return response.data[0]['embedding']
