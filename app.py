"""
Streamlit app for Mutual Fund FAQ Assistant
Simplified frontend matching HTML/CSS/JS design exactly
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
from scripts.scheduled_scraper import ScheduledScraper
from scrapers.groww_scraper import load_config
import config

# Page configuration - centered layout like HTML
st.set_page_config(
    page_title="Mutual Fund FAQ Assistant",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSS matching static/styles.css exactly
st.markdown("""
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    :root {
        --primary-color: #6366f1;
        --primary-dark: #4f46e5;
        --primary-light: #818cf8;
        --primary-lighter: #c7d2fe;
        --secondary-color: #10b981;
        --accent-color: #f59e0b;
        --background-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        --card-background: #ffffff;
        --text-primary: #111827;
        --text-secondary: #4b5563;
        --text-muted: #9ca3af;
        --border-color: #e5e7eb;
        --border-light: #f3f4f6;
        --success-color: #10b981;
        --warning-color: #f59e0b;
        --error-color: #ef4444;
        --info-color: #3b82f6;
        --chat-bg: #f9fafb;
        --user-msg-bg: linear-gradient(135deg, #6366f1 0%, #818cf8 100%);
        --assistant-msg-bg: #ffffff;
        --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        --shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    }
    
    .stApp {
        background: linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 50%, #ddd6fe 100%);
        background-attachment: fixed;
        min-height: 100vh;
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 20px;
    }
    
    .main .block-container {
        background: var(--card-background);
        border-radius: 24px;
        box-shadow: var(--shadow-2xl);
        max-width: 900px;
        width: 100%;
        padding: 40px;
        display: flex;
        flex-direction: column;
        gap: 24px;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    header {
        text-align: center;
        border-bottom: 2px solid var(--border-light);
        padding-bottom: 24px;
        position: relative;
        margin-bottom: 0;
    }
    
    header::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 60px;
        height: 3px;
        background: linear-gradient(90deg, var(--primary-color), var(--primary-light));
        border-radius: 2px;
    }
    
    header h1 {
        background: linear-gradient(135deg, var(--primary-color), var(--primary-light));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 32px;
        font-weight: 700;
        margin: 0 0 16px 0;
        letter-spacing: -0.5px;
    }
    
    .welcome-message {
        color: var(--text-secondary);
        font-size: 16px;
        margin-bottom: 8px;
        font-weight: 400;
    }
    
    .disclaimer {
        display: inline-block;
        background: linear-gradient(135deg, #fee2e2, #fecaca);
        color: #991b1b;
        font-weight: 600;
        font-size: 13px;
        padding: 6px 12px;
        border-radius: 20px;
        border: 1px solid #fca5a5;
        margin-top: 8px;
    }
    
    .example-questions {
        display: flex;
        flex-direction: column;
        gap: 12px;
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        padding: 20px;
        border-radius: 16px;
        border: 1px solid var(--border-light);
    }
    
    .example-questions h2 {
        color: var(--text-primary);
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .example-questions h2::before {
        content: '💡';
        font-size: 20px;
    }
    
    .example-question {
        background: white;
        border: 2px solid var(--border-color);
        border-radius: 12px;
        padding: 14px 18px;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        color: var(--text-primary);
        font-size: 14px;
        font-weight: 500;
        position: relative;
        overflow: hidden;
        box-shadow: var(--shadow-sm);
    }
    
    .example-question::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        height: 100%;
        width: 4px;
        background: linear-gradient(180deg, var(--primary-color), var(--primary-light));
        transform: scaleY(0);
        transition: transform 0.3s ease;
    }
    
    .example-question:hover {
        background: linear-gradient(135deg, #f8faff 0%, #f0f4ff 100%);
        border-color: var(--primary-light);
        transform: translateX(6px);
        box-shadow: var(--shadow-md);
    }
    
    .example-question:hover::before {
        transform: scaleY(1);
    }
    
    .chat-container {
        min-height: 350px;
        max-height: 600px;
        overflow-y: auto;
        border: 1px solid var(--border-light);
        border-radius: 20px;
        padding: 24px;
        background: var(--chat-bg);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        position: relative;
        backdrop-filter: blur(10px);
    }
    
    .chat-messages {
        display: flex;
        flex-direction: column;
        gap: 20px;
    }
    
    .message {
        padding: 16px 20px;
        border-radius: 16px;
        max-width: 85%;
        word-wrap: break-word;
        animation: messageSlideIn 0.3s ease-out;
        position: relative;
        box-shadow: var(--shadow-sm);
    }
    
    @keyframes messageSlideIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .message.user {
        background: var(--user-msg-bg);
        color: white;
        align-self: flex-end;
        margin-left: auto;
        border-bottom-right-radius: 8px;
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
        font-weight: 500;
    }
    
    .message.assistant {
        background: var(--assistant-msg-bg);
        color: var(--text-primary);
        align-self: flex-start;
        border: 1px solid var(--border-light);
        border-bottom-left-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 15px;
        line-height: 1.75;
        letter-spacing: -0.01em;
        border-left: 3px solid var(--primary-color);
    }
    
    .message.refusal {
        background: linear-gradient(135deg, #fef3c7, #fde68a);
        border: 2px solid #fbbf24;
        color: #92400e;
        box-shadow: var(--shadow-sm);
    }
    
    .message.error {
        background: linear-gradient(135deg, #fee2e2, #fecaca);
        border: 2px solid #f87171;
        color: #991b1b;
        box-shadow: var(--shadow-sm);
    }
    
    .message.loading {
        background: linear-gradient(135deg, #f3f4f6, #e5e7eb);
        color: var(--text-secondary);
        font-style: italic;
        position: relative;
        overflow: hidden;
    }
    
    .citations {
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid var(--border-light);
    }
    
    .citation a {
        color: var(--primary-color);
        text-decoration: none;
        font-weight: 600;
        font-size: 13px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        background: linear-gradient(135deg, #f0f4ff, #e0e7ff);
        border-radius: 8px;
        border: 1px solid var(--primary-light);
        transition: all 0.3s ease;
    }
    
    .citation a::before {
        content: '🔗';
        font-size: 12px;
    }
    
    .citation a:hover {
        background: linear-gradient(135deg, var(--primary-color), var(--primary-light));
        color: white;
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
        border-color: var(--primary-color);
    }
    
    .input-container {
        display: flex;
        gap: 12px;
        border-top: 2px solid var(--border-light);
        padding-top: 24px;
        position: relative;
    }
    
    .input-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 60px;
        height: 2px;
        background: linear-gradient(90deg, var(--primary-color), var(--primary-light));
        border-radius: 2px;
    }
    
    /* Scraper Status Indicator */
    .scraper-status {
        margin-top: 15px;
        padding: 12px 16px;
        background: linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 100%);
        border: 1px solid var(--primary-lighter);
        border-radius: 12px;
        box-shadow: var(--shadow-sm);
        animation: slideDown 0.3s ease-out;
    }
    
    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .status-indicator {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .status-spinner {
        width: 20px;
        height: 20px;
        border: 3px solid var(--primary-lighter);
        border-top-color: var(--primary-color);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    .status-spinner.scraping {
        border-top-color: var(--info-color);
    }
    
    .status-spinner.ingesting {
        border-top-color: var(--secondary-color);
    }
    
    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }
    
    .status-message {
        font-size: 14px;
        font-weight: 500;
        color: var(--text-primary);
        flex: 1;
    }
    
    .status-progress {
        margin-top: 10px;
    }
    
    .progress-bar {
        width: 100%;
        height: 6px;
        background-color: var(--border-light);
        border-radius: 3px;
        overflow: hidden;
        margin-bottom: 6px;
    }
    
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--primary-color), var(--primary-light));
        border-radius: 3px;
        transition: width 0.3s ease;
        animation: pulse 2s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: 0.8;
        }
    }
    
    .progress-text {
        font-size: 12px;
        color: var(--text-secondary);
        text-align: center;
    }
    
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Scrollbar styling */
    .chat-container::-webkit-scrollbar {
        width: 10px;
    }
    
    .chat-container::-webkit-scrollbar-track {
        background: var(--border-light);
        border-radius: 10px;
        margin: 8px 0;
    }
    
    .chat-container::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, var(--primary-color), var(--primary-light));
        border-radius: 10px;
        border: 2px solid var(--border-light);
    }
    
    .chat-container::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, var(--primary-dark), var(--primary-color));
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
if "scraper_started" not in st.session_state:
    st.session_state.scraper_started = False

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
st.markdown("""
<header>
    <h1>Mutual Fund FAQ Assistant</h1>
    <p class="welcome-message">Welcome! I'm here to help you with factual information about mutual funds.</p>
    <p class="disclaimer">Facts-only. No investment advice.</p>
</header>
""", unsafe_allow_html=True)

