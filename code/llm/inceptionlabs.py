import os
import requests
import json
from typing import Generator, Optional, Dict, Any
import aiohttp
import re
import asyncio
import threading

# ─── Configuration ─────────────────────────────────────────────────────────────

API_URL = "https://api.inceptionlabs.ai/v1/chat/completions"  # Mercury chat endpoint :contentReference[oaicite:1]{index=1}

def get_api_key() -> str:
    key = os.getenv("INCEPTION_API_KEY")
    if not key:
        raise RuntimeError("INCEPTION_API_KEY environment variable is not set")
    return key

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {get_api_key()}",
}

# ─── Chat Completion (Async) ─────────────────────────────────────────────────────

async def get_inceptionlabs_completion(
    prompt: str,
    json_schema: Optional[Dict[str, Any]] = None,
    model: str = "mercury-coder-small",
    temperature: float = 0.7,
    max_tokens: int = 512,
    diffusing: bool = False,
) -> Any:
    """
    Perform a single-shot (non-streaming) chat completion asynchronously.
    Returns the full assistant response as a string, or as structured JSON if schema is provided.
    
    Args:
        prompt: The user prompt to send to the model
        json_schema: Optional JSON schema that the response should conform to
        model: The model to use for completion
        temperature: Controls randomness (0-1)
        max_tokens: Maximum number of tokens to generate
        diffusing: Whether to use diffusion mode
        
    Returns:
        String response or parsed JSON object if json_schema is provided
    """
    
    messages = []
    
    if json_schema:
        # Add system message to enforce JSON schema
        system_prompt = f"Provide a response that matches this JSON schema: {json.dumps(json_schema)}"
        messages.append({"role": "system", "content": system_prompt})
    
    # Add user message
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if diffusing:
        payload["diffusing"] = True

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, headers=HEADERS, json=payload, timeout=30) as resp:
            resp.raise_for_status()
            data = await resp.json()
            content = data["choices"][0]["message"]["content"]
            
            # If schema was provided, parse the response as JSON
            if json_schema:
                return clean_json_response(content)
            return content

def clean_json_response(content: str) -> Dict[str, Any]:
    """
    Strip markdown fences and extract the first JSON object.
    """
    cleaned = re.sub(r"```(?:json)?\s*", "", content).strip()
    match = re.search(r"(\{.*\})", cleaned, re.S)
    if not match:
        raise ValueError("No JSON object found in response")
    return json.loads(match.group(1))


