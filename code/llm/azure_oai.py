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
import asyncio
import threading

# Global client with thread-safe initialization
_client_lock = threading.Lock()
azure_openai_client = None

def get_azure_openai_endpoint():
    """Get the Azure OpenAI endpoint from configuration."""
    provider_config = CONFIG.providers.get("azure_openai")
    if provider_config and provider_config.endpoint:
        endpoint = provider_config.endpoint
        if endpoint:
            endpoint = endpoint.strip('"')  # Remove quotes if present
            return endpoint
    return None

def get_azure_openai_api_key():
    """Get the Azure OpenAI API key from configuration."""
    provider_config = CONFIG.providers.get("azure_openai")
    if provider_config and provider_config.api_key:
        api_key = provider_config.api_key
        if api_key:
            api_key = api_key.strip('"')  # Remove quotes if present
            return api_key
    return None

def get_azure_openai_api_version():
    """Get the Azure OpenAI API version from configuration."""
    provider_config = CONFIG.providers.get("azure_openai")
    if provider_config and provider_config.api_version:
        api_version = provider_config.api_version
        return api_version
    # Default value if not found in config
    default_version = "2024-10-21"
    return default_version

def get_azure_openai_embedding_model():
    """Get the Azure OpenAI embedding model from configuration."""
    provider_config = CONFIG.providers.get("azure_openai")
    if provider_config and provider_config.embedding_model:
        model = provider_config.embedding_model
        if model:
            model = model.strip('"')  # Remove quotes if present
            return model
    # Default value if not found in config
    default_model = "text-embedding-3-small"
    return default_model

def get_model_from_config(high_tier=False):
    """Get the appropriate model from configuration based on tier."""
    provider_config = CONFIG.providers.get("azure_openai")
    if provider_config and provider_config.models:
        model_name = provider_config.models.high if high_tier else provider_config.models.low
        if model_name:
            return model_name
    # Default values if not found
    default_model = "gpt-4.1" if high_tier else "gpt-4.1-mini"
    return default_model

def get_azure_openai_client():
    """Get or initialize the Azure OpenAI client."""
    global azure_openai_client
    with _client_lock:  # Thread-safe client initialization
        if azure_openai_client is None:
            endpoint = get_azure_openai_endpoint()
            api_key = get_azure_openai_api_key()
            api_version = get_azure_openai_api_version()
            if not all([endpoint, api_key, api_version]):
                error_msg = "Missing required Azure OpenAI configuration"
                raise ValueError(error_msg)
                
            try:
                azure_openai_client = AsyncAzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=api_key,
                    api_version=api_version,
                    timeout=30.0  # Set timeout explicitly
                )
            except Exception as e:
                raise
           
    return azure_openai_client

async def get_azure_embedding(text):
    """Generate embeddings using Azure OpenAI."""
    client = get_azure_openai_client()
    embedding_model = get_azure_openai_embedding_model()
    
    if not embedding_model:
        error_msg = "Azure OpenAI embedding model not configured"
        raise ValueError(error_msg)
    
    try:
        response = await client.embeddings.create(
            input=text,
            model=embedding_model
        )
        
        embedding = response.data[0].embedding
        return embedding
    except Exception as e:
        raise

def clean_azure_openai_response(content):
    """Clean and extract JSON content from OpenAI response."""
    response_text = content.strip()
    # Remove markdown code block indicators if present
    response_text = response_text.replace('```json', '').replace('```', '').strip()
            
    # Find the JSON object within the response
    start_idx = response_text.find('{')
    end_idx = response_text.rfind('}') + 1
    
    if start_idx == -1 or end_idx == 0:
        error_msg = "No valid JSON object found in response"
        raise ValueError(error_msg)
        
    json_str = response_text[start_idx:end_idx]
            
    try:
        result = json.loads(json_str)
        return result
    except json.JSONDecodeError as e:
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
        ansr = clean_azure_openai_response(ansr_str)
        return ansr
        
    except asyncio.TimeoutError:
        raise
    except Exception as e:
        raise