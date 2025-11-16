"""
Comprehensive unit tests for the entire RAG backend system.
Consolidated test file covering all components: ingestion, vector store, retrieval, and API.
"""
import pytest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

# Import modules to test
from ingestion.document_loader import JSONDocumentLoader
from ingestion.chunker import DocumentChunker
from vector_store.chroma_store import ChromaVectorStore
from retrieval.rag_chain import RAGChain
from api.schemas import IngestRequest, QueryRequest, SearchRequest

# Mock environment before importing API
os.environ['GEMINI_API_KEY'] = 'test_api_key_12345'
from api.main import app


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_json_data():
    """Sample JSON data matching the structure of mutual fund data."""
    return [
        {
            "fund_name": "Test Large Cap Fund Direct Growth",
            "nav": {"value": "₹100.50", "as_of": "01 Jan 2025"},
            "fund_size": "₹10,000Cr",
            "summary": {
                "fund_category": "Equity",
                "fund_type": "Large Cap",
                "risk_level": "Very High Risk",
                "lock_in_period": "",
                "rating": None
            },
            "minimum_investments": {
                "min_first_investment": "₹500",
                "min_sip": "₹500",
                "min_2nd_investment_onwards": "₹500"
            },
            "returns": {
                "1y": "12.5%",
                "3y": "18.2%",
                "5y": "20.5%",
                "since_inception": "15.8%"
            },
            "category_info": {
                "category": "Equity Large",
                "category_average_annualised": {
                    "1y": "10.0%",
                    "3y": "15.0%",
                    "5y": "18.0%"
                },
                "rank_within_category": {"1y": 5, "3y": 3, "5y": 2}
            },
            "cost_and_tax": {
                "expense_ratio": "0.75%",
                "expense_ratio_effective_from": "01 Jan 2025",
                "exit_load": "Exit load of 1% if redeemed within 7 days",
                "stamp_duty": "0.005%",
                "tax_implication": "Taxed at 20% if redeemed within one year"
            },
            "top_5_holdings": [
                {"name": "Test Bank Ltd.", "asset_pct": "10.00%"},
                {"name": "Test Industries Ltd.", "asset_pct": "8.00%"}
            ],
            "advanced_ratios": {
                "pe_ratio": "25.0",
                "pb_ratio": "4.0",
                "alpha": "5.5",
                "beta": "0.95",
                "sharpe_ratio": "1.20",
                "sortino_ratio": "1.80"
            },
            "source": {"site": "Test", "page_ref": "test0view0"},
            "source_url": "https://test.com/fund",
            "last_scraped": "2025-01-01"
        }
    ]


@pytest.fixture
def temp_data_dir(sample_json_data, tmp_path):
    """Create a temporary directory with test JSON files."""
    data_dir = tmp_path / "test_data" / "mutual_funds"
    data_dir.mkdir(parents=True)
    test_file = data_dir / "test-fund.json"
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(sample_json_data, f, indent=2)
    return str(data_dir)


@pytest.fixture
def temp_chroma_db(tmp_path):
    """Create a temporary ChromaDB directory."""
    db_path = tmp_path / "test_chroma_db"
    return str(db_path)


@pytest.fixture(autouse=True)
def mock_gemini_api_key():
    """Mock Gemini API key for testing (auto-use for all tests)."""
    with patch.dict(os.environ, {'GEMINI_API_KEY': 'test_api_key_12345'}):
        yield 'test_api_key_12345'


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    with patch('api.main.ChromaVectorStore') as mock_store_class:
        mock_store = Mock()
        mock_store.get_collection_info.return_value = {
            "collection_name": "test_collection",
            "document_count": 10,
            "db_path": "./chroma_db"
        }
        mock_store_class.return_value = mock_store
        yield mock_store


