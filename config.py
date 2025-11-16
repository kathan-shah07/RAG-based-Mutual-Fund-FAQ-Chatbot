"""
Configuration file for RAG backend.
Supports both .env files and Streamlit secrets.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Try to get from Streamlit secrets first (for Streamlit Cloud), then environment variables
def get_config(key: str, default: str = "") -> str:
    """Get configuration value from Streamlit secrets or environment variables."""
    try:
        import streamlit as st
        # Try Streamlit secrets first
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except:
        pass
    # Fallback to environment variable
    return os.getenv(key, default)

# Gemini API Configuration
GEMINI_API_KEY = get_config("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
GEMINI_MODEL = get_config("GEMINI_MODEL", os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
GEMINI_EMBEDDING_MODEL = get_config("GEMINI_EMBEDDING_MODEL", os.getenv("GEMINI_EMBEDDING_MODEL", "models/embedding-001"))

# ChromaDB Configuration
CHROMA_DB_PATH = get_config("CHROMA_DB_PATH", os.getenv("CHROMA_DB_PATH", "./chroma_db"))
COLLECTION_NAME = get_config("COLLECTION_NAME", os.getenv("COLLECTION_NAME", "mutual_funds"))

# Data Configuration
DATA_DIR = get_config("DATA_DIR", os.getenv("DATA_DIR", "./data/mutual_funds"))

# RAG Configuration
CHUNK_SIZE = int(get_config("CHUNK_SIZE", os.getenv("CHUNK_SIZE", "1000")))
CHUNK_OVERLAP = int(get_config("CHUNK_OVERLAP", os.getenv("CHUNK_OVERLAP", "200")))
TOP_K_RESULTS = int(get_config("TOP_K_RESULTS", os.getenv("TOP_K_RESULTS", "5")))

# API Configuration (for local development)
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))

