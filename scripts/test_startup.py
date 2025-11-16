"""
Manual test script for startup integration.
This script tests that the startup event properly initializes components and handles scheduled scraping.
Run this script to verify the startup functionality works correctly.
"""
import sys
import os
import json
import tempfile
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test API key
os.environ['GEMINI_API_KEY'] = 'test_api_key_12345'

from unittest.mock import Mock, patch
from api.main import startup_event, shutdown_event


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_test(name, passed=True):
    """Print test result."""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status}: {name}")


def test_startup_with_scheduled_scraper_enabled():
    """Test startup when scheduled scraper is enabled."""
    print_section("Test 1: Startup with Scheduled Scraper Enabled")
    
    try:
        # Mock components
        mock_vector_store = Mock()
        mock_vector_store.get_collection_info.return_value = {
            "collection_name": "test_collection",
            "document_count": 10,
            "db_path": "./test_db"
        }
        
        mock_rag_chain = Mock()
        
        mock_scraper = Mock()
        mock_scraper.config = {
            "schedule": {
                "enabled": True,
                "interval_type": "hourly",
                "interval_hours": 1,
                "auto_ingest_after_scrape": True
            }
        }
        mock_scraper.run_full_pipeline.return_value = {
            "scraping": {
                "status": "completed",
                "successful": 2,
                "failed": 0
            },
            "ingestion": {
                "status": "success"
            }
        }
        mock_scraper.next_run = None
        mock_scraper.start = Mock()
        mock_scraper.stop = Mock()
        
        # Reset global state
        import api.main
        api.main.vector_store = None
        api.main.rag_chain = None
        api.main.scheduled_scraper = None
        
        with patch('api.main.ChromaVectorStore', return_value=mock_vector_store):
            with patch('api.main.RAGChain', return_value=mock_rag_chain):
                with patch('api.main.ScheduledScraper', return_value=mock_scraper):
                    with patch('os.path.exists', return_value=True):
                        with patch('builtins.open', create=True) as mock_open:
                            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({
                                "schedule": {"enabled": True}
                            })
                            
                            # Run startup
                            import asyncio
                            asyncio.run(startup_event())
                            
                            # Verify
                            assert api.main.vector_store is not None, "Vector store not initialized"
                            assert api.main.rag_chain is not None, "RAG chain not initialized"
                            assert mock_scraper.run_full_pipeline.called, "Initial pipeline not run"
                            assert mock_scraper.start.called, "Scheduler not started"
                            
                            print_test("Startup with scheduled scraper enabled", True)
                            return True
    except Exception as e:
        print_test(f"Startup with scheduled scraper enabled: {e}", False)
        import traceback
        traceback.print_exc()
        return False


def test_startup_with_scheduled_scraper_disabled():
    """Test startup when scheduled scraper is disabled."""
    print_section("Test 2: Startup with Scheduled Scraper Disabled")
    
    try:
        mock_vector_store = Mock()
        mock_vector_store.get_collection_info.return_value = {
            "collection_name": "test_collection",
            "document_count": 10,
            "db_path": "./test_db"
        }
        
        mock_rag_chain = Mock()
        
        mock_scraper = Mock()
        mock_scraper.config = {
            "schedule": {"enabled": False}
        }
        
        # Reset global state
        import api.main
        api.main.vector_store = None
        api.main.rag_chain = None
        api.main.scheduled_scraper = None
        
        with patch('api.main.ChromaVectorStore', return_value=mock_vector_store):
            with patch('api.main.RAGChain', return_value=mock_rag_chain):
                with patch('api.main.ScheduledScraper', return_value=mock_scraper):
                    with patch('os.path.exists', return_value=True):
                        with patch('builtins.open', create=True) as mock_open:
                            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({
                                "schedule": {"enabled": False}
                            })
                            
                            # Run startup
                            import asyncio
                            asyncio.run(startup_event())
                            
                            # Verify
                            assert api.main.vector_store is not None, "Vector store not initialized"
                            assert api.main.rag_chain is not None, "RAG chain not initialized"
                            assert not mock_scraper.run_full_pipeline.called, "Pipeline should not run when disabled"
                            assert not mock_scraper.start.called, "Scheduler should not start when disabled"
                            
                            print_test("Startup with scheduled scraper disabled", True)
                            return True
    except Exception as e:
        print_test(f"Startup with scheduled scraper disabled: {e}", False)
        import traceback
        traceback.print_exc()
        return False