@pytest.fixture
def mock_rag_chain():
    """Mock RAG chain for testing."""
    with patch('api.main.RAGChain') as mock_chain_class:
        mock_chain = Mock()
        mock_chain.query_with_retrieval.return_value = {
            "answer": "Test answer",
            "question": "Test question",
            "retrieved_documents": 3,
            "sources": [{
                "content": "Test content...",
                "metadata": {"fund_name": "Test Fund"},
                "similarity_score": 0.95
            }]
        }
        mock_chain.clear_memory.return_value = None
        mock_chain_class.return_value = mock_chain
        yield mock_chain


# ============================================================================
# Document Loader Tests
# ============================================================================

class TestJSONDocumentLoader:
    """Test cases for JSONDocumentLoader."""
    
    def test_load_documents_success(self, temp_data_dir, sample_json_data):
        """Test successful loading of JSON documents."""
        loader = JSONDocumentLoader(temp_data_dir)
        documents = loader.load_documents()
        
        assert len(documents) == 1
        assert documents[0].page_content is not None
        assert len(documents[0].page_content) > 0
        assert documents[0].metadata["fund_name"] == "Test Large Cap Fund Direct Growth"
        assert documents[0].metadata["source_file"] == "test-fund.json"
    
    def test_load_documents_empty_directory(self, tmp_path):
        """Test loading from empty directory raises error."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        loader = JSONDocumentLoader(str(empty_dir))
        with pytest.raises(ValueError, match="No JSON files found"):
            loader.load_documents()
    
    def test_load_documents_nonexistent_directory(self):
        """Test loading from non-existent directory raises error."""
        loader = JSONDocumentLoader("./nonexistent/path")
        with pytest.raises(FileNotFoundError):
            loader.load_documents()
    
    def test_json_to_text_formatting(self, temp_data_dir):
        """Test that JSON is properly formatted to text."""
        loader = JSONDocumentLoader(temp_data_dir)
        documents = loader.load_documents()
        text = documents[0].page_content
        
        assert "Fund Name: Test Large Cap Fund Direct Growth" in text
        assert "NAV: ₹100.50" in text
        assert "Fund Size: ₹10,000Cr" in text
        assert "Category: Equity" in text
        assert "Type: Large Cap" in text
        assert "Returns:" in text
        assert "Top 5 Holdings:" in text


# ============================================================================
# Document Chunker Tests
# ============================================================================

class TestDocumentChunker:
    """Test cases for DocumentChunker."""
    
    def test_chunk_documents(self, temp_data_dir):
        """Test chunking of documents."""
        loader = JSONDocumentLoader(temp_data_dir)
        documents = loader.load_documents()
        chunker = DocumentChunker(chunk_size=500, chunk_overlap=100)
        chunks = chunker.chunk_documents(documents)
        
        assert len(chunks) >= 1
        assert all(chunk.metadata.get("chunk_index") is not None for chunk in chunks)
        assert all(chunk.metadata.get("total_chunks") is not None for chunk in chunks)
        assert all(len(chunk.page_content) > 0 for chunk in chunks)
    
    def test_chunk_preserves_metadata(self, temp_data_dir):
        """Test that chunking preserves original metadata."""
        loader = JSONDocumentLoader(temp_data_dir)
        documents = loader.load_documents()
        chunker = DocumentChunker()
        chunks = chunker.chunk_documents(documents)
        
        assert chunks[0].metadata["fund_name"] == documents[0].metadata["fund_name"]
        assert chunks[0].metadata["source_file"] == documents[0].metadata["source_file"]


# ============================================================================
# Vector Store Tests
# ============================================================================

class TestChromaVectorStore:
    """Test cases for ChromaVectorStore."""
    
    @patch('vector_store.chroma_store.GoogleGenerativeAIEmbeddings')
    def test_initialize_vector_store(self, mock_embeddings, temp_chroma_db, mock_gemini_api_key):
        """Test initialization of ChromaVectorStore."""
        mock_emb = Mock()
        mock_embeddings.return_value = mock_emb
        
        store = ChromaVectorStore(
            collection_name="test_collection",
            db_path=temp_chroma_db
        )
        
        assert store.collection_name == "test_collection"
        assert store.db_path == temp_chroma_db
        assert store.collection is not None
    
    @patch('vector_store.chroma_store.GoogleGenerativeAIEmbeddings')
    def test_add_documents(self, mock_embeddings, temp_chroma_db, temp_data_dir, mock_gemini_api_key):
        """Test adding documents to vector store."""
        mock_emb = Mock()
        mock_embeddings.return_value = mock_emb
        
        store = ChromaVectorStore(db_path=temp_chroma_db)
        loader = JSONDocumentLoader(temp_data_dir)
        documents = loader.load_documents()
        chunker = DocumentChunker(chunk_size=1000)
        chunks = chunker.chunk_documents(documents)
        
        mock_emb.embed_documents.return_value = [[0.1] * 768] * len(chunks)
        doc_ids = store.add_documents(chunks)
        
        assert len(doc_ids) == len(chunks)
        assert all(isinstance(doc_id, str) for doc_id in doc_ids)
    
    @patch('vector_store.chroma_store.GoogleGenerativeAIEmbeddings')
    def test_similarity_search(self, mock_embeddings, temp_chroma_db, temp_data_dir, mock_gemini_api_key):
        """Test similarity search in vector store."""
        mock_emb = Mock()
        mock_emb.embed_query.return_value = [0.1] * 768
        mock_embeddings.return_value = mock_emb
        
        store = ChromaVectorStore(db_path=temp_chroma_db)
        loader = JSONDocumentLoader(temp_data_dir)
        documents = loader.load_documents()
        chunker = DocumentChunker(chunk_size=1000)
        chunks = chunker.chunk_documents(documents)
        
        mock_emb.embed_documents.return_value = [[0.1] * 768] * len(chunks)
        store.add_documents(chunks)
        
        results = store.similarity_search("large cap fund", k=2)
        assert isinstance(results, list)
        assert len(results) <= 2
    
    @patch('vector_store.chroma_store.GoogleGenerativeAIEmbeddings')
    def test_get_collection_info(self, mock_embeddings, temp_chroma_db, mock_gemini_api_key):
        """Test getting collection information."""
        mock_emb = Mock()
        mock_embeddings.return_value = mock_emb
        
        store = ChromaVectorStore(db_path=temp_chroma_db)
        info = store.get_collection_info()
        
        assert "collection_name" in info
        assert "document_count" in info
        assert "db_path" in info
        assert isinstance(info["document_count"], int)


# ============================================================================
# RAG Chain Tests
# ============================================================================

class TestRAGChain:
    """Test cases for RAGChain."""
    
    @patch('retrieval.rag_chain.ChatGoogleGenerativeAI')
    @patch('vector_store.chroma_store.GoogleGenerativeAIEmbeddings')
    def test_initialize_rag_chain(self, mock_embeddings, mock_llm, temp_chroma_db, mock_gemini_api_key):
        """Test initialization of RAG chain."""
        mock_emb = Mock()
        mock_embeddings.return_value = mock_emb
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        store = ChromaVectorStore(db_path=temp_chroma_db)
        rag_chain = RAGChain(store)
        
        assert rag_chain.vector_store is not None
        assert rag_chain.llm is not None
        assert rag_chain.retriever is not None
    
    @patch('retrieval.rag_chain.ChatGoogleGenerativeAI')
    @patch('vector_store.chroma_store.GoogleGenerativeAIEmbeddings')
    def test_query_with_retrieval(self, mock_embeddings, mock_llm, temp_chroma_db, temp_data_dir, mock_gemini_api_key):
        """Test querying the RAG chain."""
        mock_emb = Mock()
        mock_emb.embed_query.return_value = [0.1] * 768
        mock_embeddings.return_value = mock_emb
        
        mock_llm_instance = Mock()
        mock_response = Mock()
        mock_response.content = "The NAV is ₹100.50 as of 01 Jan 2025."
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm.return_value = mock_llm_instance
        
        store = ChromaVectorStore(db_path=temp_chroma_db)
        loader = JSONDocumentLoader(temp_data_dir)
        documents = loader.load_documents()
        chunker = DocumentChunker(chunk_size=1000)
        chunks = chunker.chunk_documents(documents)
        
        mock_emb.embed_documents.return_value = [[0.1] * 768] * len(chunks)
        store.add_documents(chunks)
        
        rag_chain = RAGChain(store)
        result = rag_chain.query_with_retrieval("What is the NAV?", k=2)
        
        assert "answer" in result
        assert "question" in result
        assert "retrieved_documents" in result
        assert "sources" in result
        assert isinstance(result["answer"], str)
        assert len(result["answer"]) > 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for the complete RAG pipeline."""
    
    @patch('retrieval.rag_chain.ChatGoogleGenerativeAI')
    @patch('vector_store.chroma_store.GoogleGenerativeAIEmbeddings')
    def test_full_pipeline(self, mock_embeddings, mock_llm, temp_chroma_db, temp_data_dir, mock_gemini_api_key):
        """Test the complete pipeline from ingestion to query."""
        mock_emb = Mock()
        mock_emb.embed_query.return_value = [0.1] * 768
        mock_embeddings.return_value = mock_emb
        
        mock_llm_instance = Mock()
        mock_response = Mock()
        mock_response.content = "Based on the context, the fund has a NAV of ₹100.50."
        mock_llm_instance.invoke.return_value = mock_response
        mock_llm.return_value = mock_llm_instance
        
        # Step 1: Load documents
        loader = JSONDocumentLoader(temp_data_dir)
        documents = loader.load_documents()
        assert len(documents) > 0
        
        # Step 2: Chunk documents
        chunker = DocumentChunker()
        chunks = chunker.chunk_documents(documents)
        assert len(chunks) > 0
        
        # Step 3: Store in vector database
        store = ChromaVectorStore(db_path=temp_chroma_db)
        mock_emb.embed_documents.return_value = [[0.1] * 768] * len(chunks)
        doc_ids = store.add_documents(chunks)
        assert len(doc_ids) == len(chunks)
        
        # Step 4: Create RAG chain
        rag_chain = RAGChain(store)
        
        # Step 5: Query
        result = rag_chain.query_with_retrieval("What is the NAV of the fund?")
        
        assert result["answer"] is not None
        assert len(result["sources"]) > 0
        assert result["retrieved_documents"] > 0


