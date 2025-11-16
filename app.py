"""
Streamlit app for Mutual Fund FAQ Assistant
Complete frontend and backend integrated for Streamlit Cloud deployment
"""
import streamlit as st
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import backend modules
from vector_store.chroma_store import ChromaVectorStore
from retrieval.rag_chain import RAGChain
from api.validation import contains_pii, validate_comparison
import config

# Page configuration
st.set_page_config(
    page_title="Mutual Fund FAQ Assistant",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        border-bottom: 2px solid #e0e0e0;
        margin-bottom: 2rem;
    }
    .disclaimer {
        text-align: center;
        color: #666;
        font-style: italic;
        margin-top: 0.5rem;
    }
    .user-message {
        background-color: #007bff;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        text-align: right;
    }
    .assistant-message {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid #28a745;
    }
    .source-info {
        font-size: 0.85rem;
        color: #666;
        margin-top: 0.5rem;
        padding-top: 0.5rem;
        border-top: 1px solid #e0e0e0;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid #dc3545;
    }
    .warning-message {
        background-color: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid #ffc107;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "initialized" not in st.session_state:
    st.session_state.initialized = False
if "vector_store" not in st.session_state:
    st.session_state.vector_store = None
if "rag_chain" not in st.session_state:
    st.session_state.rag_chain = None
if "init_error" not in st.session_state:
    st.session_state.init_error = None

@st.cache_resource
def initialize_backend():
    """
    Initialize vector store and RAG chain.
    Cached to avoid reinitializing on every rerun.
    """
    try:
        # Check for API key
        if not config.GEMINI_API_KEY:
            return None, None, "GEMINI_API_KEY not found. Please set it in Streamlit secrets."
        
        # Initialize vector store
        vector_store = ChromaVectorStore()
        
        # Initialize RAG chain
        rag_chain = RAGChain(vector_store)
        
        return vector_store, rag_chain, None
    except Exception as e:
        return None, None, f"Initialization error: {str(e)}"

# Initialize backend
if not st.session_state.initialized:
    with st.spinner("Initializing backend..."):
        vector_store, rag_chain, error = initialize_backend()
        
        if error:
            st.session_state.init_error = error
        else:
            st.session_state.vector_store = vector_store
            st.session_state.rag_chain = rag_chain
            st.session_state.initialized = True

# Header
st.markdown('<div class="main-header"><h1>💰 Mutual Fund FAQ Assistant</h1></div>', unsafe_allow_html=True)
st.markdown('<p class="disclaimer">Welcome! I\'m here to help you with factual information about mutual funds. Facts-only. No investment advice.</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("ℹ️ Information")
    
    # Status
    if st.session_state.init_error:
        st.error(f"❌ {st.session_state.init_error}")
        st.info("💡 Go to Settings → Secrets and add GEMINI_API_KEY")
    elif st.session_state.initialized:
        st.success("✅ Backend Initialized")
        
        # Show collection info
        try:
            collection_info = st.session_state.vector_store.get_collection_info()
            st.info(f"📊 Documents in database: {collection_info.get('document_count', 0)}")
        except:
            pass
    else:
        st.warning("⏳ Initializing...")
    
    st.markdown("---")
    
    # Example Questions
    st.header("💡 Example Questions")
    example_questions = [
        "What is the expense ratio of Nippon India Large Cap Fund?",
        "What is the lock-in period for ELSS funds?",
        "What is the minimum SIP amount?",
        "What are the returns of Nippon India Flexi Cap Fund?",
        "What is the AUM of Nippon India Growth Mid Cap Fund?"
    ]
    
    for question in example_questions:
        if st.button(question, key=f"example_{hash(question)}", use_container_width=True):
            st.session_state.user_question = question
    
    st.markdown("---")
    
    # Clear chat
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        if st.session_state.rag_chain:
            st.session_state.rag_chain.clear_memory()
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    
    # Admin section
    with st.expander("🔧 Admin"):
        if st.button("🔄 Reinitialize Backend"):
            st.cache_resource.clear()
            st.session_state.initialized = False
            st.session_state.vector_store = None
            st.session_state.rag_chain = None
            st.rerun()
        
        if st.session_state.vector_store:
            if st.button("📊 Show Collection Info"):
                try:
                    info = st.session_state.vector_store.get_collection_info()
                    st.json(info)
                except Exception as e:
                    st.error(f"Error: {e}")
    
    st.caption("💡 Click example questions to ask them")

# Main content area
# Display chat history
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f'<div class="user-message"><strong>You:</strong> {message["content"]}</div>', unsafe_allow_html=True)
    elif message["role"] == "assistant":
        answer_html = f'<div class="assistant-message"><strong>Assistant:</strong> {message["content"]}'
        if "sources" in message and message["sources"]:
            sources_html = "<div class='source-info'><strong>Sources:</strong><ul>"
            for source in message["sources"][:3]:  # Show first 3 sources
                source_name = source.get("metadata", {}).get("source_file", "Unknown")
                sources_html += f"<li>{source_name}</li>"
            sources_html += "</ul></div>"
            answer_html += sources_html
        answer_html += "</div>"
        st.markdown(answer_html, unsafe_allow_html=True)
    elif message["role"] == "error":
        st.markdown(f'<div class="error-message"><strong>Error:</strong> {message["content"]}</div>', unsafe_allow_html=True)
    elif message["role"] == "warning":
        st.markdown(f'<div class="warning-message"><strong>Warning:</strong> {message["content"]}</div>', unsafe_allow_html=True)

# Chat input
if "user_question" in st.session_state:
    user_input = st.session_state.user_question
    del st.session_state.user_question
else:
    user_input = st.chat_input("Ask a question about mutual funds...")

if user_input:
    # Check if backend is initialized
    if not st.session_state.initialized or not st.session_state.rag_chain:
        error_msg = st.session_state.init_error or "Backend not initialized. Please check configuration."
        st.session_state.messages.append({
            "role": "error",
            "content": error_msg
        })
        st.rerun()
    
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Show user message
    st.markdown(f'<div class="user-message"><strong>You:</strong> {user_input}</div>', unsafe_allow_html=True)
    
    # Process query
    with st.spinner("Thinking..."):
        try:
            # Validate for PII
            pii_type = contains_pii(user_input)
            if pii_type:
                error_msg = f"I cannot process questions containing personally identifiable information (PII) such as {pii_type}. For your privacy and security, please do not enter sensitive information like PAN numbers, Aadhaar numbers, account details, phone numbers, or email addresses. Please rephrase your question without any sensitive information."
                st.session_state.messages.append({
                    "role": "warning",
                    "content": error_msg
                })
                st.rerun()
            
            # Validate comparison questions
            comparison_validation = validate_comparison(user_input)
            if not comparison_validation['valid']:
                st.session_state.messages.append({
                    "role": "warning",
                    "content": comparison_validation['reason']
                })
                st.rerun()
            
            # Query with retrieval
            result = st.session_state.rag_chain.query_with_retrieval(
                question=user_input,
                k=5,
                return_scores=False
            )
            
            answer = result.get("answer", "No answer received")
            sources = result.get("sources", [])
            
            # Format sources for display
            formatted_sources = []
            for source in sources:
                formatted_sources.append({
                    "content": source.get("content", "")[:200] + "..." if len(source.get("content", "")) > 200 else source.get("content", ""),
                    "metadata": source.get("metadata", {})
                })
            
            # Add assistant message to history
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "sources": formatted_sources
            })
            
            # Display answer
            answer_html = f'<div class="assistant-message"><strong>Assistant:</strong> {answer}'
            if formatted_sources:
                sources_html = "<div class='source-info'><strong>Sources:</strong><ul>"
                for source in formatted_sources[:3]:
                    source_name = source.get("metadata", {}).get("source_file", "Unknown")
                    sources_html += f"<li>{source_name}</li>"
                sources_html += "</ul></div>"
                answer_html += sources_html
            answer_html += "</div>"
            st.markdown(answer_html, unsafe_allow_html=True)
            
        except Exception as e:
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            st.session_state.messages.append({
                "role": "error",
                "content": error_msg
            })
            st.markdown(f'<div class="error-message"><strong>Error:</strong> {error_msg}</div>', unsafe_allow_html=True)
    
    st.rerun()

# Footer
st.markdown("---")
st.caption("💡 This assistant provides factual information only. Not investment advice.")

# Show initialization status in footer
if st.session_state.init_error:
    st.error(f"⚠️ Backend Error: {st.session_state.init_error}")
