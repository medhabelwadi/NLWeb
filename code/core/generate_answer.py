# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
This file contains code for the 'generate answer' path, which provides
a flow that is more similar to RAG.

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.
"""

import asyncio
from core.baseHandler import NLWebHandler
from llm.llm import ask_llm
from prompts.prompt_runner import PromptRunner
import retrieval.retriever as DBQueryRetriever
from utils.trim import trim_json, trim_json_hard
import json
import traceback


class GenerateAnswer(NLWebHandler):

    GATHER_ITEMS_THRESHOLD = 55

    RANKING_PROMPT_NAME = "RankingPromptForGenerate"
    SYNTHESIZE_PROMPT_NAME = "SynthesizePromptForGenerate"
    DESCRIPTION_PROMPT_NAME = "DescriptionPromptForGenerate"

    def __init__(self, query_params, handler):
        super().__init__(query_params, handler)
        self.items = []
        self._results_lock = asyncio.Lock()  # Add lock for thread-safe operations
        log(f"GenerateAnswer query_params: {query_params}")

    async def runQuery(self):
        try:
            await self.prepare()
            await self.post_prepare_tasks()
            if (self.query_done):
                return self.return_value
            await self.get_ranked_answers()
            self.return_value["query_id"] = self.query_id
            return self.return_value
        except Exception as e:
            traceback.print_exc()
    
    async def prepare(self):
        # runs the tasks that that need to be done before retrieval, ranking, etc.
        tasks = []
        tasks.append(asyncio.create_task(self.get_analyze_query().do()))
        tasks.append(asyncio.create_task(self.decontextualizeQuery().do()))
        tasks.append(asyncio.create_task(self.get_relevance_detection().do()))
        tasks.append(asyncio.create_task(self.detect_memory_items().do()))
        tasks.append(asyncio.create_task(self.ensure_required_info().do()))
         
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            print(f"Error in prepare tasks: {e}")
        finally:
            self.pre_checks_done_event.set()
   
    async def rankItem(self, url, json_str, name, site):
        try:
            prompt_str, ans_struc = find_prompt(site, self.item_type, self.RANKING_PROMPT_NAME)
            description = trim_json_hard(json_str)
            prompt = fill_ranking_prompt(prompt_str, self, description)
            ranking = await ask_llm(prompt, ans_struc)
            ansr = {
                'url': url,
                'site': site,
                'name': name,
                'ranking': ranking,
                'schema_object': json.loads(json_str),
                'sent': False,
            }
            if (ranking["score"] > self.GATHER_ITEMS_THRESHOLD):
                async with self._results_lock:  # Thread-safe append
                    self.final_ranked_answers.append(ansr)
        except Exception as e:
            # Continue with other items even if one fails
            print(f"Error in rankItem: {e}")

    async def get_ranked_answers(self):
        top_embeddings = await self.retrieve_items(self.decontextualized_query).do()
        tasks = []
        for url, json_str, name, site in top_embeddings:
            tasks.append(asyncio.create_task(self.rankItem(url, json_str, name, site)))
        await asyncio.gather(*tasks, return_exceptions=True)
        await self.synthesizeAnswer()

    async def getDescription(self, url, json_str, query, answer, name, site):
        description = await PromptRunner(self).run_prompt(self.DESCRIPTION_PROMPT_NAME)
        return (url, name, site, description["description"], json_str)

    async def synthesizeAnswer(self): 
        response = await PromptRunner(self).run_prompt(self.SYNTHESIZE_PROMPT_NAME, timeout=100)
        print(f"response: {response}")
        json_results = []
        description_tasks = []
        answer = response["answer"]
        message = {"message_type": "nlws", "answer": response["answer"], "items": json_results}
        
        await self.send_message(message)
        for url in response["urls"]:
            item = next((item for item in self.items if item[0] == url), None)
            if not item:
                continue
            (url, json_str, name, site) = item
            t = asyncio.create_task(self.getDescription(url, json_str, self.decontextualized_query, answer, name, site))
            description_tasks.append(t)
        desc_answers = await asyncio.gather(*description_tasks, return_exceptions=True)
        for result in desc_answers:
            if isinstance(result, Exception):
                print(f"Error getting description: {result}")
                continue
            url, name, site, description, json_str = result
            json_results.append({
                    "url": url,
                    "name": name,
                    "description": description,
                    "site": site,
                    "schema_object": json.loads(json_str),
                })
        message = {"message_type": "nlws", "answer": response["answer"], "items": json_results}
        await self.send_message(message)
