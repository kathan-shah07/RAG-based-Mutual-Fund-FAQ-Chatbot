"""
Tests for the server startup integration with scheduled scraper.
Tests that the startup event properly initializes components and starts scheduled scraping.
"""
import pytest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Mock environment before importing API
os.environ['GEMINI_API_KEY'] = 'test_api_key_12345'
from api.main import app, startup_event, shutdown_event


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_config_file():
    """Create a temporary scraper config file for testing."""
    config_data = {
        "scraper_settings": {
            "output_dir": "./data/mutual_funds",
            "download_dir": "./data/downloaded_html",
            "use_interactive": False,
            "download_first": False
        },
        "urls": [
            {
                "url": "https://groww.in/mutual-funds/test-fund"
            }
        ],
        "schedule": {
            "enabled": True,
            "interval_type": "hourly",
            "interval_hours": 1,
            "interval_days": None,
            "run_at_times": [],
            "auto_ingest_after_scrape": True
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_config_disabled():
    """Create a temporary scraper config file with scheduling disabled."""
    config_data = {
        "scraper_settings": {
            "output_dir": "./data/mutual_funds",
            "download_dir": "./data/downloaded_html",
            "use_interactive": False,
            "download_first": False
        },
        "urls": [],
        "schedule": {
            "enabled": False,
            "interval_type": "hourly",
            "interval_hours": 1,
            "auto_ingest_after_scrape": True
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def mock_vector_store():
    """Mock ChromaVectorStore."""
    mock_store = Mock()
    mock_store.get_collection_info.return_value = {
        "collection_name": "test_collection",
        "document_count": 10,
        "db_path": "./test_db"
    }
    return mock_store


@pytest.fixture
def mock_rag_chain():
    """Mock RAGChain."""
    mock_chain = Mock()
    mock_chain.query_with_retrieval.return_value = {
        "answer": "Test answer",
        "question": "Test question",
        "retrieved_documents": 3,
        "sources": [
            {
                "content": "Test content",
                "metadata": {"fund_name": "Test Fund"},
                "similarity_score": 0.95
            }
        ],
        "citation_urls": [],
        "last_updated": None
    }
    mock_chain.clear_memory = Mock()
    return mock_chain


@pytest.fixture
def mock_scheduled_scraper():
    """Mock ScheduledScraper."""
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
            "failed": 0,
            "results": []
        },
        "ingestion": {
            "status": "success",
            "timestamp": "2024-01-01T00:00:00"
        },
        "timestamp": "2024-01-01T00:00:00"
    }
    mock_scraper.next_run = None
    mock_scraper.start = Mock()
    mock_scraper.stop = Mock()
    mock_scraper.running = False
    return mock_scraper


# ============================================================================
# Startup Event Tests
# ============================================================================

class TestStartupEvent:
    """Test cases for the startup event."""
    
    @patch('api.main.ChromaVectorStore')
    @patch('api.main.RAGChain')
    @patch('scripts.scheduled_scraper.ScheduledScraper')
    @patch.dict(os.environ, {'SCRAPER_CONFIG_PATH': 'scraper_config.json'})
    def test_startup_with_scheduled_scraper_enabled(
        self,
        mock_scraper_class,
        mock_rag_class,
        mock_vector_class,
        mock_vector_store,
        mock_rag_chain,
        mock_scheduled_scraper,
        temp_config_file
    ):
        """Test startup event when scheduled scraper is enabled."""
        # Setup mocks
        mock_vector_class.return_value = mock_vector_store
        mock_rag_class.return_value = mock_rag_chain
        mock_scraper_class.return_value = mock_scheduled_scraper
        
        # Mock config file path
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({
                    "schedule": {"enabled": True}
                })
                
                # Reset global state
                import api.main
                api.main.vector_store = None
                api.main.rag_chain = None
                api.main.scheduled_scraper = None
                
                # Run startup event
                import asyncio
                asyncio.run(startup_event())
                
                # Verify vector store was initialized
                assert api.main.vector_store is not None
                mock_vector_class.assert_called_once()
                
                # Verify RAG chain was initialized
                assert api.main.rag_chain is not None
                mock_rag_class.assert_called_once_with(mock_vector_store)
                
                # Verify scheduled scraper was initialized
                mock_scraper_class.assert_called()
                
                # Verify initial pipeline was run
                mock_scheduled_scraper.run_full_pipeline.assert_called_once()
                
                # Verify scheduler was started
                mock_scheduled_scraper.start.assert_called_once()
    
    @patch('api.main.ChromaVectorStore')
    @patch('api.main.RAGChain')
    @patch('scripts.scheduled_scraper.ScheduledScraper')
    def test_startup_with_scheduled_scraper_disabled(
        self,
        mock_scraper_class,
        mock_rag_class,
        mock_vector_class,
        mock_vector_store,
        mock_rag_chain,
        mock_scheduled_scraper
    ):
        """Test startup event when scheduled scraper is disabled."""
        # Setup mocks
        mock_vector_class.return_value = mock_vector_store
        mock_rag_class.return_value = mock_rag_chain
        mock_scheduled_scraper.config = {
            "schedule": {"enabled": False}
        }
        mock_scraper_class.return_value = mock_scheduled_scraper
        
        # Reset global state
        import api.main
        api.main.vector_store = None
        api.main.rag_chain = None
        api.main.scheduled_scraper = None
        
        # Run startup event
        import asyncio
        asyncio.run(startup_event())
        
        # Verify components were initialized
        assert api.main.vector_store is not None
        assert api.main.rag_chain is not None
        
        # Verify initial pipeline was NOT run
        mock_scheduled_scraper.run_full_pipeline.assert_not_called()
        
        # Verify scheduler was NOT started
        mock_scheduled_scraper.start.assert_not_called()
    
    @patch('api.main.ChromaVectorStore')
    @patch('api.main.RAGChain')
    def test_startup_without_config_file(
        self,
        mock_rag_class,
        mock_vector_class,
        mock_vector_store,
        mock_rag_chain
    ):
        """Test startup event when config file doesn't exist."""
        # Setup mocks
        mock_vector_class.return_value = mock_vector_store
        mock_rag_class.return_value = mock_rag_chain
        
        # Mock config file not found
        with patch('os.path.exists', return_value=False):
            # Reset global state
            import api.main
            api.main.vector_store = None
            api.main.rag_chain = None
            api.main.scheduled_scraper = None
            
            # Run startup event (should not raise exception)
            import asyncio
            asyncio.run(startup_event())
            
            # Verify components were still initialized
            assert api.main.vector_store is not None
            assert api.main.rag_chain is not None
    
    @patch('api.main.ChromaVectorStore')
    @patch('api.main.RAGChain')
    @patch('scripts.scheduled_scraper.ScheduledScraper')
    def test_startup_with_scraping_error(
        self,
        mock_scraper_class,
        mock_rag_class,
        mock_vector_class,
        mock_vector_store,
        mock_rag_chain,
        mock_scheduled_scraper
    ):
        """Test startup event handles scraping errors gracefully."""
        # Setup mocks
        mock_vector_class.return_value = mock_vector_store
        mock_rag_class.return_value = mock_rag_chain
        mock_scheduled_scraper.config = {
            "schedule": {"enabled": True}
        }
        mock_scheduled_scraper.run_full_pipeline.side_effect = Exception("Scraping failed")
        mock_scraper_class.return_value = mock_scheduled_scraper
        
        # Reset global state
        import api.main
        api.main.vector_store = None
        api.main.rag_chain = None
        api.main.scheduled_scraper = None
        
        # Run startup event (should not raise exception)
        import asyncio
        asyncio.run(startup_event())
        
        # Verify components were still initialized
        assert api.main.vector_store is not None
        assert api.main.rag_chain is not None
        
        # Verify scheduler was still started despite error
        mock_scheduled_scraper.start.assert_called_once()


# ============================================================================
# Shutdown Event Tests
# ============================================================================

class TestShutdownEvent:
    """Test cases for the shutdown event."""
    
    def test_shutdown_with_scheduled_scraper(self, mock_scheduled_scraper):
        """Test shutdown event stops scheduled scraper."""
        import api.main
        api.main.scheduled_scraper = mock_scheduled_scraper
        mock_scheduled_scraper.running = True
        
        # Run shutdown event
        import asyncio
        asyncio.run(shutdown_event())
        
        # Verify stop was called
        mock_scheduled_scraper.stop.assert_called_once()
    
    def test_shutdown_without_scheduled_scraper(self):
        """Test shutdown event when no scheduled scraper exists."""
        import api.main
        api.main.scheduled_scraper = None
        
        # Run shutdown event (should not raise exception)
        import asyncio
        asyncio.run(shutdown_event())


# ============================================================================
# Integration Tests with TestClient
# ============================================================================

class TestStartupIntegration:
    """Integration tests using FastAPI TestClient."""
    
    @patch('api.main.ChromaVectorStore')
    @patch('api.main.RAGChain')
    @patch('scripts.scheduled_scraper.ScheduledScraper')
    def test_server_startup_initializes_components(
        self,
        mock_scraper_class,
        mock_rag_class,
        mock_vector_class,
        mock_vector_store,
        mock_rag_chain
    ):
        """Test that server startup properly initializes all components."""
        # Setup mocks
        mock_vector_class.return_value = mock_vector_store
        mock_rag_class.return_value = mock_rag_chain
        mock_scraper = Mock()
        mock_scraper.config = {"schedule": {"enabled": False}}
        mock_scraper_class.return_value = mock_scraper
        
        # Reset global state
        import api.main
        api.main.vector_store = None
        api.main.rag_chain = None
        api.main.scheduled_scraper = None
        
        # Create test client (this triggers startup)
        # Note: TestClient may not trigger startup events in some pytest configurations
        # So we'll manually trigger startup_event
        import asyncio
        asyncio.run(startup_event())
        
        # Verify components were initialized
        assert api.main.vector_store is not None
        assert api.main.rag_chain is not None
    
    def test_health_endpoint_after_startup(self, mock_vector_store):
        """Test health endpoint works after startup."""
        import api.main
        api.main.vector_store = mock_vector_store
        
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "collection_info" in data
    
    @patch('scripts.scheduled_scraper.ScheduledScraper')
    def test_startup_logs_are_produced(self, mock_scraper_class, mock_scheduled_scraper):
        """Test that startup produces appropriate log messages."""
        import logging
        import api.main
        
        # Setup mock
        mock_scheduled_scraper.config = {"schedule": {"enabled": True}}
        mock_scheduled_scraper.run_full_pipeline.return_value = {
            "scraping": {"status": "completed"},
            "ingestion": {"status": "success"}
        }
        mock_scraper_class.return_value = mock_scheduled_scraper
        
        # Capture logs
        with patch('api.main.logger') as mock_logger:
            import asyncio
            asyncio.run(startup_event())
            
            # Verify logging was called
            assert mock_logger.info.called


# ============================================================================
# Configuration Tests
# ============================================================================

class TestConfigurationHandling:
    """Test configuration handling in startup."""
    
    @patch('api.main.ChromaVectorStore')
    @patch('api.main.RAGChain')
    @patch('scripts.scheduled_scraper.ScheduledScraper')
    def test_custom_config_path_from_env(
        self,
        mock_scraper_class,
        mock_rag_class,
        mock_vector_class,
        mock_vector_store,
        mock_rag_chain,
        temp_config_file
    ):
        """Test that custom config path from environment variable is used."""
        # Setup mocks
        mock_vector_class.return_value = mock_vector_store
        mock_rag_class.return_value = mock_rag_chain
        mock_scraper_class.return_value = Mock()
        
        # Reset global state
        import api.main
        api.main.vector_store = None
        api.main.rag_chain = None
        api.main.scheduled_scraper = None
        
        # Set environment variable
        with patch.dict(os.environ, {'SCRAPER_CONFIG_PATH': temp_config_file}):
            import asyncio
            asyncio.run(startup_event())
            
            # Verify ScheduledScraper was called with custom path
            mock_scraper_class.assert_called()
            call_args = mock_scraper_class.call_args
            assert call_args[1]['config_path'] == temp_config_file
    
    @patch('api.main.ChromaVectorStore')
    @patch('api.main.RAGChain')
    @patch('scripts.scheduled_scraper.ScheduledScraper')
    def test_default_config_path_when_env_not_set(
        self,
        mock_scraper_class,
        mock_rag_class,
        mock_vector_class,
        mock_vector_store,
        mock_rag_chain
    ):
        """Test that default config path is used when env var not set."""
        # Setup mocks
        mock_vector_class.return_value = mock_vector_store
        mock_rag_class.return_value = mock_rag_chain
        mock_scraper_class.return_value = Mock()
        
        # Reset global state
        import api.main
        api.main.vector_store = None
        api.main.rag_chain = None
        api.main.scheduled_scraper = None
        
        # Remove environment variable if it exists
        env_key = 'SCRAPER_CONFIG_PATH'
        original_value = os.environ.pop(env_key, None)
        
        try:
            import asyncio
            asyncio.run(startup_event())
            
            # Verify ScheduledScraper was called with default path
            mock_scraper_class.assert_called()
            call_args = mock_scraper_class.call_args
            assert call_args[1]['config_path'] == "scraper_config.json"
        finally:
            # Restore original value if it existed
            if original_value:
                os.environ[env_key] = original_value

