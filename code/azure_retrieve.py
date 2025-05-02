# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
This file contains the methods for retrieving items from the Azure AI Search index.

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.
"""

import json
import os
import mllm
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient    

import time
from mllm import get_configured_logger
import sys

search_clients = {}
index_names = ["embeddings1536", "embeddings3072", "embeddings1536compact"]
logger = get_configured_logger('azure_retrieve')

global_search_service_endpoint = None
def get_search_service_endpoint():
    global global_search_service_endpoint
    if (global_search_service_endpoint is None):
        global_search_service_endpoint = os.environ.get("AZURE_VECTOR_SEARCH_ENDPOINT")
    if (global_search_service_endpoint is None):
        logger.error("AZURE_VECTOR_SEARCH_ENDPOINT is not set.  Please set this environment variable and restart.")
        sys.exit(1)
    else:  
        global_search_service_endpoint = global_search_service_endpoint.strip('"')  # Adding the strip in case the env var has quotes in it
    return global_search_service_endpoint

global_search_api_key = None
def get_search_api_key():
    global global_search_api_key
    if (global_search_api_key is None):
        global_search_api_key = os.environ.get("AZURE_VECTOR_SEARCH_API_KEY")
    if (global_search_api_key is None):
        logger.error("AZURE_VECTOR_SEARCH_API_KEY is not set.  Please set this environment variable and restart.")
        sys.exit(1)
    else:    
        global_search_api_key = global_search_api_key.strip('"')  # Adding the strip in case the env var has quotes in it
    return global_search_api_key

def get_index_client(index_name):
    """Get a search client for a specific index"""
    if (index_name in search_clients):
        return search_clients[index_name]
    else:
        initialize_clients()
        return search_clients[index_name]

def initialize_clients():
    # Use provided API key or get from environment variable
    
    api_key = get_search_api_key()
    if not api_key:
        raise ValueError("API key not provided and AZURE_SEARCH_API_KEY environment variable not set")
    
    credential = AzureKeyCredential(api_key)
    # Create index client for managing indexes
    index_client = SearchIndexClient(endpoint=get_search_service_endpoint(), credential=credential)
    search_clients["index_client"] = index_client
    
    # Create search clients for document operations
    for index_name in index_names:
        search_client = SearchClient(endpoint=get_search_service_endpoint(), index_name=index_name, credential=credential)
        search_clients[index_name] = search_client

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
    embedding = await mllm.get_embedding(query)
    embed_time = time.time() - start_embed
    
    start_retrieve = time.time()
    results = await retrieve_by_site_and_vector(site, embedding, num_results)
    retrieve_time = time.time() - start_retrieve
    
    print(f"Timing - Embedding: {embed_time:.2f}s, Retrieval: {retrieve_time:.2f}s")
    return results
    

async def retrieve_by_site_and_vector(site, vector_embedding, top_n=10):
    """
    Retrieve top n records filtered by site and ranked by vector similarity
    
    Args:
        site (str): Site value to filter by
        vector_embedding (list or numpy.ndarray): Vector embedding for similarity search
        top_n (int, optional): Number of results to retrieve. Defaults to 10.
        
    Returns:
        list: List of search results with relevance scores
    """
    # Initialize the search client
    if (len(vector_embedding) == 1536):
        index_name = "embeddings1536"
        # experimenting with much more compact json. Needs more thought.
      #  if (site == "seriouseats" or site == "nytimes"):
       #     index_name = "embeddings1536compact"
    elif (len(vector_embedding) == 3072):
        index_name = "embeddings3072"
    else:
        raise ValueError(f"Embedding dimension {len(vector_embedding)} not supported. Must be 1536 or 3072.")
    
    search_client = get_index_client(index_name)
     
    # Create the search options with vector search and filtering
    search_options = {
        "filter": f"site eq '{site}'",
        "vector_queries": [
            {
                "kind": "vector",  # Add this line to specify the vector query kind
                "vector": vector_embedding,
                "fields": "embedding",
                "k": top_n
            }
        ],
        "top": top_n,
        "select": "url,name,site,schema_json"  # Specify the fields to return
    }
    
    # Execute the search
    results = search_client.search(search_text=None, **search_options)
    
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
        service_endpoint (str): Azure Search service endpoint URL
        api_key (str): API key for authentication
        index_name (str): Name of the search index
        url (str): URL to find
        top_n (int, optional): Maximum number of matching results to return. Defaults to 1.
        
    Returns:
        list: List of search results
    """
    # Initialize the search client
    search_client = get_index_client("embeddings1536")
    
    # Create the search options with URL filter
    search_options = {
        "filter": f"url eq '{url}'",
        "top": top_n,
        "select": "url,name,site,schema_json"  # Specify the fields to return
    }
    
    # Execute the search
    results = search_client.search(search_text=None, **search_options)
    for result in results:
        return [result["url"], result["schema_json"], result["name"], result["site"]]
    return None

async def search_all_sites(query, top_n=10):
    """
    Search across multiple indices based on embedding size
    
    Args:
        service_endpoint (str): Azure Search service endpoint URL
        api_key (str): API key for authentication
        query_embedding (list or numpy.ndarray): Vector embedding for similarity search
        site (str, optional): Site value to filter by. Defaults to None.
        top_n (int, optional): Number of results to retrieve. Defaults to 10.
        
    Returns:
        list: List of search results with relevance scores
    """
    # Determine which index to use based on embedding size
  #  query_embedding = mllm.get_embedding(query)
    query_embedding = await mllm.get_embedding(query)
    embedding_size = len(query_embedding)
    print(f"embedding size: {embedding_size}")
    if embedding_size == 1536:
        index_name = "embeddings1536"
    elif embedding_size == 3072:
        index_name = "embeddings3072"
    else:
        raise ValueError(f"Unsupported embedding size: {embedding_size}")
    
   
    search_client = get_index_client(index_name)
        
    # Create the search options with vector search only
    search_options = {
        "vector_queries": [
            {
                "kind": "vector",  # Add this line to specify the vector query kind
                "vector": query_embedding,
                "fields": "embedding",
                "k": top_n
            }
        ],
        "top": top_n,
        "select": "url,name,site,schema_json"  # Specify the fields to return
    }
        
    # Execute the search
    results = search_client.search(search_text=None, **search_options)
        
    # Process results into a more convenient format
    processed_results = []
    for result in results:
        processed_result = [result["url"], result["schema_json"], result["name"], result["site"]]
        processed_results.append(processed_result)
        
    return processed_results

# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Configuration
        service_endpoint = get_search_service_endpoint()
        # API key will be read from environment variable AZURE_SEARCH_API_KEY
        
        # Example: Search by multiple sites and vector similarity
        # Normally you would get this from your embedding model
        sample_embedding = await mllm.get_embedding("give me some spicy crunchy vegetarian snacks")
        
        # Example with a single site
        single_site_results = await retrieve_by_site_and_vector(
            "seriouseats",
            sample_embedding,
            top_n=3
        )
        print("Single Site + Vector Search Results:", json.dumps(single_site_results, indent=2))
        
        # Example with no site filter (search across all sites)
        all_sites_results = await search_all_sites(
            "give me some spicy crunchy vegetarian snacks",
            top_n=3
        )
        print("All Sites + Vector Search Results:", json.dumps(all_sites_results, indent=2))
    
    # Run the async main function
    asyncio.run(main())