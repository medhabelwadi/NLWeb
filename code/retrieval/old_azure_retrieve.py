# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
This file is used to retrieve items from the Azure AI Search index.

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.
"""

import json
import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
import time
from utils.utils import log, siteToItemType 
from llm.llm import get_embedding
import sys
from config.config import CONFIG
import asyncio
import threading


# Single global search client with thread-safe initialization
_client_lock = threading.Lock()
search_client = None

def get_azure_search_config():
    """Get Azure AI Search configuration from config file"""
    provider_name = CONFIG.preferred_retrieval_provider
    if provider_name != "azure_ai_search":
        log(f"Preferred retrieval provider is '{provider_name}', but this module requires 'azure_ai_search'")
        sys.exit(1)
    
    azure_config = CONFIG.retrieval_providers.get(provider_name)
    if not azure_config:
        log("Azure AI Search configuration not found in config_retrieval.yaml")
        sys.exit(1)
    
    return azure_config

def get_search_service_endpoint():
    """Get search service endpoint from config"""
    azure_config = get_azure_search_config()
    endpoint = azure_config.api_endpoint
    if not endpoint:
        log("Azure AI Search endpoint not configured. Please check config_retrieval.yaml")
        sys.exit(1)
    return endpoint.strip('"')  # Strip quotes if present

def get_search_api_key():
    """Get search API key from config"""
    azure_config = get_azure_search_config()
    api_key = azure_config.api_key
    if not api_key:
        log("Azure AI Search API key not configured. Please check config_retrieval.yaml")
        sys.exit(1)
    return api_key.strip('"')  # Strip quotes if present

def get_index_name():
    """Get index name from config"""
    azure_config = get_azure_search_config()
    index_name = azure_config.index_name
    if not index_name:
        log("Azure AI Search index name not configured. Please check config_retrieval.yaml")
        sys.exit(1)
    return index_name

def get_search_client():
    """Get the search client for the configured index"""
    global search_client
    with _client_lock:  # Thread-safe client initialization
        if search_client is None:
            initialize_client()
    return search_client

def initialize_client():
    """Initialize the search client"""
    global search_client
    api_key = get_search_api_key()
    endpoint = get_search_service_endpoint()
    index_name = get_index_name()
    
    credential = AzureKeyCredential(api_key)
    search_client = SearchClient(
        endpoint=endpoint, 
        index_name=index_name, 
        credential=credential
    )
    log(f"Initialized Azure Search client for index: {index_name}")

async def search_db(query, site, num_results=50):
    """
    Search the Azure AI Search index for records filtered by site and ranked by vector similarity
    
    Args:
        query (str): The search query
        site (str): Site value to filter by
        num_results (int, optional): Number of results to retrieve. Defaults to 50.
        
    Returns:
        list: List of search results with relevance scores
    """
    start_embed = time.time()
    embedding = await get_embedding(query)
    embed_time = time.time() - start_embed
    
    start_retrieve = time.time()
    results = await retrieve_by_site_and_vector(site, embedding, num_results)
    retrieve_time = time.time() - start_retrieve
    
    print(f"Timing - Embedding: {embed_time:.2f}s, Retrieval: {retrieve_time:.2f}s")
    return results

async def retrieve_by_site_and_vector(sites, vector_embedding, top_n=10):
    """
    Retrieve top n records filtered by site and ranked by vector similarity
    
    Args:
        sites (str or list): Site value(s) to filter by
        vector_embedding (list or numpy.ndarray): Vector embedding for similarity search
        top_n (int, optional): Number of results to retrieve. Defaults to 10.
        
    Returns:
        list: List of search results with relevance scores
    """
    # Validate embedding dimension
    if len(vector_embedding) != 1536:
        raise ValueError(f"Embedding dimension {len(vector_embedding)} not supported. Must be 1536.")
    
    search_client = get_search_client()
    
    # Handle both single site and multiple sites
    if isinstance(sites, str):
        sites = [sites]
    
    site_restrict = ""
    for site in sites:
        if len(site_restrict) > 0:
            site_restrict += " or "
        site_restrict += f"site eq '{site}'"
    
    # Create the search options with vector search and filtering
    print(f"site: {sites}")
    search_options = {
        "filter": site_restrict,
        "vector_queries": [
            {
                "kind": "vector",
                "vector": vector_embedding,
                "fields": "embedding",
                "k": top_n
            }
        ],
        "top": top_n,
        "select": "url,name,site,schema_json"
    }
    
    # Execute the search asynchronously
    def search_sync():
        return search_client.search(search_text=None, **search_options)
    
    results = await asyncio.get_event_loop().run_in_executor(None, search_sync)
    
    # Process results into a more convenient format
    processed_results = []
    for result in results:
        processed_result = [result["url"], result["schema_json"], result["name"], result["site"]]
        processed_results.append(processed_result)
    
    return processed_results

async def retrieve_item_with_url(url, top_n=1):
    """
    Retrieve records by exact URL match
    
    Args:
        url (str): URL to find
        top_n (int, optional): Maximum number of matching results to return. Defaults to 1.
        
    Returns:
        list: Single search result or None if not found
    """
    search_client = get_search_client()
    
    # Create the search options with URL filter
    search_options = {
        "filter": f"url eq '{url}'",
        "top": top_n,
        "select": "url,name,site,schema_json"
    }
    
    # Execute the search asynchronously
    def search_sync():
        return search_client.search(search_text=None, **search_options)
    
    results = await asyncio.get_event_loop().run_in_executor(None, search_sync)
    
    for result in results:
        return [result["url"], result["schema_json"], result["name"], result["site"]]
    return None

async def search_all_sites(query, top_n=10):
    """
    Search across all sites using vector similarity
    
    Args:
        query (str): Search query
        top_n (int, optional): Number of results to retrieve. Defaults to 10.
        
    Returns:
        list: List of search results with relevance scores
    """
    query_embedding = await get_embedding(query)
    
    # Validate embedding dimension
    if len(query_embedding) != 1536:
        raise ValueError(f"Unsupported embedding size: {len(query_embedding)}. Must be 1536.")
    
    search_client = get_search_client()
    
    # Create the search options with vector search only (no site filter)
    search_options = {
        "vector_queries": [
            {
                "kind": "vector",
                "vector": query_embedding,
                "fields": "embedding",
                "k": top_n
            }
        ],
        "top": top_n,
        "select": "url,name,site,schema_json"
    }
    
    # Execute the search asynchronously
    def search_sync():
        return search_client.search(search_text=None, **search_options)
    
    results = await asyncio.get_event_loop().run_in_executor(None, search_sync)
    
    # Process results into a more convenient format
    processed_results = []
    for result in results:
        processed_result = [result["url"], result["schema_json"], result["name"], result["site"]]
        processed_results.append(processed_result)
    
    return processed_results
