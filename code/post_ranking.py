from time import sleep
from azure_logger import log
from state import NLWebHandlerState
from prompt_runner import PromptRunner




class PostRanking:
    """This class is used to check if any post processing is needed after the ranking is done."""
    
    def __init__(self, handler):
        self.handler = handler

    async def do(self):
        log(f"generate mode = {self.handler.generate_mode}")
        if (self.handler.is_connection_alive == False):
            self.handler.query_done = True
            return
        
        if (self.handler.generate_mode == "none"):
            # nothing to do
            return
        
        if (self.handler.generate_mode == "summarize"):
            await SummarizeResults(self.handler).do()
            return
        
       
        
class SummarizeResults(PromptRunner):

    SUMMARIZE_RESULTS_PROMPT_NAME = "SummarizeResultsPrompt"

    def __init__(self, handler):
        log(f"SummarizeResults __init__")
        super().__init__(handler)

    async def do(self):
        self.handler.final_ranked_answers = self.handler.final_ranked_answers[:3]
        log(f"SummarizeResults {len(self.handler.final_ranked_answers)} final ranked answers")
        response = await self.run_prompt(self.SUMMARIZE_RESULTS_PROMPT_NAME, timeout=20)
        if (not response):
            return
        self.handler.summary = response["summary"]
        message = {"message_type": "summary", "message": self.handler.summary}
        await self.handler.send_message(message)
        self.handler.state.post_ranking = NLWebHandlerState.DONE
        