def test_startup_without_config_file():
    """Test startup when config file doesn't exist."""
    print_section("Test 3: Startup without Config File")
    
    try:
        mock_vector_store = Mock()
        mock_vector_store.get_collection_info.return_value = {
            "collection_name": "test_collection",
            "document_count": 10,
            "db_path": "./test_db"
        }
        
        mock_rag_chain = Mock()
        
        # Reset global state
        import api.main
        api.main.vector_store = None
        api.main.rag_chain = None
        api.main.scheduled_scraper = None
        
        with patch('api.main.ChromaVectorStore', return_value=mock_vector_store):
            with patch('api.main.RAGChain', return_value=mock_rag_chain):
                with patch('os.path.exists', return_value=False):
                    # Run startup (should not raise exception)
                    import asyncio
                    asyncio.run(startup_event())
                    
                    # Verify components were still initialized
                    assert api.main.vector_store is not None, "Vector store not initialized"
                    assert api.main.rag_chain is not None, "RAG chain not initialized"
                    
                    print_test("Startup without config file", True)
                    return True
    except Exception as e:
        print_test(f"Startup without config file: {e}", False)
        import traceback
        traceback.print_exc()
        return False


def test_startup_with_scraping_error():
    """Test startup handles scraping errors gracefully."""
    print_section("Test 4: Startup with Scraping Error")
    
    try:
        mock_vector_store = Mock()
        mock_vector_store.get_collection_info.return_value = {
            "collection_name": "test_collection",
            "document_count": 10,
            "db_path": "./test_db"
        }
        
        mock_rag_chain = Mock()
        
        mock_scraper = Mock()
        mock_scraper.config = {"schedule": {"enabled": True}}
        mock_scraper.run_full_pipeline.side_effect = Exception("Scraping failed")
        mock_scraper.start = Mock()
        
        # Reset global state
        import api.main
        api.main.vector_store = None
        api.main.rag_chain = None
        api.main.scheduled_scraper = None
        
        with patch('api.main.ChromaVectorStore', return_value=mock_vector_store):
            with patch('api.main.RAGChain', return_value=mock_rag_chain):
                with patch('api.main.ScheduledScraper', return_value=mock_scraper):
                    with patch('os.path.exists', return_value=True):
                        with patch('builtins.open', create=True) as mock_open:
                            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({
                                "schedule": {"enabled": True}
                            })
                            
                            # Run startup (should not raise exception)
                            import asyncio
                            asyncio.run(startup_event())
                            
                            # Verify components were still initialized
                            assert api.main.vector_store is not None, "Vector store not initialized"
                            assert api.main.rag_chain is not None, "RAG chain not initialized"
                            # Scheduler should still start despite error
                            assert mock_scraper.start.called, "Scheduler should start despite error"
                            
                            print_test("Startup with scraping error handled gracefully", True)
                            return True
    except Exception as e:
        print_test(f"Startup with scraping error: {e}", False)
        import traceback
        traceback.print_exc()
        return False


def test_shutdown_event():
    """Test shutdown event."""
    print_section("Test 5: Shutdown Event")
    
    try:
        mock_scraper = Mock()
        mock_scraper.running = True
        mock_scraper.stop = Mock()
        
        import api.main
        api.main.scheduled_scraper = mock_scraper
        
        # Run shutdown
        import asyncio
        asyncio.run(shutdown_event())
        
        # Verify stop was called
        assert mock_scraper.stop.called, "Stop should be called on shutdown"
        
        print_test("Shutdown event", True)
        return True
    except Exception as e:
        print_test(f"Shutdown event: {e}", False)
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print_section("Startup Integration Tests")
    print("Testing server startup with scheduled scraper integration")
    
    results = []
    
    # Run tests
    results.append(("Startup with scheduled scraper enabled", test_startup_with_scheduled_scraper_enabled()))
    results.append(("Startup with scheduled scraper disabled", test_startup_with_scheduled_scraper_disabled()))
    results.append(("Startup without config file", test_startup_without_config_file()))
    results.append(("Startup with scraping error", test_startup_with_scraping_error()))
    results.append(("Shutdown event", test_shutdown_event()))
    
    # Summary
    print_section("Test Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

