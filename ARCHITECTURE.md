# Azure RAG System Architecture

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION                             │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STREAMLIT FRONTEND (Port 8501)                    │
│  • Chat Interface                                                    │
│  • Session Management                                                │
│  • Source Display                                                    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                              HTTP POST
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND (Port 8000)                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              POST /query (Main RAG Endpoint)                 │   │
│  │  1. Receive user query                                       │   │
│  │  2. Search Azure AI Search                                   │   │
│  │  3. Build context from results                               │   │
│  │  4. Add conversation memory                                  │   │
│  │  5. Call Azure OpenAI                                        │   │
│  │  6. Return answer + sources                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  Other Endpoints:                                                    │
│  • GET /             - Health check                                  │
│  • GET /conversation/{id}  - Get history                            │
│  • DELETE /conversation/{id}  - Clear history                       │
└─────────────────────────────────────────────────────────────────────┘
                    │                           │
                    │                           │
                    ▼                           ▼
┌───────────────────────────────┐  ┌──────────────────────────────┐
│   AZURE AI SEARCH             │  │   AZURE OPENAI SERVICE       │
│                               │  │                              │
│  • Document Index             │  │  • GPT-3.5/GPT-4 Model       │
│  • Full-text Search           │  │  • Chat Completions          │
│  • Keyword Matching           │  │  • Context-aware Responses   │
│  • Returns top N results      │  │  • Embedding Generation      │
└───────────────────────────────┘  └──────────────────────────────┘
                    ▲
                    │
            ┌───────┴────────┐
            │ Initial Setup  │
            └───────┬────────┘
                    │
┌───────────────────────────────────────────────────────────────────┐
│                    DATA INGESTION SCRIPT                           │
│  • Reads documents from src/Data/                                  │
│  • Creates Azure AI Search index                                   │
│  • Uploads documents to index                                      │
└───────────────────────────────────────────────────────────────────┘
                    ▲
                    │
┌───────────────────────────────────────────────────────────────────┐
│                    MOCK DATA (src/Data/)                           │
│  • document1.txt  - Azure AI Search info                           │
│  • document2.txt  - Azure OpenAI info                              │
│  • document3.txt  - RAG concepts                                   │
└───────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Setup Phase (One-time)
```
Documents (txt files) → Ingestion Script → Azure AI Search Index
```

### 2. Query Phase (Every request)
```
User Question → Frontend → Backend → Azure AI Search (retrieval)
                                   → Azure OpenAI (generation)
                                   → Backend (combine results)
                                   → Frontend (display answer)
```

### 3. Memory Phase (Multi-turn conversation)
```
Backend stores conversation history in memory:
- User query 1 + Assistant response 1
- User query 2 + Assistant response 2
- ... (last 5 exchanges kept)

Each new query includes previous context for coherent conversation.
```

## Component Responsibilities

### Ingestion (src/ingestion/ingest.py)
- Read text files from Data folder
- Create search index schema
- Upload documents to Azure AI Search
- Handle errors gracefully

### Backend (src/BE/main.py)
- FastAPI web server
- Query endpoint with RAG logic
- Session-based conversation memory
- Integration with Azure services
- Error handling and validation

### Frontend (src/FE/app.py)
- Streamlit chat interface
- User input handling
- Response display with sources
- Session management
- Backend health monitoring

### Data (src/Data/)
- Sample documents in text format
- Easy to replace with your own content
- Supports any .txt file

## Technology Stack

```
┌──────────────────────────────────────────────────────────────┐
│  Python 3.8+                                                  │
├──────────────────────────────────────────────────────────────┤
│  Web Frameworks:                                              │
│    • FastAPI     - Backend REST API                           │
│    • Streamlit   - Frontend UI                                │
│    • Uvicorn     - ASGI server                                │
├──────────────────────────────────────────────────────────────┤
│  Azure SDKs:                                                  │
│    • azure-search-documents  - Search integration             │
│    • azure-identity          - Authentication                 │
│    • openai                  - Azure OpenAI integration       │
├──────────────────────────────────────────────────────────────┤
│  Utilities:                                                   │
│    • pydantic       - Data validation                         │
│    • python-dotenv  - Environment management                  │
│    • requests       - HTTP client                             │
└──────────────────────────────────────────────────────────────┘
```

## Security Considerations

```
┌──────────────────────────────────────────────────────────────┐
│  Credentials:                                                 │
│    • Stored in .env (not committed to git)                    │
│    • .env.example provides template                           │
│    • Use Azure Key Vault in production                        │
├──────────────────────────────────────────────────────────────┤
│  API Security:                                                │
│    • CORS enabled (configure for production)                  │
│    • Input validation with Pydantic                           │
│    • Error handling prevents information leakage              │
├──────────────────────────────────────────────────────────────┤
│  Dependencies:                                                │
│    • Scanned for known vulnerabilities                        │
│    • FastAPI updated to patched version (0.109.1)             │
└──────────────────────────────────────────────────────────────┘
```

## Deployment Options

### Option 1: Local Development
```bash
# Terminal 1: Backend
python src/BE/main.py

# Terminal 2: Frontend  
streamlit run src/FE/app.py
```

### Option 2: Docker
```dockerfile
# Backend container on port 8000
# Frontend container on port 8501
# Both connected via network
```

### Option 3: Azure
```
• Backend: Azure App Service or Azure Container Apps
• Frontend: Azure Static Web Apps or App Service
• Search: Azure AI Search (already in cloud)
• OpenAI: Azure OpenAI Service (already in cloud)
```

## Scalability

- **Backend**: Stateless (except in-memory sessions), can be scaled horizontally
- **Frontend**: Multiple instances can connect to same backend
- **Azure AI Search**: Managed service, auto-scales
- **Azure OpenAI**: Managed service with rate limits

## Monitoring

Add monitoring by:
1. Integrating Application Insights
2. Logging requests and responses
3. Tracking query latency
4. Monitoring Azure service health
5. Setting up alerts for errors
