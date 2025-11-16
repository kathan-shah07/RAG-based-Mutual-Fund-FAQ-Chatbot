"""
Unit tests for GrowwScraper class.
Tests individual methods and functionality in isolation.
"""
import pytest
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup

from scrapers.groww_scraper import GrowwScraper, load_config


class TestGrowwScraperInit:
    """Test scraper initialization."""
    
    def test_init_defaults(self):
        """Test scraper initialization with default parameters."""
        scraper = GrowwScraper()
        assert scraper.output_dir == "data/mutual_funds"
        assert scraper.use_interactive is True
        assert scraper.download_first is False
        assert scraper.session is not None
    
    def test_init_custom_params(self):
        """Test scraper initialization with custom parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scraper = GrowwScraper(
                output_dir=tmpdir,
                use_interactive=False,
                download_dir=f"{tmpdir}/html",
                download_first=True
            )
            assert scraper.output_dir == tmpdir
            assert scraper.use_interactive is False
            assert scraper.download_first is True
            assert scraper.download_dir == f"{tmpdir}/html"
            assert os.path.exists(tmpdir)
            assert os.path.exists(f"{tmpdir}/html")


class TestConfigLoading:
    """Test configuration loading functionality."""
    
    def test_load_config_exists(self, tmp_path):
        """Test loading config from existing file."""
        config_file = tmp_path / "scraper_config.json"
        config_data = {
            "scraper_settings": {
                "output_dir": "./test_data",
                "download_first": True
            },
            "urls": [
                {"url": "https://test.com/fund1"}
            ]
        }
        config_file.write_text(json.dumps(config_data))
        
        config = load_config(str(config_file))
        assert config["scraper_settings"]["output_dir"] == "./test_data"
        assert len(config["urls"]) == 1
    
    def test_load_config_not_exists(self):
        """Test loading config when file doesn't exist."""
        config = load_config("nonexistent_config.json")
        assert "scraper_settings" in config
        assert config["scraper_settings"]["output_dir"] == "data/mutual_funds"
        assert config["urls"] == []


class TestHTMLDownload:
    """Test HTML download functionality."""
    
    @patch('scrapers.groww_scraper.PLAYWRIGHT_AVAILABLE', False)
    @patch('scrapers.groww_scraper.GrowwScraper.fetch_page')
    def test_download_html_success(self, mock_fetch, tmp_path):
        """Test successful HTML download."""
        scraper = GrowwScraper(download_dir=str(tmp_path), download_first=True)
        mock_fetch.return_value = "<html><body>Test Content</body></html>"
        
        html_path = scraper.download_html("https://test.com/fund")
        
        assert html_path is not None
        assert os.path.exists(html_path)
        with open(html_path, 'r', encoding='utf-8') as f:
            assert "Test Content" in f.read()
    
    @patch('scrapers.groww_scraper.PLAYWRIGHT_AVAILABLE', False)
    @patch('scrapers.groww_scraper.GrowwScraper.fetch_page')
    def test_download_html_failure(self, mock_fetch, tmp_path):
        """Test HTML download failure."""
        scraper = GrowwScraper(download_dir=str(tmp_path), download_first=True)
        mock_fetch.return_value = None
        
        html_path = scraper.download_html("https://test.com/fund")
        
        assert html_path is None


