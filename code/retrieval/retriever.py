# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
This file contains the base class for all handlers. 
Currently only supports azure_ai_search and milvus.

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.

"""

import retrieval.milvus_retrieve as milvus_retrieve
import retrieval.azure_retrieve as azure_retrieve
import time
import asyncio


class DBQueryRetriever:
    def __init__(self, query, handler, db_type="azure_ai_search"):
        self.db_query = query
        self.handler = handler
        self.db_type = db_type
        self._retrieval_lock = asyncio.Lock()  # Add lock for thread-safe operations

    async def search_db(self, query, site, num_results=50):
        async with self._retrieval_lock:  # Protect database operations
            print(f"DBQueryRetriever init with query: '{query}'")
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
            print(f"retrieval query: {query}, site: '{site}', db: {self.db_type}")
            
            try:
                if (self.db_type == "milvus"):
                    results = milvus_retrieve.search_db(query, site, num_results)
                elif (self.db_type == "azure_ai_search"):
                    if site == "all" or site == "nlws":
                        results = await azure_retrieve.search_all_sites(query, num_results)
                    else:
                        results = await azure_retrieve.search_db(query, site, num_results)
                else:
                    raise ValueError(f"Invalid database: {self.db_type}")
            except Exception as e:
                print(f"Error in search_db: {e}")
                raise
            
            end_time = time.time()
            print(f"Search took {end_time - start_time:.2f} seconds {len(results)} results")
            return results

    async def do(self):
        print("in retriever do")
        try:
            results = await self.search_db(self.db_query, self.handler.site, 50)
            self.handler.retrieved_items = results
            self.handler.retrieval_done_event.set()  # Use event instead of flag
            return results
        except Exception as e:
            print(f"Error in retriever.do: {e}")
            self.handler.retrieval_done_event.set()  # Set even on error to prevent deadlock
            raise

class DBItemRetriever:
    # retrieves an item from the database based on the context url
    # used when there is a context_url in the request
    def __init__(self, handler, db_type="azure_ai_search"):
        self.handler = handler
        self.db_type = db_type
        self._retrieval_lock = asyncio.Lock()  # Add lock for thread-safe operations

    async def do(self):
        try:
            results = await self.retrieve_item_with_url(self.handler.context_url)
            self.handler.context_item = results
        except Exception as e:
            print(f"Error in DBItemRetriever.do: {e}")
            raise
        
    async def retrieve_item_with_url(self, url):
        async with self._retrieval_lock:  # Protect database operations
            try:
                if (self.db_type == "milvus"):
                    return await asyncio.to_thread(milvus_retrieve.retrieve_item_with_url, url)
                elif (self.db_type == "azure_ai_search"):
                    return await azure_retrieve.retrieve_item_with_url(url)
                else:
                    raise ValueError(f"Invalid database: {self.db_type}")
            except Exception as e:
                print(f"Error in retrieve_item_with_url: {e}")
                raise
