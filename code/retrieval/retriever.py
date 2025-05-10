# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
This file contains the base class for all handlers. 
Currently supports azure_ai_search, milvus, and qdrant.

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.

"""

import retrieval.milvus_retrieve as milvus_retrieve
import retrieval.azure_retrieve as azure_retrieve
import retrieval.snowflake_retrieve as snowflake_retrieve
import retrieval.qdrant_retrieve as qdrant_retrieve

import time
import asyncio
from config.config import CONFIG
from utils.utils import get_param
from utils.logging_config_helper import get_configured_logger
from utils.logger import LogLevel

logger = get_configured_logger("retriever")

class DBQueryRetriever:
    def __init__(self, query, handler):
        # Get default endpoint from config
        default_endpoint = CONFIG.preferred_retrieval_endpoint
        self.endpoint_name = default_endpoint
        
        # In development mode, allow query param override
        if CONFIG.is_development_mode():
            self.endpoint_name = get_param(handler.query_params, "db", str, default_endpoint)
            logger.debug(f"Development mode: endpoint overridden to {self.endpoint_name}")
        
        # Validate endpoint exists in config
        if self.endpoint_name not in CONFIG.retrieval_endpoints:
            error_msg = f"Invalid endpoint: {self.endpoint_name}. Must be one of: {list(CONFIG.retrieval_endpoints.keys())}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Get endpoint config and extract db_type
        self.endpoint_config = CONFIG.retrieval_endpoints[self.endpoint_name]
        self.db_type = self.endpoint_config.db_type
        
        self.db_query = query
        self.handler = handler
        self.query_params = handler.query_params
        self._retrieval_lock = asyncio.Lock()
        
        logger.info(f"DBQueryRetriever initialized - endpoint: {self.endpoint_name}, db_type: {self.db_type}")

    async def search_db(self, query, site, num_results=50):
        async with self._retrieval_lock:
            logger.info(f"Starting database search with query: '{query[:100]}...'")
            start_time = time.time()
            sites = []
            if (site.find(',') != -1):
                site = site.replace('[', '').replace(']', '')
                items = site.split(',')
                for item in items:
                    sites.append(item.strip())
            else:
                sites.append(site.replace(" ", "_"))
            site = site.replace(" ", "_")
            
            logger.log_with_context(
                LogLevel.INFO,
                "Executing search",
                {
                    "query": query[:50] + "..." if len(query) > 50 else query,
                    "site": site,
                    "endpoint": self.endpoint_name,
                    "db_type": self.db_type,
                    "num_results": num_results
                }
            )
            
            try:
                if self.db_type == "milvus":
                    logger.debug("Routing search to Milvus retriever")
                    results = await milvus_retrieve.search_db(query, site, num_results, self.endpoint_name, self.query_params)
                elif self.db_type == "azure_ai_search":
                    logger.debug("Routing search to Azure AI Search retriever")
                    if site == "all" or site == "nlws":
                        results = await azure_retrieve.search_all_sites(query, num_results, self.endpoint_name, self.query_params)
                    else:
                        results = await azure_retrieve.search_db(query, site, num_results, self.endpoint_name, self.query_params)
                elif self.db_type == "snowflake_cortex_search":
                    logger.debug(f"Routing search to Snowflake Cortex Search retriever {query} {site} {num_results}")
                    results = await snowflake_retrieve.search_db(query, site, num_results)
                elif self.db_type == "qdrant":
                    logger.debug("Routing search to Qdrant retriever")
                    results = await qdrant_retrieve.search_db(query, site, num_results, self.endpoint_name, self.query_params)
                else:
                    error_msg = f"Invalid database type: {self.db_type}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            except Exception as e:
                logger.exception(f"Error in search_db: {e}")
                logger.log_with_context(
                    LogLevel.ERROR,
                    "Search failed",
                    {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "db_type": self.db_type,
                        "endpoint": self.endpoint_name
                    }
                )
                raise
            
            end_time = time.time()
            search_duration = end_time - start_time
            
            logger.log_with_context(
                LogLevel.INFO,
                "Search completed",
                {
                    "duration": f"{search_duration:.2f}s",
                    "results_count": len(results),
                    "db_type": self.db_type
                }
            )
            return results
        
    async def do(self):
        results = await self.search_db(self.db_query, self.handler.site, 50)
        self.handler.retrieved_items = results
        self.handler.state.retrieval_done = True
        return results


class DBItemRetriever:
    def __init__(self, handler, db_endpoint=None):
        self.handler = handler
        # Use default endpoint if not specified
        self.endpoint_name = db_endpoint or CONFIG.preferred_retrieval_endpoint
        
        # In development mode, allow query param override
        if CONFIG.is_development_mode() and handler.query_params:
            self.endpoint_name = get_param(handler.query_params, "db", str, self.endpoint_name)
            logger.debug(f"Development mode: endpoint overridden to {self.endpoint_name}")
        
        # Validate endpoint exists in config
        if self.endpoint_name not in CONFIG.retrieval_endpoints:
            error_msg = f"Invalid endpoint: {self.endpoint_name}. Must be one of: {list(CONFIG.retrieval_endpoints.keys())}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Get endpoint config and extract db_type
        self.endpoint_config = CONFIG.retrieval_endpoints[self.endpoint_name]
        self.db_type = self.endpoint_config.db_type
        self._retrieval_lock = asyncio.Lock()
        
        logger.info(f"DBItemRetriever initialized - endpoint: {self.endpoint_name}, db_type: {self.db_type}")

    async def retrieve_item_with_url(self, url):
        async with self._retrieval_lock:
            logger.info(f"Retrieving item with URL: {url}")
            try:
                if self.db_type == "milvus":
                    logger.debug("Routing to Milvus item retrieval")
                    result = await asyncio.to_thread(milvus_retrieve.retrieve_item_with_url, url, self.endpoint_name)
                elif self.db_type == "azure_ai_search":
                    logger.debug("Routing to Azure AI Search item retrieval")
                    result = await azure_retrieve.retrieve_item_with_url(url, self.endpoint_name)
                elif self.db_type == "snowflake_cortex_search":
                    logger.debug("Routing to Snowflake Cortex Search item retrieval")
                    result = await snowflake_retrieve.retrieve_item_with_url(url)
                elif self.db_type == "qdrant":
                    logger.debug("Routing to Qdrant item retrieval")
                    result = await qdrant_retrieve.retrieve_item_with_url(url, self.endpoint_name)
                else:
                    error_msg = f"Invalid database type: {self.db_type}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                if result:
                    logger.debug(f"Successfully retrieved item for URL: {url}")
                else:
                    logger.warning(f"No item found for URL: {url}")
                
                return result
            except Exception as e:
                logger.exception(f"Error in retrieve_item_with_url: {e}")
                logger.log_with_context(
                    LogLevel.ERROR,
                    "Item retrieval failed",
                    {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "url": url,
                        "db_type": self.db_type,
                        "endpoint": self.endpoint_name
                    }
                )
                raise
            
