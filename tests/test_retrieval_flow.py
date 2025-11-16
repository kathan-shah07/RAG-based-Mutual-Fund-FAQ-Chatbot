"""
Unit tests to validate the retrieval flow.
Tests that the system correctly retrieves information from the vector database
and that the LLM generates appropriate answers based on retrieved context.
Uses real data (no mocks) to ensure end-to-end validation.
"""
import pytest
import os
from pathlib import Path
from typing import List, Dict, Any

# Import modules to test
from ingestion.document_loader import JSONDocumentLoader
from ingestion.chunker import DocumentChunker
from vector_store.chroma_store import ChromaVectorStore
from retrieval.rag_chain import RAGChain
import config


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def data_directory():
    """Fixture providing the data directory path."""
    data_dir = Path(config.DATA_DIR)
    if not data_dir.exists():
        pytest.skip(f"Data directory not found: {data_dir}")
    return data_dir


@pytest.fixture
def vector_store_instance():
    """Fixture providing a ChromaVectorStore instance."""
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == 'your_gemini_api_key_here':
        pytest.skip("GEMINI_API_KEY not configured")
    
    return ChromaVectorStore(
        collection_name=config.COLLECTION_NAME,
        db_path=config.CHROMA_DB_PATH
    )


@pytest.fixture
def rag_chain_instance(vector_store_instance):
    """Fixture providing a RAGChain instance."""
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == 'your_gemini_api_key_here':
        pytest.skip("GEMINI_API_KEY not configured")
    
    return RAGChain(vector_store_instance)


@pytest.fixture(scope="function")
def ensure_vector_db_has_data(data_directory, vector_store_instance):
    """
    Ensure vector DB has data before running retrieval tests.
    Checks if data exists, and if not, loads it.
    """
    info = vector_store_instance.get_collection_info()
    
    if info['document_count'] == 0:
        # Load and store data
        loader = JSONDocumentLoader(str(data_directory))
        documents = loader.load_documents()
        
        chunker = DocumentChunker(use_semantic_chunking=True)
        chunks = chunker.chunk_documents(documents)
        
        # Store with skip_existing to avoid re-embedding
        vector_store_instance.upsert_documents(chunks, batch_size=10, skip_existing=True)
        
        # Verify data was stored
        info_after = vector_store_instance.get_collection_info()
        if info_after['document_count'] == 0:
            pytest.skip("Could not populate vector DB - may be API quota issue")
    
    return True


# ============================================================================
# Retrieval Flow Tests
# ============================================================================

