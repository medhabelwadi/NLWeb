import asyncio
import os
from WebServer import fulfill_request, start_server

# This file is the entry point for Azure Web App

def main():
    # Get port from Azure environment or use default
    port = int(os.environ.get('PORT', 8000))
    
    # Start the server
    asyncio.run(start_server(
        host='0.0.0.0',
        port=port,
        fulfill_request=fulfill_request
    ))

if __name__ == "__main__":
    main()
