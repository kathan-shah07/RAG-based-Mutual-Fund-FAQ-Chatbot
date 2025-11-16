"""
Streamlit app for Mutual Fund FAQ Assistant
Simple local deployment with automatic scraper scheduling
"""
import streamlit as st
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import backend modules
from vector_store.chroma_store import ChromaVectorStore
from retrieval.rag_chain import RAGChain
from api.validation import contains_pii, validate_comparison
from scripts.scheduled_scraper import ScheduledScraper
import config

# Page configuration
st.set_page_config(
    page_title="Mutual Fund FAQ Assistant",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Hide Streamlit default elements
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "initialized" not in st.session_state:
    st.session_state.initialized = False
if "vector_store" not in st.session_state:
    st.session_state.vector_store = None
if "rag_chain" not in st.session_state:
    st.session_state.rag_chain = None
if "init_error" not in st.session_state:
    st.session_state.init_error = None
if "scraper" not in st.session_state:
    st.session_state.scraper = None
if "scraper_started" not in st.session_state:
    st.session_state.scraper_started = False
if "messages" not in st.session_state:
    st.session_state.messages = []

@st.cache_resource
def initialize_backend():
    """
    Initialize vector store and RAG chain.
    Cached to avoid reinitializing on every rerun.
    """
    try:
        # Check for API key
        if not config.GEMINI_API_KEY:
            return None, None, None, "GEMINI_API_KEY not found. Please set it in Streamlit secrets or .env file."
        
        # Initialize vector store
        vector_store = ChromaVectorStore()
        
        # Initialize RAG chain
        rag_chain = RAGChain(vector_store)
        
        # Initialize scraper (optional, may fail if config not found)
        scraper = None
        try:
            scraper = ScheduledScraper(config_path="scraper_config.json")
        except Exception as e:
            # Scraper initialization is optional
            pass
        
        return vector_store, rag_chain, scraper, None
    except Exception as e:
        return None, None, None, f"Initialization error: {str(e)}"

# Initialize backend
if not st.session_state.initialized:
    with st.spinner("Initializing backend..."):
        vector_store, rag_chain, scraper, error = initialize_backend()
        
        if error:
            st.session_state.init_error = error
        else:
            st.session_state.vector_store = vector_store
            st.session_state.rag_chain = rag_chain
            st.session_state.scraper = scraper
            st.session_state.initialized = True

# Start scheduled scraper in background if not already started
if st.session_state.scraper and not st.session_state.scraper_started:
    try:
        # Start the scraper scheduler in a background thread
        st.session_state.scraper.start()
        st.session_state.scraper_started = True
    except Exception as e:
        # Scraper start failure is not critical, continue
        pass

# Header
st.title("💰 Mutual Fund FAQ Assistant")
st.markdown("Welcome! I'm here to help you with factual information about mutual funds.")
st.caption("Facts-only. No investment advice.")

# Sidebar
with st.sidebar:
    st.header("ℹ️ Information")
    
    # Status
    if st.session_state.init_error:
        st.error(f"❌ {st.session_state.init_error}")
        st.info("💡 Set GEMINI_API_KEY in Streamlit secrets or .env file")
    elif st.session_state.initialized:
        st.success("✅ Backend Initialized")
        
        # Show collection info
        try:
            collection_info = st.session_state.vector_store.get_collection_info()
            st.info(f"📊 Documents in database: {collection_info.get('document_count', 0)}")
        except:
            pass
        
        # Show scraper status if available
        if st.session_state.scraper:
            try:
                scraper_status = st.session_state.scraper.get_status()
                if scraper_status.get("is_running"):
                    st.warning(f"🔄 {scraper_status.get('message', 'Running...')}")
                    if scraper_status.get("urls_total", 0) > 0:
                        processed = len(scraper_status.get("urls_processed", []))
                        total = scraper_status.get("urls_total", 0)
                        st.progress(processed / total if total > 0 else 0)
                        st.caption(f"{processed}/{total} URLs processed")
                else:
                    schedule_config = st.session_state.scraper.config.get("schedule", {})
                    if schedule_config.get("enabled", False):
                        interval_hours = schedule_config.get("interval_hours", 1)
                        st.caption(f"⏰ Scraper scheduled: Every {interval_hours} hour(s)")
            except Exception:
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
            st.session_state.messages.append({"role": "user", "content": question})
            # Process the question
            if st.session_state.rag_chain:
                with st.spinner("Thinking..."):
                    try:
                        result = st.session_state.rag_chain.query_with_retrieval(
                            question=question,
                            k=5,
                            return_scores=False
                        )
                        answer = result.get("answer", "No answer received")
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    except Exception as e:
                        st.session_state.messages.append({
                            "role": "error",
                            "content": f"Error: {str(e)}"
                        })
                st.rerun()
    
    st.markdown("---")
    
    # Clear chat
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        if st.session_state.rag_chain:
            st.session_state.rag_chain.clear_memory()
        st.session_state.messages = []
        st.rerun()

# Display chat history
for message in st.session_state.messages:
    if message["role"] == "user":
        with st.chat_message("user"):
            st.write(message["content"])
    elif message["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(message["content"])
            # Show sources if available
            if "sources" in message and message["sources"]:
                with st.expander("📚 Sources"):
                    for i, source in enumerate(message["sources"][:3], 1):
                        source_name = source.get("metadata", {}).get("source_file", "Unknown")
                        st.caption(f"{i}. {source_name}")
    elif message["role"] == "error":
        st.error(message["content"])

# Chat input
if prompt := st.chat_input("Ask a question about mutual funds..."):
    # Check if backend is initialized
    if not st.session_state.initialized or not st.session_state.rag_chain:
        error_msg = st.session_state.init_error or "Backend not initialized. Please check configuration."
        st.error(error_msg)
        st.stop()
    
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.write(prompt)
    
    # Process query
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Validate for PII
                pii_type = contains_pii(prompt)
                if pii_type:
                    error_msg = f"I cannot process questions containing personally identifiable information (PII) such as {pii_type}. For your privacy and security, please do not enter sensitive information like PAN numbers, Aadhaar numbers, account details, phone numbers, or email addresses. Please rephrase your question without any sensitive information."
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "error",
                        "content": error_msg
                    })
                    st.stop()
                
                # Validate comparison questions
                comparison_validation = validate_comparison(prompt)
                if not comparison_validation['valid']:
                    st.warning(comparison_validation['reason'])
                    st.session_state.messages.append({
                        "role": "error",
                        "content": comparison_validation['reason']
                    })
                    st.stop()
                
                # Query with retrieval
                result = st.session_state.rag_chain.query_with_retrieval(
                    question=prompt,
                    k=5,
                    return_scores=False
                )
                
                answer = result.get("answer", "No answer received")
                sources = result.get("sources", [])
                
                # Display answer
                st.markdown(answer)
                
                # Show sources
                if sources:
                    with st.expander("📚 Sources"):
                        for i, source in enumerate(sources[:3], 1):
                            source_name = source.get("metadata", {}).get("source_file", "Unknown")
                            source_url = source.get("metadata", {}).get("source_url", "")
                            if source_url:
                                st.markdown(f"{i}. [{source_name}]({source_url})")
                            else:
                                st.caption(f"{i}. {source_name}")
                
                # Add assistant message to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources
                })
                
            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "error",
                    "content": error_msg
                })

# Footer
st.markdown("---")
st.caption("💡 This assistant provides factual information only. Not investment advice.")

# Note: Scraper status is checked on each render above
# Streamlit will naturally rerun when user interacts with the page

