from pymilvus import MilvusClient
import json
from llm.llm import get_embedding
import asyncio
import threading

# v1 and v2 used milvus, a client based vector store. Retaining the code
# here. We could make this part of open source, for folks who want to play with it.

_client_lock = threading.Lock()
milvus_client_prod = None

def initialize():
    global milvus_client_prod
    with _client_lock:  # Thread-safe initialization
        if milvus_client_prod is None:
            print("initializing milvus client")
            milvus_client_prod = MilvusClient("../milvus/milvus_prod.db")
            search_db("test", "all", 10)

def get_milvus_client():
    global milvus_client_prod
    if (milvus_client_prod is None):
        initialize()
    return milvus_client_prod

async def search_db(query, site, num_results=50):
    embedding = await get_embedding(query)
    return await asyncio.get_event_loop().run_in_executor(
        None, _search_db_sync, query, site, num_results, embedding
    )

def _search_db_sync(query, site, num_results, embedding):
    """Synchronous version for thread execution"""
    client = get_milvus_client()
    if (site == "bc_product"):
        site = "backcountry"
    if (site == "npr podcasts"):
        site = ["npr podcasts", "med podcast"]
    if (site == "nlws"):
        site = "all"
    if (site == "all"):
        res = client.search(
            collection_name="prod_collection",
            data=[embedding],
            limit=num_results,
            output_fields=["url", "text", "name", "site"],
        )
    elif isinstance(site, list):
        site_filter = " || ".join([f"site == '{s}'" for s in site])
        res = client.search(
            collection_name="prod_collection", 
            data=[embedding],
            filter=site_filter,
            limit=num_results,
            output_fields=["url", "text", "name", "site"],
        )
    else:
        res = client.search(
            collection_name="prod_collection",
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
    print(f"Retrieved {len(retval)} items")
    return retval

def retrieve_item_with_url(url):
    client = get_milvus_client()
    print(f"Querying for '{url}'")
    res = client.query(
        collection_name="prod_collection",
        filter=f"url == '{url}'",
        limit=1,
        output_fields=["url", "text", "name", "site"],
    )
    if (len(res) == 0):
        return None
    return res[0]
