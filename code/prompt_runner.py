import mllm
from prompts import find_prompt, fill_prompt
from azure_logger import log


class PromptRunner:

    def get_prompt(self, prompt_name):
        item_type = self.handler.item_type
        site = self.handler.site
        prompt_str, ans_struc = find_prompt(site, item_type, prompt_name)

        if (prompt_str is None):
            return None, None
        return prompt_str, ans_struc

    def __init__(self, handler):
        self.handler = handler

    async def run_prompt(self, prompt_name, model="gpt-4.1-mini", verbose=False, timeout=8):
        prompt_str, ans_struc = self.get_prompt(prompt_name)
        if (prompt_str is None):
            if (verbose):
                log(f"Prompt {prompt_name} not found")
            return None
        prompt = fill_prompt(prompt_str, self.handler)
        if (verbose):
            log(f"Prompt: {prompt}")
        response = await mllm.get_structured_completion_async(prompt, ans_struc, model, timeout=timeout)
        if (verbose):
            log(f"Response: {response}")
        return response