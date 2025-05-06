import os
import csv
import json
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    VectorSearchAlgorithmKind
)
from db_create_utils import documentsFromCSVLine
#from webapp.mllm import get_configured_logger
import sys

# This file contains the code to create the AI Search vector databases
# and load them with the schema json and associated embeddings
# This is not part of the runtime, but is used for uploading the data


# these are files on my laptop, for now. All the data is in the vector search
# database whose endpoint is above.

EMBEDDINGS_PATH_SMALL = "/Users/guha/mahi/data/sites/embeddings/small/"
EMBEDDINGS_PATH_LARGE = "/Users/guha/mahi/data/sites/embeddings/large/"
EMBEDDINGS_PATH_COMPACT = "/Users/guha/mahi/data/sites/embeddings/compact/"


search_clients = {}
index_names = ["embeddings1536", "embeddings3072", "embeddings1536compact"]
SEARCH_SERVICE_ENDPOINT = "https://mahi-vector-search.search.windows.net"
#logger = get_configured_logger('ai_search_load')

global_search_service_endpoint = None
def get_search_service_endpoint():
    global global_search_service_endpoint
    if (global_search_service_endpoint is None):
        global_search_service_endpoint = os.environ.get("AZURE_VECTOR_SEARCH_ENDPOINT")
    if (global_search_service_endpoint is None):
        #logger.error("AZURE_VECTOR_SEARCH_ENDPOINT is not set.  Please set this environment variable and restart.")
        sys.exit(1)
    else:
        global_search_service_endpoint = global_search_service_endpoint.strip('"')  # Adding the strip in case the env var has quotes in it
    return global_search_service_endpoint

global_search_api_key = None
def get_search_api_key():
    global global_search_api_key
    if (global_search_api_key is None):
        global_search_api_key = os.environ.get("AZURE_VECTOR_SEARCH_API_KEY")
    if (global_search_api_key is None):
       # logger.error("AZURE_VECTOR_SEARCH_API_KEY is not set.  Please set this environment variable and restart.")
        sys.exit(1)
    else:
        global_search_api_key = global_search_api_key.strip('"')  # Adding the strip in case the env var has quotes in it
    return global_search_api_key

def get_index_client(index_name):
    """Get a search client for a specific index"""
    if (index_name in search_clients):
        return search_clients[index_name]
    else:
        initialize_clients()
        return search_clients[index_name]

def initialize_clients():
    # Get API key from environment variable
    api_key = get_search_api_key()
    if not api_key:
        raise ValueError("AZURE_SEARCH_API_KEY environment variable not set")
    
    credential = AzureKeyCredential(api_key)
    # Create index client for managing indexes
    index_client = SearchIndexClient(endpoint=get_search_service_endpoint(), credential=credential)
    search_clients["index_client"] = index_client
    
    # Create search clients for document operations
    for index_name in index_names:
        search_client = SearchClient(endpoint=get_search_service_endpoint(), index_name=index_name, credential=credential)
        search_clients[index_name] = search_client


def create_vector_search_config(algorithm_name="hnsw_config", profile_name="vector_config"):
    """Create and return a vector search configuration"""
    return VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name=algorithm_name,
                kind=VectorSearchAlgorithmKind.HNSW,
                parameters={
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine"
                }
            )
        ],
        profiles=[
            VectorSearchProfile(
                name=profile_name,
                algorithm_configuration_name=algorithm_name,
            )
        ]
    )


def drop_all_indices(index_names=None):
    """
    Drop all specified indices from Azure Search service
    
    Args:
        index_names (list, optional): List of index names to drop. If None, drops the default indices.
        
    Returns:
        list: List of dropped indices names
    """
    if index_names is None:
        index_names = ["embeddings1536", "embeddings3072", "embeddings1536compact"]
    
    dropped_indices = []    
    errors = []
    index_client = get_index_client("index_client")
    for index_name in index_names:
        try:
            index_client.delete_index(index_name)
            print(f"Index '{index_name}' dropped successfully.")
            dropped_indices.append(index_name)
        except Exception as e:
            error_message = str(e)
            if "ResourceNotFound" in error_message:
                print(f"Index '{index_name}' does not exist, skipping.")
            else:
                print(f"Error dropping index '{index_name}': {error_message}")
                errors.append({"index": index_name, "error": error_message})
    
    # Summary of operation
    if not errors:
        print(f"Successfully dropped {len(dropped_indices)} indices.")
    else:
        print(f"Dropped {len(dropped_indices)} indices with {len(errors)} errors.")
    
    return dropped_indices

