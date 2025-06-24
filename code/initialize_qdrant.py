#!/usr/bin/env python3
"""
Initialize Qdrant database and create the required collection for NLWeb.
This script will create the nlweb_collection if it doesn't exist.
"""

import asyncio
import sys
import os

# Add the current directory to the path so we can import from the code modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from retrieval.qdrant import QdrantVectorClient
from config.config import CONFIG

async def initialize_qdrant():
    """Initialize Qdrant database and create the required collection."""
    print("🔧 Initializing Qdrant database...")
    
    try:
        # Create Qdrant client
        client = QdrantVectorClient('qdrant_local')
        print(f"✅ Qdrant client created for endpoint: qdrant_local")
        
        # Check if collection exists
        collection_name = "nlweb_collection"
        exists = await client.collection_exists(collection_name)
        
        if exists:
            print(f"✅ Collection '{collection_name}' already exists")
        else:
            print(f"📝 Creating collection '{collection_name}'...")
            await client.create_collection(collection_name, vector_size=1536)
            print(f"✅ Collection '{collection_name}' created successfully")
        
        # Test the connection
        print("🧪 Testing connection...")
        test_results = await client.search("test", site="all", num_results=1)
        print(f"✅ Connection test successful. Found {len(test_results)} results.")
        
        print("\n🎉 Qdrant initialization completed successfully!")
        
    except Exception as e:
        print(f"❌ Error initializing Qdrant: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(initialize_qdrant()) 