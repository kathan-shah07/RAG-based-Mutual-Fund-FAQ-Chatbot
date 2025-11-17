# RAG-based Mutual Fund Chatbot Architecture

## Overview

This document describes the architecture of a RAG (Retrieval-Augmented Generation) based chatbot system for querying mutual fund information. The system uses Gemini as the LLM and embedding model, ChromaDB as the vector database, and LangChain for orchestration. It includes a web scraping pipeline for data collection, a Streamlit-based web interface, and automated scheduled updates.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Streamlit Frontend Layer                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Streamlit App (app.py)                                  │  │
│  │  - Chat Interface                                         │  │
│  │  - Real-time Status Updates                               │  │
│  │  - Example Questions                                      │  │
│  │  - Sidebar with Status & Controls                         │  │
│  └───────────────────────┬──────────────────────────────────┘  │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend Components                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │  RAG     │  │  Vector  │  │  Scraper │  │  Config  │     │
│  │  Chain   │  │  Store   │  │  Service │  │  Manager │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Validation: PII Detection & Comparison Validation      │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────┼─────────────┼─────────────┼─────────────┼──────────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Scraping Pipeline                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Groww       │→ │  JSON        │→ │  Scheduled    │         │
│  │  Scraper     │  │  Storage     │  │  Service      │         │
│  │  (Playwright │  │              │  │  (Threading)  │         │
│  │   /Selenium) │  │              │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Ingestion Pipeline                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ JSON Loader  │→ │   Chunker    │→ │   Embedder   │         │
│  │  (Metadata   │  │ (Semantic    │  │  (Gemini)    │         │
│  │   Extraction)│  │  JSON-aware) │  │  (Batched)   │         │
│  └──────────────┘  └──────────────┘  └──────┬───────┘         │
└───────────────────────────────────────────────┼─────────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ChromaDB Vector Store                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Collection: mutual_funds                                │  │
│  │  - Document embeddings                                    │  │
│  │  - Metadata (source, fund_name, etc.)                     │  │
│  │  - Similarity search (cosine)                             │  │
│  │  - Data freshness tracking                                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Retrieval & RAG Pipeline                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Retriever   │→ │  Validation  │→ │  Gemini LLM  │         │
│  │  (Similarity │  │  (PII,       │  │  (Answer     │         │
│  │   Search)    │  │   Comparison)│  │   Generator) │         │
│  └──────────────┘  └──────────────┘  └──────┬───────┘         │
│                                               │                 │
│  ┌────────────────────────────────────────────┘                 │
│  │  URL Extraction & Citation                                │
│  └────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Scraping Flow

```
Groww Website URLs (scraper_config.json)
    ↓
GrowwScraper (Playwright/Selenium/requests)
    ↓
[Scraped Fund Data]
    ↓
JSON Files (data/mutual_funds/*.json)
    ↓
ScheduledScraper Service
    ↓
[Automatic Updates on Schedule]
```

### 2. Ingestion Flow

```
JSON Files (data/mutual_funds/*.json)
    ↓
JSONDocumentLoader
    ↓
[Document objects with comprehensive metadata]
    ↓
DocumentChunker (Semantic JSON-aware chunking)
    ↓
[Chunked Documents by semantic groups]
    ↓
GoogleGenerativeAIEmbeddings (Batched with rate limiting)
    ↓
[Embeddings]
    ↓
ChromaVectorStore.upsert_documents()
    ↓
ChromaDB (Persistent Storage with timestamps)
```

### 3. Query Flow

```
User Question (Streamlit Frontend)
    ↓
app.py (Streamlit App)
    ↓
Validation (PII detection, comparison validation)
    ↓
RAGChain.query_with_retrieval()
    ↓
ChromaVectorStore.similarity_search()
    ↓
[Retrieved Documents with Context]
    ↓
Gemini LLM (with context prompt)
    ↓
[Answer Generation with URL Extraction]
    ↓
Generated Answer + Sources + Citation URLs
    ↓
Display in Streamlit Chat Interface
```

### 4. Scheduled Updates Flow

```
ScheduledScraper Service (Background Thread)
    ↓
Check for New URLs (URL-based detection)
    ↓
Check Data Freshness (Timestamp-based)
    ↓
Run Scraping (if needed)
    ↓
Run Ingestion (if auto_ingest enabled)
    ↓
Update Status (for frontend polling)
```

## Folder Structure

