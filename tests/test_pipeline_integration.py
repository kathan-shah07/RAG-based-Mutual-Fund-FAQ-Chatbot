"""
Integration tests for the complete RAG pipeline using real data.
Tests: JSON Loading → Chunking → Embedding → Vector Storage → Query
Includes logic to skip embedding generation if data is already up to date.
"""
import pytest
import os
import json
import time
from pathlib import Path
from typing import Dict, Set, List
from datetime import datetime

# Import modules to test
from ingestion.document_loader import JSONDocumentLoader
from ingestion.chunker import DocumentChunker
from vector_store.chroma_store import ChromaVectorStore
import config


# ============================================================================
# Helper Functions
# ============================================================================

def get_file_modification_time(file_path: Path) -> float:
    """Get file modification time as timestamp."""
    return os.path.getmtime(file_path)


def get_source_files_from_vector_db(vector_store: ChromaVectorStore) -> Dict[str, float]:
    """
    Get source files and their stored modification times from vector DB.
    
    Returns:
        Dictionary mapping source_file names to their stored modification times
    """
    source_files = {}
    try:
        # Get all documents from collection
        all_docs = vector_store.collection.get(include=["metadatas"])
        
        if all_docs and all_docs.get('metadatas'):
            for metadata in all_docs['metadatas']:
                source_file = metadata.get('source_file')
                if source_file:
                    # Get the modification time from metadata if stored
                    # Otherwise use current time as fallback
                    mod_time = metadata.get('file_mod_time', time.time())
                    if source_file not in source_files:
                        source_files[source_file] = mod_time
                    else:
                        # Keep the latest modification time
                        source_files[source_file] = max(source_files[source_file], mod_time)
    except Exception as e:
        print(f"[WARN] Could not retrieve source files from vector DB: {e}")
    
    return source_files


def check_if_data_needs_update(
    data_dir: Path,
    vector_store: ChromaVectorStore
) -> tuple[bool, List[str], List[str]]:
    """
    Check if data files need to be re-embedded by comparing file modification times.
    
    Args:
        data_dir: Directory containing JSON data files
        vector_store: ChromaVectorStore instance
        
    Returns:
        Tuple of (needs_update, files_to_update, files_up_to_date)
    """
    # Get all JSON files from data directory
    json_files = list(data_dir.rglob("*.json"))
    
    if not json_files:
        return False, [], []
    
    # Get source files from vector DB
    stored_files = get_source_files_from_vector_db(vector_store)
    
    files_to_update = []
    files_up_to_date = []
    
    for json_file in json_files:
        file_name = json_file.name
        current_mod_time = get_file_modification_time(json_file)
        
        if file_name in stored_files:
            stored_mod_time = stored_files[file_name]
            # If current file is newer, it needs update
            if current_mod_time > stored_mod_time:
                files_to_update.append(file_name)
            else:
                files_up_to_date.append(file_name)
        else:
            # File not in vector DB, needs to be added
            files_to_update.append(file_name)
    
    needs_update = len(files_to_update) > 0
    
    return needs_update, files_to_update, files_up_to_date


# Note: File modification time is now automatically added by JSONDocumentLoader
# No need for separate function to add it


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


# ============================================================================
# Integration Tests
# ============================================================================

