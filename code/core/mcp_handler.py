# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
This file contains the code for the MCP handler.

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.
"""

import json
import traceback
from core.baseHandler import NLWebHandler
from webserver.StreamingWrapper import HandleRequest, SendChunkWrapper
import asyncio
from utils.logger import get_logger, LogLevel

# Assuming logger is available
logger = get_logger(__name__)

async def handle_mcp_request(query_params, body, send_response, send_chunk, streaming=False):
    """
    Handle an MCP request by processing it with NLWebHandler
    
    Args:
        query_params (dict): URL query parameters
        body (bytes): Request body
        send_response (callable): Function to send response headers
        send_chunk (callable): Function to send response body
        streaming (bool, optional): Whether to use streaming response
    """
  
    try:
        # Parse the request body as JSON
        if body:
            try:
                request_data = json.loads(body)
                
                # Extract the function call details
                function_call = request_data.get("function_call", {})
                function_name = function_call.get("name")
                
                if function_name != "ask":
                    # Return error for unsupported functions
                    error_response = {
                        "type": "function_response",
                        "status": "error",
                        "error": f"Unknown function: {function_name}"
                    }
                    await send_response(400, {'Content-Type': 'application/json'})
                    await send_chunk(json.dumps(error_response), end_response=True)
                    return
                
                # Parse function arguments
                arguments = json.loads(function_call.get("arguments", "{}"))
                
                # Extract the query parameter (required)
                query = arguments.get("query")
                
                if not query:
                    # Return error for missing query parameter
                    error_response = {
                        "type": "function_response",
                        "status": "error",
                        "error": "Missing required parameter: query"
                    }
                    await send_response(400, {'Content-Type': 'application/json'})
                    await send_chunk(json.dumps(error_response), end_response=True)
                    return
                
                # Initialize query_params if it doesn't exist
                if query_params is None:
                    query_params = {}
                
                # Add the query to query_params for NLWebHandler
                query_params["query"] = [query]
                
                # Add optional parameters if they exist in the arguments
                if "site" in arguments:
                    query_params["site"] = [arguments["site"]]

                if "query_id" in arguments:
                    query_params["query_id"] = [arguments["query_id"]]
                
                if "prev_query" in arguments:
                    query_params["prev_query"] = [arguments["prev_query"]]
                
                if "context_url" in arguments:
                    query_params["context_url"] = [arguments["context_url"]]
                
                # Check if streaming was specified in the arguments
                if "streaming" in arguments:
                    streaming = arguments["streaming"] in [True, "true", "True", "1", 1]
                
                if not streaming:
                    # Non-streaming response - process request and return complete response
                    result = await NLWebHandler(query_params, None).runQuery()
                    
                    # Format the response according to MCP protocol
                    mcp_response = {
                        "type": "function_response",
                        "status": "success",
                        "response": result
                    }
                    
                    # Send the response
                    await send_response(200, {'Content-Type': 'application/json'})
                    await send_chunk(json.dumps(mcp_response), end_response=True)
                else:
                    # Streaming response - set up SSE headers
                    response_headers = {
                        'Content-Type': 'text/event-stream',
                        'Cache-Control': 'no-cache',
                        'Connection': 'keep-alive',
                        'X-Accel-Buffering': 'no'  # Disable proxy buffering
                    }
                    
                    # Send SSE headers
                    await send_response(200, response_headers)
                    
                    # Send initial keep-alive comment to establish connection
                    await send_chunk(": keep-alive\n\n", end_response=False)
                    
                    # Create wrapper for chunk sending
                    send_chunk_wrapper = SendChunkWrapper(send_chunk)
                    
                    # Add streaming parameter to query_params
                    query_params["streaming"] = ["True"]
                    
                    # Create a custom handler for streaming MCP responses
                    class MCPStreamHandler:
                        def __init__(self, send_chunk_wrapper):
                            self.send_chunk_wrapper = send_chunk_wrapper
                            self.closed = False
                            self._write_lock = asyncio.Lock()  # Add lock for thread-safe operations
                        
                        async def write(self, chunk, end_response=False):
                            if self.closed:
                                return
                            
                            async with self._write_lock:  # Ensure thread-safe writes
                                try:
                                    # Format as MCP stream event with partial response
                                    if isinstance(chunk, dict):
                                        # If it's already a dictionary, wrap it in MCP format
                                        mcp_event = {
                                            "type": "function_stream_event",
                                            "content": chunk
                                        }
                                    elif isinstance(chunk, str):
                                        # If it's a string, treat as partial content
                                        mcp_event = {
                                            "type": "function_stream_event",
                                            "content": {"partial_response": chunk}
                                        }
                                    else:
                                        # For any other type, convert to string
                                        mcp_event = {
                                            "type": "function_stream_event",
                                            "content": {"partial_response": str(chunk)}
                                        }
                                    
                                    # Send the event
                                    await self.send_chunk_wrapper.write_stream(mcp_event, end_response=False)
                                    
                                    if end_response:
                                        # Send final completion event
                                        final_event = {
                                            "type": "function_stream_end",
                                            "status": "success"
                                        }
                                        await self.send_chunk_wrapper.write_stream(final_event, end_response=True)
                                        self.closed = True
                                        
                                except Exception as e:
                                    logger.error(f"Error in MCPStreamHandler.write: {str(e)}")
                                    print(f"Error in MCPStreamHandler.write: {str(e)}")
                                    self.closed = True
                        
                        async def write_stream(self, message, end_response=False):
                            # This method can be used to pass through stream messages directly
                            await self.write(message, end_response)
                    
                    # Create the MCP stream handler
                    mcp_stream_handler = MCPStreamHandler(send_chunk_wrapper)
                    
                    try:
                        # Call HandleRequest to process the streaming request
                        method = "GET"  # Default to GET
                        path = "/ask"   # Path for the handler
                        headers = {}    # No special headers needed
                        
                        hr = HandleRequest(method, path, headers, query_params, 
                                       body, send_response, mcp_stream_handler, "none")
                        await hr.do_GET()
                    except Exception as e:
                        logger.error(f"Error in streaming request: {str(e)}")
                        print(f"Error in streaming request: {str(e)}\n{traceback.format_exc()}")
                        
                        # Try to send an error response if possible
                        if not mcp_stream_handler.closed:
                            error_event = {
                                "type": "function_stream_end",
                                "status": "error",
                                "error": f"Error processing streaming request: {str(e)}"
                            }
                            await send_chunk_wrapper.write_stream(error_event, end_response=True)
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in MCP request: {e}")
                print(f"Invalid JSON in MCP request: {e}")
                await send_response(400, {'Content-Type': 'application/json'})
                await send_chunk(json.dumps({
                    "type": "function_response",
                    "status": "error",
                    "error": f"Invalid JSON: {str(e)}"
                }), end_response=True)
        else:
            logger.error("Empty MCP request body")
            print("Empty MCP request body")
            await send_response(400, {'Content-Type': 'application/json'})
            await send_chunk(json.dumps({
                "type": "function_response",
                "status": "error",
                "error": "Empty request body"
            }), end_response=True)
            
    except Exception as e:
        logger.error(f"Error processing MCP request: {e}", exc_info=True)
        print(f"Error processing MCP request: {e}\n{traceback.format_exc()}")
        await send_response(500, {'Content-Type': 'application/json'})
        await send_chunk(json.dumps({
            "type": "function_response",
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), end_response=True)