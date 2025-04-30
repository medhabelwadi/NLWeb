import json
from enum import Enum
import asyncio
from openai import AzureOpenAI
import os
import concurrent.futures
import logging
import sys

def get_configured_logger(name):
    # Configure logging at the top of the file
    # Disable noisy logging from urllib3 and Azure core libraries
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
    logging.getLogger('azure.search.documents').setLevel(logging.WARNING)

    # Configure your application's logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # Create a logger for your application
    logger = logging.getLogger(name)
    return logger


logger = get_configured_logger('mllm')

# The code for calling Azure Open AI endpoints
# old_mllm.py includes the code for calling many more types of models

class ModelProvider(Enum):
    # These are the models we work with, for now.
    AZURE_OPENAI = "azure_openai"


def determine_best_model(prompt, query_id="Ranking", model_family="gpt"):
    # TODO: This is a placeholder. We need to determine the best model based on the prompt.
    # For now, we just return the smallest model.
    return "gpt-4.1-mini"

AZURE_OPENAI_ENDPOINT = None
def get_azure_openai_endpoint():
    global AZURE_OPENAI_ENDPOINT
    if AZURE_OPENAI_ENDPOINT is None:
        AZURE_OPENAI_ENDPOINT = os.environ.get('AZURE_OPENAI_ENDPOINT')
    if AZURE_OPENAI_ENDPOINT is None:
        # Fail fast with a clear log and exit
        logger.error(
            "AZURE_OPENAI_ENDPOINT is not set.  Please set this environment variable and restart."
        )
        sys.exit(1)
    else:
        AZURE_OPENAI_ENDPOINT = AZURE_OPENAI_ENDPOINT.strip('"')  # Adding the strip in case the env var has quotes in it
    return AZURE_OPENAI_ENDPOINT

AZURE_OPENAI_API_KEY = None
def get_azure_openai_api_key():
    global AZURE_OPENAI_API_KEY
    if AZURE_OPENAI_API_KEY is None:
        AZURE_OPENAI_API_KEY = os.environ.get('AZURE_OPENAI_API_KEY')
    if AZURE_OPENAI_API_KEY is None:
        # Fail fast with a clear log and exit
        logger.error(
            "AZURE_OPENAI_API_KEY is not set.  Please set this environment variable and restart."
        )
        sys.exit(1)
    else:
        AZURE_OPENAI_API_KEY = AZURE_OPENAI_API_KEY.strip('"')  # Adding the strip in case the env var has quotes in it
    return AZURE_OPENAI_API_KEY


azure_embedding_api_version = "2024-02-01"
azure_embedding_deployment = "text-embedding-3-small"

# Global thread pool for CPU-bound tasks
_thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=10)

class LLMClients:
    azure_openai_client = None
    
    @classmethod
    def get_azure_openai_client(cls):
        if cls.azure_openai_client is None:
            endpoint = get_azure_openai_endpoint()
            cls.azure_openai_client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=get_azure_openai_api_key(),
                api_version="2024-12-01-preview",
                timeout=30.0  # Set timeout explicitly
            )
            
        return cls.azure_openai_client
    
def get_provider(model_name):
    return ModelProvider.AZURE_OPENAI
    
async def get_embedding(query):
    client = LLMClients.get_azure_openai_client()
    response = client.embeddings.create(
        input=query,
        model=azure_embedding_deployment
    )
    embedding = response.data[0].embedding
    return embedding

async def get_azure_embedding(text):
    # Use thread pool for I/O operation to avoid blocking
    loop = asyncio.get_event_loop()
    client = LLMClients.get_azure_openai_client()
    
    # Run in thread pool
    response = await loop.run_in_executor(
        _thread_pool,
        lambda: client.embeddings.create(
            input=text,
            model=azure_embedding_deployment
        )
    )
    
    embedding = response.data[0].embedding
    return embedding


def clean_azure_openai_response(content):
    response_text = content.strip()
    response_text = content.replace('```json', '').replace('```', '').strip()
            
    start_idx = response_text.find('{')
    end_idx = response_text.rfind('}') + 1
    if start_idx == -1 or end_idx == 0:
        raise ValueError("No valid JSON object found in response")
        
    json_str = response_text[start_idx:end_idx]
            
    try:
        result = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse response as JSON: {e}")
    return result

def get_structured_completion_async(prompt, json_schema, model_name="gpt-4.1-mini", temperature=0.7, timeout=8):
  #  if ("4o" in model_name):
  #      model_name = model_name.replace("4o", "4.1")
    return get_azure_openai_completion(prompt, json_schema, model_name, temperature, timeout)

async def get_azure_openai_completion(prompt, json_schema, model_name="gpt-4.1-mini", temperature=0.7, timeout=8):
    client = LLMClients.get_azure_openai_client()
    system_prompt = f"""Provide a response that matches this JSON schema: {json.dumps(json_schema)}"""
    
    loop = asyncio.get_event_loop()
    try:
        if (model_name == "o1"):
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    _thread_pool,
                lambda: client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    max_completion_tokens=2056,
                    stream=False,
                    model=model_name
                )
            ),
                timeout=timeout * 150
            )
        else:
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    _thread_pool,
                    lambda: client.chat.completions.create(
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
                    model=model_name
                )
            ),
                timeout=timeout
            )

        ansr_str = response.choices[0].message.content
        ansr = clean_azure_openai_response(ansr_str)
        return ansr
    except asyncio.TimeoutError:
        raise TimeoutError(f"Azure OpenAI completion timed out after {timeout} seconds")
        return None
 
async def main():
    BOOK_REVIEW_SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "title": "BookReview",
        "description": "A structured book review with ratings and analysis",
        "properties": {
            "title": {"type": "string"},
            "rating": {
                "type": "number",
                "minimum": 1,
                "maximum": 5
            },
            "summary": {"type": "string"},
            "pros": {
                "type": "array",
                "items": {"type": "string"}
            },
            "cons": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["title", "rating", "summary", "pros", "cons"]
    }

    prompt = "Give me a review of the book '1984' by George Orwell"
    embedding_text = "This is a test for embedding functionality"

    try:
        logger.info("Testing Azure OpenAI:")
        
        try:
            response = await get_azure_openai_completion(
                prompt=prompt,
                json_schema=BOOK_REVIEW_SCHEMA,
                model_name="gpt-4.1"  # Using Azure OpenAI model
            )
            logger.info("Response from Azure OpenAI (gpt-4.1):")
            logger.info(json.dumps(response, indent=2))
        except Exception as e:
            logger.error(f"Error with Azure OpenAI (gpt-4.1) at line {e.__traceback__.tb_lineno}: {e}")

        logger.info("Testing Azure Embedding:")
        try:
            embedding = await get_azure_embedding(embedding_text)
            logger.info("Embedding result:")
            logger.info(f"Length of embedding vector: {len(embedding)}")
            logger.info(f"First 5 values of embedding: {embedding[:5]}")
        except Exception as e:
            logger.error(f"Error with Azure Embedding at line {e.__traceback__.tb_lineno}: {e}")

    except Exception as e:
        logger.error(f"Error in test harness at line {e.__traceback__.tb_lineno}: {e}")

if __name__ == "__main__":
    asyncio.run(main())