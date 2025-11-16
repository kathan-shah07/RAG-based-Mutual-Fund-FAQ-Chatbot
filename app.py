"""
Streamlit app for Mutual Fund FAQ Assistant
Simple local deployment with automatic scraper scheduling
"""
import streamlit as st
import os
import sys
import threading
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

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

# Enhanced CSS for modern, polished UI
st.markdown("""
<style>
    /* Hide Streamlit default elements - but keep sidebar toggle visible */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Custom footer styling */
    .custom-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 1.5rem;
        text-align: center;
        font-size: 0.85rem;
        z-index: 1000;
        box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .custom-footer p {
        margin: 0;
        padding: 0;
        color: white;
        font-weight: 500;
    }
    
    .custom-footer a {
        color: white;
        text-decoration: none;
        font-weight: 600;
        transition: opacity 0.3s ease;
    }
    
    .custom-footer a:hover {
        opacity: 0.8;
        text-decoration: underline;
    }
    
    /* Keep header visible for sidebar toggle */
    header[data-testid="stHeader"] {
        visibility: visible !important;
        display: block !important;
    }
    
    /* Ensure sidebar toggle button is visible */
    header button[kind="header"],
    header button[data-testid="baseButton-header"],
    button[kind="header"][aria-label*="sidebar"],
    button[kind="header"][aria-label*="menu"] {
        visibility: visible !important;
        display: flex !important;
        opacity: 1 !important;
        z-index: 999 !important;
    }
    
    /* Ensure sidebar is visible and properly styled */
    section[data-testid="stSidebar"] {
        visibility: visible !important;
        display: block !important;
    }
    
    /* Sidebar container - ensure it's accessible */
    section[data-testid="stSidebar"] > div {
        visibility: visible !important;
    }
    
    /* Global styles */
    * {
        box-sizing: border-box;
    }
    
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        min-height: 100vh;
    }
    
    /* Main container styling - modern and spacious */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 900px;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
        margin-top: 2rem;
        margin-bottom: 2rem;
    }
    
    /* Main title styling - modern and bold */
    /* Fixed header container */
    .fixed-header {
        position: sticky;
        top: 0;
        z-index: 100;
        background: white;
        padding: 1rem 0;
        margin-bottom: 1rem;
        border-bottom: 1px solid #e5e7eb;
    }
    
    .main-title {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
        text-align: center;
        letter-spacing: -0.5px;
    }
    
    /* Red subtitle styling - enhanced and centered */
    .red-subtitle {
        color: #dc2626;
        font-size: 1rem;
        font-weight: 600;
        text-align: center;
        margin: 0;
        padding: 0.5rem 1rem;
        background: #fee2e2;
        border-radius: 20px;
        display: inline-block;
        width: fit-content;
        border: 2px solid #fecaca;
    }
    
    /* Container for subtitle to ensure centering */
    .subtitle-container {
        text-align: center;
        width: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 0;
    }
    
    /* Scrollable content area - contains sample questions and chat */
    .scrollable-content {
        max-height: calc(100vh - 280px);
        overflow-y: auto;
        overflow-x: hidden;
        scroll-behavior: smooth;
        padding-right: 0.5rem;
    }
    
    /* Custom scrollbar for scrollable content */
    .scrollable-content::-webkit-scrollbar {
        width: 8px;
    }
    
    .scrollable-content::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    .scrollable-content::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    
    .scrollable-content::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #5568d3 0%, #6a3f8f 100%);
    }
    
    /* Fund card styling - matching reference design */
    .fund-card {
        background: white;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    .fund-card-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #111827;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .fund-card-details {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin-bottom: 0.5rem;
    }
    
    .fund-detail-item {
        font-size: 0.9rem;
        color: #6b7280;
    }
    
    .fund-detail-label {
        font-weight: 500;
        color: #374151;
    }
    
    /* Sample questions container - simple and clean */
    .sample-questions-container {
        background: #f9fafb;
        border-radius: 12px;
        padding: 1.25rem;
        margin: 0 0 1rem 0;
        border: 1px solid #e5e7eb;
    }
    
    
    /* Sample question buttons - simple with send icon */
    .sample-questions-container + div button,
    .sample-questions-container ~ div button {
        background: white !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 10px !important;
        padding: 0.875rem 1rem !important;
        color: #111827 !important;
        font-size: 0.95rem !important;
        font-weight: 400 !important;
        text-align: left !important;
        margin-bottom: 0.5rem !important;
        transition: all 0.2s ease !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
    }
    
    .sample-questions-container + div button:hover,
    .sample-questions-container ~ div button:hover {
        background: #f3f4f6 !important;
        border-color: #d1d5db !important;
        transform: translateX(4px) !important;
    }
    
    /* Send icon styling */
    .sample-send-icon {
        flex-shrink: 0;
        margin-left: 0.75rem;
        display: flex;
        align-items: center;
    }
    
    .sample-send-icon svg {
        opacity: 0.5;
        transition: all 0.2s ease;
    }
    
    .sample-questions-container + div button:hover .sample-send-icon svg,
    .sample-questions-container ~ div button:hover .sample-send-icon svg {
        opacity: 1;
        transform: translateX(2px);
    }
    
    /* Chat container - clean Q&A display only */
    .chat-container {
        margin-top: 0;
        padding: 0;
        padding-bottom: 2rem;
        background: transparent;
    }
    
    /* Remove top margin from first message */
    .chat-container > div:first-child {
        margin-top: 0 !important;
    }
    
    /* Thinking indicator - animated and modern */
    .thinking-indicator {
        background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
        color: #6b7280;
        padding: 1rem 1.25rem;
        border-radius: 18px 18px 18px 4px;
        margin-bottom: 1rem;
        max-width: 85%;
        margin-left: 0;
        margin-right: auto;
        font-style: italic;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        animation: fadeIn 0.3s ease-in;
    }
    
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .thinking-dots {
        display: inline-flex;
        gap: 0.25rem;
    }
    
    .thinking-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #6b7280;
        animation: thinking-pulse 1.4s ease-in-out infinite;
    }
    
    .thinking-dot:nth-child(2) {
        animation-delay: 0.2s;
    }
    
    .thinking-dot:nth-child(3) {
        animation-delay: 0.4s;
    }
    
    @keyframes thinking-pulse {
        0%, 60%, 100% {
            opacity: 0.3;
            transform: scale(0.8);
        }
        30% {
            opacity: 1;
            transform: scale(1);
        }
    }
    
    /* User message bubble - clean Q&A */
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.875rem 1.125rem;
        border-radius: 18px 18px 4px 18px;
        margin-bottom: 0.75rem;
        margin-top: 0;
        max-width: 85%;
        margin-left: auto;
        margin-right: 0;
        word-wrap: break-word;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.25);
        animation: slideInRight 0.3s ease-out;
        line-height: 1.5;
    }
    
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    /* Assistant message bubble - clean Q&A */
    .assistant-message {
        background: white;
        color: #111827;
        padding: 0.875rem 1.125rem;
        border-radius: 18px 18px 18px 4px;
        margin-bottom: 0.75rem;
        margin-top: 0;
        max-width: 85%;
        margin-left: 0;
        margin-right: auto;
        word-wrap: break-word;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        border: 1px solid #e5e7eb;
        animation: slideInLeft 0.3s ease-out;
        line-height: 1.5;
    }
    
    @keyframes slideInLeft {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    /* Error message styling - enhanced */
    .error-message {
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        color: #991b1b;
        padding: 1rem 1.25rem;
        border-radius: 16px;
        margin-bottom: 1rem;
        border: 2px solid #fca5a5;
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.15);
        animation: shake 0.5s ease-in-out;
    }
    
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
    }
    
    /* Chat input container - modern sticky footer */
    .stChatInputContainer {
        position: sticky;
        bottom: 0;
        background: white;
        padding: 1.5rem 0;
        border-top: 2px solid #e5e7eb;
        margin-top: 2rem;
        z-index: 100;
        box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.05);
        border-radius: 20px 20px 0 0;
    }
    
    /* Ensure Send button is always visible - comprehensive selectors */
    .stChatInput button,
    .stChatInput button[type="submit"],
    .stChatInput button[kind="primary"],
    .stChatInput button[aria-label*="Send"],
    .stChatInput button[aria-label*="send"],
    .stChatInputContainer button,
    .stChatInputContainer button[type="submit"],
    .stChatInputContainer button[kind="primary"],
    [data-testid="stChatInput"] button,
    [data-testid="stChatInput"] button[type="submit"],
    [data-testid="stChatInput"] button[kind="primary"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    
    /* Style Send button specifically - modern gradient button with arrow - MORE AGGRESSIVE */
    .stChatInput > div > div > div > button:last-child,
    .stChatInput > div > div > button:last-child,
    .stChatInput button[kind="primary"],
    .stChatInput button[aria-label*="Send"],
    .stChatInput button[aria-label*="send"],
    .stChatInput button[type="submit"]:not([aria-label*="microphone"]):not([aria-label*="Mic"]),
    [data-testid="stChatInput"] button:not([aria-label*="microphone"]):not([aria-label*="Mic"]),
    [data-testid="stChatInput"] button[type="submit"]:not([aria-label*="microphone"]):not([aria-label*="Mic"]),
    .stChatInputContainer button:not([aria-label*="microphone"]):not([aria-label*="Mic"]) {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 50% !important;
        width: 42px !important;
        height: 42px !important;
        min-width: 42px !important;
        padding: 0 !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        position: relative !important;
        z-index: 999 !important;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4) !important;
        font-size: 20px !important;
        font-weight: bold !important;
    }
    
    /* Arrow icon for send button */
    .send-button-arrow {
        display: inline-block !important;
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1 !important;
    }
    
    .stChatInput > div > div > div > button:last-child:hover,
    .stChatInput button[kind="primary"]:hover,
    .stChatInput button[aria-label*="Send"]:hover,
    .stChatInput button[aria-label*="send"]:hover {
        background: linear-gradient(135deg, #5568d3 0%, #6a3f8f 100%) !important;
        transform: scale(1.05) !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5) !important;
    }
    
    .stChatInput > div > div > div > button:last-child:active,
    .stChatInput button[kind="primary"]:active {
        transform: scale(0.95) !important;
    }
    
    /* Hide mic icon in chat input - multiple selectors to ensure it's hidden */
    .stChatInput button[aria-label*="microphone"],
    .stChatInput button[aria-label*="Mic"],
    .stChatInput button[data-testid*="microphone"],
    .stChatInput button svg[viewBox*="24"],
    .stChatInput > div > div > div > button[aria-label*="microphone"],
    .stChatInput > div > div > div > button[aria-label*="Mic"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Ensure buttons in chat input container are visible except mic */
    .stChatInputContainer button:not([aria-label*="microphone"]):not([aria-label*="Mic"]) {
        display: flex !important;
        visibility: visible !important;
    }
    
    /* Chat input field styling - modern and interactive */
    .stChatInput > div > div > input {
        border: 2px solid #e5e7eb;
        border-radius: 25px;
        padding: 0.875rem 1.25rem;
        font-size: 1rem;
        transition: all 0.3s ease;
        background: #f9fafb;
    }
    
    .stChatInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
        background: white;
        outline: none;
    }
    
    .stChatInput > div > div > input::placeholder {
        color: #9ca3af;
    }
    
    /* Citation links styling - modern and clickable */
    .citation-link {
        color: #667eea;
        text-decoration: none;
        font-size: 0.9rem;
        margin-right: 0.75rem;
        display: inline-block;
        padding: 0.25rem 0.75rem;
        background: #f0f4ff;
        border-radius: 12px;
        transition: all 0.2s ease;
        font-weight: 500;
    }
    
    .citation-link:hover {
        background: #667eea;
        color: white;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
    }
    
    .citations-container {
        margin-top: 0.75rem;
        padding-top: 0.75rem;
        border-top: 2px dashed #e5e7eb;
        font-size: 0.9rem;
        color: #6b7280;
        animation: fadeIn 0.3s ease-in;
    }
    
    /* Initial greeting message - welcoming */
    .initial-greeting {
        text-align: center;
        color: #6b7280;
        font-size: 1.1rem;
        padding: 2rem 1rem;
        margin-top: 2rem;
        background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%);
        border-radius: 16px;
        border: 2px dashed #667eea;
        font-weight: 500;
    }
    
    /* Disclaimer text - enhanced visibility */
    .disclaimer-text {
        text-align: center;
        color: #dc2626;
        font-size: 0.9rem;
        padding: 0.75rem 1rem;
        margin-top: 1rem;
        background: #fee2e2;
        border-radius: 12px;
        font-weight: 500;
        border: 1px solid #fecaca;
    }
    
    /* Sources expander */
    .streamlit-expanderHeader {
        font-weight: 500;
        color: #3b82f6;
        font-size: 0.9rem;
    }
    
    /* Hide Streamlit's default chat message avatars and styling */
    .stChatMessage {
        padding: 0 !important;
        background: transparent !important;
    }
    
    .stChatMessage > div {
        padding: 0 !important;
    }
    
    /* Remove default chat message styling */
    [data-testid="stChatMessage"] {
        padding: 0 !important;
    }
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

def is_streamlit_cloud():
    """Check if running on Streamlit Cloud."""
    # Streamlit Cloud sets these environment variables
    # Check multiple indicators to be sure
    return (
        os.getenv("STREAMLIT_SHARING") == "true" or 
        os.getenv("STREAMLIT_SERVER_PORT") == "8501" or
        os.getenv("STREAMLIT_SERVER_ADDRESS") is not None or
        "/mount/src/" in os.getcwd()  # Streamlit Cloud uses /mount/src/ as working directory
    )

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
        
        # Initialize scraper (enabled on Streamlit Cloud)
        scraper = None
        try:
            scraper = ScheduledScraper(config_path="scraper_config.json")
        except Exception as e:
            # Scraper initialization is optional - log but continue
            logger.warning(f"Scraper initialization failed: {e}")
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
            
            # On Streamlit Cloud, automatically ingest pre-populated data if available
            if is_streamlit_cloud() and vector_store:
                try:
                    # Check if data files exist but vector DB is empty
                    from pathlib import Path
                    data_dir = Path(config.DATA_DIR)
                    if data_dir.exists():
                        json_files = list(data_dir.rglob("*.json"))
                        if json_files:
                            # Check if vector DB has documents
                            collection_info = vector_store.get_collection_info()
                            doc_count = collection_info.get("document_count", 0)
                            
                            if doc_count == 0:
                                # Data files exist but not ingested - ingest them
                                from scripts.ingest_data import main as ingest_data
                                ingest_data()
                except Exception as e:
                    # Ingestion failure is not critical - log but continue
                    pass

# Start scheduled scraper in background if not already started
# Enabled on Streamlit Cloud
if st.session_state.scraper and not st.session_state.scraper_started:
    try:
        # Start the scraper scheduler in a background thread
        st.session_state.scraper.start()
        st.session_state.scraper_started = True
    except Exception as e:
        # Scraper start failure is not critical, continue
        logger.warning(f"Scraper start failed: {e}")
        pass

# Helper function to format date in Indian format
def format_indian_datetime(dt: datetime) -> str:
    """Format datetime in Indian format: 4 PM, 16th Nov"""
    if not dt:
        return "N/A"
    
    # Format time in 12-hour format
    hour = dt.hour
    minute = dt.minute
    am_pm = "AM" if hour < 12 else "PM"
    hour_12 = hour if hour <= 12 else hour - 12
    if hour_12 == 0:
        hour_12 = 12
    
    time_str = f"{hour_12} {am_pm}"
    if minute > 0:
        time_str = f"{hour_12}:{minute:02d} {am_pm}"
    
    # Format date with ordinal suffix
    day = dt.day
    if 4 <= day <= 20 or 24 <= day <= 30:
        suffix = "th"
    else:
        suffix = ["st", "nd", "rd"][day % 10 - 1]
    
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    month_str = month_names[dt.month - 1]
    
    return f"{time_str}, {day}{suffix} {month_str}"


# Helper function to detect if answer is a refusal or out-of-context
def is_refusal_or_out_of_context(answer: str) -> bool:
    """
    Detect if the answer is a refusal or out-of-context response.
    
    Args:
        answer: The answer text from LLM
        
    Returns:
        True if answer is a refusal/out-of-context, False otherwise
    """
    if not answer:
        return True
    
    answer_lower = answer.lower()
    
    # Common refusal patterns
    refusal_keywords = [
        "cannot provide",
        "cannot give",
        "can only provide",
        "can only answer",
        "cannot answer",
        "out of scope",
        "outside the scope",
        "investment advice",
        "recommendations",
        "opinions",
        "not in the context",
        "not available in the context",
        "not provided in the context",
        "i can only",
        "i cannot",
        "i'm unable to",
        "unable to provide",
        "unable to answer"
    ]
    
    # Check if answer contains refusal patterns
    for keyword in refusal_keywords:
        if keyword in answer_lower:
            return True
    
    return False


# Helper function to extract unique fund names from sources
def extract_fund_names_from_sources(sources: list) -> list:
    """
    Extract unique fund names from sources.
    
    Args:
        sources: List of source documents with metadata
        
    Returns:
        List of unique fund names
    """
    fund_names = set()
    
    for source in sources:
        metadata = source.get("metadata", {})
        fund_name = metadata.get("fund_name") or metadata.get("source_file", "")
        if fund_name:
            # Clean fund name (remove .json extension if present)
            fund_name_clean = fund_name.replace('.json', '').replace('_', ' ').title()
            if fund_name_clean:
                fund_names.add(fund_name_clean)
    
    return sorted(list(fund_names))


# Helper function to determine if answer is based on factual retrieval
def is_factual_retrieval(result: dict) -> bool:
    """
    Determine if answer is based on factual retrieval.
    
    Args:
        result: Result dictionary from query_with_retrieval
        
    Returns:
        True if answer is based on factual retrieval, False otherwise
    """
    # Check if documents were retrieved
    retrieved_docs = result.get("retrieved_documents", 0)
    if retrieved_docs == 0:
        return False
    
    # Check if sources exist
    sources = result.get("sources", [])
    if not sources:
        return False
    
    # Check if answer is a refusal/out-of-context
    answer = result.get("answer", "")
    if is_refusal_or_out_of_context(answer):
        return False
    
    return True


# Fixed header with title and subtitle
st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
st.markdown('<h1 class="main-title">Mutual Fund FAQ Assistant</h1>', unsafe_allow_html=True)
st.markdown('<div class="subtitle-container"><p class="red-subtitle">Facts-only. No investment advice.</p></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Scrollable content area - sample questions and chat
st.markdown('<div class="scrollable-content">', unsafe_allow_html=True)

# Sample questions - simple design with send buttons
st.markdown('<div class="sample-questions-container">', unsafe_allow_html=True)
st.markdown('<p style="color: #6b7280; font-size: 0.9rem; margin-bottom: 0.75rem; font-weight: 500;">💡 Try asking:</p>', unsafe_allow_html=True)

sample_questions = [
    "What is the latest NAV?",
    "Show top 5 holdings of Flexi cap",
    "Expense ratio and exit load?",
    "What is the minimum SIP amount?"
]

# Display sample questions as buttons with send icons
for idx, question in enumerate(sample_questions):
    button_key = f"sample_{hash(question)}"
    # Use Streamlit button and add send icon via CSS
    if st.button(question, key=button_key, use_container_width=True):
        st.session_state.messages.append({"role": "user", "content": question})
        st.rerun()

# st.markdown('</div>', unsafe_allow_html=True)

# JavaScript to add send icons to sample question buttons
st.markdown("""
<script>
    function addSendIconsToSampleQuestions() {
        // Find all buttons in the sample questions container
        const container = document.querySelector('.sample-questions-container');
        if (!container) return;
        
        const buttons = container.parentElement.querySelectorAll('button[data-testid*="baseButton"]');
        buttons.forEach((button, index) => {
            // Check if this button is in the sample questions area
            const buttonText = button.textContent.trim();
            const sampleQuestions = ['What is the latest NAV?', 'Show top 5 holdings of Flexi cap', 'Expense ratio and exit load?', 'What is the minimum SIP amount?'];
            
            if (sampleQuestions.some(q => buttonText.includes(q) || q.includes(buttonText))) {
                // Add send icon if not already added
                if (!button.querySelector('.sample-send-icon')) {
                    // Style the button
                    button.style.display = 'flex';
                    button.style.justifyContent = 'space-between';
                    button.style.alignItems = 'center';
                    button.style.textAlign = 'left';
                    button.style.padding = '0.875rem 1rem';
                    button.style.border = '1px solid #e5e7eb';
                    button.style.borderRadius = '10px';
                    button.style.background = 'white';
                    button.style.color = '#111827';
                    button.style.fontSize = '0.95rem';
                    button.style.fontWeight = '400';
                    button.style.marginBottom = '0.5rem';
                    button.style.transition = 'all 0.2s ease';
                    
                    // Add send icon
                    const sendIcon = document.createElement('span');
                    sendIcon.className = 'sample-send-icon';
                    sendIcon.innerHTML = `
                        <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="opacity: 0.5; transition: all 0.2s ease;">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path>
                        </svg>
                    `;
                    button.appendChild(sendIcon);
                    
                    // Add hover effect
                    button.addEventListener('mouseenter', function() {
                        this.style.background = '#f3f4f6';
                        this.style.borderColor = '#d1d5db';
                        this.style.transform = 'translateX(4px)';
                        const icon = this.querySelector('.sample-send-icon svg');
                        if (icon) {
                            icon.style.opacity = '1';
                            icon.style.transform = 'translateX(2px)';
                        }
                    });
                    
                    button.addEventListener('mouseleave', function() {
                        this.style.background = 'white';
                        this.style.borderColor = '#e5e7eb';
                        this.style.transform = 'translateX(0)';
                        const icon = this.querySelector('.sample-send-icon svg');
                        if (icon) {
                            icon.style.opacity = '0.5';
                            icon.style.transform = 'translateX(0)';
                        }
                    });
                }
            }
        });
    }
    
    // Run on load and after delays
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addSendIconsToSampleQuestions);
    } else {
        addSendIconsToSampleQuestions();
    }
    
    setTimeout(addSendIconsToSampleQuestions, 200);
    setTimeout(addSendIconsToSampleQuestions, 500);
    setTimeout(addSendIconsToSampleQuestions, 1000);
    
    // Watch for new buttons
    const observer = new MutationObserver(function() {
        addSendIconsToSampleQuestions();
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
</script>
""", unsafe_allow_html=True)

# Helper function to count scraped mutual funds
def count_scraped_funds() -> int:
    """Count number of mutual funds scraped (JSON files in scraper output directory)."""
    try:
        if not st.session_state.scraper:
            return 0
        
        from pathlib import Path
        scraper_settings = st.session_state.scraper.config.get("scraper_settings", {})
        data_dir = Path(scraper_settings.get("output_dir", "data/mutual_funds"))
        
        if not data_dir.exists():
            return 0
        
        json_files = list(data_dir.rglob("*.json"))
        return len(json_files)
    except Exception:
        return 0

# Sidebar
with st.sidebar:
    st.header("ℹ️ Information")
    
    # Status
    if st.session_state.init_error:
        st.error(f"❌ {st.session_state.init_error}")
        st.info("💡 Set GEMINI_API_KEY in Streamlit secrets or .env file")
    elif st.session_state.initialized:
        st.success("✅ Backend Initialized")
        
        # Show mutual funds count from scraper
        try:
            scraped_funds_count = count_scraped_funds()
            if scraped_funds_count > 0:
                st.info(f"📥 Mutual funds scraped: {scraped_funds_count}")
            else:
                st.caption("📥 No mutual funds scraped yet")
        except Exception:
            pass
        
        # Show mutual funds count in vector DB
        try:
            collection_info = st.session_state.vector_store.get_collection_info()
            unique_funds_count = collection_info.get('unique_funds_count', 0)
            if unique_funds_count > 0:
                st.info(f"💾 Mutual funds in vector DB: {unique_funds_count}")
            else:
                st.caption("💾 No mutual funds in vector DB yet")
        except Exception:
            pass
        
        # Show last scraper/ingestion timestamp
        try:
            latest_timestamp = st.session_state.vector_store.get_latest_ingestion_timestamp()
            if latest_timestamp:
                formatted_time = format_indian_datetime(latest_timestamp)
                st.success(f"🕒 Last updated: {formatted_time}")
            else:
                st.caption("🕒 No update timestamp available")
        except Exception as e:
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
                    
                    # Show error if any
                    if scraper_status.get("error"):
                        st.error(f"❌ Error: {scraper_status.get('error')}")
                else:
                    schedule_config = st.session_state.scraper.config.get("schedule", {})
                    if schedule_config.get("enabled", False):
                        interval_hours = schedule_config.get("interval_hours", 1)
                        st.caption(f"⏰ Scraper scheduled: Every {interval_hours} hour(s)")
                    
                    # Show last error if any
                    if scraper_status.get("error"):
                        st.error(f"❌ Last error: {scraper_status.get('error')}")
            except Exception as e:
                st.caption(f"⚠️ Could not get scraper status: {str(e)}")
    else:
        st.warning("⏳ Initializing...")
    
    st.markdown("---")
    
    # Clear chat
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        if st.session_state.rag_chain:
            st.session_state.rag_chain.clear_memory()
        st.session_state.messages = []
        st.rerun()

# Chat container - only show when there are messages
if st.session_state.messages:
    st.markdown('<div class="chat-container" id="chat-container">', unsafe_allow_html=True)
    
    # Display chat history with custom styled bubbles
    for idx, message in enumerate(st.session_state.messages):
        message_id = f"message-{idx}"
        if message["role"] == "user":
            st.markdown(f'<div class="user-message" id="{message_id}">{message["content"]}</div>', unsafe_allow_html=True)
        elif message["role"] == "assistant":
            st.markdown(f'<div class="assistant-message" id="{message_id}">{message["content"]}</div>', unsafe_allow_html=True)
            
            # Show citation links only if answer is based on factual retrieval
            if "is_factual" in message and message["is_factual"]:
                sources = message.get("sources", [])
                citation_urls = message.get("citation_urls", [])
                
                if sources and citation_urls:
                    # Extract unique fund names
                    fund_names = extract_fund_names_from_sources(sources)
                    
                    # Display citations based on number of funds
                    if len(fund_names) == 1:
                        # Single fund - show single citation link
                        citation_url = citation_urls[0]
                        fund_display_name = fund_names[0] if fund_names else "Source"
                        st.markdown(f'''
                            <div class="citations-container">
                                <strong>Source:</strong> <a href="{citation_url}" target="_blank" class="citation-link">{fund_display_name}</a>
                            </div>
                        ''', unsafe_allow_html=True)
                    elif len(fund_names) > 1:
                        # Multiple funds - show multiple citation links
                        citation_links = []
                        # Match URLs to fund names, or use generic labels
                        for i, url in enumerate(citation_urls):
                            if i < len(fund_names):
                                fund_name = fund_names[i]
                            else:
                                # If more URLs than fund names, use generic label
                                fund_name = f"Source {i+1}"
                            citation_links.append(f'<a href="{url}" target="_blank" class="citation-link">{fund_name}</a>')
                        
                        if citation_links:
                            st.markdown(f'''
                                <div class="citations-container">
                                    <strong>Sources:</strong> {', '.join(citation_links)}
                                </div>
                            ''', unsafe_allow_html=True)
                    elif citation_urls:
                        # Fallback: if no fund names but we have URLs, show them
                        if len(citation_urls) == 1:
                            st.markdown(f'''
                                <div class="citations-container">
                                    <strong>Source:</strong> <a href="{citation_urls[0]}" target="_blank" class="citation-link">View Source</a>
                                </div>
                            ''', unsafe_allow_html=True)
                        else:
                            citation_links = [f'<a href="{url}" target="_blank" class="citation-link">Source {i+1}</a>' 
                                             for i, url in enumerate(citation_urls)]
                            st.markdown(f'''
                                <div class="citations-container">
                                    <strong>Sources:</strong> {', '.join(citation_links)}
                                </div>
                            ''', unsafe_allow_html=True)
        elif message["role"] == "error":
            st.markdown(f'<div class="error-message" id="{message_id}">⚠️ {message["content"]}</div>', unsafe_allow_html=True)
    
    # Show thinking indicator if processing
    if st.session_state.messages:
        last_message = st.session_state.messages[-1]
        if last_message["role"] == "user":
            # Show thinking indicator
            st.markdown('''
                <div class="thinking-indicator">
                    <span>Finding answers</span>
                    <span class="thinking-dots">
                        <span class="thinking-dot"></span>
                        <span class="thinking-dot"></span>
                        <span class="thinking-dot"></span>
                    </span>
                </div>
            ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Close scrollable content container
st.markdown('</div>', unsafe_allow_html=True)

# Enhanced JavaScript for UI improvements and auto-scroll on new messages only
st.markdown("""
<script>
    (function() {
        let lastMessageCount = 0;
        
        // Auto-scroll function - only scrolls when new messages are added
        function scrollToBottom() {
            const scrollableContent = document.querySelector('.scrollable-content');
            if (scrollableContent) {
                // Scroll scrollable content to bottom
                scrollableContent.scrollTo({
                    top: scrollableContent.scrollHeight,
                    behavior: 'smooth'
                });
                
                // Also ensure the last message is visible in viewport
                const messages = document.querySelectorAll('[id^="message-"]');
                if (messages.length > 0) {
                    const lastMessage = messages[messages.length - 1];
                    lastMessage.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'end',
                        inline: 'nearest'
                    });
                }
            }
        }
        
        // Check if new messages were added and scroll only then
        function checkForNewMessages() {
            const messages = document.querySelectorAll('[id^="message-"], .thinking-indicator');
            const currentMessageCount = messages.length;
            
            // Only scroll if message count increased (new message added)
            if (currentMessageCount > lastMessageCount) {
                lastMessageCount = currentMessageCount;
                // Wait a bit for the message to render, then scroll
                setTimeout(() => {
                    scrollToBottom();
                }, 300);
            }
        }
        
        // Add smooth fade-in animation to messages
        function animateMessages() {
            const messages = document.querySelectorAll('[id^="message-"]');
            messages.forEach((msg, index) => {
                if (!msg.classList.contains('animated')) {
                    msg.style.opacity = '0';
                    msg.style.transform = 'translateY(10px)';
                    setTimeout(() => {
                        msg.style.transition = 'all 0.3s ease-out';
                        msg.style.opacity = '1';
                        msg.style.transform = 'translateY(0)';
                        msg.classList.add('animated');
                    }, index * 50);
                }
            });
        }
        
        // Add ripple effect to buttons
        function addRippleEffect() {
            const buttons = document.querySelectorAll('button');
            buttons.forEach(button => {
                if (!button.classList.contains('ripple-added')) {
                    button.addEventListener('click', function(e) {
                        const ripple = document.createElement('span');
                        const rect = this.getBoundingClientRect();
                        const size = Math.max(rect.width, rect.height);
                        const x = e.clientX - rect.left - size / 2;
                        const y = e.clientY - rect.top - size / 2;
                        
                        ripple.style.width = ripple.style.height = size + 'px';
                        ripple.style.left = x + 'px';
                        ripple.style.top = y + 'px';
                        ripple.classList.add('ripple');
                        
                        this.appendChild(ripple);
                        
                        setTimeout(() => {
                            ripple.remove();
                        }, 600);
                    });
                    button.classList.add('ripple-added');
                }
            });
        }
        
        // Initialize - set initial message count, no auto-scroll
        function init() {
            const messages = document.querySelectorAll('[id^="message-"]');
            lastMessageCount = messages.length;
            animateMessages();
            addRippleEffect();
        }
        
        // Run on page load - NO auto-scroll
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
        } else {
            init();
        }
        
        // Watch for new messages being added to scrollable content
        const scrollableContent = document.querySelector('.scrollable-content');
        if (scrollableContent) {
            const observer = new MutationObserver(function(mutations) {
                let newMessageAdded = false;
                mutations.forEach(function(mutation) {
                    mutation.addedNodes.forEach(function(node) {
                        // Check if a new message or thinking indicator was added
                        if (node.nodeType === 1) {
                            const isMessage = node.id && node.id.startsWith('message-');
                            const isThinking = node.classList && node.classList.contains('thinking-indicator');
                            const hasMessageChild = node.querySelector && node.querySelector('[id^="message-"]');
                            
                            if (isMessage || isThinking || hasMessageChild) {
                                newMessageAdded = true;
                            }
                        }
                    });
                });
                
                if (newMessageAdded) {
                    // Check and scroll only if new message was added
                    checkForNewMessages();
                    animateMessages();
                }
                
                // Always update ripple effects
                addRippleEffect();
            });
            
            observer.observe(chatContainer, {
                childList: true,
                subtree: true
            });
        }
    })();
