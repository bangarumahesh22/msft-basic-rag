"""
FastAPI Backend for RAG System using Agent Framework
Provides query endpoint that uses Agent Framework and Azure AI Search

Required environment variables:
- AZURE_SEARCH_ENDPOINT: The endpoint URL for Azure AI Search
- AZURE_SEARCH_KEY: The API key for Azure AI Search
- AZURE_SEARCH_INDEX_NAME: The name of the search index (default: "documents-index")
- AZURE_OPENAI_ENDPOINT: The endpoint URL for Azure OpenAI (optional if using AzureCliCredential)
- AZURE_OPENAI_API_KEY: The API key for Azure OpenAI (optional if using AzureCliCredential)
- AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME: The deployment name for Azure OpenAI (optional)
"""

import os
import asyncio
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential

# Load environment variables
load_dotenv()

# Configuration
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "documents-index")
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME", os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"))

# Initialize FastAPI app
app = FastAPI(title="RAG Backend API with Agent Framework", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Azure clients
search_client = None

if SEARCH_ENDPOINT and SEARCH_KEY:
    credential = AzureKeyCredential(SEARCH_KEY)
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=credential
    )

# In-memory conversation storage (simple memory capability)
conversations = {}


class Message(BaseModel):
    role: str
    content: str


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = "default"
    max_results: Optional[int] = 3


class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    session_id: str


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "RAG Backend API with Agent Framework is running",
        "status": "healthy",
        "search_configured": search_client is not None,
        "agent_framework_configured": True  # Using AzureCliCredential if API key not provided
    }


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Query endpoint that performs RAG:
    1. Searches Azure AI Search for relevant documents
    2. Uses Agent Framework to generate answer based on retrieved context
    3. Maintains conversation memory per session
    """
    
    if not search_client:
        raise HTTPException(status_code=500, detail="Azure Search client not configured")
    
    try:
        # Search for relevant documents
        search_results = search_client.search(
            search_text=request.query,
            top=request.max_results
        )
        
        # Extract relevant context from search results
        contexts = []
        sources = []
        
        for result in search_results:
            contexts.append(result.get("content", ""))
            sources.append({
                "filename": result.get("filename", "Unknown"),
                "content": result.get("content", "")[:200] + "..."
            })
        
        # Build context string
        context_str = "\n\n".join(contexts) if contexts else "No relevant documents found."
        
        # Get or create conversation history for this session
        if request.session_id not in conversations:
            conversations[request.session_id] = []
        
        conversation_history = conversations[request.session_id]
        
        # Prepare system message with context
        system_message = (
            "You are a helpful AI assistant. Answer the user's question based on the provided context. "
            "If the context doesn't contain relevant information, say so politely. "
            "Keep your answers clear and concise."
        )
        
        # Build the full prompt with context and question
        user_message = f"Context:\n{context_str}\n\nQuestion: {request.query}"
        
        # Add conversation history for context
        history_messages = []
        for msg in conversation_history[-5:]:  # Keep last 5 exchanges
            history_messages.append(f"{msg['role']}: {msg['content']}")
        
        if history_messages:
            user_message = f"Previous conversation:\n" + "\n".join(history_messages) + f"\n\n{user_message}"
        
        # Initialize Agent Framework client
        try:
            agent_client = AzureOpenAIResponsesClient(
                endpoint=OPENAI_ENDPOINT,
                api_key=OPENAI_API_KEY,
                deployment_name=OPENAI_DEPLOYMENT,
                credential=AzureCliCredential() if not OPENAI_API_KEY else None
            )
        except Exception as e:
            raise HTTPException(status_code=500, 
                                detail=f"Failed to initialize Agent Framework client. Please ensure AZURE_OPENAI_ENDPOINT and either AZURE_OPENAI_API_KEY or Azure CLI credentials are set. If using Azure CLI, ensure you've run 'az login'. Error: {str(e)}")
        
        # Create agent with instructions
        agent = agent_client.create_agent(
            name="RAGAssistant",
            instructions=system_message
        )
        
        # Get response
        result = await agent.run(user_message)
        answer = str(result)
        
        # Update conversation history
        conversation_history.append({"role": "user", "content": request.query})
        conversation_history.append({"role": "assistant", "content": answer})
        conversations[request.session_id] = conversation_history
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            session_id=request.session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.delete("/conversation/{session_id}")
async def clear_conversation(session_id: str):
    """Clear conversation history for a specific session."""
    if session_id in conversations:
        del conversations[session_id]
        return {"message": f"Conversation history cleared for session {session_id}"}
    return {"message": f"No conversation found for session {session_id}"}


@app.get("/conversation/{session_id}")
async def get_conversation(session_id: str):
    """Get conversation history for a specific session."""
    return {
        "session_id": session_id,
        "messages": conversations.get(session_id, [])
    }


async def main():
    """Example of using Agent Framework directly"""
    
    if not OPENAI_DEPLOYMENT:
        print("Warning: AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME or AZURE_OPENAI_DEPLOYMENT_NAME not set.")
        print("Using default deployment name: 'gpt-4'")
    
    if not OPENAI_ENDPOINT:
        print("Error: AZURE_OPENAI_ENDPOINT not set.")
        print("Please set the AZURE_OPENAI_ENDPOINT environment variable.")
        return
    
    print(f"Using endpoint: {OPENAI_ENDPOINT}")
    print(f"Using deployment: {OPENAI_DEPLOYMENT}")
    
    try:
        # Initialize a chat agent with Azure OpenAI Responses
        agent = AzureOpenAIResponsesClient(
            endpoint=OPENAI_ENDPOINT,
            deployment_name=OPENAI_DEPLOYMENT,
            api_key=OPENAI_API_KEY,
            credential=AzureCliCredential() if not OPENAI_API_KEY else None
        ).create_agent(
            name="HaikuBot",
            instructions="You are an upbeat assistant that writes beautifully.",
        )
    except Exception as e:
        print(f"Error initializing Agent Framework client: {e}")
        print("\nPossible solutions:")
        print("1. Run 'az login' to authenticate with Azure CLI")
        print("2. Set AZURE_OPENAI_API_KEY environment variable")
        print("3. Set AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME environment variable")
        print("4. Set AZURE_OPENAI_ENDPOINT environment variable")
        return

    print(await agent.run("Write a haiku about Microsoft Agent Framework."))


if __name__ == "__main__":
    if len(os.sys.argv) > 1 and os.sys.argv[1] == "haiku":
        # Run the haiku example directly
        asyncio.run(main())
    else:
        # Run as FastAPI server
        import uvicorn
        port = int(os.getenv("BACKEND_PORT", 8000))
        uvicorn.run(app, host="0.0.0.0", port=port)