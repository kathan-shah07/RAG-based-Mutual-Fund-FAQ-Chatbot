"""
Streamlit app for Mutual Fund FAQ Assistant
Main entry point for Streamlit Cloud deployment
"""
import streamlit as st
import requests
import os
from datetime import datetime

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
    .example-question {
        padding: 0.75rem;
        margin: 0.5rem 0;
        background-color: #f0f0f0;
        border-radius: 8px;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    .example-question:hover {
        background-color: #e0e0e0;
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
</style>
""", unsafe_allow_html=True)

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_ENDPOINT = f"{API_BASE_URL}/api/v1/query"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "api_available" not in st.session_state:
    st.session_state.api_available = True

# Check API health
@st.cache_data(ttl=60)
def check_api_health():
    """Check if API is available"""
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        return response.status_code == 200
    except:
        return False

# Header
st.markdown('<div class="main-header"><h1>💰 Mutual Fund FAQ Assistant</h1></div>', unsafe_allow_html=True)
st.markdown('<p class="disclaimer">Welcome! I\'m here to help you with factual information about mutual funds. Facts-only. No investment advice.</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("ℹ️ Information")
    
    # API Status
    api_status = check_api_health()
    if api_status:
        st.success("✅ API Connected")
    else:
        st.error("❌ API Not Available")
        st.info(f"Make sure the FastAPI server is running at: {API_BASE_URL}")
    
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
        if st.button(question, key=f"example_{question[:20]}", use_container_width=True):
            st.session_state.user_question = question
    
    st.markdown("---")
    
    # Clear chat
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    st.caption("💡 Click example questions to ask them")

# Main content area
# Display chat history
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f'<div class="user-message"><strong>You:</strong> {message["content"]}</div>', unsafe_allow_html=True)
    else:
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

# Chat input
if "user_question" in st.session_state:
    user_input = st.session_state.user_question
    del st.session_state.user_question
else:
    user_input = st.chat_input("Ask a question about mutual funds...")

if user_input:
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Show user message
    st.markdown(f'<div class="user-message"><strong>You:</strong> {user_input}</div>', unsafe_allow_html=True)
    
    # Check API availability
    if not check_api_health():
        st.error("❌ API is not available. Please make sure the FastAPI server is running.")
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Sorry, I cannot connect to the API server. Please check if the FastAPI backend is running."
        })
    else:
        # Show loading indicator
        with st.spinner("Thinking..."):
            try:
                # Call API
                response = requests.post(
                    API_ENDPOINT,
                    json={
                        "question": user_input,
                        "k": 5,
                        "return_sources": True,
                        "return_scores": False,
                        "clear_history": False
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("answer", "No answer received")
                    sources = data.get("sources", [])
                    
                    # Add assistant message to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    })
                    
                    # Display answer
                    answer_html = f'<div class="assistant-message"><strong>Assistant:</strong> {answer}'
                    if sources:
                        sources_html = "<div class='source-info'><strong>Sources:</strong><ul>"
                        for source in sources[:3]:
                            source_name = source.get("metadata", {}).get("source_file", "Unknown")
                            sources_html += f"<li>{source_name}</li>"
                        sources_html += "</ul></div>"
                        answer_html += sources_html
                    answer_html += "</div>"
                    st.markdown(answer_html, unsafe_allow_html=True)
                    
                elif response.status_code == 400:
                    error_data = response.json()
                    error_msg = error_data.get("detail", "Invalid request")
                    st.warning(f"⚠️ {error_msg}")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                else:
                    st.error(f"❌ API Error: {response.status_code}")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "Sorry, I encountered an error while processing your question."
                    })
                    
            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out. Please try again.")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Sorry, the request took too long. Please try again."
                })
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Sorry, I encountered an error: {str(e)}"
                })
    
    st.rerun()

# Footer
st.markdown("---")
st.caption("💡 This assistant provides factual information only. Not investment advice.")