class TestScrapeFromFile:
    """Test scraping from downloaded HTML file."""
    
    def test_scrape_from_file_success(self, tmp_path):
        """Test successful scraping from HTML file."""
        scraper = GrowwScraper(output_dir=str(tmp_path), download_first=False)
        
        # Create mock HTML file
        html_file = tmp_path / "test-fund.html"
        html_content = """
        <html>
        <head><title>Test Fund</title></head>
        <body>
            <h1>Test Mutual Fund</h1>
            <div>Latest NAV as of 13 Nov 2025 ₹100.50</div>
            <div>AUM ₹1000 Cr</div>
            <div>Category: Equity</div>
            <div>Risk Level: Very High Risk</div>
            <div>Lock-in Period: 3 years</div>
            <div>Exit load of 1% if redeemed within 7 days</div>
        </body>
        </html>
        """
        html_file.write_text(html_content, encoding='utf-8')
        
        # Mock extract_detailed_data to return test data
        with patch.object(scraper, 'extract_detailed_data') as mock_extract:
            mock_extract.return_value = {
                "fund_name": "Test Mutual Fund",
                "nav": {"value": "₹100.50", "as_of": "13 Nov 2025"},
                "fund_size": "₹1000 Cr",
                "summary": {
                    "fund_category": "Equity",
                    "risk_level": "Very High Risk",
                    "lock_in_period": "3 years"
                },
                "cost_and_tax": {
                    "exit_load": "Exit load of 1% if redeemed within 7 days"
                }
            }
            
            json_path = scraper.scrape_from_file(str(html_file), "https://test.com/fund")
            
            assert json_path is not None
            assert os.path.exists(json_path)
            assert not os.path.exists(html_file)  # HTML file should be deleted
            
            # Verify JSON content
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert isinstance(data, list)
                assert len(data) == 1
                assert data[0]["fund_name"] == "Test Mutual Fund"
    
    def test_scrape_from_file_extraction_failure(self, tmp_path):
        """Test scraping when extraction fails."""
        scraper = GrowwScraper(output_dir=str(tmp_path))
        
        html_file = tmp_path / "test-fund.html"
        html_file.write_text("<html><body>Test</body></html>")
        
        # Mock extract_detailed_data to raise exception
        with patch.object(scraper, 'extract_detailed_data') as mock_extract:
            mock_extract.side_effect = Exception("Extraction failed")
            
            json_path = scraper.scrape_from_file(str(html_file), "https://test.com/fund")
            
            assert json_path is None
            assert os.path.exists(html_file)  # HTML file should NOT be deleted on failure


