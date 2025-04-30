from baseHandler import NLWebHandler
import mllm
import retriever
import asyncio
import json
import utils
from trim import trim_json
import decontextualize
import analyze_query
import memory   
import post_prepare
import ranking
import required_info
import traceback
import relevance_detection
import fastTrack
from state import NLWebHandlerState
from utils import get_param
from azure_logger import log  # Import our new logging utility

# NLWebHandler calls the various preprocessing routines (almost all of which are
# are just LLM calls), then gets the 

# file name is from previous iteration where handlers were being subclassed. 
# Now most of the behaviour specialization can be done with the prompts that are
# in the site_type.xml file.

class WhoHandler (NLWebHandler) :

    def __init__(self, query_params, http_handler): 
        super().__init__(query_params, http_handler)
                            
    async def runQuery(self):
        try:
            await self.decontextualizeQuery().do()
            items = await self.retrieve_items(self.decontextualized_query).do()
            sites_in_embeddings = {}
            for url, json_str, name, site in items:
                sites_in_embeddings[site] = sites_in_embeddings.get(site, 0) + 1
            sites = sorted(sites_in_embeddings.items(), key=lambda x: x[1], reverse=True)[:5]
            message = {"message_type": "result", "results": str(sites)}
            await self.sendMessage(message)
            return message
        except Exception as e:
            log(f"Error in runQuery: {e}")
            traceback.print_exc()

    