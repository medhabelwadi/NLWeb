"""
Check Azure connectivity for all services required by the application.
Run this script to validate environment variables and API access.
"""

import os
import sys
import asyncio
import time

# Add error handling for imports
try:
    from openai import OpenAI
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
    from dotenv import load_dotenv
    #from env_loader import load_environment
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

# Load environment variables
#load_environment()
load_dotenv()

async def check_search_api():
    """Check Azure AI Search connectivity"""
    print("\nChecking Azure AI Search connectivity...")
    
    api_key = os.environ.get("AZURE_VECTOR_SEARCH_API_KEY")
    if not api_key:
        print("❌ AZURE_VECTOR_SEARCH_API_KEY environment variable not set")
        return False
    
    endpoint = os.environ.get("AZURE_VECTOR_SEARCH_ENDPOINT")
    if not endpoint:
        print("❌ AZURE_VECTOR_SEARCH_ENDPOINT environment variable not set")
        return False

    try:
        credential = AzureKeyCredential(api_key)
        search_client = SearchClient(
            endpoint=endpoint,
            index_name="embeddings1536",
            credential=credential
        )
        
        # Simple query to check connectivity
        result = search_client.get_document_count()
        print(f"✅ Successfully connected to Azure AI Search. Document count: {result}")
        return True
    except Exception as e:
        print(f"❌ Error connecting to Azure AI Search: {e}")
        return False

async def check_openai_api():
    """Check OpenAI API connectivity"""
    print("\nChecking OpenAI API connectivity...")
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        return False
    
    try:
        client = OpenAI(api_key=api_key)
        models = client.models.list()
        print(f"✅ Successfully connected to OpenAI API")
        return True
    except Exception as e:
        print(f"❌ Error connecting to OpenAI API: {e}")
        return False

async def check_azure_openai_api():
    """Check Azure OpenAI API connectivity"""
    print("\nChecking Azure OpenAI API connectivity...")
    
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    if not api_key:
        print("❌ AZURE_OPENAI_API_KEY environment variable not set")
        return False

    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    if not endpoint:
        print("❌ AZURE_OPENAI_ENDPOINT environment variable not set")
        return False
  
    try:
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")
        )
        
        # Try to list deployments
        deployments = client.models.list()
        print(f"✅ Successfully connected to Azure OpenAI API")
        return True
    except Exception as e:
        print(f"❌ Error connecting to Azure OpenAI API: {e}")
        return False

async def check_embedding_api():
    """Check Azure Embedding API connectivity"""
    print("\nChecking Azure Embedding API connectivity...")
    
    api_key = os.environ.get("AZURE_EMBEDDING_API_KEY")
    if not api_key:
        print("❌ AZURE_EMBEDDING_API_KEY environment variable not set")
        return False

    # Fall back to use same endpoint as Azure OpenAI if not set
    endpoint = os.environ.get("AZURE_EMBEDDING_ENDPOINT", os.environ.get("AZURE_OPENAI_ENDPOINT"))
    if not endpoint:
        print("❌ AZURE_EMBEDDING_ENDPOINT environment variable not set")
        return False
    
    try:
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=os.environ.get("AZURE_EMBEDDING_API_VERSION", "2024-10-21")
        )
        
        # Try to create an embedding
        embedding_model = os.environ.get("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
        response = client.embeddings.create(
            input="Hello world",
            model=embedding_model
        )
        
        if len(response.data[0].embedding) > 0:
            print(f"✅ Successfully connected to Azure Embedding API")
            return True
        else:
            print("❌ Got empty embedding response")
            return False
    except Exception as e:
        print(f"❌ Error connecting to Azure Embedding API: {e}")
        return False

async def main():
    """Run all connectivity checks"""
    print("Running Azure connectivity checks...")
    
    start_time = time.time()
    
    # Create and run all checks simultaneously
    tasks = [
        check_search_api(),
        check_openai_api(),
        check_azure_openai_api(),
        check_embedding_api()
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Count successful connections
    successful = sum(1 for r in results if r is True)
    total = len(tasks)
    
    print(f"\n====== SUMMARY ======")
    print(f"✅ {successful}/{total} connections successful")
    
    if successful < total:
        print("❌ Some connections failed. Please check error messages above.")
    else:
        print("✅ All connections successful! Your environment is configured correctly.")
    
    elapsed_time = time.time() - start_time
    print(f"Time taken: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())