# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
Llama on Azure wrapper  

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.

"""

import json
from openai import AsyncAzureOpenAI
import os
from config.config import CONFIG
import asyncio
import threading
import re

from utils.logging_config_helper import get_configured_logger
logger = get_configured_logger("llama_azure")

# Global client with thread-safe initialization
_client_lock = threading.Lock()
llama_client = None

def get_llama_azure_endpoint():
    """Get Llama Azure endpoint from config"""
    logger.debug("Retrieving Llama Azure endpoint from config")
    provider_config = CONFIG.providers.get("llama_azure")
    if provider_config and provider_config.endpoint:
        endpoint = provider_config.endpoint
        if endpoint:
            endpoint = endpoint.strip('"')
            logger.debug(f"Llama Azure endpoint found: {endpoint[:20]}...")
            return endpoint
    logger.warning("Llama Azure endpoint not found in config")
    return None

def get_llama_azure_api_key():
    """Get Llama Azure API key from config"""
    logger.debug("Retrieving Llama Azure API key from config")
    provider_config = CONFIG.providers.get("llama_azure")
    if provider_config and provider_config.api_key:
        api_key = provider_config.api_key
        if api_key:
            api_key = api_key.strip('"')
            logger.debug("Llama Azure API key found")
            return api_key
    logger.warning("Llama Azure API key not found in config")
    return None

def get_llama_azure_api_version():
    """Get Llama Azure API version from config"""
    logger.debug("Retrieving Llama Azure API version from config")
    provider_config = CONFIG.providers.get("llama_azure")
    if provider_config and provider_config.api_version:
        logger.debug(f"Llama Azure API version: {provider_config.api_version}")
        return provider_config.api_version
    logger.warning("Llama Azure API version not found in config")
    return None

def get_llama_client():
    """Get or create Llama Azure client"""
    global llama_client
    with _client_lock:
        if llama_client is None:
            logger.info("Initializing Llama Azure client")
            endpoint = get_llama_azure_endpoint()
            api_key = get_llama_azure_api_key()
            api_version = get_llama_azure_api_version()
            
            if not all([endpoint, api_key, api_version]):
                error_msg = "Missing required Llama Azure configuration"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            try:
                llama_client = AsyncAzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=api_key,
                    api_version=api_version,
                    timeout=30.0
                )
                logger.info("Llama Azure client initialized successfully")
            except Exception as e:
                logger.exception("Failed to initialize Llama Azure client")
                raise
    
    return llama_client

def clean_llama_response(content):
    """Clean and parse Llama response"""
    logger.debug("Cleaning Llama response")
    response_text = content.strip()
    response_text = response_text.replace('```json', '').replace('```', '').strip()
    
    start_idx = response_text.find('{')
    end_idx = response_text.rfind('}') + 1
    if start_idx == -1 or end_idx == 0:
        error_msg = "No valid JSON object found in response"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    json_str = response_text[start_idx:end_idx]
    
    try:
        result = json.loads(json_str)
        logger.debug("Successfully parsed JSON response")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse response as JSON: {e}")
        raise ValueError(f"Failed to parse response as JSON: {e}")

async def get_llama_completion(prompt, json_schema, model=None, temperature=0.7, timeout=8):
    """Get completion from Llama on Azure"""
    if model is None:
        # Get model from config if not provided
        provider_config = CONFIG.providers.get("llama_azure")
        model = provider_config.models.high if provider_config else "llama-2-70b"
    
    logger.info(f"Getting Llama completion with model: {model}")
    logger.debug(f"Temperature: {temperature}, Timeout: {timeout}s")
    
    client = get_llama_client()
    system_prompt = f"""You are a helpful assistant that provides responses in JSON format.
Your response must be valid JSON that matches this schema: {json.dumps(json_schema)}
Only output the JSON object, no additional text or explanation."""
    
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model=model,
                temperature=temperature,
                max_tokens=2048,
                response_format={"type": "json_object"}  # Force JSON response
            ),
            timeout=timeout
        )
        
        content = response.choices[0].message.content
        logger.debug(f"Raw response length: {len(content)} chars")
        
        result = clean_llama_response(content)
        logger.info("Llama completion successful")
        return result
        
    except asyncio.TimeoutError:
        logger.error(f"Llama completion timed out after {timeout}s")
        raise
    except Exception as e:
        logger.exception("Error during Llama completion")
        raise
