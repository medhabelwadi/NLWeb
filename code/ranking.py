import mllm
import retriever
import asyncio
import json
import utils
from trim import trim_json_hard, trim_json
from prompts import find_prompt, fill_ranking_prompt
from post_prepare import PostPrepare
from azure_logger import log  # Import our new logging utility

# This file contains the code for the ranking stage. 

class Ranking:
     
    EARLY_SEND_THRESHOLD = 59
    NUM_RESULTS_TO_SEND = 10

    FAST_TRACK = 1
    REGULAR_TRACK = 2

    # This is the default ranking prompt, in case, for some reason, we can't find the site_type.xml file.
    RANKING_PROMPT = ["""  Assign a score between 0 and 100 to the following {site.itemType}
based on how relevant it is to the user's question. Use your knowledge from other sources, about the item, to make a judgement. 
If the score is above 50, provide a short description of the item highlighting the relevance to the user's question, without mentioning the user's question.
Provide an explanation of the relevance of the item to the user's question, without mentioning the user's question or the score or explicitly mentioning the term relevance.
If the score is below 75, in the description, include the reason why it is still relevant.
The user's question is: {request.query}. The item's description is {item.description}""",
    {"score" : "integer between 0 and 100", 
 "description" : "short description of the item"}]
 
    RANKING_PROMPT_NAME = "RankingPrompt"
     
    def get_ranking_prompt(self):
        site = self.handler.site
        item_type = self.handler.item_type
        prompt_str, ans_struc = find_prompt(site, item_type, self.RANKING_PROMPT_NAME)
        if prompt_str is None:
            return self.RANKING_PROMPT
        else:
            return prompt_str, ans_struc
        
    def __init__(self, handler, items, ranking_type=FAST_TRACK):
        ll = len(items)
        log(f"Ranking {ll} items of type {ranking_type}")
        self.handler = handler
        self.items = items
        self.num_results_sent = 0
        self.rankedAnswers = []
        self.ranking_type = ranking_type


    async def rankItem(self, url, json_str, name, site):
        if not self.handler.is_connection_alive:
            # Skip processing if connection is already known to be lost
            return
        if (self.ranking_type == Ranking.FAST_TRACK and self.handler.abort_fast_track):
            log("Aborting fast track")
            return
        try:
            prompt_str, ans_struc = self.get_ranking_prompt()
            description = trim_json(json_str)
            prompt = fill_ranking_prompt(prompt_str, self.handler, description)
            model = "gpt-4.1-mini"
            if (self.handler.generate_mode == "summarize"):
                model = "gpt-4.1"
            ranking = await mllm.get_structured_completion_async(prompt, ans_struc, model)
            ansr = {
                'url': url,
                'site': site,
                'name': name,
                'ranking': ranking,
                'schema_object': json.loads(json_str),
                'sent': False,
            }
            if (ranking["score"] > self.EARLY_SEND_THRESHOLD):
                try:
                    await self.sendAnswers([ansr])
                except (BrokenPipeError, ConnectionResetError):
                    log(f"Client disconnected while sending early answer for {name}")
                    self.handler.is_connection_alive = False
                    return
            
            self.rankedAnswers.append(ansr)
        
        except Exception as e:
            log(f"Error in rankItem for {name}: {str(e)}")
            # Continue with other items even if one fails


    def shouldSend(self, result):
        if (self.num_results_sent < self.NUM_RESULTS_TO_SEND - 5):
            return True
        for r in self.rankedAnswers:
            if r["sent"] == True and r["ranking"]["score"] < result["ranking"]["score"]:
                return True
        return False
    
    async def sendAnswers(self, answers, force=False):
        if not self.handler.is_connection_alive:
            log("Connection lost during ranking, skipping sending results")
            return
        
        if (self.ranking_type == Ranking.FAST_TRACK and self.handler.abort_fast_track):
            return
              
        json_results = []
       # log(f"Considering sending {len(answers)} answers")
        for result in answers:
            if self.shouldSend(result) or force:
                #atn = "(fast)" if self.ranking_type == Ranking.FAST_TRACK else "Second"
                json_results.append({
                    "url": result["url"],
                    "name": result["name"],
                    "site": result["site"],
                    "siteUrl": result["site"],
                    "score": result["ranking"]["score"],
                    "description": result["ranking"]["description"],
                    "schema_object": result["schema_object"],
                })
                
                result["sent"] = True
            
        if (json_results):  # Only attempt to send if there are results
            # wait for pre checks to be done.
            while (not self.handler.pre_checks_done):
             #   log("waiting for pre checks to be done")
                if (self.handler.query_done or self.handler.abort_fast_track):
                    return
                await asyncio.sleep(.05)
            # if we got here, prechecks are done. check once again for fast track abort
            if (self.ranking_type == Ranking.FAST_TRACK and self.handler.abort_fast_track):
                return
            try:
                if (self.ranking_type == Ranking.FAST_TRACK):
                    # we are sending message from fast_track, so no need to do ranking later
                    self.handler.fastTrackWorked = True
                to_send = {"message_type": "result_batch", "results": json_results, "query_id": self.handler.query_id}
                await self.handler.send_message(to_send)
                self.num_results_sent += len(json_results)
            except (BrokenPipeError, ConnectionResetError) as e:
                log(f"Client disconnected while sending answers: {str(e)}")
                self.handler.is_connection_alive = False
                # Don't re-raise the exception - just record that connection is lost
            except Exception as e:
                log(f"Error sending answers: {str(e)}")
                self.handler.is_connection_alive = False
  
    async def sendMessageOnSitesBeingAsked(self, top_embeddings):
        if (self.handler.site == "all" or self.handler.site == "nlws"):
            sites_in_embeddings = {}
            for url, json_str, name, site in top_embeddings:
                sites_in_embeddings[site] = sites_in_embeddings.get(site, 0) + 1
            top_sites = sorted(sites_in_embeddings.items(), key=lambda x: x[1], reverse=True)[:3]
            top_sites_str = ", ".join([self.prettyPrintSite(x[0]) for x in top_sites])
            message = {"message_type": "asking_sites",  "message": "Asking " + top_sites_str}
            try:
                await self.handler.send_message(message)
                self.handler.sites_in_embeddings_sent = True
            except (BrokenPipeError, ConnectionResetError):
                print("Client disconnected when sending sites message")
                self.is_connection_alive = False

    
    async def do(self):
        tasks = []
        for url, json_str, name, site in self.items:
            if self.handler.is_connection_alive:  # Only add new tasks if connection is still alive
                tasks.append(asyncio.create_task(self.rankItem(url, json_str, name, site)))
       
        await self.sendMessageOnSitesBeingAsked(self.items)

        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            log(f"Error during ranking tasks: {str(e)}")

        if not self.handler.is_connection_alive:
            log("Connection lost during ranking, skipping sending results")
            return

        while (self.handler.pre_checks_done == False):
            await asyncio.sleep(.05)
        
        if (self.ranking_type == Ranking.FAST_TRACK and self.handler.abort_fast_track):
            return
    
        filtered = [r for r in self.rankedAnswers if r['ranking']['score'] > 51]
        ranked = sorted(filtered, key=lambda x: x['ranking']["score"], reverse=True)
        self.handler.final_ranked_answers = ranked[:self.NUM_RESULTS_TO_SEND]

        results = [r for r in self.rankedAnswers if r['sent'] == False]
        if (self.num_results_sent > self.NUM_RESULTS_TO_SEND):
            log("returning without looking at remaining results")
            return
       
        # Sort by score in descending order
        sorted_results = sorted(results, key=lambda x: x['ranking']["score"], reverse=True)
        good_results = [x for x in sorted_results if x['ranking']["score"] > 51]

        if (len(good_results) + self.num_results_sent >= self.NUM_RESULTS_TO_SEND):
            tosend = good_results[:self.NUM_RESULTS_TO_SEND - self.num_results_sent + 1]
        else:
            tosend = good_results

        try:
            await self.sendAnswers(tosend, force=True)
        except (BrokenPipeError, ConnectionResetError):
            log("Client disconnected during final answer sending")
            self.handler.is_connection_alive = False


    def prettyPrintSite(self, site):
        ans = site.replace("_", " ")
        words = ans.split()
        return ' '.join(word.capitalize() for word in words)