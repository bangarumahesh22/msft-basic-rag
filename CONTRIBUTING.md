# Contributing to Azure RAG System

Thank you for your interest in contributing to this project! This document provides guidelines for extending and customizing the system.

## 🔧 Development Setup

1. Fork the repository
2. Clone your fork locally
3. Create a virtual environment: `python -m venv venv`
4. Activate the virtual environment
5. Install dependencies: `pip install -r requirements.txt`
6. Copy `.env.example` to `.env` and configure your Azure credentials

## 📝 Adding New Documents

To add new documents to the knowledge base:

1. Place your `.txt` files in the `src/Data/` directory
2. Run the ingestion script: `python src/ingestion/ingest.py`
3. Documents will be automatically indexed in Azure AI Search

**Supported formats:** Currently only `.txt` files are supported. To add support for other formats (PDF, DOCX, etc.), modify `src/ingestion/ingest.py`.

## 🔌 Extending the Backend

### Adding New Endpoints

Edit `src/BE/main.py` to add new endpoints:

```python
@app.get("/your-endpoint")
async def your_endpoint():
    # Your logic here
    return {"message": "Success"}
```

### Modifying the RAG Pipeline

The main RAG logic is in the `/query` endpoint. Key areas to customize:

1. **Search parameters**: Modify the `search_client.search()` call
2. **Context building**: Change how contexts are combined
3. **System prompt**: Update the system message to change AI behavior
4. **Memory length**: Adjust the conversation history slice `[-5:]`

### Adding Vector Search

To enable semantic/vector search:

1. Uncomment the embedding generation code in `src/ingestion/ingest.py`
2. Add vector field to the search index schema
3. Modify the search query to use vector search

## 🎨 Customizing the Frontend

### Changing the UI

Edit `src/FE/app.py` to customize:

- **Styling**: Modify the `st.set_page_config()` call
- **Layout**: Use Streamlit's layout options (columns, expanders, etc.)
- **Components**: Add new Streamlit widgets

### Adding Features

Example: Add a document upload feature

```python
uploaded_file = st.file_uploader("Upload a document")
if uploaded_file:
    # Process the file
    content = uploaded_file.read()
    # Send to backend for indexing
```

## 🧪 Testing

Currently, the project doesn't include automated tests. To add testing:

1. Create a `tests/` directory
2. Add test files for each component:
   - `test_ingestion.py`
   - `test_backend.py`
   - `test_frontend.py`
3. Use `pytest` for testing:
   ```bash
   pip install pytest
   pytest tests/
   ```

## 🔐 Security Best Practices

- Never commit `.env` files with real credentials
- Use Azure Key Vault for production deployments
- Implement authentication for the API endpoints
- Enable HTTPS in production
- Validate and sanitize user inputs
- Implement rate limiting

## 📊 Monitoring and Logging

To add logging:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Processing query")
```

## 🚀 Deployment

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ ./src/
CMD ["python", "src/BE/main.py"]
```

### Azure App Service

1. Create an Azure App Service
2. Configure environment variables in App Service settings
3. Deploy using Azure CLI or GitHub Actions

## 📖 Code Style

- Follow PEP 8 for Python code
- Use meaningful variable names
- Add docstrings to functions
- Keep functions small and focused
- Comment complex logic

## 🐛 Reporting Issues

When reporting issues, please include:

- Python version
- Operating system
- Steps to reproduce
- Error messages
- Expected vs actual behavior

## 💡 Feature Requests

We welcome feature requests! Please:

1. Check if the feature already exists
2. Open an issue with [FEATURE] prefix
3. Describe the use case
4. Suggest an implementation approach

## 📧 Contact

For questions or discussions, please open an issue on GitHub.

## 📄 License

By contributing, you agree that your contributions will be licensed under the same license as the project.
