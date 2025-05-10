"""
Snowflake Cortex wrapper.

Wrappers over the Snowflake Cortex REST APIs.

Currently uses raw REST requests to act as the simplest, lowest-level reference.
An alternative would have been to use the Snowflake Python SDK as outlined in:
https://docs.snowflake.com/en/developer-guide/snowpark-ml/reference/1.8.1/index-cortex

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.
"""

import httpx
import json
from config.config import CONFIG
from typing import Any, Dict, List
from utils import snowflake

def get_embedding_model() -> str:
    """
    Retrieve the embedding model to use from the config, defaulting to snowflake-arctic-embed-l-v2.0
    """
    config = CONFIG.providers.get("snowflake")
    return config.embedding_model if config and config.embedding_model else "snowflake-arctic-embed-l-v2.0"


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
