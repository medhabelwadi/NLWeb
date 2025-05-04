# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.

Code for calling Azure Open AI endpoints.
"""

import json
from openai import AsyncAzureOpenAI
import os
from config.config import CONFIG
from utils.logging_config_helper import get_configured_logger
import asyncio
import threading

logger = get_configured_logger("azure_openai")

# Global client with thread-safe initialization
_client_lock = threading.Lock()
azure_openai_client = None

def get_azure_openai_endpoint():
    # Get endpoint from config - now handles both direct values and env vars
    logger.debug("Retrieving Azure OpenAI endpoint from config")
    provider_config = CONFIG.providers.get("azure_openai")
    if provider_config and provider_config.endpoint:
        endpoint = provider_config.endpoint
        if endpoint:
            endpoint = endpoint.strip('"')  # Adding the strip in case the value has quotes in it
            logger.debug(f"Azure OpenAI endpoint found: {endpoint[:20]}...")  # Log first 20 chars only
            return endpoint
    logger.warning("Azure OpenAI endpoint not found in config")
    return None

def get_azure_openai_api_key():
    # Get API key from config - now handles both direct values and env vars
    logger.debug("Retrieving Azure OpenAI API key from config")
    provider_config = CONFIG.providers.get("azure_openai")
    if provider_config and provider_config.api_key:
        api_key = provider_config.api_key
        if api_key:
            api_key = api_key.strip('"')  # Adding the strip in case the value has quotes in it
            logger.debug("Azure OpenAI API key found")  # Never log actual API key
            return api_key
    logger.warning("Azure OpenAI API key not found in config")
    return None

def get_azure_openai_api_version():
    # Get API version from config - now handles both direct values and env vars
    logger.debug("Retrieving Azure OpenAI API version from config")
    provider_config = CONFIG.providers.get("azure_openai")
    if provider_config and provider_config.api_version:
        logger.debug(f"Azure OpenAI API version: {provider_config.api_version}")
        return provider_config.api_version
    logger.warning("Azure OpenAI API version not found in config")
    return None

def get_azure_openai_embedding_model():
    # Get embedding model from config - now handles both direct values and env vars
    logger.debug("Retrieving Azure OpenAI embedding model from config")
    provider_config = CONFIG.providers.get("azure_openai")
    if provider_config and provider_config.embedding_model:
        model = provider_config.embedding_model
        if model:
            model = model.strip('"')  # Adding the strip in case the value has quotes in it
            logger.debug(f"Azure OpenAI embedding model: {model}")
            return model
    logger.warning("Azure OpenAI embedding model not found in config")
    return None

def get_azure_openai_client():
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
    logger.debug("Cleaning Azure OpenAI response")
    response_text = content.strip()
    response_text = content.replace('```json', '').replace('```', '').strip()
            
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


async def get_azure_openai_completion(prompt, json_schema, model="gpt-4.1-mini", temperature=0.7, timeout=8):
    logger.info(f"Getting Azure OpenAI completion with model: {model}")
    logger.debug(f"Temperature: {temperature}, Timeout: {timeout}s")
    logger.debug(f"Prompt length: {len(prompt)} chars")
    logger.debug(f"Schema: {json_schema}")
    
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
                model=model
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
                "model": model_name,
                "temperature": temperature,
                "timeout": timeout,
                "prompt_length": len(prompt),
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )
        raise
