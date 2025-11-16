"""
Pydantic schemas for API request/response models.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class IngestRequest(BaseModel):
    """Request model for document ingestion."""
    data_dir: Optional[str] = Field(None, description="Path to data directory (optional, uses config default if not provided)")
    upsert: bool = Field(True, description="Whether to upsert (update existing) or add new documents")


class IngestResponse(BaseModel):
    """Response model for document ingestion."""
    message: str
    documents_processed: int
    chunks_created: int
    collection_info: Dict[str, Any]


class SearchRequest(BaseModel):
    """Request model for similarity search."""
    query: str = Field(..., description="Search query text")
    k: Optional[int] = Field(None, description="Number of results to return")
    filter: Optional[Dict[str, Any]] = Field(None, description="Optional metadata filter")


class SearchResponse(BaseModel):
    """Response model for similarity search."""
    query: str
    results: List[Dict[str, Any]]
    count: int


class QueryRequest(BaseModel):
    """Request model for RAG query."""
    question: str = Field(..., description="User's question")
    k: Optional[int] = Field(None, description="Number of documents to retrieve")
    return_sources: bool = Field(True, description="Whether to return source documents")
    return_scores: bool = Field(False, description="Whether to return similarity scores")
    clear_history: bool = Field(False, description="Whether to clear conversation history")


class SourceInfo(BaseModel):
    """Model for source document information."""
    content: str
    metadata: Dict[str, Any]
    similarity_score: Optional[float] = None


class QueryResponse(BaseModel):
    """Response model for RAG query."""
    answer: str
    question: str
    retrieved_documents: int
    sources: List[SourceInfo]
    citation_urls: Optional[List[str]] = Field(None, description="All citation URLs for proper traceback")
    last_updated: Optional[str] = Field(None, description="Latest source date for transparency")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    collection_info: Dict[str, Any]


class ScraperStatusResponse(BaseModel):
    """Response model for scraper status."""
    is_running: bool
    current_operation: Optional[str] = None
    progress: Optional[str] = None
    message: str
    urls_processed: List[Dict[str, Any]] = []
    urls_total: int = 0
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    error: Optional[str] = None
    last_updated: Optional[str] = None
