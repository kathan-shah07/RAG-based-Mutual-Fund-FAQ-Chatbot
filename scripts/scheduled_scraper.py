"""
Scheduled scraper service that runs scraping and ingestion at configured intervals.
"""
import sys
import os
import time
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.groww_scraper import GrowwScraper, load_config
from scripts.ingest_data import main as ingest_data
from vector_store.chroma_store import ChromaVectorStore
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ScheduledScraper:
    """Service to run scraping and ingestion on a schedule."""
    
    # Class-level status tracking (shared across instances)
    _status = {
        "is_running": False,
        "current_operation": None,  # "scraping", "ingestion", "idle"
        "progress": None,  # "detecting_new_urls", "scraping_urls", "ingesting_data", "completed"
        "message": "",
        "urls_processed": [],
        "urls_total": 0,
        "start_time": None,
        "end_time": None,
        "error": None
    }
    
    def __init__(self, config_path: str = "scraper_config.json"):
        self.config_path = config_path
        self.config = load_config(config_path)
        self.running = False
        self.thread = None
        self.last_run = None
        self.next_run = None
    
    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Get current status of scraping/ingestion operations."""
        return cls._status.copy()
    
    @classmethod
    def update_status(cls, **kwargs):
        """Update status information."""
        cls._status.update(kwargs)
        cls._status["last_updated"] = datetime.now().isoformat()
    
    @classmethod
    def reset_status(cls):
        """Reset status to idle."""
        cls._status = {
            "is_running": False,
            "current_operation": None,
            "progress": None,
            "message": "",
            "urls_processed": [],
            "urls_total": 0,
            "start_time": None,
            "end_time": None,
            "error": None,
            "last_updated": datetime.now().isoformat()
        }
        
    def run_scraping(self, urls_to_scrape: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run scraping process.
        
        Args:
            urls_to_scrape: Optional list of specific URLs to scrape. If None, processes all URLs from config.
        
        Returns:
            Dictionary with scraping results
        """
        self.update_status(
            is_running=True,
            current_operation="scraping",
            progress="scraping_urls",
            message="Starting scraping...",
            start_time=datetime.now().isoformat(),
            urls_processed=[],
            error=None
        )
        
        logger.info("=" * 70)
        logger.info("Starting scheduled scraping...")
        logger.info("=" * 70)
        
        scraper_settings = self.config.get("scraper_settings", {})
        urls_config = self.config.get("urls", [])
        
        # Initialize scraper
        scraper = GrowwScraper(
            output_dir=scraper_settings.get("output_dir", "data/mutual_funds"),
            use_interactive=scraper_settings.get("use_interactive", True),
            download_dir=scraper_settings.get("download_dir", "data/downloaded_html"),
            download_first=scraper_settings.get("download_first", False)
        )
        
        # Determine which URLs to scrape
        if urls_to_scrape is not None:
            # Use provided list of URLs
            urls_to_process = urls_to_scrape
            logger.info(f"Scraping {len(urls_to_process)} specified URL(s)")
        else:
            # Extract URLs from config
            urls_to_process = [item.get("url") for item in urls_config if item.get("url")]
            if not urls_to_process:
                logger.warning("No URLs found in config")
                self.update_status(
                    is_running=False,
                    current_operation=None,
                    progress=None,
                    message="No URLs found in config"
                )
                return {"status": "skipped", "reason": "No URLs in config"}
            logger.info(f"Found {len(urls_to_process)} URL(s) to scrape")
        
        self.update_status(
            urls_total=len(urls_to_process),
            message=f"Scraping {len(urls_to_process)} URL(s)..."
        )
        
        results = []
        processed_urls = []
        for i, url in enumerate(urls_to_process, 1):
            if not url:
                continue
            
            try:
                logger.info(f"Scraping ({i}/{len(urls_to_process)}): {url}")
                self.update_status(
                    message=f"Scraping URL {i}/{len(urls_to_process)}: {url[:50]}...",
                    urls_processed=processed_urls.copy()
                )
                
                filepath = scraper.scrape(url)
                if filepath:
                    results.append({"url": url, "status": "success", "filepath": filepath})
                    processed_urls.append({"url": url, "status": "success"})
                    logger.info(f"✓ Successfully scraped: {filepath}")
                else:
                    results.append({"url": url, "status": "failed", "reason": "No file generated"})
                    processed_urls.append({"url": url, "status": "failed"})
                    logger.warning(f"✗ Failed to scrape: {url}")
            except Exception as e:
                results.append({"url": url, "status": "error", "error": str(e)})
                processed_urls.append({"url": url, "status": "error", "error": str(e)})
                logger.error(f"✗ Error scraping {url}: {e}")
                continue
        
        successful = sum(1 for r in results if r["status"] == "success")
        failed = len(results) - successful
        
        logger.info(f"Scraping complete: {successful} successful, {failed} failed")
        
        self.update_status(
            progress="scraping_completed",
            message=f"Scraping completed: {successful} successful, {failed} failed",
            urls_processed=processed_urls
        )
        
        return {
            "status": "completed",
            "successful": successful,
            "failed": failed,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def run_ingestion(self) -> Dict[str, Any]:
        """
        Run ingestion process.
        
        Returns:
            Dictionary with ingestion results
        """
        self.update_status(
            is_running=True,
            current_operation="ingestion",
            progress="ingesting_data",
            message="Starting ingestion...",
            start_time=datetime.now().isoformat()
        )
        
        logger.info("=" * 70)
        logger.info("Starting scheduled ingestion...")
        logger.info("=" * 70)
        
        try:
            # Check if data directory has files before ingesting
            import os
            from pathlib import Path
            scraper_settings = self.config.get("scraper_settings", {})
            data_dir = Path(scraper_settings.get("output_dir", "data/mutual_funds"))
            
            if not data_dir.exists():
                logger.warning(f"Data directory does not exist: {data_dir}")
                logger.info("Skipping ingestion - no data directory")
                self.update_status(
                    is_running=False,
                    current_operation=None,
                    progress=None,
                    message="Skipped: No data directory"
                )
                return {
                    "status": "skipped",
                    "reason": "No data directory",
                    "timestamp": datetime.now().isoformat()
                }
            
            json_files = list(data_dir.rglob("*.json"))
            if len(json_files) == 0:
                logger.warning(f"No JSON files found in {data_dir}")
                logger.info("Skipping ingestion - no files to process")
                self.update_status(
                    is_running=False,
                    current_operation=None,
                    progress=None,
                    message="Skipped: No JSON files found"
                )
                return {
                    "status": "skipped",
                    "reason": "No JSON files found",
                    "timestamp": datetime.now().isoformat()
                }
            
            self.update_status(
                message=f"Ingesting {len(json_files)} file(s) into vector database..."
            )
            
            # Import and run ingestion
            ingest_data()
            logger.info("✓ Ingestion completed successfully")
            
            self.update_status(
                is_running=False,
                current_operation=None,
                progress="completed",
                message="Ingestion completed successfully",
                end_time=datetime.now().isoformat()
            )
            
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"✗ Ingestion failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            
            self.update_status(
                is_running=False,
                current_operation=None,
                progress=None,
                message=f"Ingestion failed: {e}",
                error=str(e),
                end_time=datetime.now().isoformat()
            )
            
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def should_run_pipeline(self) -> tuple[bool, Optional[datetime], Optional[datetime]]:
        """
        Check if pipeline should run based on timestamp validation.
        
        Returns:
            Tuple of (should_run: bool, latest_timestamp: Optional[datetime], next_update_time: Optional[datetime])
        """
        schedule_config = self.config.get("schedule", {})
        interval_type = schedule_config.get("interval_type", "hourly")
        interval_hours = schedule_config.get("interval_hours", 1)
        
        # Convert interval to hours
        if interval_type == "daily":
            interval_days = schedule_config.get("interval_days", 1)
            interval_hours = interval_days * 24
        
        try:
            # Initialize vector store to check timestamps
            vector_store = ChromaVectorStore(
                collection_name=config.COLLECTION_NAME,
                db_path=config.CHROMA_DB_PATH
            )
            
            needs_update, latest_timestamp, next_update_time = vector_store.check_if_data_needs_update(interval_hours)
            
            return needs_update, latest_timestamp, next_update_time
            
        except Exception as e:
            logger.warning(f"Could not check timestamp, will run pipeline: {e}")
            # If we can't check, assume we need to run
            return True, None, None
    
    def detect_new_urls(self) -> List[str]:
        """
        Detect new URLs in config that are not yet in the vector database.
        Uses URL as unique identifier (not just timestamp).
        
        Returns:
            List of new URLs to process
        """
        try:
            self.update_status(
                is_running=True,
                current_operation="detection",
                progress="detecting_new_urls",
                message="Checking for new URLs...",
                urls_processed=[],
                urls_total=0
            )
            
            # Initialize vector store to check for existing URLs
            vector_store = ChromaVectorStore(
                collection_name=config.COLLECTION_NAME,
                db_path=config.CHROMA_DB_PATH
            )
            
            # Get URLs from config
            urls_config = self.config.get("urls", [])
            config_urls = [item.get("url") for item in urls_config if item.get("url")]
            
            if not config_urls:
                self.update_status(
                    is_running=False,
                    current_operation=None,
                    progress=None,
                    message="No URLs found in config"
                )
                return []
            
            # Find new URLs (using URL as unique ID)
            new_urls = vector_store.find_new_urls(config_urls)
            
            if new_urls:
                logger.info(f"Found {len(new_urls)} new URL(s) not in vector database:")
                for url in new_urls:
                    logger.info(f"  - {url}")
                
                self.update_status(
                    message=f"Found {len(new_urls)} new URL(s) to process",
                    urls_total=len(new_urls)
                )
            else:
                logger.info("No new URLs detected - all URLs already in vector database")
                self.update_status(
                    is_running=False,
                    current_operation=None,
                    progress=None,
                    message="No new URLs detected"
                )
            
            return new_urls
            
        except Exception as e:
            logger.warning(f"Could not detect new URLs, will process all URLs: {e}")
            self.update_status(
                error=str(e),
                message=f"Error detecting URLs: {e}"
            )
            # Fallback: return all URLs from config
            urls_config = self.config.get("urls", [])
            return [item.get("url") for item in urls_config if item.get("url")]
    
    def run_full_pipeline(self, force: bool = False, check_new_urls: bool = True) -> Dict[str, Any]:
        """
        Run full pipeline: scraping followed by ingestion.
        Checks timestamp before running unless force=True.
        If check_new_urls=True, only processes new URLs not in vector database.
        Uses URL as unique identifier for detection.
        
        Args:
            force: If True, skip timestamp check and run anyway
            check_new_urls: If True, only process new URLs. If False, process all URLs.
        
        Returns:
            Dictionary with pipeline results
        """
        # Reset status at start
        self.reset_status()
        self.update_status(
            is_running=True,
            current_operation="pipeline",
            progress="starting",
            message="Starting pipeline...",
            start_time=datetime.now().isoformat()
        )
        
        # Check for new URLs first (if enabled) - uses URL as ID
        new_urls = []
        if check_new_urls:
            new_urls = self.detect_new_urls()
            
            if new_urls:
                logger.info("=" * 70)
                logger.info(f"New URLs detected - will process {len(new_urls)} URL(s) only")
                logger.info("=" * 70)
                self.update_status(
                    message=f"New URLs detected: Processing {len(new_urls)} URL(s)",
                    urls_total=len(new_urls)
                )
            else:
                logger.info("No new URLs detected")
                self.update_status(
                    message="No new URLs detected"
                )
        
        # Check if pipeline should run based on timestamp (only if no new URLs)
        if not force and not new_urls:
            should_run, latest_timestamp, next_update_time = self.should_run_pipeline()
            
            if not should_run:
                logger.info("=" * 70)
                logger.info("Skipping pipeline - data is still fresh")
                logger.info("=" * 70)
                if latest_timestamp:
                    logger.info(f"Latest ingestion: {latest_timestamp}")
                if next_update_time:
                    logger.info(f"Next update scheduled: {next_update_time}")
                
                self.update_status(
                    is_running=False,
                    current_operation=None,
                    progress=None,
                    message="Skipped: Data is still fresh",
                    end_time=datetime.now().isoformat()
                )
                
                return {
                    "scraping": {"status": "skipped", "reason": "Data is still fresh"},
                    "ingestion": {"status": "skipped", "reason": "Data is still fresh"},
                    "timestamp": datetime.now().isoformat(),
                    "skipped": True
                }
            else:
                if latest_timestamp:
                    logger.info(f"Data needs update. Latest ingestion: {latest_timestamp}")
                    self.update_status(
                        message=f"Data needs update. Latest ingestion: {latest_timestamp}"
                    )
        
        logger.info("=" * 70)
        if new_urls:
            logger.info(f"Running pipeline for {len(new_urls)} new URL(s): Scraping + Ingestion")
        else:
            logger.info("Running full pipeline: Scraping + Ingestion")
        logger.info("=" * 70)
        
        # Run scraping (only new URLs if detected, otherwise all URLs)
        urls_to_scrape = new_urls if new_urls else None
        scraping_result = self.run_scraping(urls_to_scrape=urls_to_scrape)
        
        # Check if auto-ingest is enabled
        schedule_config = self.config.get("schedule", {})
        auto_ingest = schedule_config.get("auto_ingest_after_scrape", True)
        
        ingestion_result = None
        if auto_ingest:
            # Only ingest if scraping was successful or if we have new URLs
            if scraping_result.get("successful", 0) > 0 or new_urls:
                ingestion_result = self.run_ingestion()
            else:
                logger.info("Skipping ingestion - no successful scrapes")
                self.update_status(
                    message="Skipping ingestion - no successful scrapes"
                )
        else:
            logger.info("Auto-ingestion disabled, skipping ingestion step")
            self.update_status(
                message="Auto-ingestion disabled"
            )
        
        # Final status update
        self.update_status(
            is_running=False,
            current_operation=None,
            progress="completed",
            message="Pipeline completed",
            end_time=datetime.now().isoformat()
        )
        
        return {
            "scraping": scraping_result,
            "ingestion": ingestion_result,
            "new_urls_detected": len(new_urls) if new_urls else 0,
            "timestamp": datetime.now().isoformat()
        }
    
    def calculate_next_run(self) -> Optional[datetime]:
        """
        Calculate next run time based on schedule configuration.
        
        Returns:
            Next run datetime or None if scheduling disabled
        """
        schedule_config = self.config.get("schedule", {})
        
        if not schedule_config.get("enabled", False):
            return None
        
        interval_type = schedule_config.get("interval_type", "hourly")
        interval_hours = schedule_config.get("interval_hours", 1)
        interval_days = schedule_config.get("interval_days")
        
        now = datetime.now()
        
        if interval_type == "hourly":
            next_run = now + timedelta(hours=interval_hours)
        elif interval_type == "daily":
            days = interval_days if interval_days else 1
            next_run = now + timedelta(days=days)
        else:
            # Default to hourly
            next_run = now + timedelta(hours=1)
        
        return next_run
    
    def scheduler_loop(self):
        """Main scheduler loop that runs scraping/ingestion at intervals."""
        logger.info("Scheduled scraper service started")
        
        while self.running:
            try:
                # Calculate next run time
                self.next_run = self.calculate_next_run()
                
                if not self.next_run:
                    logger.info("Scheduling disabled in config, stopping scheduler")
                    break
                
                logger.info(f"Next run scheduled for: {self.next_run}")
                
                # Wait until next run time
                while self.running and datetime.now() < self.next_run:
                    time.sleep(60)  # Check every minute
                
                if not self.running:
                    break
                
                # Check for new URLs first (highest priority)
                new_urls = self.detect_new_urls()
                
                if new_urls:
                    # New URLs detected - run pipeline immediately
                    self.last_run = datetime.now()
                    logger.info(f"Running scheduled pipeline for {len(new_urls)} new URL(s) at {self.last_run}")
                    
                    result = self.run_full_pipeline(force=True, check_new_urls=True)
                    logger.info(f"Pipeline completed: {result.get('scraping', {}).get('status', 'unknown')}")
                    logger.info(f"New URLs processed: {result.get('new_urls_detected', 0)}")
                else:
                    # No new URLs - check timestamp validation
                    should_run, latest_timestamp, next_update_time = self.should_run_pipeline()
                    
                    if should_run:
                        # Run the pipeline
                        self.last_run = datetime.now()
                        logger.info(f"Running scheduled pipeline at {self.last_run}")
                        
                        result = self.run_full_pipeline(force=True, check_new_urls=False)
                        logger.info(f"Pipeline completed: {result.get('scraping', {}).get('status', 'unknown')}")
                    else:
                        logger.info(f"Skipping scheduled run - data is still fresh")
                        if latest_timestamp:
                            logger.info(f"Latest ingestion: {latest_timestamp}")
                        if next_update_time:
                            logger.info(f"Next update scheduled: {next_update_time}")
                        # Recalculate next run based on when data actually needs update
                        if next_update_time:
                            self.next_run = next_update_time
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                # Wait a bit before retrying
                time.sleep(300)  # 5 minutes
    
    def check_if_data_exists(self) -> bool:
        """
        Check if vector DB or scraper data already exists.
        
        Returns:
            True if data exists, False otherwise
        """
        # Check vector DB for existing documents
        try:
            vector_store = ChromaVectorStore(
                collection_name=config.COLLECTION_NAME,
                db_path=config.CHROMA_DB_PATH
            )
            collection_info = vector_store.get_collection_info()
            document_count = collection_info.get("document_count", 0)
            
            if document_count > 0:
                logger.info(f"Found {document_count} document(s) in vector database")
                return True
        except Exception as e:
            logger.warning(f"Could not check vector database: {e}")
        
        # Check scraper data directory for existing files
        try:
            from pathlib import Path
            scraper_settings = self.config.get("scraper_settings", {})
            data_dir = Path(scraper_settings.get("output_dir", "data/mutual_funds"))
            
            if data_dir.exists():
                json_files = list(data_dir.rglob("*.json"))
                if len(json_files) > 0:
                    logger.info(f"Found {len(json_files)} JSON file(s) in scraper data directory")
                    return True
        except Exception as e:
            logger.warning(f"Could not check scraper data directory: {e}")
        
        logger.info("No existing data found - will run initial scraping and ingestion")
        return False
    
    def start(self):
        """Start the scheduled scraper service."""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        schedule_config = self.config.get("schedule", {})
        if not schedule_config.get("enabled", False):
            logger.info("Scheduling is disabled in config")
            return
        
        # Check if data exists before starting scheduler
        data_exists = self.check_if_data_exists()
        
        if not data_exists:
            # No data found - run pipeline immediately in main thread
            # This allows Playwright to work properly (Playwright needs main thread)
            logger.info("=" * 70)
            logger.info("No existing data found - running initial scraping and ingestion")
            logger.info("=" * 70)
            
            try:
                # Run synchronously in main thread so Playwright can work
                result = self.run_full_pipeline(force=True, check_new_urls=False)
                logger.info(f"Initial pipeline completed: {result.get('scraping', {}).get('status', 'unknown')}")
            except Exception as e:
                logger.error(f"Initial pipeline failed: {e}", exc_info=True)
                # Scheduler will retry on next interval if needed
        
        # Start the scheduler loop
        self.running = True
        self.thread = threading.Thread(target=self.scheduler_loop, daemon=True)
        self.thread.start()
        logger.info("Scheduled scraper service started")
    
    def stop(self):
        """Stop the scheduled scraper service."""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        logger.info("Scheduled scraper service stopped")
    
    def run_once(self):
        """Run scraping/ingestion once immediately."""
        return self.run_full_pipeline()


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Scheduled scraper service")
    parser.add_argument(
        "--config",
        default="scraper_config.json",
        help="Path to scraper config file"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once immediately instead of scheduling"
    )
    parser.add_argument(
        "--scrape-only",
        action="store_true",
        help="Run only scraping, skip ingestion"
    )
    parser.add_argument(
        "--ingest-only",
        action="store_true",
        help="Run only ingestion, skip scraping"
    )
    
    args = parser.parse_args()
    
    scheduler = ScheduledScraper(config_path=args.config)
    
    if args.once:
        # Run once and exit
        if args.scrape_only:
            result = scheduler.run_scraping()
        elif args.ingest_only:
            result = scheduler.run_ingestion()
        else:
            result = scheduler.run_full_pipeline()
        print(f"\nResult: {json.dumps(result, indent=2)}")
    else:
        # Start scheduler
        try:
            scheduler.start()
            logger.info("Scheduler running. Press Ctrl+C to stop.")
            # Keep main thread alive
            while scheduler.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nStopping scheduler...")
            scheduler.stop()


if __name__ == "__main__":
    main()

