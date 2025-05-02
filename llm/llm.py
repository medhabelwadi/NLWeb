# llm_router.py

import asyncio
from typing import Optional, Dict, Any, List
from config import CONFIG

async def get_chat_completion(
    prompt: str,
    schema: Dict[str, Any],
    provider: Optional[str] = None,
    quality: str = "low"
) -> Dict[str, Any]:
    
    provider = provider or CONFIG.preferred_provider
    if provider not in CONFIG.providers:
        raise ValueError(f"Unknown provider '{provider}'")

    model_id = getattr(CONFIG.providers[provider].models, quality)

    if provider == "openai":
        from mllm_openai import get_completion as openai_complete
        return await openai_complete(prompt, schema, model=model_id)

    if provider == "anthropic":
        from mllm_anthropic import get_completion as anth_complete
        return await anth_complete(prompt, schema, model=model_id)

    if provider == "gemini":
        from mllm_gemini import get_completion as gem_complete
        return await gem_complete(prompt, schema, model=model_id)

    if provider == "azure_openai":
        from mllm_azure import get_completion as azure_complete
        # here model_id is the deployment_id
        return await azure_complete(prompt, schema, deployment_id=model_id)

    raise ValueError(f"No implementation for provider '{provider}'")


async def get_embedding(
    text: str,
    provider: Optional[str] = None,
    quality: str = "high"
) -> List[float]:
    provider = provider or CONFIG.preferred_provider
    if provider not in CONFIG.providers:
        raise ValueError(f"Unknown provider '{provider}'")

    model_id = getattr(CONFIG.providers[provider].models, quality)

    if provider == "openai":
        from mllm_openai import get_embeddings as openai_embed
        return await openai_embed(text, model=model_id)

    if provider == "anthropic":
        from mllm_anthropic import get_embeddings as anth_embed
        return await anth_embed(text, model=model_id)

    if provider == "gemini":
        from mllm_gemini import get_embeddings as gem_embed
        return await gem_embed(text, model=model_id)

    if provider == "azure_openai":
        from mllm_azure import get_embeddings as azure_embed
        # here model_id is the deployment_id
        return await azure_embed(text, deployment_id=model_id)

    raise ValueError(f"No implementation for provider '{provider}'")
