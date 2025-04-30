import retriever
from state import NLWebHandlerState
import ranking
from azure_logger import log

class FastTrack:
    def __init__(self, handler):
        self.handler = handler

    def is_fastTack_eligible(self):
        if (self.handler.context_url != ''):
            return False
        if (len(self.handler.prev_queries) > 0):
            return False
        return True
        
    async def do(self):
        if (not self.is_fastTack_eligible()):
            return
        self.handler.state.retrieval_done = True
        items = await retriever.DBQueryRetriever(self.handler.query, self.handler).do()
        self.handler.final_retrieved_items = items
        # decontextualization seems to be done. If it requires decontextualization, no
        # point kicking off ranking.
        if (self.handler.state.is_decontextualization_done()):
            log(f"On fast track Decontextualized Query: {self.handler.decontextualized_query}. Requires decontextualization: {self.handler.requires_decontextualization}")
            if (self.handler.requires_decontextualization):
                #nvm, decontextualization required. That would have kicked off another retrieval
                return
            elif (self.handler.query_done == False):
                log("Fast track. Decon call done. Decon not required.")
                self.handler.fastTrackRanker = ranking.Ranking(self.handler, items, ranking.Ranking.POST_DECONTEXTUALIZATION)
                await self.handler.fastTrackRanker.do()
                return  
        elif (self.handler.query_done == False):
            log("Fast track. Decon call not done. Decon not required.")
            self.handler.fastTrackRanker = ranking.Ranking(self.handler, items, ranking.Ranking.FAST_TRACK)
            await self.handler.fastTrackRanker.do()
            return  
        
    
    
    
