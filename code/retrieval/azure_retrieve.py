# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
This file is used to retrieve items from the Azure AI Search index.

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.
"""

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
import time
from utils.utils import log, siteToItemType 
from llm.llm import get_embedding
import sys
from config.config import CONFIG
import asyncio
import threading
from utils.logging_config_helper import get_configured_logger
from utils.logger import LogLevel

logger = get_configured_logger("azure_retrieve")

# Change to use multiple clients by endpoint
_client_lock = threading.Lock()
search_clients = {}

def get_azure_search_config(endpoint_name=None):
    """Get Azure AI Search configuration from config file"""
    endpoint_name = endpoint_name or CONFIG.preferred_retrieval_endpoint
    
    endpoint_config = CONFIG.retrieval_endpoints.get(endpoint_name)
    if not endpoint_config:
        error_msg = f"Endpoint '{endpoint_name}' configuration not found in config_retrieval.yaml"
        logger.error(error_msg)
        sys.exit(1)
    
    if endpoint_config.db_type != "azure_ai_search":
        error_msg = f"Endpoint '{endpoint_name}' is not an azure_ai_search endpoint"
        logger.error(error_msg)
        sys.exit(1)
    
    logger.debug(f"Retrieved Azure Search config for endpoint: {endpoint_name}")
    return endpoint_config

def get_search_client(endpoint_name=None):
    """Get the search client for the configured index"""
    global search_clients
    endpoint_name = endpoint_name or CONFIG.preferred_retrieval_endpoint
    
    with _client_lock:
        if endpoint_name not in search_clients:
            logger.debug(f"Client not found for {endpoint_name}, initializing")
            initialize_client(endpoint_name)
    return search_clients[endpoint_name]

def initialize_client(endpoint_name=None):
    """Initialize the search client"""
    global search_clients
    endpoint_name = endpoint_name or CONFIG.preferred_retrieval_endpoint
    
    logger.info(f"Initializing Azure Search client for endpoint: {endpoint_name}")
    
    azure_config = get_azure_search_config(endpoint_name)
    api_key = azure_config.api_key
    endpoint = azure_config.api_endpoint
    index_name = azure_config.index_name
    #print(f"endpoint_name: {endpoint_name}, api_key: {api_key}, endpoint: {endpoint}, index_name: {index_name}")
    if not api_key or not endpoint or not index_name:
        error_msg = f"Azure AI Search configuration incomplete for endpoint: {endpoint_name}"
        logger.error(error_msg)
        logger.log_with_context(
            LogLevel.ERROR,
            "Missing configuration",
            {
                "has_api_key": bool(api_key),
                "has_endpoint": bool(endpoint),
                "has_index_name": bool(index_name)
            }
        )
        sys.exit(1)
    
    credential = AzureKeyCredential(api_key.strip('"'))
    search_clients[endpoint_name] = SearchClient(
        endpoint=endpoint.strip('"'), 
        index_name=index_name, 
        credential=credential
    )
    logger.info(f"Successfully initialized Azure Search client for endpoint: {endpoint_name}, index: {index_name}")

async def search_db(query, site, num_results=50, endpoint_name=None, query_params=None):
    """
    Search the Azure AI Search index for records filtered by site and ranked by vector similarity
    """
    endpoint_name = endpoint_name or CONFIG.preferred_retrieval_endpoint
    logger.info(f"Starting Azure Search - endpoint: {endpoint_name}, site: {site}, num_results: {num_results}")
    logger.debug(f"Query: {query}")
    
    start_embed = time.time()
    embedding = await get_embedding(query)
    embed_time = time.time() - start_embed
    logger.debug(f"Embedding generated in {embed_time:.2f}s, dimension: {len(embedding)}")
    
    start_retrieve = time.time()
    results = await retrieve_by_site_and_vector(site, embedding, num_results, endpoint_name)
    retrieve_time = time.time() - start_retrieve
    
    logger.log_with_context(
        LogLevel.INFO,
        "Azure Search completed",
        {
            "embedding_time": f"{embed_time:.2f}s",
            "retrieval_time": f"{retrieve_time:.2f}s",
            "total_time": f"{embed_time + retrieve_time:.2f}s",
            "results_count": len(results)
        }
    )
    return results

async def retrieve_by_site_and_vector(sites, vector_embedding, top_n=10, endpoint_name=None):
    """
    Retrieve top n records filtered by site and ranked by vector similarity
    """
    endpoint_name = endpoint_name or CONFIG.preferred_retrieval_endpoint
    logger.debug(f"Retrieving by site and vector - sites: {sites}, top_n: {top_n}")
    
    # Validate embedding dimension
    if len(vector_embedding) != 1536:
        error_msg = f"Embedding dimension {len(vector_embedding)} not supported. Must be 1536."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    search_client = get_search_client(endpoint_name)
    
    # Handle both single site and multiple sites
    if isinstance(sites, str):
        sites = [sites]
    
    site_restrict = ""
    for site in sites:
        if len(site_restrict) > 0:
            site_restrict += " or "
        site_restrict += f"site eq '{site}'"
    
    logger.debug(f"Site filter: {site_restrict}")
    
    # Create the search options with vector search and filtering
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
    
    try:
        # Execute the search asynchronously
        def search_sync():
            return search_client.search(search_text=None, **search_options)
        
        results = await asyncio.get_event_loop().run_in_executor(None, search_sync)
        
        # Process results into a more convenient format
        processed_results = []
        for result in results:
            processed_result = [result["url"], result["schema_json"], result["name"], result["site"]]
            processed_results.append(processed_result)
        
        logger.debug(f"Retrieved {len(processed_results)} results")
        return processed_results
    
    except Exception as e:
        logger.exception(f"Error in retrieve_by_site_and_vector")
        logger.log_with_context(
            LogLevel.ERROR,
            "Azure Search retrieval failed",
            {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "sites": sites,
                "top_n": top_n
            }
        )
        raise

async def retrieve_item_with_url(url, endpoint_name=None, top_n=1):
    """
    Retrieve records by exact URL match
    """
    endpoint_name = endpoint_name or CONFIG.preferred_retrieval_endpoint
    logger.info(f"Retrieving item by URL: {url} from endpoint: {endpoint_name}")
    
    search_client = get_search_client(endpoint_name)
    
    # Create the search options with URL filter
    search_options = {
        "filter": f"url eq '{url}'",
        "top": top_n,
        "select": "url,name,site,schema_json"
    }
    
    try:
        # Execute the search asynchronously
        def search_sync():
            return search_client.search(search_text=None, **search_options)
        
        results = await asyncio.get_event_loop().run_in_executor(None, search_sync)
        
        for result in results:
            logger.info(f"Successfully retrieved item for URL: {url}")
            return [result["url"], result["schema_json"], result["name"], result["site"]]
        
        logger.warning(f"No item found for URL: {url}")
        return None
    
    except Exception as e:
        logger.exception(f"Error retrieving item with URL: {url}")
        logger.log_with_context(
            LogLevel.ERROR,
            "Azure item retrieval failed",
            {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "url": url,
                "endpoint": endpoint_name
            }
        )
        raise

async def search_all_sites(query, top_n=10, endpoint_name=None, query_params=None):
    """
    Search across all sites using vector similarity
    """
    endpoint_name = endpoint_name or CONFIG.preferred_retrieval_endpoint
    logger.info(f"Starting global Azure Search (all sites) - endpoint: {endpoint_name}, top_n: {top_n}")
    logger.debug(f"Query: {query}")
    
    try:
        query_embedding = await get_embedding(query)
        logger.debug(f"Generated embedding with dimension: {len(query_embedding)}")
        
        # Validate embedding dimension
        if len(query_embedding) != 1536:
            error_msg = f"Unsupported embedding size: {len(query_embedding)}. Must be 1536."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        search_client = get_search_client(endpoint_name)
        
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
        
        logger.info(f"Global search completed, found {len(processed_results)} results")
        return processed_results
    
    except Exception as e:
        logger.exception(f"Error in search_all_sites")
        logger.log_with_context(
            LogLevel.ERROR,
            "Global Azure Search failed",
            {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "query": query[:50] + "..." if len(query) > 50 else query,
                "endpoint": endpoint_name
            }
        )
        raise

