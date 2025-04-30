# This file contains the state of the NLWebHandler.
# It is used to track the state of the handler and the various stages
# of the query.

import asyncio

class NLWebHandlerState:

    INITIAL = 0
    DONE = 2

    def __init__(self, handler):
        self.handler = handler
        self.precheck_step_state = {}
       

    def start_precheck_step(self, step_name):
        self.precheck_step_state[step_name] = self.__class__.INITIAL

    def precheck_step_done(self, step_name):
        self.precheck_step_state[step_name] = self.__class__.DONE
        self.check_pre_checks_done()

    def check_pre_checks_done(self):
        if all(state == self.__class__.DONE for state in self.precheck_step_state.values()):
            self.handler.pre_checks_done = True

    async def pre_check_approval(self):
        while (self.handler.pre_checks_done == False and self.handler.query_done == False and 
               self.handler.is_connection_alive == True):
            await asyncio.sleep(.05)

    def is_decontextualization_done(self):
        if "Decon" in self.precheck_step_state:
            return self.precheck_step_state["Decon"] == self.__class__.DONE
        else:
            return False
   