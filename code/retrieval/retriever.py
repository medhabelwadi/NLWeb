# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
Unified vector database interface with support for Azure AI Search, Milvus, and Qdrant.
This module provides abstract base classes and concrete implementations for database operations.
"""

import time
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, Tuple, Type
import json

from config.config import CONFIG
from utils.utils import get_param
from utils.logging_config_helper import get_configured_logger
from utils.logger import LogLevel
from utils.json_utils import merge_json_array

# Import client classes
from retrieval.azure_search_client import AzureSearchClient
from retrieval.milvus_client import MilvusVectorClient
from retrieval.opensearch_client import OpenSearchClient
from retrieval.qdrant import QdrantVectorClient
from retrieval.snowflake_client import SnowflakeCortexSearchClient

logger = get_configured_logger("retriever")

# Client cache for reusing instances
_client_cache = {}
_client_cache_lock = asyncio.Lock()


class VectorDBClientInterface(ABC):
    """
    Abstract base class defining the interface for vector database clients.
    All vector database implementations should implement these methods.
    """
    
    @abstractmethod
    async def delete_documents_by_site(self, site: str, **kwargs) -> int:
        """
        Delete all documents matching the specified site.
        
        Args:
            site: Site identifier
            **kwargs: Additional parameters
            
        Returns:
            Number of documents deleted
        """
        pass
    
    @abstractmethod
    async def upload_documents(self, documents: List[Dict[str, Any]], **kwargs) -> int:
        """
        Upload documents to the database.
        
        Args:
            documents: List of document objects
            **kwargs: Additional parameters
            
        Returns:
            Number of documents uploaded
        """
        pass
    
    @abstractmethod
    async def search(self, query: str, site: Union[str, List[str]], 
                    num_results: int = 50, **kwargs) -> List[List[str]]:
        """
        Search for documents matching the query and site.
        
        Args:
            query: Search query string
            site: Site identifier or list of sites
            num_results: Maximum number of results to return
            **kwargs: Additional parameters
            
        Returns:
            List of search results
        """
        pass
    
    @abstractmethod
    async def search_by_url(self, url: str, **kwargs) -> Optional[List[str]]:
        """
        Retrieve a document by its exact URL.
        
        Args:
            url: URL to search for
            **kwargs: Additional parameters
            
        Returns:
            Document data or None if not found
        """
        pass
    
    @abstractmethod
    async def search_all_sites(self, query: str, num_results: int = 50, **kwargs) -> List[List[str]]:
        """
        Search across all sites.
        
        Args:
            query: Search query string
            num_results: Maximum number of results to return
            **kwargs: Additional parameters
            
        Returns:
            List of search results
        """
        pass
    
    async def get_sites(self, **kwargs) -> Optional[List[str]]:
        """
        Get list of all sites available in the database.
        
        Args:
            **kwargs: Additional parameters
            
        Returns:
            List of site names if supported, None if not supported by this backend.
            
        Note:
            Backends that don't support this method should return None.
            The default implementation returns None.
        """
        return None


class VectorDBClient:
    """
    Unified client for vector database operations. This class routes operations to the appropriate
    client implementation based on the database type specified in configuration.
    """
    
    def __init__(self, endpoint_name: Optional[str] = None, query_params: Optional[Dict[str, Any]] = None):
        """
        Initialize the database client.
        
        Args:
            endpoint_name: Optional name of the endpoint to use (for backward compatibility)
            query_params: Optional query parameters for overriding endpoint
        """
        self.query_params = query_params or {}
        self.endpoint_name = endpoint_name  # Store the endpoint name
        self.db_type = None  # Will be set based on the primary endpoint
        
        # If specific endpoint requested, validate and use it
        if endpoint_name:
            if endpoint_name not in CONFIG.retrieval_endpoints:
                error_msg = f"Invalid endpoint: {endpoint_name}. Must be one of: {list(CONFIG.retrieval_endpoints.keys())}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # For backward compatibility, use only the specified endpoint
            endpoint_config = CONFIG.retrieval_endpoints[endpoint_name]
            self.enabled_endpoints = {endpoint_name: endpoint_config}
            self.db_type = endpoint_config.db_type  # Set db_type from the endpoint
            logger.info(f"VectorDBClient initialized with specific endpoint: {endpoint_name}")
        else:
            # Get all enabled endpoints and validate they have required credentials
            self.enabled_endpoints = {}
            for name, config in CONFIG.retrieval_endpoints.items():
                if not config.enabled:
                    continue
                    
                # Check if endpoint has required credentials based on db_type
                if self._has_valid_credentials(name, config):
                    self.enabled_endpoints[name] = config
                else:
                    logger.warning(f"Endpoint {name} is enabled but missing required credentials, skipping")
            
            if not self.enabled_endpoints:
                error_msg = "No enabled retrieval endpoints with valid credentials found"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Set db_type to the first enabled endpoint's type (for logging)
            if self.enabled_endpoints:
                first_endpoint = next(iter(self.enabled_endpoints.values()))
                self.db_type = first_endpoint.db_type
            
            logger.info(f"VectorDBClient initialized with {len(self.enabled_endpoints)} enabled endpoints: {list(self.enabled_endpoints.keys())}")
        
        # Validate write endpoint if configured
        self.write_endpoint = CONFIG.write_endpoint
        if self.write_endpoint:
            if self.write_endpoint not in CONFIG.retrieval_endpoints:
                raise ValueError(f"Write endpoint '{self.write_endpoint}' not found in configuration")
            
            write_config = CONFIG.retrieval_endpoints[self.write_endpoint]
            if not self._has_valid_credentials(self.write_endpoint, write_config):
                raise ValueError(f"Write endpoint '{self.write_endpoint}' is missing required credentials")
            
            logger.info(f"Write operations will use endpoint: {self.write_endpoint}")
        else:
            logger.warning("No write endpoint configured - write operations will fail")
        
        self._retrieval_lock = asyncio.Lock()
        
        # Cache for endpoint sites - will be populated lazily
        self._endpoint_sites_cache: Dict[str, Optional[List[str]]] = {}
    
    async def _get_endpoint_sites(self, endpoint_name: str) -> Optional[List[str]]:
        """
        Get the list of sites available in an endpoint, with caching.
        
        Args:
            endpoint_name: Name of the endpoint
            
        Returns:
            List of site names if supported, None if not supported by this backend.
        """
        # Return cached value if available
        if endpoint_name in self._endpoint_sites_cache:
            return self._endpoint_sites_cache[endpoint_name]
        
        try:
            client = await self.get_client(endpoint_name)
            sites = await client.get_sites()
            self._endpoint_sites_cache[endpoint_name] = sites
            logger.info(f"Endpoint {endpoint_name} has {len(sites)} sites: {sites[:5]}{'...' if len(sites) > 5 else ''}")
            return sites
        except Exception as e:
            # Any error means the backend doesn't support get_sites or it failed
            logger.info(f"Backend for endpoint {endpoint_name} does not support get_sites() or it failed: {e}")
            # Cache None to indicate unsupported
            self._endpoint_sites_cache[endpoint_name] = None
            return None
    
    async def _endpoint_has_site(self, endpoint_name: str, site: Union[str, List[str]]) -> bool:
        """
        Check if an endpoint has data for the requested site(s).
        
        If the backend doesn't support get_sites, we assume it might have the site.
        
        Args:
            endpoint_name: Name of the endpoint
            site: Site name or list of site names to check
            
        Returns:
            True if endpoint has data for at least one of the requested sites
        """
        # Handle 'all' case - endpoint should be queried for all sites
        if site == "all":
            return True
            
        endpoint_sites = await self._get_endpoint_sites(endpoint_name)
        if endpoint_sites is None:
            # Backend doesn't support get_sites, assume it might have the site
            return True
        elif not endpoint_sites:
            # Backend supports get_sites but returned empty list
            return False
        
        # Convert site to list for uniform handling
        if isinstance(site, str):
            sites_to_check = [site]
        else:
            sites_to_check = site
        
        # Check if any requested site is available in the endpoint
        for site_name in sites_to_check:
            if site_name in endpoint_sites:
                return True
        
        return False
    
    def _has_valid_credentials(self, name: str, config) -> bool:
        """
        Check if an endpoint has valid credentials based on its database type.
        
        Args:
            name: Endpoint name
            config: Endpoint configuration
            
        Returns:
            True if endpoint has required credentials
        """
        db_type = config.db_type
        
        if db_type in ["azure_ai_search", "snowflake_cortex_search"]:
            # These require API key and endpoint
            return bool(config.api_key and config.api_endpoint)
        elif db_type == "opensearch":
            # OpenSearch requires endpoint and credentials (api_key)
            return bool(config.api_endpoint and config.api_key)
        elif db_type == "qdrant":
            # Qdrant can use either local path or remote URL
            if config.database_path:
                return True  # Local file-based storage
            else:
                return bool(config.api_endpoint)  # Remote server (api_key is optional)
        elif db_type == "milvus":
            # Milvus requires database path
            return bool(config.database_path)
        else:
            logger.warning(f"Unknown database type {db_type} for endpoint {name}")
            return False
    
    async def get_client(self, endpoint_name: str) -> VectorDBClientInterface:
        """
        Get or initialize the appropriate vector database client for a specific endpoint.
        Uses a cache to avoid creating duplicate client instances.
        
        Args:
            endpoint_name: Name of the endpoint to get client for
            
        Returns:
            Appropriate vector database client
        """
        if endpoint_name not in self.enabled_endpoints:
            raise ValueError(f"Endpoint {endpoint_name} is not in enabled endpoints")
            
        config = self.enabled_endpoints[endpoint_name]
        db_type = config.db_type
        
        # Use cache key combining db_type and endpoint
        cache_key = f"{db_type}_{endpoint_name}"
        
        # Check if client already exists in cache
        async with _client_cache_lock:
            if cache_key in _client_cache:
                return _client_cache[cache_key]
            
            # Create the appropriate client
            logger.debug(f"Creating new client for {db_type} with endpoint {endpoint_name}")
            
            if db_type == "azure_ai_search":
                client = AzureSearchClient(endpoint_name)
            elif db_type == "milvus":
                client = MilvusVectorClient(endpoint_name)
            elif db_type == "opensearch":
                client = OpenSearchClient(endpoint_name)
            elif db_type == "qdrant":
                client = QdrantVectorClient(endpoint_name)
            elif db_type == "snowflake_cortex_search":
                client = SnowflakeCortexSearchClient(endpoint_name)
            else:
                error_msg = f"Unsupported database type: {db_type}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Store in cache and return
            _client_cache[cache_key] = client
            return client
    
    def _deduplicate_by_url(self, results: List[List[str]]) -> List[List[str]]:
        """
        Deduplicate search results by URL, keeping the entry with longer content.
        
        Args:
            results: List of search results from multiple endpoints
            
        Returns:
            Deduplicated list of results
        """
        url_to_result = {}
        
        for result in results:
            # Assuming result format is [url, title, content, ...]
            if len(result) >= 3:
                url = result[0]
                content = result[2] if len(result) > 2 else ""
                
                # If URL not seen before or current content is longer, keep it
                if url not in url_to_result or len(content) > len(url_to_result[url][2]):
                    url_to_result[url] = result
        
        # Return deduplicated results
        return list(url_to_result.values())
    
    def _aggregate_results(self, endpoint_results: Dict[str, List[List[str]]]) -> List[List[str]]:
        """
        Aggregate results from multiple endpoints, merging JSON data for duplicate URLs.
        
        When the same URL appears in multiple endpoints, the JSON data (second element)
        from each source is merged into a single array.
        
        Args:
            endpoint_results: Dictionary mapping endpoint names to their results
            
        Returns:
            Aggregated results with merged JSON for duplicate URLs
        """
        # Dictionary to store aggregated data by URL
        # Format: {url: {"result": [url, json_array, name, site], "sources": [json1, json2...]}}
        url_to_data = {}
        
        # First pass: collect all results and group by URL
        for endpoint_name, results in endpoint_results.items():
            if results:
                logger.debug(f"Got {len(results)} results from {endpoint_name}")
                
                for result in results:
                    if len(result) >= 4:  # Ensure we have [url, json, name, site]
                        url = result[0]
                        json_data = result[1]
                        name = result[2]
                        site = result[3]
                        
                        if url not in url_to_data:
                            # First occurrence of this URL
                            url_to_data[url] = {
                                "url": url,
                                "json_list": [json_data] if json_data else [],
                                "name": name,
                                "site": site,
                                "first_endpoint": endpoint_name
                            }
                        else:
                            # URL already seen, append JSON data
                            if json_data:
                                url_to_data[url]["json_list"].append(json_data)
        
        # Second pass: build final results maintaining order from first endpoint
        # We'll interleave to preserve relevance ordering
        final_results = []
        seen_urls = set()
        
        # Create iterators for each endpoint's results
        iterators = {}
        for endpoint_name, results in endpoint_results.items():
            if results:
                iterators[endpoint_name] = iter(results)
        
        # Interleave results to maintain relevance ordering
        while iterators:
            endpoints_to_remove = []
            
            for endpoint_name, iterator in iterators.items():
                try:
                    result = next(iterator)
                    if len(result) >= 1:
                        url = result[0]
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            # Get the aggregated data for this URL
                            data = url_to_data.get(url)
                            if data:
                                # Merge JSON data if multiple sources
                                json_list = data["json_list"]
                                if len(json_list) > 1:
                                    # Multiple sources - merge them
                                    merged_json = merge_json_array(json_list)
                                    # Convert back to JSON string
                                    merged_json_str = json.dumps(merged_json)
                                else:
                                    # Single source - use as is
                                    merged_json_str = json_list[0] if json_list else "{}"
                                
                                # Create result with merged JSON
                                merged_result = [
                                    data["url"],
                                    merged_json_str,  # Single merged JSON string
                                    data["name"],
                                    data["site"]
                                ]
                                final_results.append(merged_result)
                except StopIteration:
                    endpoints_to_remove.append(endpoint_name)
            
            # Remove exhausted iterators
            for endpoint in endpoints_to_remove:
                del iterators[endpoint]
        
        logger.info(f"Aggregated {sum(len(r) for r in endpoint_results.values())} total results into {len(final_results)} unique URLs")
        
        return final_results
    
    async def delete_documents_by_site(self, site: str, **kwargs) -> int:
        """
        Delete all documents matching the specified site.
        
        Args:
            site: Site identifier
            **kwargs: Additional parameters
            
        Returns:
            Number of documents deleted
        """
        if not self.write_endpoint:
            raise ValueError("No write endpoint configured for delete operations")
            
        async with self._retrieval_lock:
            logger.info(f"Deleting documents for site: {site} using write endpoint: {self.write_endpoint}")
            
            try:
                client = await self.get_client(self.write_endpoint)
                count = await client.delete_documents_by_site(site, **kwargs)
                logger.info(f"Successfully deleted {count} documents for site: {site}")
                return count
            except Exception as e:
                logger.exception(f"Error deleting documents for site {site}: {e}")
                logger.log_with_context(
                    LogLevel.ERROR,
                    "Document deletion failed",
                    {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "site": site,
                        "endpoint": self.write_endpoint
                    }
                )
                raise
    
    async def upload_documents(self, documents: List[Dict[str, Any]], **kwargs) -> int:
        """
        Upload documents to the database.
        
        Args:
            documents: List of document objects
            **kwargs: Additional parameters
            
        Returns:
            Number of documents uploaded
        """
        if not self.write_endpoint:
            raise ValueError("No write endpoint configured for upload operations")
            
        async with self._retrieval_lock:
            logger.info(f"Uploading {len(documents)} documents to write endpoint: {self.write_endpoint}")
            
            try:
                client = await self.get_client(self.write_endpoint)
                count = await client.upload_documents(documents, **kwargs)
                logger.info(f"Successfully uploaded {count} documents")
                return count
            except Exception as e:
                logger.exception(f"Error uploading documents: {e}")
                logger.log_with_context(
                    LogLevel.ERROR,
                    "Document upload failed",
                    {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "document_count": len(documents),
                        "endpoint": self.write_endpoint
                    }
                )
                raise
    
    async def search(self, query: str, site: Union[str, List[str]], 
                    num_results: int = 50, endpoint_name: Optional[str] = None, **kwargs) -> List[List[str]]:
        """
        Search for documents matching the query and site.
        
        Args:
            query: Search query string
            site: Site identifier or list of sites
            num_results: Maximum number of results to return
            endpoint_name: Optional endpoint name override
            **kwargs: Additional parameters
            
        Returns:
            List of search results
        """
        # Handle configured sites
        if site == "all":
            sites = CONFIG.nlweb.sites
            if sites and sites != "all":
                # Use configured sites instead of "all"
                site = sites

        # If specific endpoint is requested, use only that endpoint
        if endpoint_name:
            if endpoint_name not in CONFIG.retrieval_endpoints:
                raise ValueError(f"Invalid endpoint: {endpoint_name}")
            temp_client = VectorDBClient(endpoint_name=endpoint_name)
            return await temp_client.search(query, site, num_results, **kwargs)
        
        # Process site parameter for consistency
        if isinstance(site, str) and ',' in site:
            site = site.replace('[', '').replace(']', '')
            site = [s.strip() for s in site.split(',')]
        elif isinstance(site, str):
            site = site.replace(" ", "_")

        async with self._retrieval_lock:
            logger.info(f"Searching for '{query[:50]}...' in site: {site}, num_results: {num_results}")
            logger.info(f"Querying {len(self.enabled_endpoints)} enabled endpoints in parallel")
            start_time = time.time()
            
            # Create tasks for parallel queries to endpoints that have the requested site
            tasks = []
            endpoint_names = []
            skipped_endpoints = []
            
            for endpoint_name in self.enabled_endpoints:
                try:
                    # Check if endpoint has data for the requested site
                    if not await self._endpoint_has_site(endpoint_name, site):
                        skipped_endpoints.append(endpoint_name)
                        continue
                    
                    client = await self.get_client(endpoint_name)
                    # Use search_all_sites if site is "all"
                    if site == "all":
                        task = asyncio.create_task(client.search_all_sites(query, num_results, **kwargs))
                    else:
                        task = asyncio.create_task(client.search(query, site, num_results, **kwargs))
                    tasks.append(task)
                    endpoint_names.append(endpoint_name)
                except Exception as e:
                    logger.warning(f"Failed to create search task for endpoint {endpoint_name}: {e}")
            
            if skipped_endpoints:
                logger.debug(f"Skipped endpoints without site '{site}': {skipped_endpoints}")
            
            if not tasks:
                raise ValueError("No valid endpoints available for search")
            
            # Execute all searches in parallel and collect results
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and handle failures gracefully
            endpoint_results = {}
            successful_endpoints = 0
            
            for endpoint_name, result in zip(endpoint_names, results):
                if isinstance(result, Exception):
                    logger.warning(f"Search failed for endpoint {endpoint_name}: {result}")
                else:
                    endpoint_results[endpoint_name] = result
                    successful_endpoints += 1
            
            if successful_endpoints == 0:
                raise ValueError("All endpoint searches failed")
            
            # Aggregate and deduplicate results
            final_results = self._aggregate_results(endpoint_results)
            
            # Limit to requested number of results
            # Results are already in relevance order from aggregation
            final_results = final_results[:num_results]
            
            end_time = time.time()
            search_duration = end_time - start_time
            
            logger.log_with_context(
                LogLevel.INFO,
                "Parallel search completed",
                {
                    "duration": f"{search_duration:.2f}s",
                    "endpoints_queried": len(tasks),
                    "endpoints_succeeded": successful_endpoints,
                    "total_results": len(final_results),
                    "site": site
                }
            )
            
            return final_results
    
    async def search_by_url(self, url: str, endpoint_name: Optional[str] = None, **kwargs) -> Optional[List[str]]:
        """
        Retrieve a document by its exact URL.
        
        Args:
            url: URL to search for
            endpoint_name: Optional endpoint name override
            **kwargs: Additional parameters
            
        Returns:
            Document data or None if not found
        """
        # If endpoint is specified and different from current, create a new client for that endpoint
        if endpoint_name and endpoint_name != self.endpoint_name:
            temp_client = VectorDBClient(endpoint_name=endpoint_name)
            return await temp_client.search_by_url(url, **kwargs)
        
        async with self._retrieval_lock:
            logger.info(f"Retrieving item with URL: {url}")
            
            try:
                # For single endpoint mode, use the first (and only) endpoint
                if self.endpoint_name:
                    client = await self.get_client(self.endpoint_name)
                else:
                    # Multiple endpoints - need to search all of them
                    for endpoint_name in self.enabled_endpoints:
                        try:
                            client = await self.get_client(endpoint_name)
                            result = await client.search_by_url(url, **kwargs)
                            if result:
                                return result
                        except Exception as e:
                            logger.warning(f"Failed to search by URL in endpoint {endpoint_name}: {e}")
                    return None
                
                result = await client.search_by_url(url, **kwargs)
                
                if result:
                    logger.debug(f"Successfully retrieved item for URL: {url}")
                else:
                    logger.warning(f"No item found for URL: {url}")
                
                return result
            except Exception as e:
                logger.exception(f"Error retrieving item with URL: {url}")
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
    
    async def search_all_sites(self, query: str, num_results: int = 50, 
                             endpoint_name: Optional[str] = None, **kwargs) -> List[List[str]]:
        """
        Search across all sites.
        
        Args:
            query: Search query string
            num_results: Maximum number of results to return
            endpoint_name: Optional endpoint name override
            **kwargs: Additional parameters
            
        Returns:
            List of search results
        """
        # Just call search with "all" as the site parameter
        # The individual clients will handle "all" appropriately
        return await self.search(query, "all", num_results, endpoint_name, **kwargs)
    
    async def get_sites(self, endpoint_name: Optional[str] = None, **kwargs) -> List[str]:
        """
        Get list of all sites available in the database.
        
        For backends that don't support get_sites, returns an empty list to indicate
        that the backend should be queried for all sites.
        
        Args:
            endpoint_name: Optional endpoint name override
            **kwargs: Additional parameters
            
        Returns:
            List of site names, or empty list if backend doesn't support get_sites
        """
        # If endpoint is specified and different from current, create a new client for that endpoint
        if endpoint_name and endpoint_name != self.endpoint_name:
            temp_client = VectorDBClient(endpoint_name=endpoint_name)
            return await temp_client.get_sites(**kwargs)
        
        async with self._retrieval_lock:
            logger.info("Retrieving list of sites from database")
            
            try:
                # For single endpoint mode, use the first (and only) endpoint
                if self.endpoint_name:
                    client = await self.get_client(self.endpoint_name)
                    sites = await client.get_sites(**kwargs)
                else:
                    # Multiple endpoints - aggregate sites from all
                    all_sites = set()
                    for endpoint_name in self.enabled_endpoints:
                        try:
                            client = await self.get_client(endpoint_name)
                            endpoint_sites = await client.get_sites(**kwargs)
                            if endpoint_sites:  # Not None and not empty
                                all_sites.update(endpoint_sites)
                        except Exception as e:
                            logger.warning(f"Failed to get sites from endpoint {endpoint_name}: {e}")
                    sites = list(all_sites)
                
                # If backend doesn't support get_sites, it should return None
                if sites is None:
                    # Return empty list to indicate unknown sites
                    logger.info(f"Backend doesn't support get_sites, will query for all sites")
                    return []
                
                logger.log_with_context(
                    LogLevel.INFO,
                    "Sites retrieved",
                    {
                        "sites_count": len(sites),
                        "db_type": self.db_type,
                        "endpoint": self.endpoint_name
                    }
                )
                return sites
            except Exception as e:
                # Backend doesn't support get_sites or error occurred
                logger.info(f"Backend doesn't support get_sites or error occurred: {e}")
                
                # Return empty list to indicate unknown sites (will be queried for all)
                logger.log_with_context(
                    LogLevel.INFO,
                    "Backend doesn't support get_sites, will query for all sites",
                    {
                        "db_type": self.db_type,
                        "endpoint": self.endpoint_name,
                        "error": str(e)
                    }
                )
                return []


# Factory function to make it easier to get a client with the right type
def get_vector_db_client(endpoint_name: Optional[str] = None, 
                        query_params: Optional[Dict[str, Any]] = None) -> VectorDBClient:
    """
    Factory function to create a vector database client with the appropriate configuration.
    
    Args:
        endpoint_name: Optional name of the endpoint to use
        query_params: Optional query parameters for overriding endpoint
        
    Returns:
        Configured VectorDBClient instance
    """
    return VectorDBClient(endpoint_name=endpoint_name, query_params=query_params)