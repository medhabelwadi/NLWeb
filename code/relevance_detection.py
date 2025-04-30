import asyncio
from state import NLWebHandlerState
from azure_logger import log
from prompt_runner import PromptRunner

class RelevanceDetection(PromptRunner):

    RELEVANCE_PROMPT_NAME = "DetectIrrelevantQueryPrompt"
    STEP_NAME = "Relevance"
    def __init__(self, handler):
        super().__init__(handler)
        self.handler.state.start_precheck_step(self.STEP_NAME)

    async def do(self):
        if (self.handler.site == 'all' or self.handler.site == 'nlws'):
            self.handler.state.precheck_step_done(self.STEP_NAME)
            return
        response = await self.run_prompt(self.RELEVANCE_PROMPT_NAME)
        if (not response):
            self.handler.state.precheck_step_done(self.STEP_NAME)
            return
        self.site_is_irrelevant_to_query = response["site_is_irrelevant_to_query"]
        self.explanation_for_irrelevance = response["explanation_for_irrelevance"]
        if (self.site_is_irrelevant_to_query == "True"):
            log(f"site is irrelevant to query: {self.explanation_for_irrelevance}")
            message = {"message_type": "site_is_irrelevant_to_query", "message": self.explanation_for_irrelevance}
            self.handler.query_is_irrelevant = True
            self.handler.query_done = True
            self.handler.abort_fast_track = True
            await self.handler.send_message(message)
        else:
          #  print(f"site is relevant to query: {self.explanation_for_irrelevance}")
            self.handler.query_is_irrelevant = False
        self.handler.state.precheck_step_done(self.STEP_NAME)

if __name__ == "__main__":
    class MockHandler:
        def __init__(self, site, query, item_type):
            self.site = site
            self.query = query
            self.item_type = item_type
            self.query_is_irrelevant = False
            self.query_done = False
            self.abort_fast_track = False
            self.state = NLWebHandlerState(self)
            
        async def send_message(self, message):
            print(f"Would send message: {message}")

    async def test_relevance_detection():
        # Get inputs from user
        site = input("Enter site name (e.g. allrecipes.com): ")
        query = input("Enter query (e.g. How many angels can dance on the head of a pin?): ")
        item_type = input("Enter item type (e.g. Recipe): ")

        # Create mock handler
        handler = MockHandler(site, query, item_type)
        
        # Create and test RelevanceDetection instance
        relevance = RelevanceDetection(handler)
        
        print("\nTesting relevance detection...")
        await relevance.do()
        
        print(f"\nResults:")
        print(f"Is site irrelevant to query: {relevance.site_is_irrelevant_to_query}")
        print(f"Explanation: {relevance.explanation_for_irrelevance}")
        print(f"Handler query_is_irrelevant: {handler.query_is_irrelevant}")
        print(f"Handler query_done: {handler.query_done}")

    # Run the test
    asyncio.run(test_relevance_detection())