</script>
<style>
    /* Ripple effect */
    button {
        position: relative;
        overflow: hidden;
    }
    
    .ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.6);
        transform: scale(0);
        animation: ripple-animation 0.6s ease-out;
        pointer-events: none;
    }
    
    @keyframes ripple-animation {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
</style>
""", unsafe_allow_html=True)

# Process any pending user messages (from sample questions or chat input)
# Check if the last message is a user message without a response
if st.session_state.messages:
    last_message = st.session_state.messages[-1]
    if last_message["role"] == "user":
        # Process this question
        if st.session_state.rag_chain:
            try:
                # Validate for PII - DO NOT send to LLM if PII detected
                pii_type = contains_pii(last_message["content"])
                if pii_type:
                    # Graceful denial without sending to LLM
                    error_msg = (
                        "I cannot process questions containing personally identifiable information (PII) such as "
                        f"{pii_type}. For your privacy and security, please do not enter sensitive information "
                        "like PAN numbers, Aadhaar numbers, account details, phone numbers, or email addresses. "
                        "Please rephrase your question without any sensitive information."
                    )
                    st.session_state.messages.append({
                        "role": "error",
                        "content": error_msg
                    })
                    st.rerun()
                
                # Validate comparison questions
                comparison_validation = validate_comparison(last_message["content"])
                if not comparison_validation['valid']:
                    st.session_state.messages.append({
                        "role": "error",
                        "content": comparison_validation['reason']
                    })
                    st.rerun()
                
                # Process query
                result = st.session_state.rag_chain.query_with_retrieval(
                    question=last_message["content"],
                    k=5,
                    return_scores=False
                )
                answer = result.get("answer", "No answer received")
                sources = result.get("sources", [])
                citation_urls = result.get("citation_urls", [])
                
                # Determine if answer is based on factual retrieval
                is_factual = is_factual_retrieval(result)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "citation_urls": citation_urls,
                    "is_factual": is_factual
                })
                st.rerun()
            except Exception as e:
                st.session_state.messages.append({
                    "role": "error",
                    "content": f"Error: {str(e)}"
                })
                st.rerun()

# Chat input - text only, no mic icon
# Add JavaScript to ensure Send button is visible (runs after chat input is rendered)
st.markdown("""
<script>
    (function() {
        function ensureSendButtonVisible() {
            // Find ALL possible chat input containers
            const selectors = [
                '[data-testid="stChatInput"]',
                '.stChatInput',
                '.stChatInputContainer',
                'div[class*="stChatInput"]',
                'div[data-baseweb="input"]'
            ];
            
            let chatInputs = [];
            selectors.forEach(selector => {
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => chatInputs.push(el));
            });
            
            // Also search in body for any buttons near input fields
            const allButtons = document.querySelectorAll('button');
            
            chatInputs.forEach(container => {
                // Find all buttons in the container and parent containers
                const buttons = container.querySelectorAll('button');
                buttons.forEach(button => processButton(button));
            });
            
            // Process all buttons on page that might be send buttons
            allButtons.forEach(button => {
                const ariaLabel = (button.getAttribute('aria-label') || '').toLowerCase();
                const parent = button.closest('[data-testid="stChatInput"], .stChatInput, .stChatInputContainer');
                if (parent || ariaLabel.includes('send') || button.type === 'submit') {
                    processButton(button);
                }
            });
        }
        
        function processButton(button) {
            if (!button) return;
            
            const ariaLabel = (button.getAttribute('aria-label') || '').toLowerCase();
            const hasMicIcon = button.querySelector('svg[viewBox*="24"], svg[viewBox*="20"]');
            const isMic = ariaLabel.includes('microphone') || 
                         ariaLabel.includes('mic') ||
                         (hasMicIcon && !ariaLabel.includes('send'));
            
            if (isMic) {
                // Hide mic button
                button.style.display = 'none';
                button.style.visibility = 'hidden';
                button.style.opacity = '0';
            } else {
                // This is the Send button - make it visible and styled with arrow icon
                button.style.setProperty('display', 'flex', 'important');
                button.style.setProperty('visibility', 'visible', 'important');
                button.style.setProperty('opacity', '1', 'important');
                button.style.setProperty('background', 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 'important');
                button.style.setProperty('color', 'white', 'important');
                button.style.setProperty('border', 'none', 'important');
                button.style.setProperty('border-radius', '50%', 'important');
                button.style.setProperty('width', '42px', 'important');
                button.style.setProperty('height', '42px', 'important');
                button.style.setProperty('min-width', '42px', 'important');
                button.style.setProperty('padding', '0', 'important');
                button.style.setProperty('align-items', 'center', 'important');
                button.style.setProperty('justify-content', 'center', 'important');
                button.style.setProperty('cursor', 'pointer', 'important');
                button.style.setProperty('z-index', '999', 'important');
                button.style.setProperty('font-size', '20px', 'important');
                button.style.setProperty('font-weight', 'bold', 'important');
                button.style.setProperty('box-shadow', '0 4px 12px rgba(102, 126, 234, 0.4)', 'important');
                button.style.setProperty('position', 'relative', 'important');
                
                // Add arrow icon if not already present
                const hasArrow = button.textContent.includes('→') || 
                                button.textContent.includes('➜') || 
                                button.querySelector('.send-button-arrow');
                
                if (!hasArrow) {
                    // Remove any existing SVG icons
                    const svgs = button.querySelectorAll('svg');
                    svgs.forEach(svg => {
                        if (!svg.closest('.send-button-arrow')) {
                            svg.remove();
                        }
                    });
                    
                    const arrow = document.createElement('span');
                    arrow.className = 'send-button-arrow';
                    arrow.textContent = '→';
                    arrow.style.display = 'inline-block';
                    arrow.style.margin = '0';
                    arrow.style.padding = '0';
                    arrow.style.lineHeight = '1';
                    arrow.style.fontSize = '20px';
                    arrow.style.fontWeight = 'bold';
                    // Clear any existing content and add arrow
                    button.innerHTML = '';
                    button.appendChild(arrow);
                }
                
                // Add hover effect (check if already added)
                if (!button.hasAttribute('data-send-button-styled')) {
                    button.setAttribute('data-send-button-styled', 'true');
                    
                    button.addEventListener('mouseenter', function() {
                        this.style.setProperty('background', 'linear-gradient(135deg, #5568d3 0%, #6a3f8f 100%)', 'important');
                        this.style.setProperty('transform', 'scale(1.05)', 'important');
                        this.style.setProperty('box-shadow', '0 6px 20px rgba(102, 126, 234, 0.5)', 'important');
                    });
                    button.addEventListener('mouseleave', function() {
                        this.style.setProperty('background', 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 'important');
                        this.style.setProperty('transform', 'scale(1)', 'important');
                        this.style.setProperty('box-shadow', '0 4px 12px rgba(102, 126, 234, 0.4)', 'important');
                    });
                    
                    // Add active effect
                    button.addEventListener('mousedown', function() {
                        this.style.setProperty('transform', 'scale(0.95)', 'important');
                    });
                    button.addEventListener('mouseup', function() {
                        this.style.setProperty('transform', 'scale(1)', 'important');
                    });
                }
            }
        }
        
        // Run immediately
        ensureSendButtonVisible();
        
        // Run after DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', ensureSendButtonVisible);
        }
        
        // Run after delays to catch Streamlit's dynamic rendering - MORE FREQUENTLY
        setTimeout(ensureSendButtonVisible, 50);
        setTimeout(ensureSendButtonVisible, 100);
        setTimeout(ensureSendButtonVisible, 200);
        setTimeout(ensureSendButtonVisible, 300);
        setTimeout(ensureSendButtonVisible, 500);
        setTimeout(ensureSendButtonVisible, 800);
        setTimeout(ensureSendButtonVisible, 1000);
        setTimeout(ensureSendButtonVisible, 1500);
        setTimeout(ensureSendButtonVisible, 2000);
        
        // Watch for Streamlit's frame updates - MORE AGGRESSIVE
        const targetNode = document.body;
        const observer = new MutationObserver(function(mutations) {
            let shouldCheck = false;
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length > 0) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) {
                            // Check for chat input or buttons
                            if (node.classList && (
                                node.classList.contains('stChatInput') ||
                                node.classList.contains('stChatInputContainer') ||
                                node.tagName === 'BUTTON' ||
                                node.querySelector('.stChatInput') ||
                                node.querySelector('[data-testid="stChatInput"]') ||
                                node.querySelector('button')
                            )) {
                                shouldCheck = true;
                            }
                            // Also check if it's a button
                            if (node.tagName === 'BUTTON') {
                                shouldCheck = true;
                            }
                        }
                    });
                }
            });
            if (shouldCheck) {
                // Run immediately and with slight delay
                ensureSendButtonVisible();
                setTimeout(ensureSendButtonVisible, 10);
                setTimeout(ensureSendButtonVisible, 50);
            }
        });
        
        observer.observe(targetNode, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['style', 'class']
        });
        
        // Also set up interval as backup (runs every 500ms)
        setInterval(ensureSendButtonVisible, 500);
        
        // Also listen for Streamlit's custom events
        window.addEventListener('load', ensureSendButtonVisible);
    })();
</script>
""", unsafe_allow_html=True)

if prompt := st.chat_input("Ask a fact-based question...", key="chat_input"):
    # Check if backend is initialized
    if not st.session_state.initialized or not st.session_state.rag_chain:
        error_msg = st.session_state.init_error or "Backend not initialized. Please check configuration."
        st.error(error_msg)
        st.stop()
    
    # Add user message to history - will be processed on next rerun
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# Custom Footer with Attribution
st.markdown("""
<div class="custom-footer">
    <p>Made with ❤️ by <strong>Kathan Shah</strong></p>
</div>
""", unsafe_allow_html=True)

# Note: Scraper status is checked on each render above
# Streamlit will naturally rerun when user interacts with the page