# ============================================================================
# Real Data Tests
# ============================================================================

class TestWithRealData:
    """Test with actual JSON files from the data directory."""
    
    def test_load_real_json_files(self):
        """Test loading actual JSON files from data directory."""
        data_dir = "./data/mutual_funds"
        
        if not os.path.exists(data_dir):
            pytest.skip(f"Data directory {data_dir} not found")
        
        loader = JSONDocumentLoader(data_dir)
        documents = loader.load_documents()
        
        assert len(documents) > 0
        for doc in documents:
            assert doc.page_content is not None
            assert len(doc.page_content) > 0
            assert "fund_name" in doc.metadata or doc.metadata.get("source_file")
    
    @patch('vector_store.chroma_store.GoogleGenerativeAIEmbeddings')
    def test_chunk_real_data(self, mock_embeddings, temp_chroma_db, mock_gemini_api_key):
        """Test chunking with real data files."""
        data_dir = "./data/mutual_funds"
        
        if not os.path.exists(data_dir):
            pytest.skip(f"Data directory {data_dir} not found")
        
        mock_emb = Mock()
        mock_embeddings.return_value = mock_emb
        
        loader = JSONDocumentLoader(data_dir)
        documents = loader.load_documents()
        chunker = DocumentChunker(chunk_size=500, chunk_overlap=100)
        chunks = chunker.chunk_documents(documents)
        
        assert len(chunks) >= len(documents)
        
        store = ChromaVectorStore(db_path=temp_chroma_db)
        mock_emb.embed_documents.return_value = [[0.1] * 768] * len(chunks)
        doc_ids = store.add_documents(chunks)
        
        assert len(doc_ids) == len(chunks)
        info = store.get_collection_info()
        assert info["document_count"] == len(chunks)


