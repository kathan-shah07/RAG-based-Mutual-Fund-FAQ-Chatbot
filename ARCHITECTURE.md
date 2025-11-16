# RAG-based Mutual Fund Chatbot Architecture

## Overview

This document describes the architecture of a RAG (Retrieval-Augmented Generation) based chatbot system for querying mutual fund information. The system uses Gemini as the LLM and embedding model, ChromaDB as the vector database, and LangChain for orchestration. It includes a web scraping pipeline for data collection, a web-based frontend interface, and automated scheduled updates.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Static Web UI (HTML/CSS/JS)                            │  │
│  │  - Chat Interface                                        │  │
│  │  - Real-time Status Updates                              │  │
│  │  - Example Questions                                     │  │
│  └───────────────────────┬──────────────────────────────────┘  │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │  Ingest  │  │  Search  │  │  Query   │  │  Health  │        │
│  │  Endpoint│  │ Endpoint │  │ Endpoint │  │ Endpoint │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │  Scraper │  │  Admin   │  │  Static  │                      │
│  │  Status  │  │  Delete  │  │  Files   │                      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                      │
│  ┌──────────────────────────────────────────┐                   │
│  │  Middleware: CORS, Logging, Validation  │                   │
│  └──────────────────────────────────────────┘                   │
└───────┼─────────────┼─────────────┼─────────────┼──────────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Scraping Pipeline                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Groww       │→ │  JSON        │→ │  Scheduled    │         │
│  │  Scraper     │  │  Storage     │  │  Service      │         │
│  │  (Playwright)│  │              │  │  (Threading)  │         │
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
GrowwScraper (Playwright)
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
User Question (Frontend or API)
    ↓
FastAPI /api/v1/query endpoint
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
JSON Response to User
```

### 4. Search Flow

```
Search Query
    ↓
FastAPI /api/v1/search endpoint
    ↓
ChromaVectorStore.similarity_search()
    ↓
[Similar Documents]
    ↓
