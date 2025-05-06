# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
This file is used to retrieve items from a local Milvus database.

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.
"""

from pymilvus import MilvusClient
import json
from llm.llm import get_embedding
import asyncio
import threading
from config.config import CONFIG
from utils.logging_config_helper import get_configured_logger
from utils.logger import LogLevel

logger = get_configured_logger("milvus_retrieve")

_client_lock = threading.Lock()

# Add a dict to store clients by endpoint
milvus_clients = {}

def initialize(endpoint_name=None):
    global milvus_clients
    endpoint_name = endpoint_name or CONFIG.preferred_retrieval_endpoint
    
    with _client_lock:
        if endpoint_name not in milvus_clients:
            logger.info(f"Initializing Milvus client for endpoint: {endpoint_name}")
            try:
                endpoint_config = CONFIG.retrieval_endpoints[endpoint_name]
                database_path = endpoint_config.database_path
                if database_path is None:
                    error_msg = f"database_path is not set for endpoint: {endpoint_name}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                milvus_clients[endpoint_name] = MilvusClient(database_path)
                logger.info(f"Successfully initialized Milvus client for {endpoint_name} at {database_path}")
                
                # Test search
                logger.debug("Performing test search to verify connection")
                search_db("test", "all", 10, endpoint_name)
            except Exception as e:
                logger.exception(f"Failed to initialize Milvus client for endpoint {endpoint_name}")
                raise

def get_milvus_client(endpoint_name=None):
    endpoint_name = endpoint_name or CONFIG.preferred_retrieval_endpoint
    if endpoint_name not in milvus_clients:
        logger.debug(f"Client not found for {endpoint_name}, initializing")
        initialize(endpoint_name)
    return milvus_clients[endpoint_name]

def get_collection_name(site, endpoint_name=None, query_params=None):
    endpoint_name = endpoint_name or CONFIG.preferred_retrieval_endpoint
    endpoint_config = CONFIG.retrieval_endpoints[endpoint_name]
    index_name = endpoint_config.index_name
    if index_name is None:
        logger.debug(f"No index_name configured for {endpoint_name}, using default 'prod_collection'")
        return "prod_collection"
    else:
        logger.debug(f"Using collection name: {index_name}")
        return index_name

async def search_db(query, site, num_results=50, endpoint_name=None, query_params=None):
    endpoint_name = endpoint_name or CONFIG.preferred_retrieval_endpoint
    logger.info(f"Starting Milvus search - endpoint: {endpoint_name}, site: {site}, num_results: {num_results}")
    logger.debug(f"Query: {query}")
    
    try:
        embedding = await get_embedding(query)
        logger.debug(f"Generated embedding with dimension: {len(embedding)}")
        
        results = await asyncio.get_event_loop().run_in_executor(
            None, _search_db_sync, query, site, num_results, embedding, endpoint_name, query_params
        )
        
        logger.info(f"Milvus search completed successfully, found {len(results)} results")
        return results
    
    except Exception as e:
        logger.exception(f"Error in Milvus search_db")
        logger.log_with_context(
            LogLevel.ERROR,
            "Milvus search failed",
            {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "endpoint": endpoint_name,
                "site": site,
                "query_length": len(query)
            }
        )
        raise

def _search_db_sync(query, site, num_results, embedding, endpoint_name, query_params):
    """Synchronous version for thread execution"""
    logger.debug(f"Executing synchronous search - site: {site}, num_results: {num_results}")
    
    try:
        client = get_milvus_client(endpoint_name)
        collection = get_collection_name(site, endpoint_name, query_params)
        
        # Rest of the function remains the same...
        if site == "all":
            logger.debug(f"Searching all sites in collection: {collection}")
            res = client.search(
                collection_name=collection,
                data=[embedding],
                limit=num_results,
                output_fields=["url", "text", "name", "site"],
            )
        elif isinstance(site, list):
            site_filter = " || ".join([f"site == '{s}'" for s in site])
            logger.debug(f"Searching sites: {site} with filter: {site_filter}")
            res = client.search(
                collection_name=collection, 
                data=[embedding],
                filter=site_filter,
                limit=num_results,
                output_fields=["url", "text", "name", "site"],
            )
        else:
            logger.debug(f"Searching site: {site} in collection: {collection}")
            res = client.search(
                collection_name=collection,
                data=[embedding],
                filter=f"site == '{site}'",
                limit=num_results,
                output_fields=["url", "text", "name", "site"],
            )

        retval = []
        for item in res[0]:
            ent = item["entity"]
            txt = json.dumps(ent["text"])
            retval.append([ent["url"], txt, ent["name"], ent["site"]])
        
        logger.info(f"Retrieved {len(retval)} items from Milvus")
        logger.debug(f"First result URL: {retval[0][0] if retval else 'No results'}")
        return retval
    
    except Exception as e:
        logger.exception(f"Error in _search_db_sync")
        raise

def retrieve_item_with_url(url, endpoint_name=None):
    endpoint_name = endpoint_name or CONFIG.preferred_retrieval_endpoint
    logger.info(f"Retrieving item by URL: {url} from endpoint: {endpoint_name}")
    
    try:
        client = get_milvus_client(endpoint_name)
        collection = get_collection_name(None, endpoint_name)  # Pass None for site since it's not used here
        
        logger.debug(f"Querying collection: {collection} for URL: {url}")
        res = client.query(
            collection_name=collection,
            filter=f"url == '{url}'",
            limit=1,
            output_fields=["url", "text", "name", "site"],
        )
        if len(res) == 0:
            logger.warning(f"No item found for URL: {url}")
            return None
        
        logger.info(f"Successfully retrieved item for URL: {url}")
        return res[0]
    
    except Exception as e:
        logger.exception(f"Error retrieving item with URL: {url}")
        logger.log_with_context(
            LogLevel.ERROR,
            "Milvus item retrieval failed",
            {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "url": url,
                "endpoint": endpoint_name
            }
        )
        raise

