"""
FastAPI main application with RAG endpoints.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from typing import List
import config
import os
import time
import logging
from datetime import datetime
from api.schemas import (
    IngestRequest, IngestResponse,
    SearchRequest, SearchResponse,
    QueryRequest, QueryResponse,
    HealthResponse,
    ScraperStatusResponse
)
from ingestion.document_loader import JSONDocumentLoader
from ingestion.chunker import DocumentChunker
from vector_store.chroma_store import ChromaVectorStore
from retrieval.rag_chain import RAGChain
from api.validation import contains_pii, validate_comparison

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class APILoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log API calls with details."""
    
    async def dispatch(self, request: Request, call_next):
        """Log request and response details."""
        start_time = time.time()
        
        # Log request
        client_ip = request.client.host if request.client else "unknown"
        logger.info(f"→ {request.method} {request.url.path} | IP: {client_ip}")
        
        # Log query parameters if present
        if request.url.query:
            logger.info(f"  Query params: {request.url.query}")
        
        # Process request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log successful response
            status_code = response.status_code
            status_emoji = "✓" if 200 <= status_code < 300 else "⚠" if 300 <= status_code < 400 else "✗"
            logger.info(
                f"{status_emoji} {request.method} {request.url.path} | "
                f"Status: {status_code} | Time: {process_time:.3f}s"
            )
            
            # Log error details for 4xx and 5xx responses
            if status_code >= 400:
                logger.error(
                    f"  Error: {status_code} - {request.method} {request.url.path} | "
                    f"Time: {process_time:.3f}s"
                )
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"✗ {request.method} {request.url.path} | "
                f"Exception: {str(e)} | Time: {process_time:.3f}s",
                exc_info=True
            )
            raise


# Initialize FastAPI app
app = FastAPI(
    title="RAG-based Mutual Fund Chatbot API",
    description="API for RAG-based chatbot using Gemini, ChromaDB, and LangChain",
    version="1.0.0"
)

