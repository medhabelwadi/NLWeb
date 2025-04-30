from time import sleep
import asyncio
from azure_logger import log
from state import NLWebHandlerState

# don't think we need this anymore

class PostPrepare:
    """This class is used to check if the pre processing for the query before any 
    results are returned."""
    
    def __init__(self, handler):
        self.handler = handler


    async def do(self):
    
        while (self.handler.pre_checks_done == False and self.handler.query_done == False and 
               self.handler.is_connection_alive == True):
            await asyncio.sleep(.05)
        
        
        
        
      
       
        
