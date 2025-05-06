from code.core.baseHandler import NLWebHandler
import mllm
import code.retrieval.retriever as retriever
import asyncio
import json
import utils
from code.utils.trim import trim_json
import code.pre_retrieval.decontextualize as decontextualize
import code.pre_retrieval.analyze_query as analyze_query
import code.pre_retrieval.memory as memory   
import code.pre_retrieval.post_prepare as post_prepare
import code.core.ranking as ranking
import code.pre_retrieval.required_info as required_info
import traceback
import code.pre_retrieval.relevance_detection as relevance_detection
import code.core.fastTrack as fastTrack
from code.core.state import NLWebHandlerState
from utils import get_param
from code.utils.azure_logger import log  # Import our new logging utility

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

    