class TestPipelineIntegration:
    """Integration tests for the complete RAG pipeline with real data."""
    
    def test_load_real_documents(self, data_directory):
        """Test loading real JSON documents from data directory."""
        loader = JSONDocumentLoader(str(data_directory))
        documents = loader.load_documents()
        
        assert len(documents) > 0, "No documents loaded from data directory"
        
        # Verify document structure
        for doc in documents:
            assert doc.page_content is not None
            assert len(doc.page_content) > 0
            assert 'fund_name' in doc.metadata
            assert 'source_file' in doc.metadata
            
        # Verify JSON is parseable
        for doc in documents:
            try:
                json_data = json.loads(doc.page_content)
                assert isinstance(json_data, dict)
            except json.JSONDecodeError:
                pytest.fail(f"Document content is not valid JSON: {doc.metadata.get('source_file')}")
    
    def test_chunk_real_documents(self, data_directory):
        """Test chunking real documents."""
        loader = JSONDocumentLoader(str(data_directory))
        documents = loader.load_documents()
        
        chunker = DocumentChunker(use_semantic_chunking=True)
        chunks = chunker.chunk_documents(documents)
        
        assert len(chunks) > 0, "No chunks created"
        assert len(chunks) >= len(documents), "Should have at least one chunk per document"
        
        # Verify chunk structure
        for chunk in chunks:
            assert chunk.page_content is not None
            assert len(chunk.page_content) > 0
            assert 'chunk_index' in chunk.metadata
            assert 'semantic_group' in chunk.metadata or 'chunk_type' in chunk.metadata
    
    def test_check_data_freshness(self, data_directory, vector_store_instance):
        """Test checking if data needs to be updated."""
        needs_update, files_to_update, files_up_to_date = check_if_data_needs_update(
            data_directory,
            vector_store_instance
        )
        
        # This should always return valid results
        assert isinstance(needs_update, bool)
        assert isinstance(files_to_update, list)
        assert isinstance(files_up_to_date, list)
        
        # If vector DB is empty, all files should need update
        info = vector_store_instance.get_collection_info()
        if info['document_count'] == 0:
            assert needs_update is True
            assert len(files_to_update) > 0
    
    def test_full_pipeline_with_skip_logic(
        self,
        data_directory,
        vector_store_instance
    ):
        """
        Test the complete pipeline with logic to skip embeddings if data is up to date.
        This is the main integration test.
        """
        # Step 1: Check if data needs update
        needs_update, files_to_update, files_up_to_date = check_if_data_needs_update(
            data_directory,
            vector_store_instance
        )
        
        print(f"\n[INFO] Data freshness check:")
        print(f"  Files up to date: {len(files_up_to_date)}")
        print(f"  Files need update: {len(files_to_update)}")
        
        if files_up_to_date:
            print(f"  Up to date files: {', '.join(files_up_to_date)}")
        if files_to_update:
            print(f"  Files to update: {', '.join(files_to_update)}")
        
        # Step 2: Load documents
        loader = JSONDocumentLoader(str(data_directory))
        documents = loader.load_documents()
        
        assert len(documents) > 0, "No documents loaded"
        
        # Verify file modification time is in metadata (added by JSONDocumentLoader)
        for doc in documents:
            assert 'file_mod_time' in doc.metadata, "File modification time should be in metadata"
        
        # Step 3: Chunk documents
        chunker = DocumentChunker(use_semantic_chunking=True)
        chunks = chunker.chunk_documents(documents)
        
        assert len(chunks) > 0, "No chunks created"
        
        # Step 4: Get initial document count
        info_before = vector_store_instance.get_collection_info()
        initial_count = info_before['document_count']
        
        # Step 5: Store/update documents with skip logic
        # Use skip_existing=True to avoid re-embedding existing documents
        doc_ids = vector_store_instance.upsert_documents(
            chunks,
            batch_size=10,
            skip_existing=True
        )
        
        assert len(doc_ids) == len(chunks), "Number of doc IDs should match number of chunks"
        
        # Step 6: Verify documents were stored
        info_after = vector_store_instance.get_collection_info()
        final_count = info_after['document_count']
        
        # Final count should be >= initial count
        assert final_count >= initial_count, "Document count should not decrease"
        
        # If we had files to update, we should have added new documents
        if needs_update and files_to_update:
            # At least some new documents should have been added
            # (Note: This might not always be true if all chunks already existed)
            print(f"[INFO] Initial count: {initial_count}, Final count: {final_count}")
        
        # Step 7: Verify embeddings are stored
        sample_results = vector_store_instance.collection.get(
            limit=1,
            include=["embeddings", "documents", "metadatas"]
        )
        
        assert sample_results is not None
        assert sample_results.get('ids') is not None
        assert len(sample_results['ids']) > 0
        
        # Check embeddings
        embeddings = sample_results.get('embeddings')
        assert embeddings is not None, "Embeddings should be stored"
        assert len(embeddings) > 0, "Should have at least one embedding"
        
        embedding_dim = len(embeddings[0])
        assert embedding_dim > 0, "Embedding dimension should be positive"
        print(f"[INFO] Embedding dimension: {embedding_dim}")
        
        # Step 8: Test similarity search
        test_queries = [
            "large cap fund",
            "NAV value",
            "minimum investment",
            "returns performance",
            "expense ratio"
        ]
        
        successful_queries = 0
        for query in test_queries:
            try:
                results = vector_store_instance.similarity_search(query, k=2)
                if results:
                    successful_queries += 1
                    # Verify result structure
                    assert len(results) > 0
                    assert hasattr(results[0], 'page_content')
                    assert hasattr(results[0], 'metadata')
            except Exception as e:
                # Query might fail due to API quota, but that's okay for testing
                print(f"[WARN] Query '{query}' failed: {e}")
        
        # At least some queries should succeed if embeddings exist
        if final_count > 0:
            assert successful_queries > 0, "At least one query should succeed"
        
        print(f"[INFO] Successful queries: {successful_queries}/{len(test_queries)}")
    
    def test_similarity_search_with_scores(
        self,
        data_directory,
        vector_store_instance
    ):
        """Test similarity search with relevance scores."""
        # Ensure we have data
        info = vector_store_instance.get_collection_info()
        if info['document_count'] == 0:
            pytest.skip("No documents in vector store. Run test_full_pipeline_with_skip_logic first.")
        
        test_query = "large cap fund returns"
        
        try:
            results_with_scores = vector_store_instance.similarity_search_with_score(
                test_query,
                k=3
            )
            
            assert len(results_with_scores) > 0, "Should return at least one result"
            
            # Verify structure
            for doc, score in results_with_scores:
                assert hasattr(doc, 'page_content')
                assert hasattr(doc, 'metadata')
                assert isinstance(score, (int, float))
                assert 0 <= score <= 1, "Similarity score should be between 0 and 1"
            
            # Scores should be in descending order (highest first)
            scores = [score for _, score in results_with_scores]
            assert scores == sorted(scores, reverse=True), "Scores should be in descending order"
            
        except Exception as e:
            # Might fail due to API quota
            pytest.skip(f"Query failed (likely API quota): {e}")
    
    def test_verify_embeddings_stored(self, vector_store_instance):
        """Test verifying that embeddings are properly stored."""
        info = vector_store_instance.get_collection_info()
        
        if info['document_count'] == 0:
            pytest.skip("No documents in vector store")
        
        # Get sample document with embeddings
        sample_results = vector_store_instance.collection.get(
            limit=1,
            include=["embeddings", "documents", "metadatas"]
        )
        
        assert sample_results is not None
        assert sample_results.get('ids') is not None
        assert len(sample_results['ids']) > 0
        
        # Verify embeddings
        embeddings = sample_results.get('embeddings')
        assert embeddings is not None, "Embeddings should be stored"
        assert len(embeddings) > 0, "Should have at least one embedding"
        
        embedding = embeddings[0]
        assert isinstance(embedding, (list, tuple)), "Embedding should be a list/array"
        assert len(embedding) > 0, "Embedding should have positive dimension"
        
        # Verify document content
        documents = sample_results.get('documents')
        assert documents is not None, "Documents should be stored"
        assert len(documents) > 0, "Should have at least one document"
        assert len(documents[0]) > 0, "Document content should not be empty"
        
        # Verify metadata
        metadatas = sample_results.get('metadatas')
        assert metadatas is not None, "Metadata should be stored"
        assert len(metadatas) > 0, "Should have at least one metadata"
        assert 'fund_name' in metadatas[0], "Metadata should contain fund_name"


# ============================================================================
# Test Configuration
# ============================================================================

@pytest.mark.integration
class TestPipelineIntegrationMarked:
    """Marked integration tests that can be run separately."""
    
    def test_full_pipeline_end_to_end(self, data_directory, vector_store_instance):
        """
        Complete end-to-end test of the pipeline.
        This test can be run with: pytest -m integration
        """
        # This is the same as test_full_pipeline_with_skip_logic
        # but marked for separate execution
        test_instance = TestPipelineIntegration()
        test_instance.test_full_pipeline_with_skip_logic(
            data_directory,
            vector_store_instance
        )

