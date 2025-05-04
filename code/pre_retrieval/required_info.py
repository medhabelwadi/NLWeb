# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
This file contains the methods for checking if we have the required information.

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.
"""

from prompts.prompt_runner import PromptRunner
import asyncio

class RequiredInfo(PromptRunner):
    """For some sites, we will need to make sure that we have enough information, either from the user
       or context, before we process the query. This class is used to check if we have the required information."""

    REQUIRED_INFO_PROMPT_NAME = "RequiredInfoPrompt"
    STEP_NAME = "RequiredInfo"
    
    def __init__(self, handler):
        super().__init__(handler)
        self.handler.state.start_precheck_step(self.STEP_NAME)

    async def do(self):
        response = await self.run_prompt(self.REQUIRED_INFO_PROMPT_NAME, level="low")
        if (response):
            log(f"Required info prompt response: {response}")
            self.handler.required_info_found = response["required_info_found"] == "True"
            if (not self.handler.required_info_found):
                self.handler.query_done = True
                self.handler.abort_fast_track_event.set()  # Use event instead of flag
                await self.handler.send_message({"message_type": "ask_user", "message": response["user_question"]})
                await self.handler.state.precheck_step_done(self.STEP_NAME)
                return
        else:
            self.handler.required_info_found = True
            self.handler.user_question = ""
        await self.handler.state.precheck_step_done(self.STEP_NAME)
