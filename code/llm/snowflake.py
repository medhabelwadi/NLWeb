# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
Snowflake AI wrapper for LLM functionality.

Snowflake Cortex wrapper.

Wrappers over the Snowflake Cortex REST APIs.

Currently uses raw REST requests to act as the simplest, lowest-level reference.
An alternative would have been to use the Snowflake Python SDK as outlined in:
https://docs.snowflake.com/en/developer-guide/snowpark-ml/reference/1.8.1/index-cortex


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


async def cortex_embed(text: str, model: str|None = None) -> List[float]:
    """
    Embed text using snowflake.cortex.embed.

    See: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-llm-rest-api#label-cortex-llm-embed-function
    """
    if model is None:
        model = get_embedding_model()
    response = await post(
        "/api/v2/cortex/inference:embed",
        {
            "text":[text], 
            "model":model,
        })
    return response.get("data")[0].get("embedding")[0]
        

async def cortex_complete(
        prompt: str, 
        schema: Dict[str, Any],
        model: str|None = None, 
        max_tokens: int = 4096, 
        top_p: float=1.0, 
        temperature: float=0.0) -> str:
    """
    Send an async chat completion request via snowflake.cortex.complete and return parsed JSON output.

    See: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-llm-rest-api#complete-function

    Arguments:
    - prompt: The prompt to complete
    - schema: JSON schema of the desired response.
    - model: The name of the model to use (if not specified, one will be chosen)
    - max_tokens: A value between 1 and 4096 (inclusive) that controls the maximum number of tokens to output. Output is truncated after this number of tokens.
    - top_p: A value from 0 to 1 (inclusive) that controls the diversity of the language model by restricting the set of possible tokens that the model outputs.
    - temperature: A value from 0 to 1 (inclusive) that controls the randomness of the output of the language model by influencing which possible token is chosen at each step.
    """
    if model is None:
        model = "claude-3-5-sonnet"
    response = await post(
        "/api/v2/cortex/inference:complete",
        {
            "model": model,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "temperature": temperature,
            "messages": [
                # The precise system prompt may need adjustment given a model. For example, a simpler prompt worked well for larger
                # models but saying JSON twice helped for llama3.1-8b
                # Alternatively, should explore using structured outputs support as outlined in:
                # https://docs.snowflake.com/en/user-guide/snowflake-cortex/complete-structured-outputs
                {"role": "system", "content": f"Provide a response in valid JSON that matches this JSON schema: {json.dumps(schema)}"},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }
    )
    content = response.get("choices")[0].get("message").get("content").strip()
    # Attempt to be resilient to the model adding something before or after the JSON
    start_idx = content.find('{')
    limit_idx = content.rfind('}')+1
    if start_idx < 0 or limit_idx <= 0:
        raise ValueError(f"model did not generate valid JSON, it generated '{content}'")
    return json.loads(content[start_idx:limit_idx])
    

async def post(api: str, request: dict) -> dict:
    async with httpx.AsyncClient() as client:
        response =  await client.post(
            snowflake.get_account_url() + api,
            json=request,
            headers={
                    "Authorization": f"Bearer {snowflake.get_pat()}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
            },
            timeout=60,
        )
        if response.status_code == 400:
            raise Exception(response.json())
        response.raise_for_status()
        return response.json()

