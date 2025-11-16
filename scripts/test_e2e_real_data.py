"""
End-to-End Test Script with Real Data
=====================================

This script tests the entire pipeline from config loading to query answering using REAL data.
No mocks are used - all components are tested with actual implementations.

Test Flow:
1. Load and validate scraper_config.json
2. Load existing scraped data (or optionally scrape new data)
3. Ingest data into vector database
4. Validate vector database contents
5. Test similarity search
6. Test RAG query answering
7. Validate end-to-end query flow

Usage:
    python scripts/test_e2e_real_data.py [--scrape] [--skip-ingestion] [--verbose]
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.groww_scraper import GrowwScraper, load_config
from ingestion.document_loader import JSONDocumentLoader
from ingestion.chunker import DocumentChunker
from vector_store.chroma_store import ChromaVectorStore
from retrieval.rag_chain import RAGChain
import config


# ============================================================================
# Test Configuration
# ============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")


def print_section(text: str):
    """Print a formatted section."""
    try:
        print(f"\n{Colors.OKCYAN}{Colors.BOLD}▶ {text}{Colors.ENDC}")
    except UnicodeEncodeError:
        print(f"\n{Colors.OKCYAN}{Colors.BOLD}>> {text}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{'-' * 80}{Colors.ENDC}")


def print_success(text: str):
    """Print success message."""
    try:
        print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")
    except UnicodeEncodeError:
        print(f"{Colors.OKGREEN}[OK] {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message."""
    try:
        print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")
    except UnicodeEncodeError:
        print(f"{Colors.FAIL}[ERROR] {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message."""
    try:
        print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")
    except UnicodeEncodeError:
        print(f"{Colors.WARNING}[WARN] {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")


# ============================================================================
# Test Components
# ============================================================================

class E2ETestRunner:
    """End-to-end test runner with real data."""
    
    def __init__(self, scrape_new: bool = False, skip_ingestion: bool = False, verbose: bool = False):
        """
        Initialize the test runner.
        
        Args:
            scrape_new: If True, run actual scraping (requires internet)
            skip_ingestion: If True, skip ingestion step (use existing vector DB)
            verbose: If True, print detailed information
        """
        self.scrape_new = scrape_new
        self.skip_ingestion = skip_ingestion
        self.verbose = verbose
        self.config_path = "scraper_config.json"
        self.scraper_config = None
        self.scraper = None
        self.vector_store = None
        self.rag_chain = None
        self.test_results = []
        
    def run_all_tests(self) -> bool:
        """Run all end-to-end tests."""
        print_header("End-to-End Test Suite - Real Data Pipeline")
        
        try:
            # Step 1: Load and validate config
            if not self.test_config_loading():
                return False
            
            # Step 2: Test data availability
            if not self.test_data_availability():
                return False
            
            # Step 3: Optional scraping
            if self.scrape_new:
                if not self.test_scraping():
                    print_warning("Scraping failed, but continuing with existing data...")
            
            # Step 4: Test document loading
            if not self.test_document_loading():
                return False
            
            # Step 5: Test chunking
            if not self.test_chunking():
                return False
            
            # Step 6: Test ingestion (unless skipped)
            if not self.skip_ingestion:
                if not self.test_ingestion():
                    return False
            else:
                print_warning("Skipping ingestion step (using existing vector DB)")
            
            # Step 7: Test vector database
            if not self.test_vector_database():
                return False
            
            # Step 8: Test similarity search
            if not self.test_similarity_search():
                return False
            
            # Step 9: Test RAG query answering
            if not self.test_rag_queries():
                return False
            
            # Step 10: Test end-to-end query flow
            if not self.test_end_to_end_queries():
                return False
            
            # Print summary
            self.print_summary()
            return True
            
        except Exception as e:
            print_error(f"Test suite failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_config_loading(self) -> bool:
        """Test 1: Load and validate scraper_config.json"""
        print_section("Test 1: Config Loading")
        
        try:
            # Check if config file exists
            if not os.path.exists(self.config_path):
                print_error(f"Config file not found: {self.config_path}")
                return False
            
            print_success(f"Config file found: {self.config_path}")
            
            # Load config
            self.scraper_config = load_config(self.config_path)
            
            # Validate config structure
            required_keys = ["scraper_settings", "urls", "schedule"]
            for key in required_keys:
                if key not in self.scraper_config:
                    print_error(f"Missing required config key: {key}")
                    return False
            
            print_success("Config structure validated")
            
            # Print config details
            if self.verbose:
                print_info(f"  Scraper settings: {json.dumps(self.scraper_config['scraper_settings'], indent=2)}")
                print_info(f"  URLs configured: {len(self.scraper_config['urls'])}")
                print_info(f"  Schedule enabled: {self.scraper_config['schedule'].get('enabled', False)}")
            
            # Validate URLs
            urls = self.scraper_config.get('urls', [])
            print_success(f"Found {len(urls)} URL(s)")
            
            if len(urls) == 0:
                print_warning("No URLs found in config")
            
            self.test_results.append(("Config Loading", True, "Config loaded and validated"))
            return True
            
        except Exception as e:
            print_error(f"Config loading failed: {e}")
            self.test_results.append(("Config Loading", False, str(e)))
            return False
    
    def test_data_availability(self) -> bool:
        """Test 2: Check if scraped data exists"""
        print_section("Test 2: Data Availability")
        
        try:
            data_dir = Path(self.scraper_config['scraper_settings']['output_dir'])
            
            # If scraping is enabled, directory will be created during scraping
            if not data_dir.exists():
                if self.scrape_new:
                    print_info(f"Data directory will be created during scraping: {data_dir}")
                    # Create parent directory if needed
                    data_dir.parent.mkdir(parents=True, exist_ok=True)
                    self.test_results.append(("Data Availability", True, "Directory will be created"))
                    return True
                else:
                    print_error(f"Data directory not found: {data_dir}")
                    print_info("Run with --scrape flag to fetch new data")
                    return False
            
            print_success(f"Data directory exists: {data_dir}")
            
            # Find JSON files
            json_files = list(data_dir.rglob("*.json"))
            
            if len(json_files) == 0:
                if self.scrape_new:
                    print_info("No JSON files found, will scrape new data")
                    self.test_results.append(("Data Availability", True, "Will scrape new data"))
                    return True
                else:
                    print_warning("No JSON files found in data directory")
                    print_info("Consider running with --scrape flag to fetch new data")
                    return False
            
            print_success(f"Found {len(json_files)} JSON file(s)")
            
            if self.verbose:
                for json_file in json_files:
                    file_size = os.path.getsize(json_file) / 1024  # KB
                    print_info(f"  - {json_file.name} ({file_size:.2f} KB)")
            
            self.test_results.append(("Data Availability", True, f"{len(json_files)} files found"))
            return True
            
        except Exception as e:
            print_error(f"Data availability check failed: {e}")
            self.test_results.append(("Data Availability", False, str(e)))
            return False
    
    def test_scraping(self) -> bool:
        """Test 3: Run actual scraping (optional)"""
        print_section("Test 3: Scraping (Real Web Scraping)")
        
        try:
            print_info("Initializing scraper...")
            
            scraper_settings = self.scraper_config['scraper_settings']
            self.scraper = GrowwScraper(
                output_dir=scraper_settings.get("output_dir", "data/mutual_funds"),
                use_interactive=scraper_settings.get("use_interactive", True),
                download_dir=scraper_settings.get("download_dir", "data/downloaded_html"),
                download_first=scraper_settings.get("download_first", False)
            )
            
            print_success("Scraper initialized")
            
            # Get all URLs from config
            urls_config = self.scraper_config.get('urls', [])
            
            if len(urls_config) == 0:
                print_warning("No URLs to scrape")
                return False
            
            print_info(f"Scraping {len(urls_config)} URL(s)...")
            
            results = []
            for item in urls_config:
                url = item.get("url")
                if not url:
                    continue
                
                try:
                    print_info(f"  Scraping: {url}")
                    filepath = self.scraper.scrape(url)
                    if filepath:
                        results.append({"url": url, "status": "success", "filepath": filepath})
                        print_success(f"    ✓ Scraped: {filepath}")
                    else:
                        results.append({"url": url, "status": "failed"})
                        print_error(f"    ✗ Failed to scrape: {url}")
                except Exception as e:
                    results.append({"url": url, "status": "error", "error": str(e)})
                    print_error(f"    ✗ Error: {e}")
            
            successful = sum(1 for r in results if r["status"] == "success")
            print_success(f"Scraping complete: {successful}/{len(enabled_urls)} successful")
            
            self.test_results.append(("Scraping", successful > 0, f"{successful}/{len(enabled_urls)} successful"))
            return successful > 0
            
        except Exception as e:
            print_error(f"Scraping failed: {e}")
            self.test_results.append(("Scraping", False, str(e)))
            return False
    
    def test_document_loading(self) -> bool:
        """Test 4: Load documents from data directory"""
        print_section("Test 4: Document Loading")
        
        try:
            data_dir = self.scraper_config['scraper_settings']['output_dir']
            
            print_info(f"Loading documents from: {data_dir}")
            
            loader = JSONDocumentLoader(data_dir)
            documents = loader.load_documents()
            
            if len(documents) == 0:
                print_error("No documents loaded")
                return False
            
            print_success(f"Loaded {len(documents)} document(s)")
            
            # Validate document structure
            for i, doc in enumerate(documents[:3]):  # Check first 3
                if not doc.page_content:
                    print_error(f"Document {i} has empty content")
                    return False
                
                if not doc.metadata.get('fund_name'):
                    print_warning(f"Document {i} missing fund_name in metadata")
            
            if self.verbose:
                for i, doc in enumerate(documents[:3], 1):
                    fund_name = doc.metadata.get('fund_name', 'Unknown')
                    source_file = doc.metadata.get('source_file', 'Unknown')
                    print_info(f"  [{i}] {fund_name} (from {source_file})")
            
            self.documents = documents
            self.test_results.append(("Document Loading", True, f"{len(documents)} documents"))
            return True
            
        except Exception as e:
            print_error(f"Document loading failed: {e}")
            self.test_results.append(("Document Loading", False, str(e)))
            return False
    
    def test_chunking(self) -> bool:
        """Test 5: Chunk documents"""
        print_section("Test 5: Document Chunking")
        
        try:
            if not hasattr(self, 'documents'):
                print_error("Documents not loaded. Run test_document_loading first.")
                return False
            
            print_info("Chunking documents...")
            
            chunker = DocumentChunker(use_semantic_chunking=True)
            chunks = chunker.chunk_documents(self.documents)
            
            if len(chunks) == 0:
                print_error("No chunks created")
                return False
            
            print_success(f"Created {len(chunks)} chunk(s) from {len(self.documents)} document(s)")
            
            # Validate chunks
            for i, chunk in enumerate(chunks[:3]):  # Check first 3
                if not chunk.page_content:
                    print_error(f"Chunk {i} has empty content")
                    return False
            
            if self.verbose:
                chunk_groups = {}
                for chunk in chunks:
                    group = chunk.metadata.get('semantic_group', 'unknown')
                    chunk_groups[group] = chunk_groups.get(group, 0) + 1
                
                print_info("Chunk distribution by semantic group:")
                for group, count in sorted(chunk_groups.items()):
                    print_info(f"  - {group}: {count} chunk(s)")
            
            self.chunks = chunks
            self.test_results.append(("Chunking", True, f"{len(chunks)} chunks"))
            return True
            
        except Exception as e:
            print_error(f"Chunking failed: {e}")
            self.test_results.append(("Chunking", False, str(e)))
            return False
    
    def test_ingestion(self) -> bool:
        """Test 6: Ingest documents into vector database"""
        print_section("Test 6: Vector Database Ingestion")
        
        try:
            if not hasattr(self, 'chunks'):
                print_error("Chunks not created. Run test_chunking first.")
                return False
            
            print_info("Initializing vector store...")
            
            self.vector_store = ChromaVectorStore(
                collection_name=config.COLLECTION_NAME,
                db_path=config.CHROMA_DB_PATH
            )
            
            info_before = self.vector_store.get_collection_info()
            print_success(f"Vector store initialized (existing docs: {info_before['document_count']})")
            
            print_info(f"Ingesting {len(self.chunks)} chunk(s)...")
            print_warning("This may take a while and requires API quota...")
            
            start_time = time.time()
            
            doc_ids = self.vector_store.upsert_documents(
                self.chunks,
                batch_size=10,
                skip_existing=True
            )
            
            elapsed_time = time.time() - start_time
            
            info_after = self.vector_store.get_collection_info()
            new_docs = info_after['document_count'] - info_before['document_count']
            
            print_success(f"Ingestion complete!")
            print_info(f"  Time taken: {elapsed_time:.2f} seconds")
            print_info(f"  New documents added: {new_docs}")
            print_info(f"  Total documents in DB: {info_after['document_count']}")
            
            if info_after['document_count'] == 0:
                print_error("No documents in database after ingestion")
                return False
            
            self.test_results.append(("Ingestion", True, f"{new_docs} new, {info_after['document_count']} total"))
            return True
            
        except Exception as e:
            print_error(f"Ingestion failed: {e}")
            import traceback
            if self.verbose:
                traceback.print_exc()
            self.test_results.append(("Ingestion", False, str(e)))
            return False
    
    def test_vector_database(self) -> bool:
        """Test 7: Validate vector database"""
        print_section("Test 7: Vector Database Validation")
        
        try:
            if self.vector_store is None:
                print_info("Initializing vector store (using existing DB)...")
                self.vector_store = ChromaVectorStore(
                    collection_name=config.COLLECTION_NAME,
                    db_path=config.CHROMA_DB_PATH
                )
            
            info = self.vector_store.get_collection_info()
            
            print_success(f"Collection: {info['collection_name']}")
            print_success(f"Total documents: {info['document_count']}")
            print_success(f"Database path: {info['db_path']}")
            
            if info['document_count'] == 0:
                print_error("Vector database is empty")
                return False
            
            # Test retrieval
            print_info("Testing document retrieval...")
            sample_results = self.vector_store.collection.get(
                limit=1,
                include=["embeddings", "documents", "metadatas"]
            )
            
            if not sample_results or not sample_results.get('ids'):
                print_error("Could not retrieve sample document")
                return False
            
            # Check embeddings
            embeddings = sample_results.get('embeddings')
            if embeddings is not None:
                try:
                    # Handle numpy arrays and lists
                    if hasattr(embeddings, '__len__') and len(embeddings) > 0:
                        first_embedding = embeddings[0]
                        if hasattr(first_embedding, '__len__'):
                            embedding_dim = len(first_embedding)
                            print_success(f"Embeddings verified (dimension: {embedding_dim})")
                        else:
                            print_success("Embeddings verified")
                    else:
                        print_error("No embeddings found")
                        return False
                except (TypeError, ValueError) as e:
                    # If we can't determine dimension, just verify embeddings exist
                    print_success("Embeddings verified (dimension check skipped)")
            else:
                print_error("No embeddings found")
                return False
            
            self.test_results.append(("Vector Database", True, f"{info['document_count']} docs"))
            return True
            
        except Exception as e:
            print_error(f"Vector database validation failed: {e}")
            self.test_results.append(("Vector Database", False, str(e)))
            return False
    
    def test_similarity_search(self) -> bool:
        """Test 8: Test similarity search"""
        print_section("Test 8: Similarity Search")
        
        try:
            if self.vector_store is None:
                print_error("Vector store not initialized")
                return False
            
            test_queries = [
                "large cap fund",
                "NAV value",
                "minimum investment amount",
                "expense ratio",
                "ELSS tax saver fund"
            ]
            
            print_info(f"Testing {len(test_queries)} similarity search queries...")
            
            successful = 0
            for query in test_queries:
                try:
                    results = self.vector_store.similarity_search(query, k=3)
                    if results and len(results) > 0:
                        successful += 1
                        if self.verbose:
                            top_result = results[0]
                            fund_name = top_result.metadata.get('fund_name', 'Unknown')
                            print_info(f"  ✓ '{query}' → {fund_name}")
                    else:
                        print_warning(f"  ✗ '{query}' → No results")
                except Exception as e:
                    print_error(f"  ✗ '{query}' → Error: {e}")
            
            print_success(f"Similarity search: {successful}/{len(test_queries)} successful")
            
            if successful == 0:
                print_error("All similarity searches failed")
                return False
            
            self.test_results.append(("Similarity Search", successful > 0, f"{successful}/{len(test_queries)}"))
            return True
            
        except Exception as e:
            print_error(f"Similarity search test failed: {e}")
            self.test_results.append(("Similarity Search", False, str(e)))
            return False
    
    def test_rag_queries(self) -> bool:
        """Test 9: Test RAG query answering"""
        print_section("Test 9: RAG Query Answering")
        
        try:
            if self.vector_store is None:
                print_error("Vector store not initialized")
                return False
            
            print_info("Initializing RAG chain...")
            
            self.rag_chain = RAGChain(self.vector_store)
            
            print_success("RAG chain initialized")
            
            test_queries = [
                "What is the NAV of Nippon India Large Cap Fund?",
                "What is the minimum investment amount?",
                "What is the expense ratio?",
                "Tell me about ELSS tax saver fund",
                "What are the returns for flexi cap fund?"
            ]
            
            print_info(f"Testing {len(test_queries)} RAG queries...")
            print_warning("This requires API quota and may take time...")
            
            successful = 0
            for query in test_queries:
                try:
                    print_info(f"  Query: '{query}'")
                    result = self.rag_chain.query_with_retrieval(query, k=3)
                    
                    if result and result.get('answer'):
                        answer = result['answer']
                        retrieved = result.get('retrieved_documents', 0)
                        sources = result.get('sources', [])
                        
                        successful += 1
                        
                        if self.verbose:
                            print_success(f"    ✓ Retrieved {retrieved} docs, {len(sources)} sources")
                            print_info(f"    Answer preview: {answer[:100]}...")
                    else:
                        print_warning(f"    ✗ No answer generated")
                        
                except Exception as e:
                    print_error(f"    ✗ Error: {e}")
                    if self.verbose:
                        import traceback
                        traceback.print_exc()
            
            print_success(f"RAG queries: {successful}/{len(test_queries)} successful")
            
            if successful == 0:
                print_error("All RAG queries failed")
                return False
            
            self.test_results.append(("RAG Queries", successful > 0, f"{successful}/{len(test_queries)}"))
            return True
            
        except Exception as e:
            print_error(f"RAG query test failed: {e}")
            import traceback
            if self.verbose:
                traceback.print_exc()
            self.test_results.append(("RAG Queries", False, str(e)))
            return False
    
    def test_end_to_end_queries(self) -> bool:
        """Test 10: End-to-end query flow"""
        print_section("Test 10: End-to-End Query Flow")
        
        try:
            if self.rag_chain is None:
                print_error("RAG chain not initialized")
                return False
            
            # Complex queries that test the full pipeline
            complex_queries = [
                {
                    "query": "What is the NAV and expense ratio of Nippon India Large Cap Fund?",
                    "expected_keywords": ["NAV", "expense"]
                },
                {
                    "query": "Compare the minimum investment amounts for different funds",
                    "expected_keywords": ["minimum", "investment"]
                },
                {
                    "query": "What are the returns for ELSS tax saver fund?",
                    "expected_keywords": ["returns", "ELSS"]
                }
            ]
            
            print_info(f"Testing {len(complex_queries)} complex end-to-end queries...")
            
            successful = 0
            for test_case in complex_queries:
                query = test_case["query"]
                expected_keywords = test_case["expected_keywords"]
                
                try:
                    print_info(f"  Query: '{query}'")
                    result = self.rag_chain.query_with_retrieval(query, k=5)
                    
                    if result and result.get('answer'):
                        answer = result['answer'].lower()
                        
                        # Check if answer contains expected keywords
                        found_keywords = [kw for kw in expected_keywords if kw.lower() in answer]
                        
                        if len(found_keywords) > 0:
                            successful += 1
                            if self.verbose:
                                print_success(f"    ✓ Found keywords: {found_keywords}")
                                print_info(f"    Retrieved: {result.get('retrieved_documents', 0)} docs")
                                print_info(f"    Sources: {len(result.get('sources', []))}")
                        else:
                            print_warning(f"    ⚠ Answer doesn't contain expected keywords")
                            if self.verbose:
                                print_info(f"    Answer: {answer[:200]}...")
                    else:
                        print_warning(f"    ✗ No answer generated")
                        
                except Exception as e:
                    print_error(f"    ✗ Error: {e}")
            
            print_success(f"End-to-end queries: {successful}/{len(complex_queries)} successful")
            
            self.test_results.append(("End-to-End Queries", successful > 0, f"{successful}/{len(complex_queries)}"))
            return successful > 0
            
        except Exception as e:
            print_error(f"End-to-end query test failed: {e}")
            self.test_results.append(("End-to-End Queries", False, str(e)))
            return False
    
    def print_summary(self):
        """Print test summary."""
        print_header("Test Summary")
        
        total = len(self.test_results)
        passed = sum(1 for _, success, _ in self.test_results if success)
        failed = total - passed
        
        for test_name, success, details in self.test_results:
            try:
                status = "✓ PASS" if success else "✗ FAIL"
            except UnicodeEncodeError:
                status = "[PASS]" if success else "[FAIL]"
            color = Colors.OKGREEN if success else Colors.FAIL
            print(f"{color}{status}{Colors.ENDC}: {test_name} - {details}")
        
        print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.ENDC}")
        
        if failed > 0:
            print(f"{Colors.FAIL}{failed} test(s) failed{Colors.ENDC}")
        else:
            try:
                print(f"{Colors.OKGREEN}All tests passed! ✓{Colors.ENDC}")
            except UnicodeEncodeError:
                print(f"{Colors.OKGREEN}All tests passed! [OK]{Colors.ENDC}")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="End-to-End Test Suite with Real Data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests with existing data
  python scripts/test_e2e_real_data.py
  
  # Run with new scraping
  python scripts/test_e2e_real_data.py --scrape
  
  # Skip ingestion (use existing vector DB)
  python scripts/test_e2e_real_data.py --skip-ingestion
  
  # Verbose output
  python scripts/test_e2e_real_data.py --verbose
        """
    )
    
    parser.add_argument(
        "--scrape",
        action="store_true",
        help="Run actual web scraping (requires internet)"
    )
    
    parser.add_argument(
        "--skip-ingestion",
        action="store_true",
        help="Skip ingestion step (use existing vector database)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print verbose output"
    )
    
    args = parser.parse_args()
    
    # Check API key
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == 'your_gemini_api_key_here':
        print_error("GEMINI_API_KEY not configured")
        print_info("Please set GEMINI_API_KEY in your .env file")
        return 1
    
    # Run tests
    runner = E2ETestRunner(
        scrape_new=args.scrape,
        skip_ingestion=args.skip_ingestion,
        verbose=args.verbose
    )
    
    success = runner.run_all_tests()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

