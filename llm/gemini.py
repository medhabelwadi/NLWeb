import os
import json
import re
import logging
import asyncio
from typing import Dict, Any, List

import vertexai
from vertexai.preview.language_models import ChatModel, TextEmbeddingModel

logger = logging.getLogger(__name__)


class ConfigurationError(RuntimeError):
    """Raised when configuration is missing or invalid."""
    pass


def get_gcp_project() -> str:
    """Retrieve the GCP project ID from the environment or raise an error."""
    project = os.getenv("GCP_PROJECT")
    if not project:
        raise ConfigurationError("GCP_PROJECT is not set")
    return project


def get_gcp_location() -> str:
    """Retrieve the GCP location from the environment or use default 'us-central1'."""
    return os.getenv("GCP_LOCATION", "us-central1")


def init_vertex_ai():
    """Initialize Vertex AI with project and location."""
    vertexai.init(
        project=get_gcp_project(),
        location=get_gcp_location()
    )


def _build_prompt(prompt: str, schema: Dict[str, Any]) -> (str, str):
    """Return system context and user message for JSON-schema enforcement."""
    system = f"Provide a valid JSON response matching this schema: {json.dumps(schema)}"
    return system, prompt


def clean_response(content: str) -> Dict[str, Any]:
    """Strip markdown fences and extract the first JSON object."""
    cleaned = re.sub(r"```(?:json)?\s*", "", content).strip()
    match = re.search(r"(\{.*\})", cleaned, re.S)
    if not match:
        logger.error("Failed to parse JSON from content: %r", content)
        raise ValueError("No JSON object found in response")
    return json.loads(match.group(1))


async def get_completion(
    prompt: str,
    schema: Dict[str, Any],
    model: str = "chat-bison@001",
    temperature: float = 0.7,
    max_output_tokens: int = 1024,
    timeout: float = 30.0
) -> Dict[str, Any]:
    """Async chat completion using Vertex AI (Gemini)."""
    init_vertex_ai()
    chat_model = ChatModel.from_pretrained(model)
    system_ctx, user_prompt = _build_prompt(prompt, schema)
    chat = chat_model.start_chat(context=system_ctx)

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                lambda: chat.send_message(
                    user_prompt,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens
                )
            ),
            timeout
        )
    except asyncio.TimeoutError:
        logger.error("Completion request timed out after %s seconds", timeout)
        raise

    # response.text contains the generated content
    return clean_response(response.text)


async def get_embeddings(
    text: str,
    model: str = "textembedding-gecko@001",
    timeout: float = 30.0
) -> List[float]:
    """Async embedding request using Vertex AI (Gemini)."""
    init_vertex_ai()
    embedding_model = TextEmbeddingModel.from_pretrained(model)

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                lambda: embedding_model.get_embeddings([text])
            ),
            timeout
        )
    except asyncio.TimeoutError:
        logger.error("Embedding request timed out after %s seconds", timeout)
        raise

    # Assuming response is a list where each element has a 'values' attribute holding the vector
    return response[0].values