# Scraper status indicator (matching HTML design)
if st.session_state.scraper:
    try:
        scraper_status = st.session_state.scraper.get_status()
        if scraper_status.get("is_running"):
            status_html = '<div class="scraper-status">'
            status_html += '<div class="status-indicator">'
            
            # Spinner based on operation
            spinner_class = "status-spinner"
            if scraper_status.get("current_operation") == "scraping":
                spinner_class += " scraping"
            elif scraper_status.get("current_operation") == "ingestion":
                spinner_class += " ingesting"
            
            status_html += f'<span class="{spinner_class}"></span>'
            status_html += f'<span class="status-message">{scraper_status.get("message", "Processing...")}</span>'
            status_html += '</div>'
            
            # Progress bar if URLs are being processed
            if scraper_status.get("urls_total", 0) > 0:
                processed = len(scraper_status.get("urls_processed", []))
                total = scraper_status.get("urls_total", 0)
                percentage = int((processed / total) * 100) if total > 0 else 0
                
                status_html += '<div class="status-progress">'
                status_html += '<div class="progress-bar">'
                status_html += f'<div class="progress-fill" style="width: {percentage}%;"></div>'
                status_html += '</div>'
                status_html += f'<div class="progress-text">{processed}/{total} URLs processed</div>'
                status_html += '</div>'
            
            status_html += '</div>'
            st.markdown(status_html, unsafe_allow_html=True)
    except Exception:
        pass

