# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""

Unified vector database interface with support for Azure AI Search, Milvus, and Qdrant.
This module provides abstract base classes and concrete implementations for database operations.

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.

"""

import retrieval.milvus_retrieve as milvus_retrieve
import retrieval.azure_retrieve as azure_retrieve
import retrieval.snowflake_retrieve as snowflake_retrieve
import retrieval.qdrant_retrieve as qdrant_retrieve

                client = await self.get_client()
                count = await client.delete_documents_by_site(site, **kwargs)
                logger.info(f"Successfully deleted {count} documents for site: {site}")
                return count

                client = await self.get_client()
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
        # If endpoint is specified, create a new client for that endpoint
        if endpoint_name and endpoint_name != self.endpoint_name:
            temp_client = VectorDBClient(endpoint_name=endpoint_name)
            return await temp_client.search_all_sites(query, num_results, **kwargs)
        
        async with self._retrieval_lock:
            logger.info(f"Searching across all sites for '{query[:50]}...', num_results: {num_results}")
            start_time = time.time()
            
            try:
                client = await self.get_client()
                results = await client.search_all_sites(query, num_results, **kwargs)
                
                end_time = time.time()
                search_duration = end_time - start_time
                
                logger.log_with_context(
                    LogLevel.INFO,
                    "All-sites search completed",
                    {
                        "duration": f"{search_duration:.2f}s",
                        "results_count": len(results),
                        "db_type": self.db_type
                    }
                )
                return results
            except Exception as e:
                logger.exception(f"Error in search_all_sites: {e}")
                logger.log_with_context(
                    LogLevel.ERROR,
                    "All-sites search failed",
                    {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "query": query[:50] + "..." if len(query) > 50 else query,
                        "db_type": self.db_type,
                        "endpoint": self.endpoint_name
                    }
                )
                raise


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