```
MF-Chatbot/
├── app.py                          # Main Streamlit application
├── config.py                       # Configuration management
├── scraper_config.json             # Scraper configuration (URLs, schedule)
├── requirements.txt                # Python dependencies
├── packages.txt                    # System dependencies (for Streamlit Cloud)
├── .env.example                    # Environment variables template
├── api/                            # API validation utilities
│   ├── __init__.py
│   └── validation.py               # PII detection & comparison validation
├── ingestion/                      # Document processing
│   ├── __init__.py
│   ├── document_loader.py          # JSON file loader with metadata extraction
│   └── chunker.py                  # Semantic JSON-aware chunking
├── vector_store/                   # Vector database integration
│   ├── __init__.py
│   └── chroma_store.py             # ChromaDB wrapper with freshness tracking
├── retrieval/                      # RAG implementation
│   ├── __init__.py
│   └── rag_chain.py                # RAG chain with Gemini & URL extraction
├── scrapers/                       # Web scraping
│   └── groww_scraper.py           # Groww website scraper (Playwright/Selenium)
├── scripts/                        # Utility scripts
│   ├── __init__.py
│   ├── ingest_data.py             # Manual ingestion script
│   ├── scheduled_scraper.py       # Scheduled scraping service
│   ├── load_and_test_pipeline.py  # Pipeline testing
│   ├── test_e2e_real_data.py      # End-to-end testing
│   └── test_startup.py            # Startup testing
├── tests/                          # Test suite
│   ├── __init__.py
│   ├── conftest.py                 # Pytest configuration
│   ├── test_all.py                 # Test runner
│   ├── test_pipeline_integration.py
│   ├── test_retrieval_flow.py
│   ├── test_scraper_unit.py
│   ├── test_scraper.py
│   └── test_startup_integration.py
├── data/                           # Source data
│   ├── mutual_funds/               # JSON files (scraped data)
│   └── downloaded_html/            # Cached HTML (if any)
├── chroma_db/                      # ChromaDB storage (created at runtime)
├── ARCHITECTURE.md                 # This file
├── README.md                       # Project documentation
└── STREAMLIT_CLOUD_DEPLOYMENT.md   # Deployment guide
```

## Key Components

### 1. Streamlit Application (`app.py`)
- Main entry point for the application
- Provides interactive chat interface with modern UI/UX
- Displays real-time scraper status in sidebar
- Handles user input validation and query processing
- Manages conversation history and session state
- Auto-initializes backend components on startup
- Supports Streamlit Cloud deployment

### 2. Document Loader (`ingestion/document_loader.py`)
- Loads JSON files from the data directory recursively
- Converts JSON to structured text format (preserves JSON structure)
- Extracts comprehensive metadata (fund_name, category, risk_level, source URLs, timestamps)
- Tracks file modification times for data freshness

### 3. Chunker (`ingestion/chunker.py`)
- Semantic JSON-aware chunking by grouping related fields
- Creates chunks for: fund_overview, investment_details, costs_and_taxes, holdings, performance_metrics, comparison_data, metadata
- Falls back to RecursiveCharacterTextSplitter for non-JSON content
- Preserves metadata across chunks with chunk indices

### 4. Vector Store (`vector_store/chroma_store.py`)
- Manages ChromaDB collection with persistent storage
- Handles embedding generation with Gemini (batched with rate limiting)
- Provides similarity search functionality (cosine similarity)
- Supports upsert operations for updating existing documents
- Tracks data freshness with timestamps
- Checks if data needs update based on configured intervals
- Detects new URLs automatically
- Counts unique funds in the database

### 5. RAG Chain (`retrieval/rag_chain.py`)
- Orchestrates retrieval and generation
- Uses Gemini LLM for answer generation with conversation memory
- Extracts and normalizes URLs from retrieved documents
- Returns answers with source citations and citation URLs
- Includes last_updated timestamps for transparency
- Handles parameter-only queries (e.g., "show AUM for all funds")
- Formats answers as tables, lists, or structured text
- Limits answer length to 3 sentences for conciseness

### 6. Validation (`api/validation.py`)
- PII (Personally Identifiable Information) detection
  - Detects PAN cards, Aadhaar numbers, account numbers, OTPs, emails, phone numbers
- Comparison question validation
  - Restricts performance/return comparisons
  - Allows only factual parameter comparisons (expense ratio, lock-in period, etc.)

### 7. Scraper (`scrapers/groww_scraper.py`)
- Web scraping using Playwright (primary), Selenium (fallback), or requests (last resort)
- Scrapes mutual fund data from Groww website
- Extracts comprehensive fund information (NAV, returns, holdings, etc.)
- Saves data as JSON files with metadata
- Handles dynamic content loading
- Supports retry logic and error handling

### 8. Scheduled Scraper Service (`scripts/scheduled_scraper.py`)
- Background service for automated scraping and ingestion
- Configurable schedule (hourly/daily intervals)
- Detects new URLs automatically (URL-based detection)
- Runs full pipeline (scraping + ingestion) on schedule
- Provides status tracking for frontend polling
- Thread-safe status updates
- Checks data freshness before running
- Runs initial pipeline if no data exists

### 9. Configuration (`config.py`)
- Manages environment variables and Streamlit secrets
- Supports both `.env` files and Streamlit Cloud secrets
- Provides default values for all configuration options
- Handles API keys, model names, paths, and other settings

## Configuration

Configuration is managed through `config.py` and environment variables (`.env` file or Streamlit secrets):

### Environment Variables