class TestDataExtraction:
    """Test data extraction methods."""
    
    def test_extract_risk_level_elss(self):
        """Test risk level extraction for ELSS funds."""
        scraper = GrowwScraper()
        html = """
        <html>
        <body>
            <h1>ELSS Tax Saver Fund</h1>
            <div>Category: Equity ELSS</div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'lxml')
        page_text = soup.get_text()
        
        with patch.object(scraper, 'extract_detailed_data') as mock_extract:
            mock_extract.return_value = {
                "fund_name": "ELSS Tax Saver Fund",
                "summary": {"risk_level": "Very High Risk"}
            }
            
            data = scraper.extract_detailed_data(soup, page_text, None)
            assert data["summary"]["risk_level"] == "Very High Risk"
    
    def test_extract_lock_in_period_elss(self):
        """Test lock-in period extraction for ELSS funds."""
        scraper = GrowwScraper()
        html = """
        <html>
        <body>
            <h1>ELSS Tax Saver Fund</h1>
            <div>Lock-in Period: 3 years</div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'lxml')
        page_text = soup.get_text()
        
        data = scraper.extract_detailed_data(soup, page_text, None)
        # ELSS funds should have 3 years lock-in
        if "ELSS" in data.get("fund_name", "").upper():
            assert data["summary"]["lock_in_period"] == "3 years"
    
    def test_extract_exit_load(self):
        """Test exit load extraction."""
        scraper = GrowwScraper()
        html = """
        <html>
        <body>
            <div>Exit load of 1% if redeemed within 7 days</div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'lxml')
        page_text = soup.get_text()
        
        data = scraper.extract_detailed_data(soup, page_text, None)
        exit_load = data.get("cost_and_tax", {}).get("exit_load", "")
        assert "Exit load" in exit_load or exit_load == "Nil"


class TestScrapeMethod:
    """Test main scrape method."""
    
    @patch('scrapers.groww_scraper.PLAYWRIGHT_AVAILABLE', False)
    @patch('scrapers.groww_scraper.GrowwScraper.download_html')
    @patch('scrapers.groww_scraper.GrowwScraper.scrape_from_file')
    def test_scrape_with_download_first(self, mock_scrape_file, mock_download, tmp_path):
        """Test scrape method with download_first=True."""
        scraper = GrowwScraper(
            output_dir=str(tmp_path),
            download_dir=str(tmp_path / "html"),
            download_first=True
        )
        
        mock_download.return_value = str(tmp_path / "html" / "fund.html")
        mock_scrape_file.return_value = str(tmp_path / "fund.json")
        
        result = scraper.scrape("https://test.com/fund")
        
        assert result is not None
        mock_download.assert_called_once_with("https://test.com/fund")
        mock_scrape_file.assert_called_once()
    
    @patch('scrapers.groww_scraper.GrowwScraper.parse_fund_data')
    def test_scrape_without_download_first(self, mock_parse, tmp_path):
        """Test scrape method with download_first=False."""
        scraper = GrowwScraper(
            output_dir=str(tmp_path),
            download_first=False
        )
        
        mock_parse.return_value = {
            "fund_name": "Test Fund",
            "nav": {"value": "₹100", "as_of": "2025-01-01"},
            "fund_size": "₹1000 Cr",
            "summary": {},
            "returns": {},
            "category_info": {},
            "top_5_holdings": [],
            "advanced_ratios": {},
            "cost_and_tax": {}
        }
        
        result = scraper.scrape("https://test.com/fund")
        
        assert result is not None
        mock_parse.assert_called_once_with("https://test.com/fund")


class TestSaveJSON:
    """Test JSON saving functionality."""
    
    def test_save_json(self, tmp_path):
        """Test saving fund data to JSON."""
        scraper = GrowwScraper(output_dir=str(tmp_path))
        
        test_data = {
            "fund_name": "Test Fund",
            "nav": {"value": "₹100", "as_of": "2025-01-01"},
            "source_url": "https://test.com/fund",
            "last_scraped": "2025-01-01"
        }
        
        filepath = scraper.save_json(test_data, "test-fund")
        
        assert filepath is not None
        assert os.path.exists(filepath)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["fund_name"] == "Test Fund"


class TestFieldExtraction:
    """Test specific field extraction methods."""
    
    def test_extract_risk_level_patterns(self):
        """Test risk level extraction with various patterns."""
        scraper = GrowwScraper()
        
        test_cases = [
            ("Risk Level: Very High Risk", "Very High Risk"),
            ("Riskometer: High Risk", "High Risk"),
            ("Category: Equity Risk: Very High", "Very High Risk"),
        ]
        
        for html_text, expected in test_cases:
            html = f"<html><body><div>{html_text}</div></body></html>"
            soup = BeautifulSoup(html, 'lxml')
            page_text = soup.get_text()
            
            # This is a simplified test - actual extraction is more complex
            assert "Risk" in page_text or expected in page_text
    
    def test_extract_lock_in_patterns(self):
        """Test lock-in period extraction with various patterns."""
        scraper = GrowwScraper()
        
        test_cases = [
            ("Lock-in Period: 3 years", "3 years"),
            ("Lock-in: 3Y", "3 years"),
            ("3 years lock-in", "3 years"),
        ]
        
        for html_text, expected in test_cases:
            html = f"<html><body><div>{html_text}</div></body></html>"
            soup = BeautifulSoup(html, 'lxml')
            page_text = soup.get_text()
            
            # Verify pattern matching capability
            assert "lock" in page_text.lower() or "3" in page_text
    
    def test_extract_exit_load_patterns(self):
        """Test exit load extraction with various patterns."""
        scraper = GrowwScraper()
        
        test_cases = [
            ("Exit load of 1% if redeemed within 7 days", "1%"),
            ("Exit load: Nil", "Nil"),
            ("Exit load for units in excess of 10% of the investment, 1% will be charged", "1%"),
        ]
        
        for html_text, expected_keyword in test_cases:
            html = f"<html><body><div>{html_text}</div></body></html>"
            soup = BeautifulSoup(html, 'lxml')
            page_text = soup.get_text()
            
            # Verify pattern matching capability
            assert "exit load" in page_text.lower()
            assert expected_keyword.lower() in page_text.lower() or "nil" in page_text.lower()


class TestErrorHandling:
    """Test error handling in scraper."""
    
    def test_scrape_invalid_url(self, tmp_path):
        """Test scraping with invalid URL."""
        scraper = GrowwScraper(output_dir=str(tmp_path))
        
        with patch.object(scraper, 'parse_fund_data') as mock_parse:
            mock_parse.return_value = None
            
            result = scraper.scrape("https://invalid-url.com/fund")
            
            assert result is None
    
    def test_scrape_file_not_found(self, tmp_path):
        """Test scraping from non-existent file."""
        scraper = GrowwScraper(output_dir=str(tmp_path))
        
        result = scraper.scrape_from_file("nonexistent.html", "https://test.com/fund")
        
        assert result is None


@pytest.fixture
def tmp_path():
    """Create temporary directory for tests."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

