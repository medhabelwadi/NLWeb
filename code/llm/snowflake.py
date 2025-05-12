# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
Snowflake AI wrapper for LLM functionality.

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.
"""

import os
import json
import re
import logging
import asyncio
from typing import Dict, Any, List, Optional

from config.config import CONFIG
import threading

from llm.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class ConfigurationError(RuntimeError):
    """Raised when configuration is missing or invalid."""
    pass


class SnowflakeProvider(LLMProvider):
    """Implementation of LLMProvider for Snowflake AI."""
    
    _client_lock = threading.Lock()
    _client = None

    @classmethod
    def get_api_key(cls) -> str:
        """Retrieve the Snowflake API key from the environment or raise an error."""
        # Get the API key from the preferred provider config
        provider_config = CONFIG.llm_providers.get("snowflake")
        if not provider_config:
            raise ConfigurationError("Snowflake provider not configured")
            
        api_key_env_var = provider_config.api_key_env
        
        key = os.getenv(api_key_env_var)
        if not key:
            raise ConfigurationError(f"{api_key_env_var} is not set")
        return key

    @classmethod
    def get_client(cls):
        """
        Configure and return a Snowflake client.
        
        Note: This is a placeholder implementation as the actual client
        initialization would depend on the Snowflake AI SDK.
        """
        with cls._client_lock:  # Thread-safe client initialization
            if cls._client is None:
                # TODO: Initialize Snowflake client
                # This is a stub implementation
                cls._client = None
        return cls._client

    @classmethod
    def clean_response(cls, content: str) -> Dict[str, Any]:
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
        self,
        prompt: str,
        schema: Dict[str, Any],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: float = 30.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send an async chat completion request to Snowflake AI and return parsed JSON.
        
        Note: This is a placeholder implementation as the actual API calls
        would depend on the Snowflake AI SDK.
        """
        # If model not provided, get it from config
        if model is None:
            provider_config = CONFIG.llm_providers.get("snowflake")
            if provider_config and provider_config.models:
                # Use the 'high' model for completions by default
                model = provider_config.models.high
        
        # TODO: Implement actual Snowflake AI API call
        # This is a stub implementation that raises NotImplementedError
        raise NotImplementedError("Snowflake AI provider is not yet implemented")


# Create a singleton instance
provider = SnowflakeProvider()

# For backwards compatibility
async def get_snowflake_completion(prompt, schema, model=None, temperature=0.7, timeout=30.0):
    """For backwards compatibility with the existing API."""
    return await provider.get_completion(
        prompt, schema, model=model, temperature=temperature, timeout=timeout
    )