def create_index_definition(index_name, embedding_size, profile_name="vector_config"):
    """Create and return an index definition with specified embedding size"""
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SimpleField(name="url", type=SearchFieldDataType.String,  filterable=True),
        SimpleField(name="name", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SimpleField(name="site", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="schema_json", type=SearchFieldDataType.String, filterable=False),
        SearchField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            vector_search_dimensions=embedding_size,
            vector_search_profile_name=profile_name
        )
    ]
    
    vector_search = create_vector_search_config(profile_name=profile_name)
    return SearchIndex(name=index_name, fields=fields, vector_search=vector_search)

def create_search_index(index_name, embedding_size):
    """Create a single search index with the specified name and embedding size"""
    # Make sure clients are initialized
    initialize_clients()
    
    # Get the proper index client for managing indices
    index_client = search_clients.get("index_client")
    if not index_client:
        raise ValueError("Index client not initialized properly")
    
    index = create_index_definition(index_name, embedding_size)
    index_client.create_or_update_index(index)
    print(f"Index '{index_name}' created or updated successfully.")

def get_documents_from_csv(csv_file_path, site, index_name):
    """Read CSV file and return documents for a specific index"""
    documents = []
    
    with open(csv_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            if line.strip():  # Skip empty lines
                try:
                    docs = documentsFromCSVLine(line, site)
                    for document in docs:
                        documents.append(document)
                except ValueError as e:
                    print(f"Skipping row due to error: {str(e)}")
    
    return documents

def upload_documents(index_name, documents, site):
    """Upload documents to the specified index in batches"""
    index_client = get_index_client(index_name)
    
    batch_size = 500 if index_name == "embeddings3072" else 1000

    total_batches = (len(documents) + batch_size - 1) // batch_size
    
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i+batch_size]
        current_batch = i // batch_size + 1
        index_client.upload_documents(batch)
        print(f"Uploaded batch {current_batch} of {total_batches} ({len(batch)} documents) to {index_name} from {site}")

def upload_data_from_csv(csv_file_path, site, index_name):
    """Process CSV file and upload documents to the specified index"""
    documents = get_documents_from_csv(csv_file_path, site, index_name)
    
    print(f"Found {len(documents)} documents from {site}")
    upload_documents(index_name, documents, site)
    
    return len(documents)

def main():
    import sys

    # Parse command line argument
    complete_reload = False
    if len(sys.argv) > 1:
        reload_arg = sys.argv[1].lower()
        if reload_arg == "reload=true":
            complete_reload = True
        elif reload_arg == "reload=false":
            complete_reload = False
        else:
            print("Invalid argument. Use 'reload=true' or 'reload=false'")
            sys.exit(1)
    else:
        print("Please provide reload argument: reload=true or reload=false")
        sys.exit(1)
    
    # Define indices with their embedding sizes
    indices = {
        "embeddings1536": 1536,
        "embeddings3072": 3072,
        "embeddings1536compact": 1536
    }
    
    if complete_reload:
        drop_all_indices(list(indices.keys()))
        # Create each index individually
        for index_name, embedding_size in indices.items():
            create_search_index(index_name, embedding_size)
    
    # Upload data from multiple CSV files, in these folders
   
    embedding_paths = [EMBEDDINGS_PATH_SMALL] #, EMBEDDINGS_PATH_LARGE, EMBEDDINGS_PATH_COMPACT]
    for path in embedding_paths:
        csv_files = [f.replace('.txt', '') for f in os.listdir(path) if f.endswith('.txt')]
        print(csv_files)
        total_documents = 0
        for csv_file in csv_files:
            print(f"\nProcessing file: {csv_file}")
            csv_file_path = f"{path}{csv_file}.txt"
            try:
                # In a real implementation, you would need to determine which index to use
                # For this example, we're using embeddings1536
                index_name = "embeddings1536"
                documents_added = upload_data_from_csv(csv_file_path, csv_file, index_name)
                total_documents += documents_added
            except Exception as e:
                print(f"Error processing file {csv_file}: {e}")
    
    print(f"\nData processing completed successfully. {total_documents} total documents added.")

if __name__ == "__main__":
  #   main()
    upload_data_from_csv("/Users/guha/mahi/data/sites/embeddings/small/eventbrite.txt", "eventbrite", "embeddings1536")
