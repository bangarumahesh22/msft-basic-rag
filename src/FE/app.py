"""
Streamlit Frontend for RAG Q&A System
Simple interface for querying the backend API
"""

import os
import requests
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BACKEND_HOST = os.getenv("BACKEND_HOST", "localhost")
BACKEND_PORT = os.getenv("BACKEND_PORT", "8000")

# Construct the backend URL based on the host value and environment
if BACKEND_HOST == "localhost" or BACKEND_HOST.startswith("127.0.0.1"):
    # Local development - use HTTP and include port
    BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
elif BACKEND_HOST.startswith("http://") or BACKEND_HOST.startswith("https://"):
    # Host already includes protocol - use as is
    BACKEND_URL = BACKEND_HOST
elif "azurecontainerapps.io" in BACKEND_HOST:
    # Azure Container Apps domain - always use HTTPS without port
    BACKEND_URL = f"https://{BACKEND_HOST}"
else:
    # Default case - use HTTP with port
    BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

# Print for debugging
print(f"Backend URL: {BACKEND_URL}")

# Page configuration
st.set_page_config(
    page_title="Azure RAG Q&A System",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())

# Title and description
st.title("🤖 Azure RAG Q&A System")
st.markdown("""
This application uses Azure AI Search and Azure OpenAI to answer questions based on your documents.
Ask any question and the system will search relevant documents and generate an answer.
""")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    st.info(f"**Session ID:** {st.session_state.session_id[:8]}...")
    
    max_results = st.slider("Max search results", min_value=1, max_value=5, value=3)
    
    if st.button("🗑️ Clear Conversation"):
        try:
            response = requests.delete(f"{BACKEND_URL}/conversation/{st.session_state.session_id}")
            if response.status_code == 200:
                st.session_state.messages = []
                st.success("Conversation cleared!")
                st.rerun()
        except Exception as e:
            st.error(f"Error clearing conversation: {e}")
    
    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
    This RAG system combines:
    - 🔍 Azure AI Search for document retrieval
    - 🧠 Azure OpenAI for response generation
    - 💬 Conversation memory for context
    """)

# Check backend health
try:
    health_response = requests.get(f"{BACKEND_URL}/", timeout=2)
    if health_response.status_code == 200:
        health_data = health_response.json()
        if not health_data.get("search_configured") or not health_data.get("openai_configured"):
            st.warning("⚠️ Backend is running but not fully configured. Please check your .env file.")
    else:
        st.error("❌ Backend is not responding properly.")
except Exception as e:
    st.error(f"❌ Cannot connect to backend at {BACKEND_URL}. Please ensure the backend is running.")
    st.code(f"Error: {e}")
    st.stop()

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Display sources if available
        if message["role"] == "assistant" and "sources" in message:
            if message["sources"]:
                with st.expander("📚 View Sources"):
                    for i, source in enumerate(message["sources"], 1):
                        st.markdown(f"**Source {i}: {source['filename']}**")
                        st.text(source['content'])
                        st.markdown("---")

# Chat input
if prompt := st.chat_input("Ask a question about your documents..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Call backend API
                response = requests.post(
                    f"{BACKEND_URL}/query",
                    json={
                        "query": prompt,
                        "session_id": st.session_state.session_id,
                        "max_results": max_results
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data["answer"]
                    sources = data["sources"]
                    
                    # Display answer
                    st.markdown(answer)
                    
                    # Display sources
                    if sources:
                        with st.expander("📚 View Sources"):
                            for i, source in enumerate(sources, 1):
                                st.markdown(f"**Source {i}: {source['filename']}**")
                                st.text(source['content'])
                                st.markdown("---")
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    })
                else:
                    error_msg = f"Error: {response.status_code} - {response.text}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                    
            except requests.exceptions.Timeout:
                error_msg = "Request timed out. Please try again."
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
            except Exception as e:
                error_msg = f"Error calling backend: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.8em;'>
    Powered by Azure AI Search & Azure OpenAI | Built with FastAPI & Streamlit
</div>
""", unsafe_allow_html=True)