- `GEMINI_API_KEY`: Your Gemini API key (required)
- `GEMINI_MODEL`: LLM model name (default: gemini-1.5-flash)
- `GEMINI_EMBEDDING_MODEL`: Embedding model (default: models/embedding-001)
- `CHROMA_DB_PATH`: Path to ChromaDB storage (default: ./chroma_db)
- `COLLECTION_NAME`: ChromaDB collection name (default: mutual_funds)
- `DATA_DIR`: Path to JSON data files (default: ./data/mutual_funds)
- `CHUNK_SIZE`: Document chunk size (default: 1000)
- `CHUNK_OVERLAP`: Chunk overlap size (default: 200)
- `TOP_K_RESULTS`: Default number of retrieval results (default: 5)

### Scraper Configuration (`scraper_config.json`)

The scraper configuration file defines:
- URLs to scrape (mutual fund pages from Groww)
- Schedule settings (enabled/disabled, interval type, interval hours/days)
- Scraping behavior (timeouts, retries, output directories, etc.)

Example structure:
```json
{
  "scraper_settings": {
    "output_dir": "./data/mutual_funds",
    "download_dir": "./data/downloaded_html",
    "use_interactive": true,
    "download_first": true,
    "retry_failed": true,
    "max_retries": 3
  },
  "urls": [
    {
      "url": "https://groww.in/mutual-funds/..."
    }
  ],
  "schedule": {
    "enabled": true,
    "interval_type": "hourly",
    "interval_hours": 1,
    "auto_ingest_after_scrape": true
  }
}
```

## Usage Example

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Configure Scraper (Optional)
Edit `scraper_config.json` to add URLs and configure schedule.

### 4. Start the Application

```bash
streamlit run app.py
```

The application will automatically:
- Initialize vector store and RAG chain
- Check for new URLs if scraper is enabled
- Run initial scraping/ingestion if data is stale or missing
- Start scheduled scraper service if enabled

### 5. Access the Frontend
Open your browser to `http://localhost:8501` to use the web-based chat interface.

### 6. Ingest Documents (Manual)
```bash
python scripts/ingest_data.py
```

### 7. Query the System

**Via Streamlit Frontend:**
- Use the web interface at `http://localhost:8501`
- Type questions in the chat input
- View answers with source citations
- Check scraper status in the sidebar

### 8. Check Scraper Status
The sidebar in the Streamlit app shows:
- Backend initialization status
- Number of mutual funds scraped
- Number of mutual funds in vector DB
- Last update timestamp
- Current scraper operation status

### 9. Manually Trigger Scraping
```bash
python scripts/scheduled_scraper.py --once
```

## Technology Stack

- **Streamlit**: Modern web framework for building interactive Python apps
- **LangChain**: Framework for LLM applications and orchestration
- **Google Gemini**: LLM and embedding model
- **ChromaDB**: Open-source vector database
- **Pydantic**: Data validation using Python type annotations
- **Playwright/Selenium**: Browser automation for web scraping
- **BeautifulSoup**: HTML parsing for web scraping

## Design Decisions

1. **Streamlit for Frontend**: Provides a modern, interactive web interface without requiring separate frontend development.

2. **Gemini for Embeddings**: Using Gemini's embedding model ensures consistency with the LLM and better semantic understanding.

3. **ChromaDB**: Lightweight, persistent vector database that doesn't require separate infrastructure.

4. **Semantic JSON-aware Chunking**: Groups related fields together (fund_overview, investment_details, etc.) for better embedding quality and retrieval accuracy.

5. **Batched Embeddings with Rate Limiting**: Processes embeddings in batches with delays to respect API quotas and avoid rate limit errors.

6. **Upsert Support**: Allows updating existing documents without recreating the entire index.

7. **Source Citations**: All answers include source documents, citation URLs, and last_updated timestamps for transparency and verification.

8. **Conversation Memory**: RAG chain maintains context for follow-up questions.

9. **PII Detection**: Validates user queries to prevent processing of personally identifiable information (PAN, Aadhaar, account numbers, etc.) for privacy and security.

10. **Comparison Question Validation**: Restricts performance/return comparisons while allowing factual parameter comparisons (expense ratio, lock-in period, etc.) to prevent investment advice.

11. **Scheduled Scraping Service**: Automated background service for keeping data fresh without manual intervention.

12. **New URL Detection**: Automatically detects and processes new URLs added to the scraper configuration using URL-based comparison.

13. **Data Freshness Tracking**: Tracks ingestion timestamps and checks if data needs updating based on configured intervals.

14. **Streamlit Cloud Support**: Designed to work seamlessly on Streamlit Cloud with proper configuration and fallback mechanisms.

15. **Multi-browser Support**: Scraper supports Playwright (primary), Selenium (fallback), and requests (last resort) for maximum compatibility.

16. **Startup Initialization**: Automatic initialization of all components (vector store, RAG chain, scheduled scraper) with intelligent data freshness checks.

17. **Answer Formatting**: Supports tables, lists, and structured text based on query type, with automatic formatting for parameter-only queries.

18. **Concise Answers**: Limits answer length to 3 sentences for better user experience while maintaining accuracy.
