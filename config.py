"""
Configuration file for RAG backend.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "models/embedding-001")

# ChromaDB Configuration
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "mutual_funds")

# Data Configuration
DATA_DIR = os.getenv("DATA_DIR", "./data/mutual_funds")

# RAG Configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "5"))

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
# Railway provides PORT environment variable, fallback to API_PORT or 8000
API_PORT = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))

