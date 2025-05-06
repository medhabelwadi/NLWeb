# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
Gemini/Vertex AI wrapper  

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.

"""

import os
import json
import re
import logging
import asyncio
from typing import Dict, Any, List

import vertexai
from vertexai.generative_models import GenerativeModel, ChatSession
from vertexai.language_models import TextEmbeddingModel
from config.config import CONFIG
import threading

logger = logging.getLogger(__name__)


class ConfigurationError(RuntimeError):
    """Raised when configuration is missing or invalid."""
    pass


def get_gcp_project() -> str:
    """Retrieve the GCP project ID from the environment or raise an error."""
    # Get the project ID from the preferred provider config
    preferred_provider = CONFIG.preferred_provider
    provider_config = CONFIG.providers[preferred_provider]
    
    # For Gemini, we need the GCP project ID, which might be stored in API_KEY_ENV or a specific field
    # First check if there's a specific project env var in the config
    project_env_var = provider_config.api_key_env  # This might actually be the project ID for GCP
    
    project = os.getenv("GCP_PROJECT") or os.getenv(project_env_var)
    if not project:
        raise ConfigurationError("GCP_PROJECT is not set")
    return project


def get_gcp_location() -> str:
    """Retrieve the GCP location from the environment or use default 'us-central1'."""
    return os.getenv("GCP_LOCATION", "us-central1")


def get_api_key() -> str:
    """Retrieve the API key if needed for Gemini API."""
    preferred_provider = CONFIG.preferred_provider
    provider_config = CONFIG.providers[preferred_provider]
    api_key_env_var = provider_config.api_key_env
    
    if api_key_env_var:
        return os.getenv(api_key_env_var)
    return None

_init_lock = threading.Lock()
_initialized = False

def init_vertex_ai():
    """Initialize Vertex AI with project and location."""
    global _initialized
    with _init_lock:  # Thread-safe initialization
        if not _initialized:
            vertexai.init(
                project=get_gcp_project(),
                location=get_gcp_location()
            )
            _initialized = True


def _build_messages(prompt: str, schema: Dict[str, Any]) -> List[Dict[str, str]]:
    """Construct the message sequence for JSON-schema enforcement."""
    return [
        f"Provide a valid JSON response matching this schema: {json.dumps(schema)}",
        prompt
    ]


def clean_response(content: str) -> Dict[str, Any]:
    """Strip markdown fences and extract the first JSON object."""
    cleaned = re.sub(r"```(?:json)?\s*", "", content).strip()
    match = re.search(r"(\{.*\})", cleaned, re.S)
    if not match:
        logger.error("Failed to parse JSON from content: %r", content)
        raise ValueError("No JSON object found in response")
    return json.loads(match.group(1))


async def get_gemini_completion(
    prompt: str,
    schema: Dict[str, Any],
    model: str = None,  # Make model optional
    temperature: float = 0.7,
    max_output_tokens: int = 2048,
    timeout: float = 30.0
) -> Dict[str, Any]:
    """Async chat completion using Vertex AI (Gemini)."""
    # If model not provided, get it from config
    if model is None:
        preferred_provider = CONFIG.preferred_provider
        provider_config = CONFIG.providers[preferred_provider]
        # Use the 'high' model for completions by default
        model = provider_config.models.high
    
    init_vertex_ai()
    generative_model = GenerativeModel(model)
    
    # Combine system and user messages
    messages = _build_messages(prompt, schema)
    
    generation_config = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                lambda: generative_model.generate_content(
                    messages,
                    generation_config=generation_config
                )
            ),
            timeout
        )
    except asyncio.TimeoutError:
        logger.error("Completion request timed out after %s seconds", timeout)
        raise

    # Extract the response text
    content = response.text
    return clean_response(content)


async def get_gemini_embeddings(
    text: str,
    model: str = None,  # Make model optional
    timeout: float = 30.0
) -> List[float]:
    """Async embedding request using Vertex AI (Gemini)."""
    # If model not provided, get it from config
    if model is None:
        preferred_provider = CONFIG.preferred_provider
        provider_config = CONFIG.providers[preferred_provider]
        embedding_model_env_var = provider_config.embedding_model_env
        
        if embedding_model_env_var:
            model = os.getenv(embedding_model_env_var)
        
        # Use default if still not set
        if not model:
            model = "textembedding-gecko@003"  # Updated to newer version
    
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

    # Extract the embedding values
    return response[0].values
