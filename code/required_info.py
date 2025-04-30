import mllm
import asyncio
from prompts import find_prompt, fill_prompt
from state import NLWebHandlerState
import time
from azure_logger import log
from prompt_runner import PromptRunner

class RequiredInfo(PromptRunner):
    """For some sites, we will need to make sure that we have enough information, either from the user
       or context, before we process the query. This class is used to check if we have the required information.
       Whether the information is required or not is determined by whether we have a prompt for it"""


    REQUIRED_INFO_PROMPT_NAME = "RequiredInfoPrompt"
    STEP_NAME = "RequiredInfo"
    
    def __init__(self, handler):
        super().__init__(handler)
        self.handler.state.start_precheck_step(self.STEP_NAME)

    async def do(self):
        response = await self.run_prompt(self.REQUIRED_INFO_PROMPT_NAME)
        if (response):
            log(f"Required info prompt response: {response}")
            self.handler.required_info_found = response["required_info_found"] == "True"
            if (not self.handler.required_info_found):
                self.handler.query_done = True
                self.handler.abort_fast_track = True
                await self.handler.send_message({"message_type": "ask_user", "message": response["user_question"]})
                return
        else:
            self.handler.required_info_found = True
            self.handler.user_question = ""
        self.handler.state.precheck_step_done(self.STEP_NAME)


if __name__ == "__main__":
    class MockHandler:
        def __init__(self, site, query, item_type, required_info, prev_queries, context, memory):
            self.site = site
            self.query = query
            self.item_type = item_type
            self.required_info = required_info
            self.prev_queries = prev_queries
            self.context = context
            self.memory = memory

    async def test_required_info():
        # Get inputs from user
        site = input("Enter site name (e.g. imdb, seriouseats): ")
        query = input("Enter query: ")
        item_type = input("Enter item type (e.g. Recipe, Movie): ")
        required_info = input("Enter required info (comma separated, or empty): ").split(",")
        prev_queries = input("Enter previous queries (comma separated, or empty): ").split(",")
        context = input("Enter context (or empty): ")
        memory = input("Enter memory about user (or empty): ")

        # Create mock handler
        handler = MockHandler(site, query, item_type, required_info, prev_queries, context, memory)
        
        # Create and test RequiredInfo instance
        required_info = RequiredInfo(handler)
        
        print("\nChecking required info...")
        await required_info.do()
        
        print(f"\nResults:")
        print(f"Required info found: {handler.required_info_found}")
        print(f"Question to ask user: {handler.user_question}")

    # Run the test
    asyncio.run(test_required_info())

