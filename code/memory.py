import asyncio
from prompt_runner import PromptRunner
from prompts import find_prompt, fill_prompt
from state import NLWebHandlerState

# this file is used to analyze the query to see if it mentions anything that
# should go into the long term memory for the user.
# at this point, the memory is only in the session (i.e., in the conversation history)
# and is not stored in any database.
# There is a hook below to store it where appropriate

class Memory(PromptRunner):

    MEMORY_PROMPT_NAME = "DetectMemoryRequestPrompt"
    STEP_NAME = "Memory"
    def __init__(self, handler):
        super().__init__(handler)
        self.handler.state.start_precheck_step(self.STEP_NAME)

    async def do(self):
        response = await self.run_prompt(self.MEMORY_PROMPT_NAME)
        if (not response):
            self.handler.state.precheck_step_done(self.STEP_NAME)
            return
        self.is_memory_request = response["is_memory_request"]
        self.memory_request = response["memory_request"]
        if (self.is_memory_request == "True"):
            # this is where we would write to a database
            print(f"writing memory request: {self.memory_request}")
            message = {"message_type": "remember", "item_to_remember": self.memory_request, "message": "I'll remember that"}
            await self.handler.send_message(message)
        self.handler.state.precheck_step_done(self.STEP_NAME)

if __name__ == "__main__":
    class MockHandler:
        def __init__(self, site, query, item_type):
            self.site = site
            self.query = query
            self.item_type = item_type
            
        async def write_stream(self, message):
            print(f"Would send message: {message}")


    async def test_memory():
        # Get inputs from user
        site = input("Enter site name (e.g. allrecipes.com): ")
        query = input("Enter query (e.g. Remember I'm vegetarian): ")
        item_type = input("Enter item type (e.g. Recipe): ")

        # Create mock handler
        handler = MockHandler(site, query, item_type)
        
        # Create and test Memory instance
        memory = Memory(handler)
        
        
        print("\nTesting memory analysis...")
        await memory.do()
        
        print(f"\nResults:")
        print(f"Is memory request: {memory.is_memory_request}")
        print(f"Memory request: {memory.memory_request}")

    # Run the test
    asyncio.run(test_memory())

