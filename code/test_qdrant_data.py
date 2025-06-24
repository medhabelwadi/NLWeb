#!/usr/bin/env python3
"""
Add test data to Qdrant collection for connectivity testing.
"""

import asyncio
import sys
import os
import uuid

# Add the current directory to the path so we can import from the code modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from retrieval.qdrant import QdrantVectorClient
from embedding.embedding import get_embedding

async def add_test_data():
    """Add some test data to the Qdrant collection."""
    print("📝 Adding test data to Qdrant collection...")
    
    try:
        # Create Qdrant client
        client = QdrantVectorClient('qdrant_local')
        
        # Test document with proper format
        test_doc = {
            "id": str(uuid.uuid4()),
            "text": "This is a test document for NLWeb connectivity testing.",
            "url": "https://example.com/test",
            "site": "example.com",
            "name": "Test Document",
            "schema_json": '{"@type": "WebPage", "name": "Test Document", "url": "https://example.com/test"}'
        }
        
        # Get embedding for the test document
        embedding = await get_embedding(test_doc["text"])
        test_doc["embedding"] = embedding
        
        # Add the document to the collection
        uploaded_count = await client.upload_documents([test_doc], collection_name="nlweb_collection")
        
        print(f"✅ Test data added successfully! Uploaded {uploaded_count} documents.")
        
        # Verify the data was added
        results = await client.search("test", site="all", num_results=5)
        print(f"✅ Search test successful. Found {len(results)} results.")
        
    except Exception as e:
        print(f"❌ Error adding test data: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(add_test_data()) 