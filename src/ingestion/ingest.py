"""
Data Ingestion Script for Azure AI Search
This script reads documents from the Data folder and indexes them into Azure AI Search.
"""

import os
from pathlib import Path
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType,
)
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Configuration
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "documents-index")
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")


def create_index(index_client: SearchIndexClient):
    """Create search index if it doesn't exist."""
    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            searchable=True,
        ),
        SearchableField(
            name="filename",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
        ),
    ]
    
    index = SearchIndex(name=INDEX_NAME, fields=fields)
    
    try:
        index_client.create_index(index)
        print(f"Index '{INDEX_NAME}' created successfully.")
    except Exception as e:
        print(f"Index '{INDEX_NAME}' already exists or error occurred: {e}")


def get_embedding(text: str) -> list:
    """Generate embedding for text using Azure OpenAI."""
    try:
        client = openai.AzureOpenAI(
            api_key=OPENAI_KEY,
            api_version=OPENAI_API_VERSION,
            azure_endpoint=OPENAI_ENDPOINT
        )
        
        response = client.embeddings.create(
            input=text,
            model=EMBEDDING_DEPLOYMENT
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def read_documents(data_dir: str) -> list:
    """Read all text documents from the data directory."""
    documents = []
    data_path = Path(data_dir)
    
    for file_path in data_path.glob("*.txt"):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            documents.append({
                "id": file_path.stem,
                "filename": file_path.name,
                "content": content
            })
    
    return documents


def upload_documents(search_client: SearchClient, documents: list):
    """Upload documents to Azure AI Search."""
    try:
        result = search_client.upload_documents(documents=documents)
        print(f"Uploaded {len(documents)} documents successfully.")
        for item in result:
            print(f"  - {item.key}: {item.succeeded}")
    except Exception as e:
        print(f"Error uploading documents: {e}")


def main():
    """Main function to ingest data into Azure AI Search."""
    print("Starting data ingestion...")
    
    # Validate configuration
    if not SEARCH_ENDPOINT or not SEARCH_KEY:
        print("Error: Azure Search credentials not configured. Please set AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY in .env file.")
        return
    
    # Initialize clients
    credential = AzureKeyCredential(SEARCH_KEY)
    index_client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=credential)
    search_client = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=credential)
    
    # Create index
    create_index(index_client)
    
    # Read documents from Data folder
    data_dir = os.path.join(os.path.dirname(__file__), "..", "Data")
    documents = read_documents(data_dir)
    
    if not documents:
        print("No documents found in Data directory.")
        return
    
    print(f"Found {len(documents)} documents to ingest.")
    
    # Upload documents to Azure AI Search
    upload_documents(search_client, documents)
    
    print("Data ingestion completed.")


if __name__ == "__main__":
    main()