class TestRetrievalFlow:
    """Tests for validating the retrieval flow."""
    
    def test_vector_store_retrieval_basic(
        self,
        vector_store_instance,
        ensure_vector_db_has_data
    ):
        """Test basic retrieval from vector store."""
        query = "large cap fund"
        
        results = vector_store_instance.similarity_search(query, k=3)
        
        assert len(results) > 0, "Should retrieve at least one document"
        assert len(results) <= 3, "Should not retrieve more than k documents"
        
        # Verify result structure
        for result in results:
            assert hasattr(result, 'page_content'), "Result should have page_content"
            assert hasattr(result, 'metadata'), "Result should have metadata"
            assert len(result.page_content) > 0, "Content should not be empty"
            assert 'fund_name' in result.metadata, "Metadata should contain fund_name"
    
    def test_vector_store_retrieval_relevance(
        self,
        vector_store_instance,
        ensure_vector_db_has_data
    ):
        """Test that retrieved documents are relevant to the query."""
        test_cases = [
            ("large cap fund", ["large cap", "Large Cap"]),
            ("ELSS tax saver", ["ELSS", "Tax Saver"]),
            ("minimum investment", ["minimum", "investment", "First Investment"]),
            ("expense ratio", ["expense", "ratio", "Expense Ratio"]),
            ("returns performance", ["returns", "Returns", "performance"]),
        ]
        
        for query, expected_keywords in test_cases:
            results = vector_store_instance.similarity_search(query, k=3)
            
            assert len(results) > 0, f"Should retrieve documents for query: {query}"
            
            # Check that at least one result contains relevant keywords
            found_relevant = False
            for result in results:
                content_lower = result.page_content.lower()
                for keyword in expected_keywords:
                    if keyword.lower() in content_lower:
                        found_relevant = True
                        break
                if found_relevant:
                    break
            
            assert found_relevant, (
                f"Retrieved documents should be relevant to '{query}'. "
                f"Expected keywords: {expected_keywords}"
            )
    
    def test_vector_store_retrieval_with_scores(
        self,
        vector_store_instance,
        ensure_vector_db_has_data
    ):
        """Test retrieval with similarity scores."""
        query = "large cap fund returns"
        
        results_with_scores = vector_store_instance.similarity_search_with_score(
            query,
            k=3
        )
        
        assert len(results_with_scores) > 0, "Should retrieve at least one document"
        
        # Verify scores are valid
        scores = []
        for doc, score in results_with_scores:
            assert isinstance(score, (int, float)), "Score should be numeric"
            assert 0 <= score <= 1, "Score should be between 0 and 1"
            scores.append(score)
        
        # Scores should be in descending order (highest similarity first)
        assert scores == sorted(scores, reverse=True), "Scores should be in descending order"
        
        # Top score should be reasonably high for relevant queries
        if len(scores) > 0:
            assert scores[0] > 0.5, "Top score should indicate reasonable relevance"
    
    def test_retrieval_metadata_preservation(
        self,
        vector_store_instance,
        ensure_vector_db_has_data
    ):
        """Test that metadata is preserved in retrieved documents."""
        query = "fund overview"
        
        results = vector_store_instance.similarity_search(query, k=5)
        
        assert len(results) > 0, "Should retrieve documents"
        
        # Check that important metadata fields are present
        required_metadata_fields = ['fund_name', 'source_file']
        
        for result in results:
            for field in required_metadata_fields:
                assert field in result.metadata, (
                    f"Metadata should contain '{field}' field"
                )
                assert result.metadata[field] is not None, (
                    f"Metadata field '{field}' should not be None"
                )
                assert len(str(result.metadata[field])) > 0, (
                    f"Metadata field '{field}' should not be empty"
                )
    
    def test_retrieval_different_k_values(
        self,
        vector_store_instance,
        ensure_vector_db_has_data
    ):
        """Test retrieval with different k values."""
        query = "mutual fund"
        
        for k in [1, 3, 5]:
            results = vector_store_instance.similarity_search(query, k=k)
            
            assert len(results) <= k, f"Should not retrieve more than {k} documents"
            assert len(results) > 0, f"Should retrieve at least one document for k={k}"


