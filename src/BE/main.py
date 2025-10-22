"""
FastAPI Backend for RAG System
Provides query endpoint that uses Azure OpenAI and Azure AI Search
"""

import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "documents-index")
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")

# Initialize FastAPI app
app = FastAPI(title="RAG Backend API", version="1.0.0")

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
openai_client = None

if SEARCH_ENDPOINT and SEARCH_KEY:
    credential = AzureKeyCredential(SEARCH_KEY)
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=credential
    )

if OPENAI_ENDPOINT and OPENAI_KEY:
    # Initialize the ChatCompletionsClient
    openai_client = ChatCompletionsClient(
        endpoint=f"{OPENAI_ENDPOINT}/openai/deployments/{OPENAI_DEPLOYMENT}",
        credential=AzureKeyCredential(OPENAI_KEY),
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
        "message": "RAG Backend API is running",
        "status": "healthy",
        "search_configured": search_client is not None,
        "openai_configured": openai_client is not None
    }


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Query endpoint that performs RAG:
    1. Searches Azure AI Search for relevant documents
    2. Uses Azure OpenAI to generate answer based on retrieved context
    3. Maintains conversation memory per session
    """
    
    if not search_client:
        raise HTTPException(status_code=500, detail="Azure Search client not configured")
    
    if not openai_client:
        raise HTTPException(status_code=500, detail="Azure OpenAI client not configured")
    
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
        
        # Build messages for Azure AI Inference API
        messages = [
            SystemMessage(content=(
                "You are a helpful AI assistant. Answer the user's question based on the provided context. "
                "If the context doesn't contain relevant information, say so politely. "
                "Keep your answers clear and concise."
            ))
        ]
        
        # Add conversation history (memory capability)
        for msg in conversation_history[-5:]:  # Keep last 5 exchanges
            if msg["role"] == "user":
                messages.append(UserMessage(content=msg["content"]))
            else:
                # For assistant messages we need to use the content but keep it as a system message
                # since the Azure AI Inference API only supports SystemMessage and UserMessage
                messages.append(SystemMessage(content=f"Assistant: {msg['content']}"))
        
        # Add current query with context
        user_message = f"Context:\n{context_str}\n\nQuestion: {request.query}"
        messages.append(UserMessage(content=user_message))
        
        # Call Azure AI Inference API
        response = openai_client.complete(
            messages=messages,
            max_tokens=500,
            temperature=0.7,
            top_p=1.0,
            model=OPENAI_DEPLOYMENT
        )
        
        answer = response.choices[0].message.content
        
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


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