# ============================================================================
# API Schema Tests
# ============================================================================

class TestAPISchemas:
    """Test cases for API request/response schemas."""
    
    def test_ingest_request(self):
        """Test IngestRequest schema."""
        request = IngestRequest(data_dir="./test", upsert=True)
        assert request.data_dir == "./test"
        assert request.upsert is True
    
    def test_query_request(self):
        """Test QueryRequest schema."""
        request = QueryRequest(
            question="What is the NAV?",
            k=5,
            return_sources=True
        )
        assert request.question == "What is the NAV?"
        assert request.k == 5
        assert request.return_sources is True
    
    def test_search_request(self):
        """Test SearchRequest schema."""
        request = SearchRequest(query="large cap", k=3)
        assert request.query == "large cap"
        assert request.k == 3


# ============================================================================
# API Endpoint Tests
# ============================================================================

class TestAPIEndpoints:
    """Test cases for FastAPI endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data
    
    def test_health_endpoint(self, client, mock_vector_store):
        """Test health check endpoint."""
        import api.main
        api.main.vector_store = mock_vector_store
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "collection_info" in data
    
    @patch('api.main.JSONDocumentLoader')
    @patch('api.main.DocumentChunker')
    def test_ingest_endpoint(self, mock_chunker, mock_loader, client, mock_vector_store):
        """Test document ingestion endpoint."""
        from langchain_core.documents import Document
        
        mock_loader_instance = Mock()
        mock_doc = Document(
            page_content="Test content",
            metadata={"fund_name": "Test Fund"}
        )
        mock_loader_instance.load_documents.return_value = [mock_doc]
        mock_loader.return_value = mock_loader_instance
        
        mock_chunker_instance = Mock()
        mock_chunk = Document(
            page_content="Test chunk",
            metadata={"fund_name": "Test Fund", "chunk_index": 0}
        )
        mock_chunker_instance.chunk_documents.return_value = [mock_chunk]
        mock_chunker.return_value = mock_chunker_instance
        
        import api.main
        api.main.vector_store = mock_vector_store
        mock_vector_store.upsert_documents.return_value = ["doc_id_1"]
        
        response = client.post("/api/v1/ingest", json={"upsert": True})
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "documents_processed" in data
        assert "chunks_created" in data
    
    def test_search_endpoint(self, client, mock_vector_store):
        """Test similarity search endpoint."""
        from langchain_core.documents import Document
        
        mock_doc = Document(
            page_content="Test search result",
            metadata={"fund_name": "Test Fund"}
        )
        mock_vector_store.similarity_search.return_value = [mock_doc]
        
        import api.main
        api.main.vector_store = mock_vector_store
        
        response = client.post(
            "/api/v1/search",
            json={"query": "large cap fund", "k": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data
        assert "count" in data
        assert len(data["results"]) > 0
    
    def test_query_endpoint(self, client, mock_rag_chain):
        """Test RAG query endpoint."""
        import api.main
        api.main.rag_chain = mock_rag_chain
        
        response = client.post(
            "/api/v1/query",
            json={"question": "What is the NAV?", "return_sources": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "question" in data
        assert "sources" in data
        assert len(data["sources"]) > 0
    
    def test_query_with_clear_history(self, client, mock_rag_chain):
        """Test query endpoint with clear_history flag."""
        import api.main
        api.main.rag_chain = mock_rag_chain
        
        response = client.post(
            "/api/v1/query",
            json={"question": "What is the NAV?", "clear_history": True}
        )
        
        assert response.status_code == 200
        mock_rag_chain.clear_memory.assert_called_once()
    
    def test_delete_collection_endpoint(self, client, mock_vector_store):
        """Test delete collection endpoint."""
        import api.main
        api.main.vector_store = mock_vector_store
        mock_vector_store.collection_name = "test_collection"
        
        response = client.delete("/api/v1/collection")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "collection_name" in data
        mock_vector_store.delete_collection.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

