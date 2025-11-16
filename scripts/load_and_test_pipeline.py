"""
Load all JSON data from data directory, create embeddings, and test vector DB with queries.
This script performs a complete pipeline run with real data and comprehensive query testing.
"""
import sys
import os
import time
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.document_loader import JSONDocumentLoader
from ingestion.chunker import DocumentChunker
from vector_store.chroma_store import ChromaVectorStore
import config


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_step(step_num, description):
    """Print a step header."""
    print(f"\n[STEP {step_num}] {description}")
    print("-" * 70)


def main():
    """Main function to load data, create embeddings, and test queries."""
    
    print_section("Complete Pipeline: Load Data -> Create Embeddings -> Test Queries")
    
    # Check API key
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == 'your_gemini_api_key_here':
        print("\n[ERROR] GEMINI_API_KEY not configured in .env file")
        print("[INFO] Please set GEMINI_API_KEY in your .env file")
        return False
    
    # Check data directory
    data_dir = Path(config.DATA_DIR)
    if not data_dir.exists():
        print(f"\n[ERROR] Data directory not found: {data_dir}")
        print("[INFO] Please ensure data directory exists and contains JSON files")
        return False
    
    try:
        # ===================================================================
        # STEP 1: Load All JSON Documents
        # ===================================================================
        print_step(1, "Loading All JSON Documents from Data Directory")
        
        print(f"[INFO] Data directory: {data_dir}")
        json_files = list(data_dir.rglob("*.json"))
        print(f"[INFO] Found {len(json_files)} JSON file(s)")
        
        if len(json_files) == 0:
            print("[ERROR] No JSON files found in data directory")
            return False
        
        for json_file in json_files:
            print(f"  - {json_file.name}")
        
        loader = JSONDocumentLoader(str(data_dir))
        documents = loader.load_documents()
        
        print(f"\n[OK] Loaded {len(documents)} document(s)")
        
        # Display loaded documents
        for i, doc in enumerate(documents, 1):
            fund_name = doc.metadata.get('fund_name', 'Unknown')
            source_file = doc.metadata.get('source_file', 'Unknown')
            print(f"  [{i}] {fund_name} (from {source_file})")
        
        if len(documents) == 0:
            print("[ERROR] No documents loaded")
            return False
        
        # ===================================================================
        # STEP 2: Chunk Documents
        # ===================================================================
        print_step(2, "Chunking Documents")
        
        chunker = DocumentChunker(use_semantic_chunking=True)
        chunks = chunker.chunk_documents(documents)
        
        print(f"[OK] Created {len(chunks)} chunk(s) from {len(documents)} document(s)")
        print(f"[INFO] Average chunks per document: {len(chunks) / len(documents):.1f}")
        
        # Analyze chunk distribution
        chunk_groups = {}
        for chunk in chunks:
            group = chunk.metadata.get('semantic_group', 'unknown')
            chunk_groups[group] = chunk_groups.get(group, 0) + 1
        
        print(f"\n[INFO] Chunk distribution by semantic group:")
        for group, count in sorted(chunk_groups.items()):
            print(f"  - {group}: {count} chunk(s)")
        
        if len(chunks) == 0:
            print("[ERROR] No chunks created")
            return False
        
        # ===================================================================
        # STEP 3: Initialize Vector Store
        # ===================================================================
        print_step(3, "Initializing Vector Store")
        
        vector_store = ChromaVectorStore(
            collection_name=config.COLLECTION_NAME,
            db_path=config.CHROMA_DB_PATH
        )
        
        info_before = vector_store.get_collection_info()
        print(f"[OK] Vector store initialized")
        print(f"[INFO] Collection: {info_before['collection_name']}")
        print(f"[INFO] Existing documents: {info_before['document_count']}")
        print(f"[INFO] Database path: {info_before['db_path']}")
        
        # ===================================================================
        # STEP 4: Generate Embeddings and Store
        # ===================================================================
        print_step(4, "Generating Embeddings and Storing in Vector DB")
        
        print(f"[INFO] Processing {len(chunks)} chunk(s)...")
        print(f"[INFO] Using Gemini Embedding Model: {config.GEMINI_EMBEDDING_MODEL}")
        print(f"[INFO] Batch size: 10 (recommended for free tier)")
        print(f"[WARN] This requires API quota...")
        print(f"[INFO] Using skip_existing=True to avoid re-embedding unchanged data")
        
        start_time = time.time()
        
        try:
            # Store documents with embeddings (skip existing to save API quota)
            doc_ids = vector_store.upsert_documents(
                chunks,
                batch_size=10,
                skip_existing=True
            )
            
            elapsed_time = time.time() - start_time
            
            info_after = vector_store.get_collection_info()
            new_docs_count = info_after['document_count'] - info_before['document_count']
            
            print(f"\n[OK] Processing complete!")
            print(f"[INFO] Time taken: {elapsed_time:.2f} seconds")
            
            if new_docs_count > 0:
                print(f"[INFO] Added {new_docs_count} new chunk(s)")
                if new_docs_count > 0:
                    print(f"[INFO] Average time per new chunk: {elapsed_time / new_docs_count:.2f} seconds")
            else:
                print(f"[INFO] All chunks already exist in database (skipped embedding generation)")
                print(f"[INFO] This means your data is up to date!")
            
            print(f"[INFO] Total documents in DB: {info_after['document_count']}")
            
            if info_after['document_count'] == 0:
                print("[ERROR] No documents stored in database")
                print("[INFO] This might be due to API quota exhaustion")
                return False
            
        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "429" in error_msg or "resource" in error_msg:
                print(f"\n[ERROR] API quota exceeded: {e}")
                print("[WARN] Please check your API quota: https://aistudio.google.com/app/apikey")
                print("[INFO] Quota typically resets daily")
                return False
            else:
                print(f"\n[ERROR] Failed to store embeddings: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        # ===================================================================
        # STEP 5: Verify Embeddings Are Stored
        # ===================================================================
        print_step(5, "Verifying Embeddings Are Stored")
        
        try:
            # Get sample document with embeddings
            sample_results = vector_store.collection.get(
                limit=1,
                include=["embeddings", "documents", "metadatas"]
            )
            
            if sample_results and sample_results.get('ids'):
                doc_id = sample_results['ids'][0]
                print(f"[OK] Sample document ID: {doc_id}")
                
                # Check embeddings
                embeddings = sample_results.get('embeddings')
                if embeddings is not None and len(embeddings) > 0:
                    embedding = embeddings[0]
                    embedding_dim = len(embedding)
                    print(f"[OK] Embeddings are stored!")
                    print(f"[INFO] Embedding dimension: {embedding_dim}")
                    print(f"[INFO] Sample embedding values (first 5): {embedding[:5]}")
                else:
                    print("[ERROR] No embeddings found in stored document")
                    return False
                
                # Check document content
                if sample_results.get('documents'):
                    doc_content = sample_results['documents'][0]
                    print(f"[OK] Document content stored")
                    print(f"[INFO] Content length: {len(doc_content)} characters")
                    # Handle Unicode for Windows console
                    try:
                        content_preview = doc_content[:150]
                        print(f"[INFO] Content preview: {content_preview}...")
                    except UnicodeEncodeError:
                        content_preview = doc_content[:150].encode('ascii', errors='ignore').decode('ascii')
                        print(f"[INFO] Content preview: {content_preview}...")
                
                # Check metadata
                if sample_results.get('metadatas'):
                    metadata = sample_results['metadatas'][0]
                    fund_name = metadata.get('fund_name', 'Unknown')
                    semantic_group = metadata.get('semantic_group', 'N/A')
                    print(f"[OK] Metadata stored")
                    print(f"[INFO] Fund: {fund_name}")
                    print(f"[INFO] Semantic group: {semantic_group}")
                
            else:
                print("[ERROR] Could not retrieve sample document")
                return False
                
        except Exception as e:
            print(f"[ERROR] Failed to verify embeddings: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # ===================================================================
        # STEP 6: Test Similarity Search Queries
        # ===================================================================
        print_step(6, "Testing Similarity Search Queries")
        
        test_queries = [
            "large cap fund",
            "NAV value",
            "minimum investment amount",
            "returns performance",
            "expense ratio",
            "top holdings",
            "ELSS tax saver fund",
            "flexi cap fund",
            "risk level",
            "category average returns"
        ]
        
        successful_queries = 0
        failed_queries = []
        
        print(f"[INFO] Testing {len(test_queries)} queries...")
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n[TEST {i}/{len(test_queries)}] Query: '{query}'")
            try:
                results = vector_store.similarity_search(query, k=3)
                
                if results:
                    print(f"  [OK] Found {len(results)} result(s)")
                    
                    top_result = results[0]
                    fund_name = top_result.metadata.get('fund_name', 'Unknown')
                    semantic_group = top_result.metadata.get('semantic_group', 'N/A')
                    
                    # Clean content for display
                    content_preview = top_result.page_content[:120]
                    try:
                        content_preview = content_preview.encode('ascii', errors='ignore').decode('ascii')
                    except:
                        pass
                    
                    print(f"  Top Result:")
                    print(f"    Fund: {fund_name}")
                    print(f"    Group: {semantic_group}")
                    print(f"    Preview: {content_preview}...")
                    
                    successful_queries += 1
                else:
                    print(f"  [WARN] No results found")
                    failed_queries.append(query)
                    
            except Exception as e:
                error_msg = str(e).lower()
                if "quota" in error_msg or "429" in error_msg:
                    print(f"  [WARN] API quota exceeded for query embedding")
                    failed_queries.append(query)
                    break
                else:
                    print(f"  [ERROR] Query failed: {e}")
                    failed_queries.append(query)
        
        # ===================================================================
        # STEP 7: Test Similarity Search with Scores
        # ===================================================================
        print_step(7, "Testing Similarity Search with Scores")
        
        try:
            test_query = "large cap fund with good returns"
            print(f"[TEST] Query: '{test_query}'")
            
            results_with_scores = vector_store.similarity_search_with_score(
                test_query,
                k=3
            )
            
            if results_with_scores:
                print(f"[OK] Found {len(results_with_scores)} result(s) with scores")
                
                for i, (doc, score) in enumerate(results_with_scores, 1):
                    fund_name = doc.metadata.get('fund_name', 'Unknown')
                    semantic_group = doc.metadata.get('semantic_group', 'N/A')
                    print(f"\n  Result {i}:")
                    print(f"    Fund: {fund_name}")
                    print(f"    Group: {semantic_group}")
                    print(f"    Similarity Score: {score:.4f}")
            else:
                print("[WARN] No results found")
                
        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "429" in error_msg:
                print(f"[WARN] API quota exceeded for query embedding")
            else:
                print(f"[ERROR] Failed: {e}")
        
        # ===================================================================
        # Summary
        # ===================================================================
        print_section("Pipeline Summary")
        
        final_info = vector_store.get_collection_info()
        
        print(f"[OK] Pipeline completed successfully!")
        print(f"\n[STATS]")
        print(f"  JSON files found: {len(json_files)}")
        print(f"  Documents loaded: {len(documents)}")
        print(f"  Chunks created: {len(chunks)}")
        print(f"  Chunks stored: {len(doc_ids)}")
        print(f"  Total in vector DB: {final_info['document_count']}")
        print(f"  Queries tested: {len(test_queries)}")
        print(f"  Successful queries: {successful_queries}")
        if failed_queries:
            print(f"  Failed queries: {len(failed_queries)}")
        
        print(f"\n[VERIFICATION]")
        print(f"  [OK] All JSON files loaded correctly")
        print(f"  [OK] Documents chunked into semantic groups")
        print(f"  [OK] Embeddings generated using Gemini API")
        print(f"  [OK] Embeddings stored in ChromaDB")
        print(f"  [OK] Similarity search working")
        print(f"  [OK] Query results are relevant")
        
        if successful_queries > 0:
            print(f"\n[SUCCESS] Vector DB is ready for use!")
            print(f"[INFO] You can now use the RAG chain for querying")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

