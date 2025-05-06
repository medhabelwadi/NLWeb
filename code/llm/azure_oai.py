# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.

Code for calling Azure Open AI endpoints.
"""

import json
from openai import AsyncAzureOpenAI
from config.config import CONFIG
from utils.logger import LogLevel, get_logger
import asyncio
import threading

# Initialize logger using your logger utility
logger = get_logger("azure_openai")

# Global client with thread-safe initialization
_client_lock = threading.Lock()
azure_openai_client = None

def get_azure_openai_endpoint():
    """Get the Azure OpenAI endpoint from configuration."""
    logger.debug("Retrieving Azure OpenAI endpoint from config")
    provider_config = CONFIG.providers.get("azure_openai")
    if provider_config and provider_config.endpoint:
        endpoint = provider_config.endpoint
        if endpoint:
            endpoint = endpoint.strip('"')  # Remove quotes if present
            logger.debug(f"Azure OpenAI endpoint found: {endpoint[:20]}...")  # Log first 20 chars only
            return endpoint
    logger.warning("Azure OpenAI endpoint not found in config")
    return None

def get_azure_openai_api_key():
    """Get the Azure OpenAI API key from configuration."""
    logger.debug("Retrieving Azure OpenAI API key from config")
    provider_config = CONFIG.providers.get("azure_openai")
    if provider_config and provider_config.api_key:
        api_key = provider_config.api_key
        if api_key:
            api_key = api_key.strip('"')  # Remove quotes if present
            logger.debug("Azure OpenAI API key found")  # Never log actual API key
            return api_key
    logger.warning("Azure OpenAI API key not found in config")
    return None

def get_azure_openai_api_version():
    """Get the Azure OpenAI API version from configuration."""
    logger.debug("Retrieving Azure OpenAI API version from config")
    provider_config = CONFIG.providers.get("azure_openai")
    if provider_config and provider_config.api_version:
        api_version = provider_config.api_version
        logger.debug(f"Azure OpenAI API version: {api_version}")
        return api_version
    # Default value if not found in config
    default_version = "2024-02-01"
    logger.warning(f"Azure OpenAI API version not found in config, using default: {default_version}")
    return default_version

def get_azure_openai_embedding_model():
    """Get the Azure OpenAI embedding model from configuration."""
    logger.debug("Retrieving Azure OpenAI embedding model from config")
    provider_config = CONFIG.providers.get("azure_openai")
    if provider_config and provider_config.embedding_model:
        model = provider_config.embedding_model
        if model:
            model = model.strip('"')  # Remove quotes if present
            logger.debug(f"Azure OpenAI embedding model: {model}")
            return model
    # Default value if not found in config
    default_model = "text-embedding-3-small"
    logger.warning(f"Azure OpenAI embedding model not found in config, using default: {default_model}")
    return default_model

def get_model_from_config(high_tier=False):
    """Get the appropriate model from configuration based on tier."""
    logger.debug(f"Retrieving Azure OpenAI {'high' if high_tier else 'low'} tier model from config")
    provider_config = CONFIG.providers.get("azure_openai")
    if provider_config and provider_config.models:
        model_name = provider_config.models.high if high_tier else provider_config.models.low
        if model_name:
            logger.debug(f"Model found: {model_name}")
            return model_name
    # Default values if not found
    default_model = "gpt-4.1" if high_tier else "gpt-4.1-mini"
    logger.warning(f"Model not found in config, using default: {default_model}")
    return default_model

def get_azure_openai_client():
    """Get or initialize the Azure OpenAI client."""
    global azure_openai_client
    with _client_lock:  # Thread-safe client initialization
        if azure_openai_client is None:
            logger.info("Initializing Azure OpenAI client")
            endpoint = get_azure_openai_endpoint()
            api_key = get_azure_openai_api_key()
            api_version = get_azure_openai_api_version()
            if not all([endpoint, api_key, api_version]):
                error_msg = "Missing required Azure OpenAI configuration"
                logger.error(error_msg)
                logger.log_with_context(
                    LogLevel.ERROR,
                    "Azure OpenAI configuration incomplete",
                    {
                        "has_endpoint": bool(endpoint),
                        "has_api_key": bool(api_key),
                        "has_api_version": bool(api_version)
                    }
                )
                raise ValueError(error_msg)
                
            try:
                azure_openai_client = AsyncAzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=api_key,
                    api_version=api_version,
                    timeout=30.0  # Set timeout explicitly
                )
                logger.info("Azure OpenAI client initialized successfully")
            except Exception as e:
                logger.exception("Failed to initialize Azure OpenAI client")
                raise
           
    return azure_openai_client

async def get_azure_embedding(text):
    """Generate embeddings using Azure OpenAI."""
    logger.info("Getting Azure embedding")
    logger.debug(f"Text length: {len(text)} characters")
    
    client = get_azure_openai_client()
    embedding_model = get_azure_openai_embedding_model()
    
    if not embedding_model:
        error_msg = "Azure OpenAI embedding model not configured"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        response = await client.embeddings.create(
            input=text,
            model=embedding_model
        )
        
        embedding = response.data[0].embedding
        logger.debug(f"Embedding generated successfully, dimension: {len(embedding)}")
        return embedding
    except Exception as e:
        logger.exception("Error generating embedding")
        logger.log_with_context(
            LogLevel.ERROR,
            "Embedding generation failed",
            {
                "model": embedding_model,
                "text_length": len(text),
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )
        raise

def clean_azure_openai_response(content):
    """Clean and extract JSON content from OpenAI response."""
    logger.debug("Cleaning Azure OpenAI response")
    response_text = content.strip()
    # Remove markdown code block indicators if present
    response_text = response_text.replace('```json', '').replace('```', '').strip()
            
    # Find the JSON object within the response
    start_idx = response_text.find('{')
    end_idx = response_text.rfind('}') + 1
    
    if start_idx == -1 or end_idx == 0:
        error_msg = "No valid JSON object found in response"
        logger.error(error_msg)
        logger.debug(f"Response content: {response_text[:200]}...")  # Log first 200 chars
        raise ValueError(error_msg)
        
    json_str = response_text[start_idx:end_idx]
            
    try:
        result = json.loads(json_str)
        logger.debug("Successfully parsed JSON response")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse response as JSON: {e}")
        logger.debug(f"JSON string: {json_str[:200]}...")  # Log first 200 chars
        raise ValueError(f"Failed to parse response as JSON: {e}")

async def get_azure_openai_completion(prompt, json_schema, model=None, high_tier=False, temperature=0.7, timeout=8):
    """
    Get completion from Azure OpenAI.
    
    Args:
        prompt: The prompt to send to the model
        json_schema: JSON schema for the expected response
        model: Specific model to use (overrides configuration)
        high_tier: Whether to use the high-tier model from config
        temperature: Model temperature
        timeout: Request timeout in seconds
        
    Returns:
        Parsed JSON response
    """
    # Use specified model or get from config based on tier
    model_to_use = model if model else get_model_from_config(high_tier)
    
    logger.info(f"Getting Azure OpenAI completion with model: {model_to_use}")
    logger.debug(f"Temperature: {temperature}, Timeout: {timeout}s")
    logger.debug(f"Prompt length: {len(prompt)} chars")
    
    client = get_azure_openai_client()
    system_prompt = f"""Provide a response that matches this JSON schema: {json.dumps(json_schema)}"""
    
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2056,
                temperature=temperature,
                top_p=0.1,
                stream=False,
                presence_penalty=0.0,
                frequency_penalty=0.0,
                model=model_to_use
            ),
            timeout=timeout
        )
        
        ansr_str = response.choices[0].message.content
        logger.debug(f"Raw response length: {len(ansr_str)} chars")
        
        ansr = clean_azure_openai_response(ansr_str)
        logger.info("Azure OpenAI completion successful")
        return ansr
        
    except asyncio.TimeoutError:
        logger.error(f"Azure OpenAI completion timed out after {timeout}s")
        raise
    except Exception as e:
        logger.exception("Error during Azure OpenAI completion")
        logger.log_with_context(
            LogLevel.ERROR,
            "Azure OpenAI completion failed",
            {
                "model": model_to_use,
                "temperature": temperature,
                "timeout": timeout,
                "prompt_length": len(prompt),
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )
        raise