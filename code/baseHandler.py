# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
This file contains the base class for all handlers.

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.
"""

import retriever
import asyncio
import utils
import decontextualize
import analyze_query
import memory   
import post_prepare
import ranking
import required_info
import traceback
import relevance_detection
import fastTrack
import post_ranking
from state import NLWebHandlerState
from utils import get_param
from azure_logger import log  # Import our new logging utility
import logging

logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("WebServer").setLevel(logging.ERROR)
logging.getLogger("openai").setLevel(logging.WARNING)  # This is the new one
logging.getLogger("openai._base_client").setLevel(logging.WARNING)  # And this specific one

# NLWebHandler calls the various preprocessing routines (almost all of which are
# are just LLM calls), then gets the 

# file name is from previous iteration where handlers were being subclassed. 
# Now most of the behaviour specialization can be done with the prompts that are
# in the site_type.xml file.

class NLWebHandler :

    def __init__(self, query_params, http_handler): 
        self.http_handler = http_handler
        self.query_params = query_params

        # the site that is being queried
        self.site = get_param(query_params, "site", str, "all")  

        # the query that the user entered
        self.query = get_param(query_params, "query", str, "")

        # the previous queries that the user has entered
        self.prev_queries = get_param(query_params, "prev", list, [])

        # the model that is being used
        self.model = get_param(query_params, "model", str, "gpt-4o-mini")

        # the request may provide a fully decontextualized query, in which case 
        # we don't need to decontextualize the latest query.
        self.decontextualized_query = get_param(query_params, "decontextualized_query", str, "") 

        # the url of the page on which the query was entered, in case that needs to be 
        # used to decontextualize the query. Typically left empty
        self.context_url = get_param(query_params, "context_url", str, "")

        # this allows for the request to specify an arbitrary string as background/context
        self.context_description = get_param(query_params, "context_description", str, "")

        # this is the query id which is useful for some bookkeeping
        self.query_id = get_param(query_params, "query_id", str, "")

        streaming = get_param(query_params, "streaming", str, "True")
        self.streaming = streaming not in ["False", "false", "0"]

        # should we just list the results or try to summarize the results or use the results to generate an answer
        # Valid values are "none","summarize" and "generate"
        self.generate_mode = get_param(query_params, "generate_mode", str, "none")
        # the items that have been retrieved from the vector database, could be before decontextualization.
        # See below notes on fasttrack
        self.retrieved_items = []

        # the final set of items retrieved from vector database, after decontextualization, etc.
        # items from these will be returned. If there is no decontextualization required, this will
        # be the same as retrieved_items
        self.final_retrieved_items = []

        # the final ranked answers that will be returned to the user (or have already been streamed)
        self.final_ranked_answers = []

        # whether the query has been done. Can happen if it is determined that we don't have enough
        # information to answer the query, or if the query is irrelevant.
        self.query_done = False

        # whether the query is irrelevant. e.g., how many angels on a pinhead asked of seriouseats.com
        self.query_is_irrelevant = False

        # whether the query requires decontextualization
        self.requires_decontextualization = False

        self.is_connection_alive = True

        # the type of item that is being sought. e.g., recipe, movie, etc.
        self.item_type = utils.siteToItemType(self.site)

        # the state of the handler. This is a singleton that holds the state of the handler.
        self.state = NLWebHandlerState(self)

        # whether the handler is ready to return results. This is set by the post_prepare_tasks
        # method after all the pre checks have been done.
        self.pre_checks_done = False

        self.fastTrackRanker = None
        self.fastTrackWorked = False
        self.sites_in_embeddings_sent = False

        # this is the value that will be returned to the user. 
        # it will be a dictionary with the message type as the key and the value being
        # the value of the message.
        self.return_value = {}

        # whether the fast track has been aborted. See the documentation on FastTrack
        self.abort_fast_track = False
        log(f"NLWebHandler initialized with site: {self.site}, query: {self.query}, prev_queries: {self.prev_queries}, mode: {self.generate_mode}, query_id: {self.query_id}, context_url: {self.context_url}")


    async def send_message(self, message):
        # if the request is coming from a browser, it will likely be in streaming mode. If so, send answers as they are ready.
        # otherwise, don't actually send the message but store it in self.return_value
        if (self.streaming and self.http_handler is not None):
            message["query_id"] = self.query_id
            await self.http_handler.write_stream(message)
        else:
            #{"message_type": "remember", "item_to_remember": self.memory_request, "message": "I'll remember that"}
            val = {}
            message_type = message["message_type"]
            if (message_type == "result_batch"):
                val = message["results"]
                for result in val:
                    if "results" not in self.return_value:
                        self.return_value["results"] = []
                    self.return_value["results"].append(result)
            else:
                for key in message:
                    if (key != "message_type"):
                        val[key] = message[key]
                self.return_value[message["message_type"]] = val


    async def runQuery(self):
        try:
            await self.prepare()
            if (self.query_done):
                log(f"query done prematurely")
                return self.return_value
            if (not self.fastTrackWorked):
                log(f"Going to get ranked answers")
                await self.get_ranked_answers()
                log(f"ranked answers done")
            await self.post_ranking_tasks()
            self.return_value["query_id"] = self.query_id
            return self.return_value
        except Exception as e:
            log(f"Error in runQuery: {e}")
            traceback.print_exc()
    
    async def prepare(self):
        # runs the tasks that that need to be done before retrieval, ranking, etc.
        tasks = []
        self.state.retrieval_done = False
        # fast track is causing more problems than is worth it.
        tasks.append(asyncio.create_task(fastTrack.FastTrack(self).do()))
        tasks.append(asyncio.create_task(analyze_query.DetectItemType(self).do()))
        tasks.append(asyncio.create_task(analyze_query.DetectMultiItemTypeQuery(self).do()))
        tasks.append(asyncio.create_task(analyze_query.DetectQueryType(self).do()))
        tasks.append(asyncio.create_task(self.decontextualizeQuery().do()))
        tasks.append(asyncio.create_task(relevance_detection.RelevanceDetection(self).do()))
        tasks.append(asyncio.create_task(memory.Memory(self).do()))
        tasks.append(asyncio.create_task(required_info.RequiredInfo(self).do()))
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            self.pre_checks_done = True
         
        # retrieval should have been done by now, by fastTrack and/or 
        # after decontextualization. if not
        if (self.state.retrieval_done == False):
            items = await retriever.DBQueryRetriever(self.decontextualized_query, self).do()
            self.final_retrieved_items = items
        log(f"prepare tasks done")

    def decontextualizeQuery(self):
        # needs to incorporate context_description. 
        if (self.context_url == '' and len(self.prev_queries) < 1):
            self.decontextualized_query = self.query
            return decontextualize.NoOpDecontextualizer(self)
        elif (self.decontextualized_query != ''):
            return decontextualize.NoOpDecontextualizer(self)
        elif (self.context_url == '' and len(self.prev_queries) > 0):
            return decontextualize.PrevQueryDecontextualizer(self)
        elif (self.context_url != '' and len(self.prev_queries) == 0):
            return decontextualize.ContextUrlDecontextualizer(self)
        else:
            return decontextualize.FullDecontextualizer(self)
    
    
    async def get_ranked_answers(self):
        try:
            log(f"Getting ranked answers on {len(self.final_retrieved_items)} items")
            await ranking.Ranking(self, self.final_retrieved_items, ranking.Ranking.REGULAR_TRACK).do()
            return self.return_value
        except Exception as e:
            log(f"Error in get_ranked_answers: {e}")
            traceback.print_exc()

    async def post_ranking_tasks(self):
       await post_ranking.PostRanking(self).do()

   
        