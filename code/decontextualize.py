# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
This file contains the classes for the different levels of decontextualization. 
A traditional chatbot, which generates all the output shown to the user
and hence has all the context.
In contrast, with NLWeb, the code generates the results shown. In order to keep
the processing fast (i.e., not blow up the context window for each query) and cheap
(i.e., keep token count low) we compute a 'decontextualized' statement of the query
and use that for generating the new round of answers.

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.
"""

import mllm
from prompt_runner import PromptRunner
import retriever
from trim import trim_json
from prompts import fill_prompt
import json


class NoOpDecontextualizer(PromptRunner):
  
    DECONTEXTUALIZE_QUERY_PROMPT_NAME = "NoOpDecontextualizer"
    STEP_NAME = "Decon"

    def __init__(self, handler):
        super().__init__(handler)
        self.handler.state.start_precheck_step(self.STEP_NAME)
    
    async def do(self):
        self.handler.decontextualized_query = self.handler.query
        self.handler.state.precheck_step_done(self.STEP_NAME)
        self.handler.requires_decontextualization = False
        print("Decontextualization not required")
        return
    
class PrevQueryDecontextualizer(NoOpDecontextualizer):

    DECONTEXTUALIZE_QUERY_PROMPT_NAME = "PrevQueryDecontextualizer"
  
    def __init__(self, handler):
        super().__init__(handler)

    async def do(self):
        response = await self.run_prompt(self.DECONTEXTUALIZE_QUERY_PROMPT_NAME, "gpt-4.1")
        if response is None:
            self.handler.requires_decontextualization = False
            self.handler.state.precheck_step_done(self.STEP_NAME)
            return
        elif (response["requires_decontextualization"] == "True"):
            self.handler.requires_decontextualization = True
            self.handler.abort_fast_track = True
            self.handler.decontextualized_query = response["decontextualized_query"]
            self.handler.state.precheck_step_done(self.STEP_NAME)
            message = {
                "type": "decontextualized_query",
                "decontextualized_query": self.handler.decontextualized_query
            }
            await self.handler.send_message(message)
        else:
            self.handler.decontextualized_query = self.handler.query
            self.handler.state.precheck_step_done(self.STEP_NAME)
        return

class ContextUrlDecontextualizer(PrevQueryDecontextualizer):
    
    DECONTEXTUALIZE_QUERY_PROMPT_NAME = "DecontextualizeContextPrompt"
     
    def __init__(self, handler):    
        super().__init__(handler)
        self.context_url = handler.context_url
        self.retriever = self.retriever()

    def retriever(self):
        return retriever.DBItemRetriever(self.handler)  

    async def do(self):
        response = await self.run_prompt(self.DECONTEXTUALIZE_QUERY_PROMPT_NAME, "gpt-4.1")
        if response is None:
            self.handler.requires_decontextualization = False
            self.handler.state.precheck_step_done(self.STEP_NAME)
            return
        await self.retriever.do()
        item = self.retriever.handler.context_item
        if (item is None):
            self.handler.requires_decontextualization = False
            self.handler.state.precheck_step_done(self.STEP_NAME)
            return
        else:
            (url, schema_json, name, site) = item
            self.context_description = json.dumps(trim_json(schema_json))
            self.handler.context_description = self.context_description
            response = await self.run_prompt(self.DECONTEXTUALIZE_QUERY_PROMPT_NAME, "gpt-4.1")
            self.handler.requires_decontextualization = True
            self.handler.abort_fast_track = True
            self.handler.decontextualized_query = response["decontextualized_query"]
            self.handler.state.precheck_step_done(self.STEP_NAME)
            return

class FullDecontextualizer(ContextUrlDecontextualizer):
    
    DECONTEXTUALIZE_QUERY_PROMPT_NAME = "FullDecontextualizePrompt"

    def __init__(self, handler):
       super().__init__(handler)
   