import asyncio
from baseHandler import NLWebHandler
import mllm
from prompt_runner import PromptRunner
from prompts import find_prompt, fill_ranking_prompt
import utils
import retriever
from trim import trim_json, trim_json_hard
import json
from azure_logger import log
import traceback


class GenerateAnswer(NLWebHandler):

    GATHER_ITEMS_THRESHOLD = 55

    RANKING_PROMPT_NAME = "RankingPromptForGenerate"
    SYNTHESIZE_PROMPT_NAME = "SynthesizePromptForGenerate"
    DESCRIPTION_PROMPT_NAME = "DescriptionPromptForGenerate"

    def __init__(self, query_params, handler):
        super().__init__(query_params, handler)
        self.items = []
        log(f"GenerateAnswer query_params: {query_params}")
        # self.firstQueryResponse()

    async def runQuery(self):
        try:
            await self.prepare()
            await self.post_prepare_tasks()
            if (self.query_done):
                log(f"query done prematurely")
                return self.return_value
            await self.get_ranked_answers()
            self.return_value["query_id"] = self.query_id
            return self.return_value
        except Exception as e:
            log(f"Error in runQuery: {e}")
            traceback.print_exc()
    
    async def prepare(self):
        # runs the tasks that that need to be done before retrieval, ranking, etc.
        tasks = []
        tasks.append(asyncio.create_task(self.get_analyze_query().do()))
        tasks.append(asyncio.create_task(self.decontextualizeQuery().do()))
        tasks.append(asyncio.create_task(self.get_relevance_detection().do()))
        tasks.append(asyncio.create_task(self.detect_memory_items().do()))
        tasks.append(asyncio.create_task(self.ensure_required_info().do()))
         
        await asyncio.gather(*tasks)
        self.pre_checks_done = True
       
        log(f"prepare tasks done")
   
    async def rankItem(self, url, json_str, name, site):
        
        try:
            prompt_str, ans_struc = find_prompt(site, self.item_type, self.RANKING_PROMPT_NAME)
            description = trim_json_hard(json_str)
            prompt = fill_ranking_prompt(prompt_str, self, description)
          #  log(f"prompt: {prompt} {ans_struc}")
            ranking = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4.1")
            ansr = {
                'url': url,
                'site': site,
                'name': name,
                'ranking': ranking,
                'schema_object': json.loads(json_str),
                'sent': False,
            }
            if (ranking["score"] > self.GATHER_ITEMS_THRESHOLD):
                self.final_ranked_answers.append(ansr)
        except Exception as e:
            log(f"Error in rankItem for {name}: {str(e)}")
            # Continue with other items even if one fails
    
    async def get_ranked_answers(self):
        top_embeddings = await self.retrieve_items(self.decontextualized_query).do()
        tasks = []
        for url, json_str, name, site in top_embeddings:
            tasks.append(asyncio.create_task(self.rankItem(url, json_str, name, site)))
        await asyncio.gather(*tasks)
        await self.synthesizeAnswer()

    async def getDescription(self, url, json_str, query, answer, name, site):
        description = await PromptRunner(self).run_prompt(self.DESCRIPTION_PROMPT_NAME)
        return (url, name, site, description["description"], json_str)

    async def synthesizeAnswer(self): 
        response = await  PromptRunner(self).run_prompt(self.SYNTHESIZE_PROMPT_NAME, model="gpt-4.1", timeout=100)
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
        desc_answers = await asyncio.gather(*description_tasks)
        for url, name, site, description, json_str in desc_answers:
            json_results.append({
                    "url": url,
                    "name": name,
                    "description": description,
                    "site": site,
                    "schema_object": json.loads(json_str),
                })
        message = {"message_type": "nlws", "answer": response["answer"], "items": json_results}
        await self.send_message(message)
   #     print(f"message: {message}")