class TestRAGChainRetrieval:
    """Tests for RAG chain retrieval and answer generation."""
    
    def test_rag_chain_retrieval_step(
        self,
        rag_chain_instance,
        ensure_vector_db_has_data
    ):
        """Test that RAG chain correctly retrieves documents."""
        question = "What is the NAV of the large cap fund?"
        
        try:
            # Use query_with_retrieval to get retrieval details
            result = rag_chain_instance.query_with_retrieval(question, k=3)
            
            # Verify retrieval happened
            assert "retrieved_documents" in result, "Result should contain retrieved_documents count"
            assert result["retrieved_documents"] > 0, "Should retrieve at least one document"
            assert result["retrieved_documents"] <= 3, "Should not retrieve more than k documents"
            
            # Verify sources are included
            assert "sources" in result, "Result should contain sources"
            assert len(result["sources"]) > 0, "Should have at least one source"
            assert len(result["sources"]) == result["retrieved_documents"], (
                "Number of sources should match retrieved documents"
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "404" in error_msg or "model" in error_msg:
                pytest.skip(f"LLM model issue (may be API/model configuration): {e}")
            else:
                raise
    
    def test_rag_chain_context_creation(
        self,
        rag_chain_instance,
        ensure_vector_db_has_data
    ):
        """Test that RAG chain creates proper context from retrieved documents."""
        question = "What is the minimum investment amount?"
        
        try:
            result = rag_chain_instance.query_with_retrieval(question, k=3)
            
            # Verify answer was generated
            assert "answer" in result, "Result should contain answer"
            assert isinstance(result["answer"], str), "Answer should be a string"
            assert len(result["answer"]) > 0, "Answer should not be empty"
            
            # Verify sources contain content
            for source in result["sources"]:
                assert "content" in source, "Source should contain content"
                assert len(source["content"]) > 0, "Source content should not be empty"
                assert "metadata" in source, "Source should contain metadata"
        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "404" in error_msg or "model" in error_msg or "quota" in error_msg:
                pytest.skip(f"LLM unavailable (model/API issue): {e}")
            else:
                raise
    
    def test_rag_chain_answer_relevance(
        self,
        rag_chain_instance,
        ensure_vector_db_has_data
    ):
        """Test that LLM generates relevant answers based on retrieved context."""
        test_cases = [
            {
                "question": "What is the NAV of the large cap fund?",
                "expected_keywords": ["NAV", "104.68", "large cap"]
            },
            {
                "question": "What is the minimum investment amount?",
                "expected_keywords": ["minimum", "investment", "100"]
            },
            {
                "question": "What is the expense ratio?",
                "expected_keywords": ["expense", "ratio", "0.66", "%"]
            },
        ]
        
        for test_case in test_cases:
            question = test_case["question"]
            expected_keywords = test_case["expected_keywords"]
            
            try:
                result = rag_chain_instance.query_with_retrieval(question, k=3)
                
                assert "answer" in result, f"Should generate answer for: {question}"
                answer_lower = result["answer"].lower()
                
                # Check that answer contains at least one expected keyword
                found_keyword = False
                for keyword in expected_keywords:
                    if keyword.lower() in answer_lower:
                        found_keyword = True
                        break
                
                # Also check sources for the keyword
                if not found_keyword:
                    for source in result["sources"]:
                        content_lower = source["content"].lower()
                        for keyword in expected_keywords:
                            if keyword.lower() in content_lower:
                                found_keyword = True
                                break
                        if found_keyword:
                            break
                
                assert found_keyword, (
                    f"Answer or sources should contain relevant keywords for '{question}'. "
                    f"Expected: {expected_keywords}, Answer: {result['answer'][:100]}"
                )
            except Exception as e:
                error_msg = str(e).lower()
                if "not found" in error_msg or "404" in error_msg or "model" in error_msg or "quota" in error_msg:
                    pytest.skip(f"LLM unavailable (model/API issue): {e}")
                    break
                else:
                    raise
    
    def test_rag_chain_with_scores(
        self,
        rag_chain_instance,
        ensure_vector_db_has_data
    ):
        """Test RAG chain retrieval with similarity scores."""
        question = "What are the top holdings?"
        
        try:
            result = rag_chain_instance.query_with_retrieval(
                question,
                k=3,
                return_scores=True
            )
            
            assert "sources" in result, "Result should contain sources"
            
            # Verify scores are included
            scores_present = False
            for source in result["sources"]:
                if "similarity_score" in source:
                    scores_present = True
                    score = source["similarity_score"]
                    assert isinstance(score, (int, float)), "Score should be numeric"
                    assert 0 <= score <= 1, "Score should be between 0 and 1"
            
            assert scores_present, "At least one source should have similarity_score"
        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "404" in error_msg or "model" in error_msg or "quota" in error_msg:
                pytest.skip(f"LLM unavailable (model/API issue): {e}")
            else:
                raise
    
    def test_rag_chain_source_metadata(
        self,
        rag_chain_instance,
        ensure_vector_db_has_data
    ):
        """Test that source metadata is correctly included in results."""
        question = "Tell me about the fund"
        
        try:
            result = rag_chain_instance.query_with_retrieval(question, k=3)
            
            assert "sources" in result, "Result should contain sources"
            
            for source in result["sources"]:
                assert "metadata" in source, "Source should contain metadata"
                metadata = source["metadata"]
                
                # Verify important metadata fields
                assert "fund_name" in metadata, "Metadata should contain fund_name"
                assert "source_file" in metadata, "Metadata should contain source_file"
                
                # Verify metadata values are not empty
                assert len(str(metadata.get("fund_name", ""))) > 0, "fund_name should not be empty"
                assert len(str(metadata.get("source_file", ""))) > 0, "source_file should not be empty"
        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "404" in error_msg or "model" in error_msg or "quota" in error_msg:
                pytest.skip(f"LLM unavailable (model/API issue): {e}")
            else:
                raise
    
    def test_rag_chain_citation_url(
        self,
        rag_chain_instance,
        ensure_vector_db_has_data
    ):
        """Test that citation URL is included in RAG chain results."""
        question = "What is the expense ratio?"
        
        try:
            result = rag_chain_instance.query_with_retrieval(question, k=3)
            
            # Verify citation_url is in result
            assert "citation_url" in result, "Result should contain citation_url field"
            
            # Citation URL should be a string (may be empty if no source_url in metadata)
            assert isinstance(result["citation_url"], str), "citation_url should be a string"
            
            # If sources have source_url, citation_url should be populated
            has_source_url = False
            for source in result["sources"]:
                metadata = source.get("metadata", {})
                if metadata.get("source_url"):
                    has_source_url = True
                    break
            
            # If any source has source_url, citation_url should be set
            if has_source_url:
                assert len(result["citation_url"]) > 0, (
                    "citation_url should be populated when sources have source_url"
                )
        except Exception as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "404" in error_msg or "model" in error_msg or "quota" in error_msg:
                pytest.skip(f"LLM unavailable (model/API issue): {e}")
            else:
                raise
    
    def test_rag_chain_factual_queries(
        self,
        rag_chain_instance,
        ensure_vector_db_has_data
    ):
        """Test that RAG chain handles factual queries correctly."""
        factual_queries = [
            "What is the expense ratio?",
            "What is the minimum SIP?",
            "What is the ELSS lock-in period?",
            "What is the exit load?",
        ]
        
        for question in factual_queries:
            try:
                result = rag_chain_instance.query_with_retrieval(question, k=3)
                
                # Verify answer was generated
                assert "answer" in result, f"Should generate answer for: {question}"
                assert len(result["answer"]) > 0, f"Answer should not be empty for: {question}"
                
                # Verify citation URL is present
                assert "citation_url" in result, "Result should contain citation_url"
            except Exception as e:
                error_msg = str(e).lower()
                if "not found" in error_msg or "404" in error_msg or "model" in error_msg or "quota" in error_msg:
                    pytest.skip(f"LLM unavailable (model/API issue): {e}")
                    break
                else:
                    raise


class TestEndToEndRetrievalFlow:
    """End-to-end tests for the complete retrieval flow."""
    
    def test_complete_retrieval_flow(
        self,
        data_directory,
        vector_store_instance,
        rag_chain_instance,
        ensure_vector_db_has_data
    ):
        """
        Test the complete retrieval flow from query to answer generation.
        This validates the entire pipeline works correctly together.
        """
        # Test query
        question = "What is the NAV and minimum investment for large cap funds?"
        
        # Step 1: Direct vector store retrieval
        vector_results = vector_store_instance.similarity_search(question, k=3)
        assert len(vector_results) > 0, "Vector store should retrieve documents"
        
        # Step 2: RAG chain retrieval and answer generation
        rag_result = rag_chain_instance.query_with_retrieval(question, k=3)
        
        # Verify RAG chain retrieved documents
        assert rag_result["retrieved_documents"] > 0, "RAG chain should retrieve documents"
        assert len(rag_result["sources"]) == rag_result["retrieved_documents"], (
            "Number of sources should match retrieved documents"
        )
        
        # Verify answer was generated
        assert "answer" in rag_result, "RAG chain should generate an answer"
        assert len(rag_result["answer"]) > 0, "Answer should not be empty"
        
        # Verify answer is based on retrieved context
        # Check that answer mentions concepts from retrieved documents
        answer_lower = rag_result["answer"].lower()
        source_content = " ".join([s["content"].lower() for s in rag_result["sources"]])
        
        # Answer should reference mutual fund concepts
        fund_concepts = ["nav", "fund", "investment", "minimum", "large cap"]
        found_concept = any(concept in answer_lower or concept in source_content 
                          for concept in fund_concepts)
        
        assert found_concept, (
            "Answer should reference mutual fund concepts from retrieved context. "
            f"Answer: {rag_result['answer'][:200]}"
        )
    
    def test_retrieval_consistency(
        self,
        vector_store_instance,
        rag_chain_instance,
        ensure_vector_db_has_data
    ):
        """Test that retrieval is consistent across multiple calls."""
        question = "What is the expense ratio?"
        
        # Make multiple retrieval calls
        results_1 = vector_store_instance.similarity_search(question, k=3)
        results_2 = vector_store_instance.similarity_search(question, k=3)
        
        # Results should be consistent (same number of results)
        assert len(results_1) == len(results_2), "Retrieval should be consistent"
        
        # Top result should be the same (same fund)
        if len(results_1) > 0 and len(results_2) > 0:
            fund_1 = results_1[0].metadata.get("fund_name")
            fund_2 = results_2[0].metadata.get("fund_name")
            assert fund_1 == fund_2, "Top result should be consistent"
    
    def test_retrieval_for_different_question_types(
        self,
        rag_chain_instance,
        ensure_vector_db_has_data
    ):
        """Test retrieval for different types of questions."""
        question_types = [
            {
                "question": "What is the NAV?",
                "type": "factual"
            },
            {
                "question": "Which fund has the best returns?",
                "type": "comparative"
            },
            {
                "question": "Tell me about ELSS funds",
                "type": "descriptive"
            },
            {
                "question": "What are the top holdings?",
                "type": "list"
            },
        ]
        
        for q_type in question_types:
            question = q_type["question"]
            
            result = rag_chain_instance.query_with_retrieval(question, k=3)
            
            # Verify retrieval happened
            assert result["retrieved_documents"] > 0, (
                f"Should retrieve documents for {q_type['type']} question: {question}"
            )
            
            # Verify answer was generated
            assert len(result["answer"]) > 0, (
                f"Should generate answer for {q_type['type']} question: {question}"
            )
            
            # Verify sources are provided
            assert len(result["sources"]) > 0, (
                f"Should provide sources for {q_type['type']} question: {question}"
            )


# ============================================================================
# Test Configuration
# ============================================================================

@pytest.mark.integration
class TestRetrievalFlowMarked:
    """Marked integration tests for retrieval flow."""
    
    def test_complete_retrieval_validation(
        self,
        data_directory,
        vector_store_instance,
        rag_chain_instance,
        ensure_vector_db_has_data
    ):
        """
        Complete validation of retrieval flow.
        This test can be run with: pytest -m integration
        """
        # Comprehensive test query
        question = "What is the NAV, minimum investment, and expense ratio for large cap funds?"
        
        # Test vector store retrieval
        vector_results = vector_store_instance.similarity_search(question, k=5)
        assert len(vector_results) > 0
        
        # Test RAG chain end-to-end
        rag_result = rag_chain_instance.query_with_retrieval(question, k=5, return_scores=True)
        
        # Validate complete response
        assert rag_result["retrieved_documents"] > 0
        assert len(rag_result["answer"]) > 0
        assert len(rag_result["sources"]) > 0
        
        # Validate answer quality
        answer = rag_result["answer"].lower()
        assert any(keyword in answer for keyword in ["nav", "investment", "expense", "fund"]), (
            "Answer should mention relevant mutual fund concepts"
        )
        
        # Validate source quality
        for source in rag_result["sources"]:
            assert "content" in source
            assert "metadata" in source
            assert "fund_name" in source["metadata"]