# Example Questions
st.markdown("""
<div class="example-questions">
    <h2>Example Questions:</h2>
""", unsafe_allow_html=True)

example_questions = [
    "What is the expense ratio of Nippon India Large Cap Fund?",
    "What is the lock-in period for ELSS funds?",
    "What is the minimum SIP amount?"
]

# Style buttons to match HTML design
st.markdown("""
<style>
    .stButton > button {
        background: white;
        border: 2px solid var(--border-color);
        border-radius: 12px;
        padding: 14px 18px;
        color: var(--text-primary);
        font-size: 14px;
        font-weight: 500;
        width: 100%;
        text-align: left;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: var(--shadow-sm);
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        height: 100%;
        width: 4px;
        background: linear-gradient(180deg, var(--primary-color), var(--primary-light));
        transform: scaleY(0);
        transition: transform 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #f8faff 0%, #f0f4ff 100%);
        border-color: var(--primary-light);
        transform: translateX(6px);
        box-shadow: var(--shadow-md);
    }
    
    .stButton > button:hover::before {
        transform: scaleY(1);
    }
</style>
""", unsafe_allow_html=True)

for question in example_questions:
    if st.button(question, key=f"example_{hash(question)}", use_container_width=True):
        st.session_state.user_question = question
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# Chat container
st.markdown('<div class="chat-container"><div class="chat-messages" id="chat-messages">', unsafe_allow_html=True)

# Display chat history
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f'<div class="message user"><strong>You:</strong> {message["content"]}</div>', unsafe_allow_html=True)
    elif message["role"] == "assistant":
        answer_html = f'<div class="message assistant"><strong>Assistant:</strong> {message["content"]}'
        if "sources" in message and message["sources"]:
            sources_html = '<div class="citations">'
            for source in message["sources"][:1]:  # Show first source only
                source_url = source.get("metadata", {}).get("source_url", "")
                if source_url:
                    sources_html += f'<div class="citation"><a href="{source_url}" target="_blank" rel="noopener noreferrer">Source: {source_url}</a></div>'
            sources_html += '</div>'
            answer_html += sources_html
        answer_html += "</div>"
        st.markdown(answer_html, unsafe_allow_html=True)
    elif message["role"] == "error":
        st.markdown(f'<div class="message error"><strong>Error:</strong> {message["content"]}</div>', unsafe_allow_html=True)
    elif message["role"] == "refusal":
        st.markdown(f'<div class="message refusal"><strong>Warning:</strong> {message["content"]}</div>', unsafe_allow_html=True)

st.markdown('</div></div>', unsafe_allow_html=True)

# Chat input
if "user_question" in st.session_state:
    user_input = st.session_state.user_question
    del st.session_state.user_question
else:
    user_input = st.chat_input("💬 Ask a question about mutual funds...")

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
    
    # Process query
    with st.spinner("Thinking..."):
        try:
            # Validate for PII
            pii_type = contains_pii(user_input)
            if pii_type:
                error_msg = f"I cannot process questions containing personally identifiable information (PII) such as {pii_type}. For your privacy and security, please do not enter sensitive information like PAN numbers, Aadhaar numbers, account details, phone numbers, or email addresses. Please rephrase your question without any sensitive information."
                st.session_state.messages.append({
                    "role": "refusal",
                    "content": error_msg
                })
                st.rerun()
            
            # Validate comparison questions
            comparison_validation = validate_comparison(user_input)
            if not comparison_validation['valid']:
                st.session_state.messages.append({
                    "role": "refusal",
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
            
        except Exception as e:
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            st.session_state.messages.append({
                "role": "error",
                "content": error_msg
            })
    
    st.rerun()

# Note: Scraper status is checked on each render above
# Streamlit will naturally rerun when user interacts with the page
