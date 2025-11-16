"""
Streamlit app for Mutual Fund FAQ Assistant
Complete frontend and backend integrated for Streamlit Cloud deployment
Includes: Chat, Ingestion, and Scraper functionality
"""
import streamlit as st
import os
import sys
import json
import threading
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import backend modules
from vector_store.chroma_store import ChromaVectorStore
from retrieval.rag_chain import RAGChain
from api.validation import contains_pii, validate_comparison
from ingestion.document_loader import JSONDocumentLoader
from ingestion.chunker import DocumentChunker
from scripts.scheduled_scraper import ScheduledScraper
from scrapers.groww_scraper import load_config
import config

# Page configuration
st.set_page_config(
    page_title="Mutual Fund FAQ Assistant",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS adapted from static/styles.css
st.markdown("""
<style>
    :root {
        --primary-color: #6366f1;
        --primary-dark: #4f46e5;
        --primary-light: #818cf8;
        --secondary-color: #10b981;
        --accent-color: #f59e0b;
        --error-color: #ef4444;
        --warning-color: #f59e0b;
        --info-color: #3b82f6;
    }
    
    .main-header {
        text-align: center;
        padding: 2rem 0;
        border-bottom: 2px solid #e5e7eb;
        margin-bottom: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .disclaimer {
        text-align: center;
        color: #6b7280;
        font-style: italic;
        margin-top: 0.5rem;
        font-size: 0.9rem;
    }
    
    .user-message {
        background: linear-gradient(135deg, #6366f1 0%, #818cf8 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 16px;
        margin: 1rem 0;
        text-align: right;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        max-width: 80%;
        margin-left: auto;
    }
    
    .assistant-message {
        background: #ffffff;
        padding: 1rem 1.5rem;
        border-radius: 16px;
        margin: 1rem 0;
        border-left: 4px solid #10b981;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        max-width: 80%;
    }
    
    .source-info {
        font-size: 0.85rem;
        color: #6b7280;
        margin-top: 0.75rem;
        padding-top: 0.75rem;
        border-top: 1px solid #e5e7eb;
    }
    
    .source-info ul {
        margin: 0.5rem 0 0 1.5rem;
        padding: 0;
    }
    
    .source-info li {
        margin: 0.25rem 0;
    }
    
    .error-message {
        background-color: #fef2f2;
        color: #991b1b;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        border-left: 4px solid #ef4444;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }
    
    .warning-message {
        background-color: #fffbeb;
        color: #92400e;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        border-left: 4px solid #f59e0b;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }
    
    .status-indicator {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem 1rem;
        background: #f0f9ff;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 3px solid #3b82f6;
    }
    
    .status-spinner {
        width: 16px;
        height: 16px;
        border: 2px solid #e5e7eb;
        border-top-color: #3b82f6;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    
    .progress-bar-container {
        margin-top: 0.5rem;
        background: #e5e7eb;
        border-radius: 4px;
        height: 8px;
        overflow: hidden;
    }
    
    .progress-bar-fill {
        background: linear-gradient(90deg, #6366f1, #818cf8);
        height: 100%;
        transition: width 0.3s ease;
        border-radius: 4px;
    }
    
    .example-question-btn {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 0.75rem;
        margin: 0.25rem 0;
        cursor: pointer;
        transition: all 0.2s;
        text-align: left;
        width: 100%;
    }
    
    .example-question-btn:hover {
        background: #f3f4f6;
        border-color: #6366f1;
        transform: translateX(4px);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.75rem 1.5rem;
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
if "scraper" not in st.session_state:
    st.session_state.scraper = None
if "scraper_status" not in st.session_state:
    st.session_state.scraper_status = {
        "is_running": False,
        "current_operation": None,
        "progress": None,
        "message": "Idle",
        "urls_processed": [],
        "urls_total": 0,
        "error": None
    }

@st.cache_resource
def initialize_backend():
    """
    Initialize vector store and RAG chain.
    Cached to avoid reinitializing on every rerun.
    """
    try:
        # Check for API key
        if not config.GEMINI_API_KEY:
            return None, None, None, "GEMINI_API_KEY not found. Please set it in Streamlit secrets."
        
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
            st.session_state.scraper = None
            st.rerun()
        
        if st.session_state.vector_store:
            if st.button("📊 Show Collection Info"):
                try:
                    info = st.session_state.vector_store.get_collection_info()
                    st.json(info)
                except Exception as e:
                    st.error(f"Error: {e}")
    
    st.caption("💡 Click example questions to ask them")

# Main content area - Tabs for Chat, Ingestion, and Scraper
tab1, tab2, tab3 = st.tabs(["💬 Chat", "📥 Ingest Data", "🕷️ Scraper"])

with tab1:
    # Chat page
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

with tab2:
    # Ingestion page
    st.header("📥 Data Ingestion")
    st.markdown("Ingest JSON documents from the data directory into ChromaDB vector store.")
    
    if not st.session_state.initialized or not st.session_state.vector_store:
        st.error("❌ Backend not initialized. Please check configuration and ensure GEMINI_API_KEY is set.")
        st.info("💡 Go to Settings → Secrets and add GEMINI_API_KEY")
    else:
        # Show current collection status
        st.markdown("---")
        st.subheader("📊 Current Collection Status")
        try:
            collection_info = st.session_state.vector_store.get_collection_info()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Collection Name", collection_info.get('collection_name', 'N/A'))
            with col2:
                st.metric("Total Documents", collection_info.get('document_count', 0))
            with col3:
                st.metric("Database Path", collection_info.get('db_path', 'N/A'))
            
            if collection_info.get('document_count', 0) == 0:
                st.warning("⚠️ No documents in database. Please ingest data first.")
        except Exception as e:
            st.error(f"Error getting collection info: {e}")
        
        st.markdown("---")
        
        # Ingestion form
        with st.form("ingestion_form"):
            st.subheader("🚀 Ingestion Settings")
            
            # Data directory selection
            default_data_dir = config.DATA_DIR
            data_dir = st.text_input(
                "Data Directory",
                value=default_data_dir,
                help="Path to directory containing JSON files to ingest"
            )
            
            # Show info about data directory
            data_path = Path(data_dir)
            if data_path.exists():
                json_files = list(data_path.rglob("*.json"))
                if json_files:
                    st.success(f"✅ Found {len(json_files)} JSON file(s) in {data_dir}")
                    with st.expander(f"📁 View Files ({len(json_files)})"):
                        for json_file in json_files[:10]:  # Show first 10
                            st.text(f"• {json_file.name}")
                        if len(json_files) > 10:
                            st.caption(f"... and {len(json_files) - 10} more files")
                else:
                    st.warning(f"⚠️ No JSON files found in {data_dir}")
            else:
                st.error(f"❌ Data directory not found: {data_dir}")
            
            # Upsert option
            col1, col2 = st.columns(2)
            with col1:
                upsert_mode = st.checkbox(
                    "Upsert Mode",
                    value=True,
                    help="If enabled, updates existing documents. If disabled, only adds new documents."
                )
            with col2:
                show_details = st.checkbox(
                    "Show Detailed Progress",
                    value=True,
                    help="Show step-by-step progress during ingestion"
                )
            
            # Submit button
            submitted = st.form_submit_button("🚀 Start Ingestion", use_container_width=True, type="primary")
            
            if submitted:
                # Validate data directory
                if not data_path.exists():
                    st.error(f"❌ Data directory not found: {data_dir}")
                    st.info("💡 Make sure the data directory path is correct.")
                    st.stop()
                
                # Check for JSON files
                json_files = list(data_path.rglob("*.json"))
                if not json_files:
                    st.warning(f"⚠️ No JSON files found in {data_dir}")
                    st.info("💡 Make sure your JSON files are in the data directory.")
                    st.stop()
                
                # Show progress
                progress_bar = st.progress(0)
                status_text = st.empty()
                details_container = st.container() if show_details else None
                
                try:
                    # Step 1: Load documents
                    if show_details:
                        with details_container:
                            status_text.text("📂 Step 1/4: Loading documents...")
                    progress_bar.progress(10)
                    
                    loader = JSONDocumentLoader(data_dir)
                    documents = loader.load_documents()
                    
                    if not documents:
                        st.error("❌ No documents loaded. Check JSON file format.")
                        progress_bar.empty()
                        status_text.empty()
                        st.stop()
                    
                    if show_details:
                        with details_container:
                            st.success(f"✅ Loaded {len(documents)} document(s)")
                    progress_bar.progress(30)
                    
                    # Step 2: Chunk documents
                    if show_details:
                        with details_container:
                            status_text.text("✂️ Step 2/4: Chunking documents...")
                    progress_bar.progress(40)
                    
                    chunker = DocumentChunker()
                    chunks = chunker.chunk_documents(documents)
                    
                    if show_details:
                        with details_container:
                            st.success(f"✅ Created {len(chunks)} chunk(s) from {len(documents)} document(s)")
                    progress_bar.progress(60)
                    
                    # Step 3: Store in vector database
                    if show_details:
                        with details_container:
                            status_text.text(f"💾 Step 3/4: {'Upserting' if upsert_mode else 'Adding'} documents to vector store...")
                    progress_bar.progress(70)
                    
                    if upsert_mode:
                        doc_ids = st.session_state.vector_store.upsert_documents(chunks)
                        action = "upserted"
                    else:
                        doc_ids = st.session_state.vector_store.add_documents(chunks)
                        action = "added"
                    
                    progress_bar.progress(90)
                    
                    # Step 4: Get collection info
                    if show_details:
                        with details_container:
                            status_text.text("📊 Step 4/4: Getting collection information...")
                    collection_info = st.session_state.vector_store.get_collection_info()
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Ingestion complete!")
                    
                    # Display results
                    st.markdown("---")
                    st.subheader("🎉 Ingestion Results")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Documents Processed", len(documents))
                    with col2:
                        st.metric("Chunks Created", len(chunks))
                    with col3:
                        st.metric("Chunks Stored", len(doc_ids))
                    with col4:
                        st.metric("Total in Database", collection_info.get('document_count', 0))
                    
                    # Show collection details
                    with st.expander("📋 Collection Details"):
                        st.json(collection_info)
                    
                    # Show file list
                    with st.expander(f"📁 Processed Files ({len(json_files)})"):
                        for json_file in json_files:
                            st.text(f"• {json_file.name}")
                    
                    st.success(f"🎉 Successfully {action} {len(doc_ids)} chunk(s) to vector store!")
                    
                    # Clear RAG chain cache to refresh with new data
                    if st.session_state.rag_chain:
                        st.session_state.rag_chain.clear_memory()
                    
                    # Refresh sidebar collection info
                    st.rerun()
                    
                except FileNotFoundError as e:
                    st.error(f"❌ File not found: {str(e)}")
                    st.info("💡 Make sure the data directory path is correct.")
                    progress_bar.empty()
                    status_text.empty()
                except ValueError as e:
                    st.error(f"❌ Validation error: {str(e)}")
                    progress_bar.empty()
                    status_text.empty()
                except Exception as e:
                    st.error(f"❌ Error during ingestion: {str(e)}")
                    st.exception(e)
                    progress_bar.empty()
                    status_text.empty()

with tab3:
    # Scraper page
    st.header("🕷️ Web Scraper")
    st.markdown("Scrape mutual fund data from Groww and ingest into the vector database.")
    
    if not st.session_state.initialized:
        st.error("❌ Backend not initialized. Please check configuration.")
    elif not st.session_state.scraper:
        st.warning("⚠️ Scraper not available. Make sure `scraper_config.json` exists.")
        st.info("💡 The scraper requires Playwright and browser dependencies.")
    else:
        # Load scraper config
        try:
            scraper_config = load_config("scraper_config.json")
            schedule_config = scraper_config.get("schedule", {})
            urls_config = scraper_config.get("urls", [])
            scraper_settings = scraper_config.get("scraper_settings", {})
        except Exception as e:
            st.error(f"❌ Error loading scraper config: {e}")
            scraper_config = None
            schedule_config = {}
            urls_config = []
            scraper_settings = {}
        
        # Show scraper status
        st.markdown("---")
        st.subheader("📊 Scraper Status")
        
        # Get current status
        if st.session_state.scraper:
            status = st.session_state.scraper.get_status()
            st.session_state.scraper_status = status
            
            col1, col2 = st.columns(2)
            with col1:
                if status.get("is_running"):
                    st.warning(f"🔄 {status.get('current_operation', 'Running').title()}")
                else:
                    st.success("✅ Idle")
            
            with col2:
                if status.get("start_time"):
                    start_time = datetime.fromisoformat(status["start_time"])
                    st.caption(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Show progress if running
            if status.get("is_running") and status.get("urls_total", 0) > 0:
                processed = len(status.get("urls_processed", []))
                total = status.get("urls_total", 0)
                progress = processed / total if total > 0 else 0
                
                st.progress(progress)
                st.caption(f"{status.get('message', 'Processing...')} ({processed}/{total} URLs)")
                
                # Show processed URLs
                if status.get("urls_processed"):
                    with st.expander(f"📋 Processed URLs ({processed})"):
                        for url_info in status.get("urls_processed", [])[-10:]:  # Show last 10
                            url = url_info.get("url", "Unknown")
                            url_status = url_info.get("status", "unknown")
                            status_icon = "✅" if url_status == "success" else "❌"
                            st.text(f"{status_icon} {url[:60]}...")
            
            # Show error if any
            if status.get("error"):
                st.error(f"❌ Error: {status.get('error')}")
        
        st.markdown("---")
        
        # Scraper configuration display
        if scraper_config:
            st.subheader("⚙️ Scraper Configuration")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total URLs", len(urls_config))
                st.metric("Output Directory", scraper_settings.get("output_dir", "N/A"))
            with col2:
                schedule_enabled = schedule_config.get("enabled", False)
                st.metric("Schedule Enabled", "Yes" if schedule_enabled else "No")
                if schedule_enabled:
                    interval_type = schedule_config.get("interval_type", "hourly")
                    interval_hours = schedule_config.get("interval_hours", 1)
                    st.caption(f"Interval: {interval_hours} {interval_type}")
            
            # Show URLs
            with st.expander(f"🔗 URLs to Scrape ({len(urls_config)})"):
                for i, url_item in enumerate(urls_config, 1):
                    url = url_item.get("url", "")
                    st.text(f"{i}. {url}")
        
        st.markdown("---")
        
        # Manual scraping controls
        st.subheader("🚀 Manual Scraping")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            scrape_only = st.checkbox("Scrape Only", help="Only scrape, don't ingest")
        
        with col2:
            ingest_only = st.checkbox("Ingest Only", help="Only ingest existing data, don't scrape")
        
        with col3:
            auto_ingest = st.checkbox("Auto Ingest After Scrape", value=True, help="Automatically ingest after scraping")
        
        if st.button("🕷️ Start Scraping", type="primary", use_container_width=True):
            if scrape_only and ingest_only:
                st.error("❌ Cannot select both 'Scrape Only' and 'Ingest Only'")
            else:
                with st.spinner("Starting scraping operation..."):
                    try:
                        def run_scraper():
                            try:
                                if scrape_only:
                                    result = st.session_state.scraper.run_scraping()
                                elif ingest_only:
                                    result = st.session_state.scraper.run_ingestion()
                                else:
                                    # Full pipeline
                                    result = st.session_state.scraper.run_full_pipeline(
                                        force=True,
                                        check_new_urls=True
                                    )
                                
                                # Auto-ingest if enabled and not ingest_only
                                if auto_ingest and not ingest_only and not scrape_only:
                                    if result.get("status") == "completed":
                                        st.session_state.scraper.run_ingestion()
                                
                                st.success("✅ Scraping operation completed!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Scraping error: {e}")
                                st.rerun()
                        
                        # Run in thread to avoid blocking
                        thread = threading.Thread(target=run_scraper, daemon=True)
                        thread.start()
                        
                        st.info("🔄 Scraping started in background. Check status above for progress.")
                        time.sleep(1)  # Brief delay to show message
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error starting scraper: {e}")
        
        # Auto-refresh status every 3 seconds if running
        if st.session_state.scraper_status.get("is_running"):
            time.sleep(3)
            if st.session_state.scraper:
                # Update status
                st.session_state.scraper_status = st.session_state.scraper.get_status()
            st.rerun()

# Footer
st.markdown("---")
st.caption("💡 This assistant provides factual information only. Not investment advice.")

# Show initialization status in footer
if st.session_state.init_error:
    st.error(f"⚠️ Backend Error: {st.session_state.init_error}")