JSON Response with Results
```

## Folder Structure

```
MF-Chatbot/
├── api/                          # FastAPI application
│   ├── __init__.py
│   ├── main.py                   # FastAPI app with endpoints & middleware
│   ├── schemas.py                # Pydantic models
│   └── validation.py             # PII detection & comparison validation
├── ingestion/                    # Document processing
│   ├── __init__.py
│   ├── document_loader.py        # JSON file loader with metadata extraction
│   └── chunker.py                # Semantic JSON-aware chunking
├── vector_store/                 # Vector database integration
│   ├── __init__.py
│   └── chroma_store.py           # ChromaDB wrapper with freshness tracking
├── retrieval/                    # RAG implementation
│   ├── __init__.py
│   └── rag_chain.py              # RAG chain with Gemini & URL extraction
├── scrapers/                     # Web scraping
│   └── groww_scraper.py          # Groww website scraper (Playwright)
├── scripts/                      # Utility scripts
│   ├── __init__.py
│   ├── ingest_data.py            # Manual ingestion script
│   ├── scheduled_scraper.py      # Scheduled scraping service
│   ├── load_and_test_pipeline.py # Pipeline testing
│   ├── test_e2e_real_data.py     # End-to-end testing
│   └── test_startup.py            # Startup testing
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest configuration
│   ├── test_all.py                # Test runner
│   ├── test_pipeline_integration.py
│   ├── test_retrieval_flow.py
│   ├── test_scraper_unit.py
│   ├── test_scraper.py
│   └── test_startup_integration.py
├── static/                       # Frontend files
│   ├── index.html                # Main HTML page
│   ├── script.js                 # Frontend JavaScript
│   └── styles.css                # Frontend styles
├── data/                         # Source data
│   ├── mutual_funds/             # JSON files (scraped data)
│   └── downloaded_html/          # Cached HTML (if any)
├── chroma_db/                    # ChromaDB storage (created at runtime)
├── config.py                     # Configuration
├── scraper_config.json            # Scraper configuration (URLs, schedule)
├── start_frontend.py             # Frontend server launcher
├── requirements.txt              # Dependencies
├── .env.example                  # Environment variables template
└── ARCHITECTURE.md               # This file
```

## Key Components

### 1. Document Loader (`ingestion/document_loader.py`)
- Loads JSON files from the data directory recursively
- Converts JSON to structured text format (preserves JSON structure)
- Extracts comprehensive metadata (fund_name, category, risk_level, source URLs, timestamps)
- Tracks file modification times for data freshness

### 2. Chunker (`ingestion/chunker.py`)
- Semantic JSON-aware chunking by grouping related fields
- Creates chunks for: fund_overview, investment_details, costs_and_taxes, holdings, performance_metrics, comparison_data, metadata
- Falls back to RecursiveCharacterTextSplitter for non-JSON content
- Preserves metadata across chunks with chunk indices

### 3. Vector Store (`vector_store/chroma_store.py`)
- Manages ChromaDB collection with persistent storage
- Handles embedding generation with Gemini (batched with rate limiting)
- Provides similarity search functionality (cosine similarity)
- Supports upsert operations for updating existing documents
- Tracks data freshness with timestamps
- Checks if data needs update based on configured intervals

### 4. RAG Chain (`retrieval/rag_chain.py`)
- Orchestrates retrieval and generation
- Uses Gemini LLM for answer generation with conversation memory
- Extracts and normalizes URLs from retrieved documents
- Returns answers with source citations and citation URLs
- Includes last_updated timestamps for transparency

### 5. API Layer (`api/main.py`)
- FastAPI application with REST endpoints
- Handles ingestion, search, and query requests
- Provides health check, admin, and scraper status endpoints
- Serves static frontend files
- Includes CORS middleware for cross-origin requests
- API logging middleware for request/response tracking
- Startup initialization: vector store, RAG chain, scheduled scraper
- Automatic data freshness checks and new URL detection on startup

### 6. Validation (`api/validation.py`)
- PII (Personally Identifiable Information) detection
  - Detects PAN cards, Aadhaar numbers, account numbers, OTPs, emails, phone numbers
- Comparison question validation
  - Restricts performance/return comparisons
  - Allows only factual parameter comparisons (expense ratio, lock-in period, etc.)

### 7. Scraper (`scrapers/groww_scraper.py`)
- Web scraping using Playwright
- Scrapes mutual fund data from Groww website
- Extracts comprehensive fund information (NAV, returns, holdings, etc.)
- Saves data as JSON files with metadata

### 8. Scheduled Scraper Service (`scripts/scheduled_scraper.py`)
- Background service for automated scraping and ingestion
- Configurable schedule (hourly/daily intervals)
- Detects new URLs automatically
- Runs full pipeline (scraping + ingestion) on schedule
- Provides status tracking for frontend polling
- Thread-safe status updates

### 9. Frontend (`static/`)
- Modern web-based chat interface
- Real-time status updates for scraping operations
- Example questions for user guidance
- Responsive design with modern UI/UX

## API Endpoints

### GET `/`
Root endpoint that serves the frontend HTML page or returns API information.

### POST `/api/v1/ingest`
Ingest documents from the data directory.

**Request:**
```json
{
  "data_dir": "./data/mutual_funds",
  "upsert": true
}
```

**Response:**
```json
{
  "message": "Successfully upserted documents",
  "documents_processed": 3,
  "chunks_created": 15,
  "collection_info": {
    "collection_name": "mutual_funds",
    "document_count": 15,
    "db_path": "./chroma_db"
  }
}
```

### POST `/api/v1/search`
Perform similarity search in the vector store.

**Request:**
```json
{
  "query": "large cap funds",
  "k": 5,
  "filter": null
}
```

**Response:**
```json
{
  "query": "large cap funds",
  "results": [
    {
      "content": "Fund Name: Nippon India Large Cap...",
      "metadata": {
        "source_file": "nippon-india-large-cap-fund-direct-growth.json",
        "fund_name": "Nippon India Large Cap Fund Direct Growth"
      }
    }
  ],
  "count": 5
}
```

### POST `/api/v1/query`
Query the RAG system with validation.

**Request:**
```json
{
  "question": "What is the NAV of Nippon India Large Cap Fund?",
  "k": 5,
  "return_sources": true,
  "return_scores": false,
  "clear_history": false
}
```

**Response:**
```json
{
  "answer": "The NAV of Nippon India Large Cap Fund Direct Growth is ₹104.68 as of 12 Nov 2025...",
  "question": "What is the NAV of Nippon India Large Cap Fund?",
  "retrieved_documents": 3,
  "sources": [
    {
      "content": "Fund Name: Nippon India Large Cap Fund...",
      "metadata": {
        "source_file": "nippon-india-large-cap-fund-direct-growth.json",
        "fund_name": "Nippon India Large Cap Fund Direct Growth"
      },
      "similarity_score": 0.92
    }
  ],
  "citation_urls": ["https://groww.in/mutual-funds/..."],
  "last_updated": "2025-11-12T10:30:00"
}
```

### GET `/health`
Health check endpoint with collection information.

**Response:**
```json
{
  "status": "healthy",
  "collection_info": {
    "collection_name": "mutual_funds",
    "document_count": 15,
    "db_path": "./chroma_db"
  }
}
```

### DELETE `/api/v1/collection`
Admin endpoint to delete the entire collection.

**WARNING:** This will delete all stored vectors.

**Response:**
```json
{
  "message": "Collection deleted successfully",
  "collection_name": "mutual_funds"
}
```

### GET `/api/v1/scraper-status`
Get current status of scraping/ingestion operations.

**Response:**
```json
{
  "is_running": false,
  "current_operation": null,
  "progress": null,
  "message": "Idle",
  "urls_processed": [],
  "urls_total": 0,
  "start_time": null,
  "end_time": null,
  "error": null,
  "last_updated": "2025-11-12T10:30:00"
}
```

### POST `/api/v1/scrape`
Manually trigger scraping and/or ingestion.

**Query Parameters:**
- `scrape_only`: If true, only run scraping (skip ingestion)
- `ingest_only`: If true, only run ingestion (skip scraping)
- `config_path`: Path to scraper config file (default: "scraper_config.json")

**Response:**
```json
{
  "status": "started",
  "message": "Scraping/ingestion started in background. Check /api/v1/scraper-status for progress.",
  "timestamp": "2025-11-12T10:30:00"
}
```

## Configuration

Configuration is managed through `config.py` and environment variables (`.env` file):

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
- `API_HOST`: API server host (default: 0.0.0.0)
- `API_PORT`: API server port (default: 8000)
- `SCRAPER_CONFIG_PATH`: Path to scraper configuration file (default: scraper_config.json)

### Scraper Configuration (`scraper_config.json`)

The scraper configuration file defines:
- URLs to scrape (mutual fund pages from Groww)
- Schedule settings (enabled/disabled, interval type, interval hours/days)
- Scraping behavior (timeouts, retries, etc.)

Example structure:
```json
{
  "urls": [
    "https://groww.in/mutual-funds/...",
    ...
  ],
  "schedule": {
    "enabled": true,
    "interval_type": "hourly",
    "interval_hours": 1
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
Edit `scraper_config.json` to add URLs and configure schedule:
```json
{
  "urls": ["https://groww.in/mutual-funds/..."],
  "schedule": {
    "enabled": true,
    "interval_type": "hourly",
    "interval_hours": 1
  }
}
```

### 4. Start the Server

**Option A: Start with Frontend (Recommended)**
```bash
python start_frontend.py
```
This will:
- Start the FastAPI server
- Automatically open the browser to the frontend
- Show all API logs in the terminal

**Option B: Start API Server Only**
```bash
python -m api.main
# Or
uvicorn api.main:app --reload
```

The server will automatically:
- Initialize vector store and RAG chain
- Check for new URLs if scraper is enabled
- Run initial scraping/ingestion if data is stale
- Start scheduled scraper service if enabled

### 5. Access the Frontend
Open your browser to `http://localhost:8000` to use the web-based chat interface.

### 6. Ingest Documents (Manual)
```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{"upsert": true}'
```

### 7. Query the System

**Via Frontend:**
- Use the web interface at `http://localhost:8000`
- Type questions in the chat input
- View answers with source citations

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the expense ratio of Nippon India Large Cap Fund?",
    "return_sources": true
  }'
```

### 8. Check Scraper Status
```bash
curl "http://localhost:8000/api/v1/scraper-status"
```

### 9. Manually Trigger Scraping
```bash
curl -X POST "http://localhost:8000/api/v1/scrape"
```

## Technology Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **LangChain**: Framework for LLM applications and orchestration
- **Google Gemini**: LLM and embedding model
- **ChromaDB**: Open-source vector database
- **Pydantic**: Data validation using Python type annotations
- **Uvicorn**: ASGI server for FastAPI
- **Playwright**: Browser automation for web scraping
- **HTML/CSS/JavaScript**: Frontend web interface

## Design Decisions

1. **Gemini for Embeddings**: Using Gemini's embedding model ensures consistency with the LLM and better semantic understanding.

2. **ChromaDB**: Lightweight, persistent vector database that doesn't require separate infrastructure.

3. **Semantic JSON-aware Chunking**: Groups related fields together (fund_overview, investment_details, etc.) for better embedding quality and retrieval accuracy.

4. **Batched Embeddings with Rate Limiting**: Processes embeddings in batches with delays to respect API quotas and avoid rate limit errors.

5. **Upsert Support**: Allows updating existing documents without recreating the entire index.

6. **Source Citations**: All answers include source documents, citation URLs, and last_updated timestamps for transparency and verification.

7. **Conversation Memory**: RAG chain maintains context for follow-up questions.

8. **PII Detection**: Validates user queries to prevent processing of personally identifiable information (PAN, Aadhaar, account numbers, etc.) for privacy and security.

9. **Comparison Question Validation**: Restricts performance/return comparisons while allowing factual parameter comparisons (expense ratio, lock-in period, etc.) to prevent investment advice.

10. **Scheduled Scraping Service**: Automated background service for keeping data fresh without manual intervention.

11. **New URL Detection**: Automatically detects and processes new URLs added to the scraper configuration.

12. **Data Freshness Tracking**: Tracks ingestion timestamps and checks if data needs updating based on configured intervals.

13. **Frontend Integration**: Web-based chat interface for better user experience, with real-time status updates for scraping operations.

14. **API Logging Middleware**: Comprehensive logging of all API requests and responses for debugging and monitoring.

15. **CORS Support**: Enables cross-origin requests for frontend integration.

16. **Startup Initialization**: Automatic initialization of all components (vector store, RAG chain, scheduled scraper) with intelligent data freshness checks.