# Add API logging middleware (before CORS)
app.add_middleware(APILoggingMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Global instances (initialized on startup)
vector_store: ChromaVectorStore = None
rag_chain: RAGChain = None
scheduled_scraper = None


@app.on_event("startup")
async def startup_event():
    """Initialize vector store, RAG chain, and scheduled scraper on startup."""
    global vector_store, rag_chain, scheduled_scraper
    
    try:
        logger.info("=" * 70)
        logger.info("Starting RAG-based Mutual Fund Chatbot API")
        logger.info("=" * 70)
        
        # Step 1: Initialize vector store
        logger.info("Step 1: Initializing vector store...")
        vector_store = ChromaVectorStore()
        logger.info("✓ Vector store initialized successfully")
        
        # Step 2: Initialize RAG chain
        logger.info("Step 2: Initializing RAG chain...")
        rag_chain = RAGChain(vector_store)
        logger.info("✓ RAG chain initialized successfully")
        
        # Step 3: Check and start scheduled scraper if enabled
        logger.info("Step 3: Checking scheduled scraper configuration...")
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            from scripts.scheduled_scraper import ScheduledScraper
            
            # Load scraper config
            config_path = os.getenv("SCRAPER_CONFIG_PATH", "scraper_config.json")
            scheduled_scraper = ScheduledScraper(config_path=config_path)
            
            schedule_config = scheduled_scraper.config.get("schedule", {})
            is_enabled = schedule_config.get("enabled", False)
            
            if is_enabled:
                logger.info("✓ Scheduled scraper is enabled in config")
                
                # Check for new URLs first (highest priority)
                logger.info("Step 4: Checking for new URLs...")
                try:
                    new_urls = scheduled_scraper.detect_new_urls()
                    
                    if new_urls:
                        logger.info(f"  ⚠ Found {len(new_urls)} new URL(s) - will process immediately")
                        for url in new_urls:
                            logger.info(f"    - {url}")
                        
                        # Run pipeline for new URLs in background (non-blocking)
                        logger.info("Step 5: Starting pipeline for new URLs in background...")
                        try:
                            # Run in thread pool to avoid Playwright async/sync conflicts
                            def run_pipeline():
                                try:
                                    result = scheduled_scraper.run_full_pipeline(force=True, check_new_urls=True)
                                    scraping_status = result.get("scraping", {}).get("status", "unknown")
                                    ingestion_status = result.get("ingestion", {}).get("status", "unknown")
                                    new_urls_count = result.get("new_urls_detected", 0)
                                    
                                    logger.info(f"✓ Pipeline completed for new URLs")
                                    logger.info(f"  - New URLs processed: {new_urls_count}")
                                    logger.info(f"  - Scraping: {scraping_status}")
                                    logger.info(f"  - Ingestion: {ingestion_status}")
                                    
                                    # Update vector store info after ingestion
                                    collection_info = vector_store.get_collection_info()
                                    logger.info(f"  - Total documents in vector DB: {collection_info['document_count']}")
                                except Exception as e:
                                    logger.warning(f"⚠ Pipeline for new URLs failed: {e}")
                                    logger.warning("  Server will continue, but new URLs may not be processed")
                            
                            # Start in background thread (non-blocking)
                            import threading
                            pipeline_thread = threading.Thread(target=run_pipeline, daemon=True)
                            pipeline_thread.start()
                            logger.info("  Pipeline started in background thread")
                            
                        except Exception as e:
                            logger.warning(f"⚠ Error starting pipeline for new URLs: {e}")
                            logger.warning("  Server will continue, but new URLs may not be processed")
                    
                    # Check if data needs update based on timestamp (only if no new URLs)
                    if not new_urls:
                        logger.info("Step 5: Checking data freshness...")
                        schedule_config = scheduled_scraper.config.get("schedule", {})
                        interval_type = schedule_config.get("interval_type", "hourly")
                        interval_hours = schedule_config.get("interval_hours", 1)
                        
                        # Convert interval to hours
                        if interval_type == "daily":
                            interval_days = schedule_config.get("interval_days", 1)
                            interval_hours = interval_days * 24
                        
                        needs_update, latest_timestamp, next_update_time = vector_store.check_if_data_needs_update(interval_hours)
                        
                        if latest_timestamp:
                            logger.info(f"  Latest ingestion timestamp: {latest_timestamp}")
                            time_since_ingestion = datetime.now() - latest_timestamp
                            logger.info(f"  Time since last ingestion: {time_since_ingestion}")
                        
                        if needs_update:
                            logger.info("  ⚠ Data is stale, running pipeline...")
                            
                            # Run initial scrape + ingest on startup (in background, non-blocking)
                            logger.info("Step 6: Starting initial scrape and ingestion in background...")
                            try:
                                # Run in background thread to avoid Playwright async/sync conflicts
                                def run_pipeline():
                                    try:
                                        result = scheduled_scraper.run_full_pipeline(force=True, check_new_urls=False)
                                        scraping_status = result.get("scraping", {}).get("status", "unknown")
                                        ingestion_status = result.get("ingestion", {}).get("status", "unknown")
                                        
                                        logger.info(f"✓ Initial pipeline completed")
                                        logger.info(f"  - Scraping: {scraping_status}")
                                        logger.info(f"  - Ingestion: {ingestion_status}")
                                        
                                        # Update vector store info after ingestion
                                        collection_info = vector_store.get_collection_info()
                                        logger.info(f"  - Total documents in vector DB: {collection_info['document_count']}")
                                    except Exception as e:
                                        logger.warning(f"⚠ Initial scrape/ingest failed: {e}")
                                        logger.warning("  Server will continue, but data may be outdated")
                                
                                # Start in background thread (non-blocking)
                                import threading
                                pipeline_thread = threading.Thread(target=run_pipeline, daemon=True)
                                pipeline_thread.start()
                                logger.info("  Pipeline started in background thread")
                                
                            except Exception as e:
                                logger.warning(f"⚠ Error starting initial pipeline: {e}")
                                logger.warning("  Server will continue, but data may be outdated")
                                logger.warning("  Scheduled runs will continue according to config")
                        else:
                            logger.info("  ✓ Data is fresh, skipping initial pipeline")
                            if next_update_time:
                                logger.info(f"  Next update scheduled: {next_update_time}")
                            
                            # Update vector store info
                            collection_info = vector_store.get_collection_info()
                            logger.info(f"  - Total documents in vector DB: {collection_info['document_count']}")
                    else:
                        logger.info("  ✓ New URLs processed, skipping timestamp check")
                    
                except Exception as e:
                    logger.warning(f"⚠ Error checking data freshness: {e}")
                    logger.warning("  Will run initial pipeline as fallback")
                    try:
                        initial_result = scheduled_scraper.run_full_pipeline(force=True)
                        scraping_status = initial_result.get("scraping", {}).get("status", "unknown")
                        ingestion_status = initial_result.get("ingestion", {}).get("status", "unknown")
                        logger.info(f"✓ Initial pipeline completed (fallback)")
                        logger.info(f"  - Scraping: {scraping_status}")
                        logger.info(f"  - Ingestion: {ingestion_status}")
                    except Exception as e2:
                        logger.warning(f"⚠ Initial scrape/ingest failed: {e2}")
                        logger.warning("  Server will continue, but data may be outdated")
                
                # Start scheduled scraper service in background
                logger.info("Step 7: Starting scheduled scraper service...")
                scheduled_scraper.start()
                
                next_run = scheduled_scraper.next_run
                if next_run:
                    logger.info(f"✓ Scheduled scraper service started")
                    logger.info(f"  Next scheduled run: {next_run}")
                else:
                    logger.info("✓ Scheduled scraper service started (no next run scheduled)")
            else:
                logger.info("ℹ Scheduled scraper is disabled in config")
                logger.info("  To enable, set 'schedule.enabled: true' in scraper_config.json")
                
        except FileNotFoundError:
            logger.warning("⚠ scraper_config.json not found, skipping scheduled scraper")
        except Exception as e:
            logger.warning(f"⚠ Error setting up scheduled scraper: {e}")
            logger.warning("  Server will continue without scheduled scraping")
            import traceback
            logger.debug(traceback.format_exc())
        
        logger.info("=" * 70)
        logger.info("✓ RAG backend initialized successfully")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"✗ Error initializing RAG backend: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown."""
    global scheduled_scraper
    
    try:
        if scheduled_scraper:
            logger.info("Stopping scheduled scraper service...")
            scheduled_scraper.stop()
            logger.info("✓ Scheduled scraper service stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduled scraper: {e}", exc_info=True)


@app.get("/", tags=["General"])
async def root():
    """Root endpoint - redirects to frontend."""
    from fastapi.responses import FileResponse
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "RAG-based Mutual Fund Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "ingest": "/api/v1/ingest",
            "search": "/api/v1/search",
            "query": "/api/v1/query",
            "docs": "/docs"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """Health check endpoint."""
    try:
        if vector_store is None:
            raise HTTPException(status_code=503, detail="Vector store not initialized")
        
        collection_info = vector_store.get_collection_info()
        
        return HealthResponse(
            status="healthy",
            collection_info=collection_info
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ingest", response_model=IngestResponse, tags=["Ingestion"])
async def ingest_documents(request: IngestRequest):
    """
    Ingest documents from the data directory.
    
    This endpoint:
    1. Loads JSON documents from the data directory
    2. Chunks the documents
    3. Generates embeddings
    4. Stores them in ChromaDB
    """
    try:
        # Determine data directory
        data_dir = request.data_dir or config.DATA_DIR
        logger.info(f"Starting ingestion from: {data_dir} (upsert={request.upsert})")
        
        # Load documents
        loader = JSONDocumentLoader(data_dir)
        documents = loader.load_documents()
        logger.info(f"Loaded {len(documents)} documents")
        
        if not documents:
            logger.error("No documents found to ingest")
            raise HTTPException(status_code=400, detail="No documents found to ingest")
        
        # Chunk documents
        chunker = DocumentChunker()
        chunks = chunker.chunk_documents(documents)
        logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")
        
        # Store in vector database
        if request.upsert:
            logger.info("Upserting documents to vector store...")
            doc_ids = vector_store.upsert_documents(chunks)
        else:
            logger.info("Adding documents to vector store...")
            doc_ids = vector_store.add_documents(chunks)
        
        # Get collection info
        collection_info = vector_store.get_collection_info()
        logger.info(
            f"Ingestion complete: {len(doc_ids)} chunks stored, "
            f"Total in DB: {collection_info['document_count']}"
        )
        
        return IngestResponse(
            message=f"Successfully {'upserted' if request.upsert else 'added'} documents",
            documents_processed=len(documents),
            chunks_created=len(chunks),
            collection_info=collection_info
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/search", response_model=SearchResponse, tags=["Retrieval"])
async def similarity_search(request: SearchRequest):
    """
    Perform similarity search in the vector store.
    
    Returns the most similar documents to the query.
    """
    try:
        if vector_store is None:
            raise HTTPException(status_code=503, detail="Vector store not initialized")
        
        # Perform search
        results = vector_store.similarity_search(
            query=request.query,
            k=request.k,
            filter=request.filter
        )
        
        # Format results
        formatted_results = []
        for doc in results:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata
            })
        
        return SearchResponse(
            query=request.query,
            results=formatted_results,
            count=len(formatted_results)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/query", response_model=QueryResponse, tags=["RAG"])
async def query_rag(request: QueryRequest):
    """
    Query the RAG system with a question.
    
    This endpoint:
    1. Retrieves relevant documents from the vector store
    2. Generates an answer using Gemini LLM
    3. Returns the answer with source citations
    """
    try:
        if rag_chain is None:
            logger.error("RAG chain not initialized")
            raise HTTPException(status_code=503, detail="RAG chain not initialized")
        
        # Validate for PII
        pii_type = contains_pii(request.question)
        if pii_type:
            logger.warning(f"Query rejected due to PII detection: {pii_type}")
            raise HTTPException(
                status_code=400,
                detail=f"I cannot process questions containing personally identifiable information (PII) such as {pii_type}. For your privacy and security, please do not enter sensitive information like PAN numbers, Aadhaar numbers, account details, phone numbers, or email addresses. Please rephrase your question without any sensitive information."
            )
        
        # Validate comparison questions
        comparison_validation = validate_comparison(request.question)
        if not comparison_validation['valid']:
            logger.warning(f"Query rejected due to invalid comparison: {request.question[:100]}")
            raise HTTPException(
                status_code=400,
                detail=comparison_validation['reason']
            )
        
        logger.info(f"Processing query: '{request.question[:100]}...' (k={request.k or 'default'})")
        
        # Clear history if requested
        if request.clear_history:
            logger.info("Clearing conversation history")
            rag_chain.clear_memory()
        
        # Query with retrieval
        result = rag_chain.query_with_retrieval(
            question=request.question,
            k=request.k,
            return_scores=request.return_scores
        )
        
        logger.info(
            f"Query completed: Retrieved {result['retrieved_documents']} documents, "
            f"Answer length: {len(result['answer'])} chars"
        )
        
        # Convert to response model
        from api.schemas import SourceInfo
        sources = [
            SourceInfo(
                content=src["content"],
                metadata=src["metadata"],
                similarity_score=src.get("similarity_score")
            )
            for src in result["sources"]
        ]
        
        return QueryResponse(
            answer=result["answer"],
            question=result["question"],
            retrieved_documents=result["retrieved_documents"],
            sources=sources,
            citation_urls=result.get("citation_urls", []),  # All citation URLs for proper traceback
            last_updated=result.get("last_updated")  # Latest source date for transparency
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/collection", tags=["Admin"])
async def delete_collection():
    """
    Delete the entire collection (admin endpoint).
    
    WARNING: This will delete all stored vectors.
    """
    try:
        if vector_store is None:
            raise HTTPException(status_code=503, detail="Vector store not initialized")
        
        vector_store.delete_collection()
        
        return {
            "message": "Collection deleted successfully",
            "collection_name": vector_store.collection_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/scraper-status", response_model=ScraperStatusResponse, tags=["Admin"])
async def get_scraper_status():
    """
    Get current status of scraping/ingestion operations.
    Frontend can poll this endpoint to show loading indicators.
    """
    try:
        if scheduled_scraper is None:
            return ScraperStatusResponse(
                is_running=False,
                message="Scraper not initialized",
                urls_processed=[],
                urls_total=0
            )
        
        status = scheduled_scraper.get_status()
        return ScraperStatusResponse(**status)
    except Exception as e:
        logger.error(f"Error getting scraper status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/scrape", tags=["Admin"])
async def trigger_scraping(
    scrape_only: bool = False,
    ingest_only: bool = False,
    config_path: str = "scraper_config.json"
):
    """
    Trigger scraping and/or ingestion manually.
    
    Args:
        scrape_only: If True, only run scraping (skip ingestion)
        ingest_only: If True, only run ingestion (skip scraping)
        config_path: Path to scraper config file
        
    Returns:
        Results of scraping/ingestion operation
    """
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        from scripts.scheduled_scraper import ScheduledScraper
        
        scheduler = ScheduledScraper(config_path=config_path)
        
        # Run in background thread to avoid blocking
        import threading
        def run_operation():
            if scrape_only:
                scheduler.run_scraping()
            elif ingest_only:
                scheduler.run_ingestion()
            else:
                scheduler.run_full_pipeline()
        
        thread = threading.Thread(target=run_operation, daemon=True)
        thread.start()
        
        logger.info("Manual scraping triggered (running in background)")
        
        return {
            "status": "started",
            "message": "Scraping/ingestion started in background. Check /api/v1/scraper-status for progress.",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error triggering scraping: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)

