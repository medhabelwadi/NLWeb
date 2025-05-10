import httpx
import json
from config.config import CONFIG
from typing import Dict, List, Tuple
from utils import snowflake

async def search_all_sites(query: str, top_n: int=10):
    return await search(query, top_n=top_n)

async def search_db(query: str, site: str, num_results: int=50):
    return await search(query, site=site, top_n=num_results)

async def retrieve_item_with_url(url: str, top_n=1):
    # As of May 2025 cortex search requires a non-empty query for ranking.
    return await search(query="a", url=url, top_n=top_n)


def get_cortex_search_service() -> Tuple[str,str,str]:
    """
    Retrieve the Cortex Search Service (database, schema, service) to use from the configuration, or raise an error.
    """
    config = CONFIG
    if not config:
        raise snowflake.ConfigurationError("Unable to determine Snowflake configuration, is SNOWFLAKE_CONFIG set?")
    index_name = config.retrieval_endpoints["snowflake_cortex_search_1"].index_name
    if not index_name:
        raise snowflake.ConfigurationError("Unable to determine Snowflake Cortex Search Service, is SNOWFLAKE_CORTEX_SEARCH_SERVICE set?")
    parts = index_name.split(".")
    if len(parts) != 3:
        raise snowflake.ConfigurationError(f"Invalid SNOWFLAKE_CORTEX_SEARCH_SERVICE, expected format:<database>.<schema>.<service>, got {index_name}")
    return (parts[0], parts[1], parts[2])

async def search(query: str, site: str|None=None, url: str|None=None, top_n: int=10) -> dict:
    """
    Send a search request to a Cortex Search Service which has the columns
    URL and SCHEMA.

    See: https://docs.snowflake.com/developer-guide/snowflake-rest-api/reference/cortex-search-service
    """

    # Filtering language:
    # https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/query-cortex-search-service#filter-syntax
    filter = None
    if url and not site:
        filter = {"@eq": {"url": url}}
    elif not url and site:
        filter = {"@eq": {"site": site}}
    elif url and site:
        filter = {
            "@and": [
                {"@eq": {"url": url}},
                {"@eq": {"site": site}},
            ]
        }

    (database, schema, service) = get_cortex_search_service()
    async with httpx.AsyncClient() as client:
        response =  await client.post(
            snowflake.get_account_url() + f"/api/v2/databases/{database}/schemas/{schema}/cortex-search-services/{service}:query",
            json={
                "query": query,
                "limit": max(1, min(top_n, 1000)),
                "columns": ["url", "site", "schema_json"],
                "filter": filter,
            },
            headers={
                    "Authorization": f"Bearer {snowflake.get_pat()}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
            },
            timeout=60,
        )
        if response.status_code == 400:
            raise Exception(response.json())
        response.raise_for_status()
        results = response.json().get("results", [])
        return list(map(_process_result, results))

def _process_result(r: Dict[str, str]) -> List[str]:
    url = r.get("url", "")
    schema_json = r.get("schema_json", "{}")
    name = _name_from_schema_json(schema_json)
    site = r.get("site", "")
    return [url, schema_json, name, site]

def _name_from_schema_json(schema_json: str) -> str:
    try:
        return json.loads(schema_json).get("name", "")
    except Exception as e:
        return ""
