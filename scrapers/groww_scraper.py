"""
Groww Mutual Fund Scraper
Extracts structured data from Groww mutual fund pages and saves to JSON.
"""

import json
import re
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# Try Playwright first (works better on cloud environments)
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Try async Playwright as fallback for Python 3.13 compatibility
try:
    from playwright.async_api import async_playwright
    import asyncio
    ASYNC_PLAYWRIGHT_AVAILABLE = True
except ImportError:
    ASYNC_PLAYWRIGHT_AVAILABLE = False

def _is_main_thread():
    """Check if we're running in the main thread."""
    return threading.current_thread() is threading.main_thread()

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class GrowwScraper:
    """Scraper for Groww mutual fund pages with dynamic content discovery."""
    
    # Configuration: Parameters to extract (can be customized)
    EXTRACTABLE_PARAMETERS = {
        "returns": ["1y", "3y", "5y", "all", "one_year", "three_year", "since_inception"],
        "advanced_ratios": ["pe_ratio", "pb_ratio", "alpha", "beta", "sharpe_ratio", "sortino_ratio", "top_5_weight_pct", "top_20_weight_pct"],
        "cost_and_tax": ["expense_ratio", "exit_load", "stamp_duty", "tax_implication"],
        "portfolio": ["top_5_holdings", "top_10_holdings", "holdings_count"],
        "category_info": ["category", "category_average_annualised", "rank_within_category"],
    }
    
    def __init__(self, output_dir: str = "data/mutual_funds", use_interactive: bool = True, 
                 download_dir: str = "data/downloaded_html", download_first: bool = False):
        self.output_dir = output_dir
        self.download_dir = download_dir
        self.use_interactive = use_interactive
        self.download_first = download_first
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        os.makedirs(self.output_dir, exist_ok=True)
        if self.download_first:
            os.makedirs(self.download_dir, exist_ok=True)
    
    def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch webpage content using Playwright first (best for cloud), then Selenium, then requests.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content as string, or None if failed
        """
        # Try Playwright first (works best on cloud environments)
        if PLAYWRIGHT_AVAILABLE:
            try:
                playwright_result = self._fetch_with_playwright(url, interactive=True)
                if playwright_result:
                    html, page_obj, browser, playwright_instance = playwright_result
                    try:
                        browser.close()
                        playwright_instance.stop()
                    except:
                        pass
                    return html
            except Exception as e:
                print(f"Playwright failed, trying alternatives: {e}")
        
        # Try requests first (fastest)
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            html = response.text
            
            # Check if page is blocked or dynamic content is missing
            if self._is_blocked_or_empty(html):
                print(f"Page appears blocked or empty, trying browser automation...")
                # Try Selenium as fallback
                selenium_html = self._fetch_with_selenium(url)
                if selenium_html:
                    return selenium_html
                return None
            
            return html
        except requests.RequestException as e:
            print(f"Request failed: {e}, trying browser automation...")
            # Try Selenium as fallback
            selenium_html = self._fetch_with_selenium(url)
            if selenium_html:
                return selenium_html
            return None
    
    def _is_blocked_or_empty(self, html: str) -> bool:
        """Check if page is blocked or has no meaningful content."""
        soup = BeautifulSoup(html, 'lxml')
        
        # Check for common blocking indicators
        if soup.find('title') and any(keyword in soup.find('title').get_text().lower() 
                                     for keyword in ['blocked', 'access denied', 'captcha']):
            return True
        
        # Check if main content exists (Groww pages typically have specific classes)
        main_content = soup.find(['main', 'div'], class_=re.compile(r'fund|scheme|details', re.I))
        if not main_content:
            # Check for common Groww page elements
            if not soup.find_all(['table', 'div'], class_=re.compile(r'nav|aum|expense|holding', re.I)):
                return True
        
        return False
    
    def _fetch_with_playwright(self, url: str, interactive: bool = True) -> Optional[tuple]:
        """
        Fetch page using Playwright (works better on cloud environments).
        
        Returns:
            Tuple of (html, page_obj, browser, playwright_context) or None if failed
        """
        if not PLAYWRIGHT_AVAILABLE:
            return None
        
        try:
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            
            # Navigate to URL
            page.goto(url, wait_until='networkidle', timeout=60000)
            
            # Wait for content to load
            import time
            time.sleep(3)
            
            # Scroll to load lazy content
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(1)
            
            # Scroll gradually
            for i in range(5):
                scroll_position = (i + 1) / 5
                page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {scroll_position})")
                time.sleep(1)
            
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            
            # Get HTML
            html = page.content()
            
            # Store playwright instance for cleanup
            playwright_instance = playwright
            
            return (html, page, browser, playwright_instance)
        except Exception as e:
            print(f"Playwright failed: {e}")
            try:
                if 'browser' in locals():
                    browser.close()
                if 'playwright' in locals():
                    playwright.stop()
            except:
                pass
            return None
    
    def _fetch_with_async_playwright(self, url: str, interactive: bool = True) -> Optional[tuple]:
        """
        Async Playwright method - kept for compatibility but not used in sync context.
        """
        # Not used in sync context - return None
        return None
    
    def _fetch_with_selenium(self, url: str) -> Optional[str]:
        """
        Fetch page using Selenium with dynamic content loading.
        Enhanced to handle lazy-loaded content similar to Playwright.
        Configured for Streamlit Cloud compatibility.
        """
        if not SELENIUM_AVAILABLE:
            print("Selenium not available. Please install it or use Playwright.")
            return None
        
        try:
            # Try to use chromedriver-autoinstaller for automatic ChromeDriver setup
            try:
                import chromedriver_autoinstaller
                chromedriver_autoinstaller.install()
            except ImportError:
                # chromedriver-autoinstaller not available, try system ChromeDriver
                pass
            except Exception as e:
                print(f"Warning: chromedriver-autoinstaller failed: {e}")
            
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-software-rasterizer')
            options.add_argument('--disable-background-timer-throttling')
            options.add_argument('--disable-backgrounding-occluded-windows')
            options.add_argument('--disable-renderer-backgrounding')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Try to find Chrome binary in common locations (for Streamlit Cloud)
            chrome_binary_paths = [
                '/usr/bin/google-chrome',
                '/usr/bin/chromium',
                '/usr/bin/chromium-browser',
                '/snap/bin/chromium',
            ]
            for chrome_path in chrome_binary_paths:
                if os.path.exists(chrome_path):
                    options.binary_location = chrome_path
                    break
            
            driver = webdriver.Chrome(options=options)
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Wait for initial content
            import time
            time.sleep(3)
            
            # Scroll to bottom to load lazy content
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Scroll back to top
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Scroll gradually to trigger lazy loading
            scroll_steps = 5
            for i in range(scroll_steps):
                scroll_position = (i + 1) / scroll_steps
                driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {scroll_position});")
                time.sleep(1)
            
            # Scroll to bottom again
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Try to click "Load More" or "View All" buttons
            try:
                button_selectors = [
                    "//button[contains(text(), 'Load More')]",
                    "//button[contains(text(), 'View All')]",
                    "//button[contains(text(), 'Show More')]",
                    "//a[contains(text(), 'View All')]",
                    "//a[contains(text(), 'Load More')]"
                ]
                for selector in button_selectors[:3]:  # Try first 3
                    try:
                        buttons = driver.find_elements(By.XPATH, selector)
                        for btn in buttons[:2]:  # Click first 2
                            try:
                                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                                time.sleep(0.5)
                                btn.click()
                                time.sleep(2)
                            except:
                                pass
                    except:
                        pass
            except Exception as e:
                print(f"Warning: Error clicking buttons: {e}")
            
            # Final scroll to ensure all content is loaded
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Scroll to top for final HTML capture
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            html = driver.page_source
            driver.quit()
            return html
        except Exception as e:
            print(f"Selenium failed: {e}")
            return None
    
    def extract_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract all tables from the page."""
        tables = []
        for table in soup.find_all('table'):
            table_data = []
            headers = []
            
            # Extract headers
            header_row = table.find('thead')
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
            else:
                # Try first row as headers
                first_row = table.find('tr')
                if first_row:
                    headers = [td.get_text(strip=True) for td in first_row.find_all(['th', 'td'])]
            
            # Extract rows
            tbody = table.find('tbody') or table
            for row in tbody.find_all('tr'):
                cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                if cells:
                    if headers:
                        table_data.append(dict(zip(headers, cells)))
                    else:
                        table_data.append(cells)
            
            if table_data:
                tables.append({
                    'headers': headers,
                    'data': table_data
                })
        
        return tables
    
    def extract_key_value_pairs(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract key-value pairs from various page structures."""
        kv_pairs = {}
        
        # Look for common patterns: dt-dd, div pairs, span pairs, etc.
        # Pattern 1: <dt>Key</dt><dd>Value</dd>
        for dt in soup.find_all('dt'):
            dd = dt.find_next_sibling('dd')
            if dd:
                key = dt.get_text(strip=True)
                value = dd.get_text(strip=True)
                kv_pairs[key.lower()] = value
        
        # Pattern 2: Divs with labels and values
        for div in soup.find_all('div', class_=re.compile(r'label|key|field', re.I)):
            key = div.get_text(strip=True)
            value_elem = div.find_next_sibling(['div', 'span', 'p'])
            if value_elem:
                value = value_elem.get_text(strip=True)
                kv_pairs[key.lower()] = value
        
        # Pattern 3: Span pairs with specific classes
        for span in soup.find_all('span', class_=re.compile(r'label|key', re.I)):
            key = span.get_text(strip=True)
            value_elem = span.find_next_sibling('span', class_=re.compile(r'value|data', re.I))
            if value_elem:
                value = value_elem.get_text(strip=True)
                kv_pairs[key.lower()] = value
        
        return kv_pairs
    
    def _clean_text(self, text: str, max_length: int = 200) -> str:
        """Clean and truncate extracted text."""
        if not text:
            return ""
        text = text.strip()
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length].rsplit(' ', 1)[0] + "..."
        return text
    
    def _extract_from_element(self, soup: BeautifulSoup, label_pattern: str, value_pattern: Optional[str] = None) -> Optional[str]:
        """Extract value from element containing label pattern."""
        # Try to find element with label
        for elem in soup.find_all(string=re.compile(label_pattern, re.I)):
            parent = elem.parent
            if parent:
                # Look for value in next sibling or parent's next sibling
                next_sib = parent.find_next_sibling()
                if next_sib:
                    text = next_sib.get_text(strip=True)
                    if value_pattern:
                        match = re.search(value_pattern, text, re.I)
                        if match:
                            return match.group(1) if match.groups() else match.group(0)
                    return self._clean_text(text, 100)
                # Or look in same element
                text = parent.get_text(strip=True)
                if value_pattern:
                    match = re.search(value_pattern, text, re.I)
                    if match:
                        return match.group(1) if match.groups() else match.group(0)
                # Extract after label
                match = re.search(f'{label_pattern}[:\\s]+(.+?)(?:\\n|$)', text, re.I)
                if match:
                    return self._clean_text(match.group(1), 100)
        return None
    
    def extract_detailed_data(self, soup: BeautifulSoup, page_text: str, page_obj=None) -> Dict[str, Any]:
        """Extract all detailed fund data matching the required JSON structure."""
        data = {}
        
        # Extract fund name (clean version without extra text)
        fund_name_elem = soup.find('title') or soup.find('h1')
        fund_name = ""
        if fund_name_elem:
            fund_name = fund_name_elem.get_text(strip=True)
            # Clean up: remove " - NAV, Mutual Fund Performance & Portfolio"
            fund_name = re.sub(r'\s*-\s*NAV.*$', '', fund_name, flags=re.I)
        data["fund_name"] = fund_name
        
        # Extract NAV with date
        nav_value = None
        nav_date = None
        nav_elem = soup.find(string=re.compile(r'Latest NAV|Current NAV|NAV.*as of', re.I))
        if nav_elem:
            parent_text = nav_elem.parent.get_text() if nav_elem.parent else ""
            nav_match = re.search(r'as of\s+(\d+\s+\w+\s+\d+).*?₹\s*([\d,]+\.?\d{2,})', parent_text, re.I)
            if nav_match:
                nav_date = nav_match.group(1)
                nav_value = "₹" + nav_match.group(2).replace(',', '')
        
        if not nav_value:
            nav_match = re.search(r'Latest NAV.*?as of\s+(\d+\s+\w+\s+\d+).*?₹\s*([\d,]+\.?\d{2,})', page_text, re.I)
            if nav_match:
                nav_date = nav_match.group(1)
                nav_candidate = nav_match.group(2).replace(',', '')
                try:
                    if 1 <= float(nav_candidate) <= 10000:
                        nav_value = "₹" + nav_candidate
                except:
                    pass
        
        data["nav"] = {
            "value": nav_value or "",
            "as_of": nav_date or ""
        }
        
        # Extract Fund Size from start/top of page (separate from AUM)
        fund_size_value = None
        
        # Method 1: Extract Fund Size from top of page using page_obj
        if page_obj:
            try:
                fund_size_text = page_obj.evaluate("""
                    () => {
                        // Get text from top portion of page (first 30% of scroll height)
                        const viewportHeight = window.innerHeight;
                        const topSectionHeight = Math.min(viewportHeight * 3, document.body.scrollHeight * 0.3);
                        
                        // Get all elements in top section
                        const allElements = Array.from(document.querySelectorAll('*'));
                        let topText = '';
                        
                        for (let el of allElements) {
                            const rect = el.getBoundingClientRect();
                            const elY = rect.top + window.scrollY;
                            
                            if (elY <= topSectionHeight) {
                                const text = el.textContent || '';
                                if (text.includes('Fund Size') && !text.includes('Fund Objective')) {
                                    topText += ' ' + text;
                                }
                            }
                        }
                        
                        return topText;
                    }
                """)
                
                # Look for Fund Size pattern (not AUM)
                fund_size_patterns = [
                    r'Fund Size[:\s]+₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore)',
                    r'₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore).*?Fund Size',
                ]
                for pattern in fund_size_patterns:
                    fund_size_match = re.search(pattern, fund_size_text, re.I)
                    if fund_size_match:
                        fund_size_num = fund_size_match.group(1).replace(',', '')
                        try:
                            fund_size_float = float(fund_size_num)
                            if 1 <= fund_size_float <= 100000:
                                fund_size_formatted = f"{fund_size_float:,.2f}".rstrip('0').rstrip('.')
                                fund_size_value = f"₹{fund_size_formatted}Cr"
                                break
                        except:
                            pass
            except:
                pass
        
        # Method 2: Extract Fund Size from soup (top sections)
        if not fund_size_value:
            # Look in header/top sections first
            top_sections = soup.find_all(['div', 'section', 'header'], limit=20)
            for section in top_sections[:10]:  # Check first 10 top sections
                section_text = section.get_text()
                # Look for Fund Size (not AUM) in top sections
                fund_size_match = re.search(r'Fund Size[:\s]+₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore)', section_text, re.I)
                if fund_size_match and 'Fund Objective' not in section_text:
                    fund_size_num = fund_size_match.group(1).replace(',', '')
                    try:
                        fund_size_float = float(fund_size_num)
                        if 1 <= fund_size_float <= 100000:
                            fund_size_formatted = f"{fund_size_float:,.2f}".rstrip('0').rstrip('.')
                            fund_size_value = f"₹{fund_size_formatted}Cr"
                            break
                    except:
                        pass
        
        # Method 3: Fallback - look for Fund Size in first part of page text
        if not fund_size_value:
            # Get first 30% of page text
            first_part = page_text[:len(page_text)//3] if len(page_text) > 100 else page_text
            fund_size_match = re.search(r'Fund Size[:\s]+₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore)', first_part, re.I)
            if fund_size_match:
                fund_size_num = fund_size_match.group(1).replace(',', '')
                try:
                    fund_size_float = float(fund_size_num)
                    if 1 <= fund_size_float <= 100000:
                        fund_size_formatted = f"{fund_size_float:,.2f}".rstrip('0').rstrip('.')
                        fund_size_value = f"₹{fund_size_formatted}Cr"
                except:
                    pass
        
        data["fund_size"] = fund_size_value or ""
        
        # Extract AUM from Fund Objective section specifically (separate from Fund Size)
        # Use downloaded HTML for better extraction if available
        aum_value = None
        
        # Method 1: Extract AUM from Fund Objective section using page_obj (with better scrolling)
        if page_obj:
            try:
                # Scroll through page to load all content, especially Fund Objective section
                page_obj.evaluate("window.scrollTo(0, 0)")  # Start from top
                page_obj.wait_for_timeout(500)
                
                # Scroll down gradually to find Fund Objective section
                scroll_steps = 5
                for i in range(scroll_steps):
                    scroll_position = (i + 1) * (1.0 / scroll_steps)
                    page_obj.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {scroll_position})")
                    page_obj.wait_for_timeout(800)
                
                # Scroll to find Fund Objective section specifically
                page_obj.evaluate("""
                    () => {
                        // Try to scroll to Fund Objective section
                        const objectiveHeaders = Array.from(document.querySelectorAll('h2, h3, h4, h5, h6, div, section'));
                        for (let el of objectiveHeaders) {
                            const text = (el.textContent || '').toLowerCase();
                            if (text.includes('fund objective') || text.includes('investment objective')) {
                                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                break;
                            }
                        }
                    }
                """)
                page_obj.wait_for_timeout(1500)  # Wait longer for content to load
                
                objective_aum = page_obj.evaluate("""
                    () => {
                        // Find Fund Objective section - multiple strategies
                        let objectiveSection = null;
                        
                        // Strategy 1: Look for headers with "Fund Objective" or "Investment Objective"
                        const headers = Array.from(document.querySelectorAll('h2, h3, h4, h5, h6'));
                        for (let header of headers) {
                            const text = (header.textContent || '').toLowerCase();
                            if (text.includes('fund objective') || text.includes('investment objective')) {
                                // Find parent container
                                objectiveSection = header.closest('div, section, article, main') || header.parentElement;
                                break;
                            }
                        }
                        
                        // Strategy 2: Look for divs/sections with objective-related classes
                        if (!objectiveSection) {
                            const sections = Array.from(document.querySelectorAll('[class*="objective"], [class*="Objective"], [id*="objective"], [id*="Objective"]'));
                            for (let section of sections) {
                                const text = (section.textContent || '').toLowerCase();
                                if (text.includes('fund objective') || text.includes('investment objective')) {
                                    objectiveSection = section;
                                    break;
                                }
                            }
                        }
                        
                        // Strategy 3: Search all elements for objective text
                        if (!objectiveSection) {
                            const allElements = Array.from(document.querySelectorAll('*'));
                            for (let el of allElements) {
                                const text = (el.textContent || '').toLowerCase();
                                if ((text.includes('fund objective') || text.includes('investment objective')) && 
                                    text.length < 200) {  // Avoid matching entire page
                                    objectiveSection = el.closest('div, section, article') || el.parentElement;
                                    break;
                                }
                            }
                        }
                        
                        if (objectiveSection) {
                            // Look for AUM specifically in this section (not Fund Size)
                            const sectionText = objectiveSection.textContent || '';
                            
                            // Try multiple AUM patterns - more comprehensive
                            const aumPatterns = [
                                /AUM[:\\s]+₹\\s*([\\d,]+\\.?\\d*)\\s*(?:Cr|Crore)/i,
                                /Assets Under Management[:\\s]+₹\\s*([\\d,]+\\.?\\d*)\\s*(?:Cr|Crore)/i,
                                /Assets Under Management[:\\s]+([\\d,]+\\.?\\d*)\\s*(?:Cr|Crore)/i,
                                /₹\\s*([\\d,]+\\.?\\d*)\\s*(?:Cr|Crore).*?AUM/i,
                                /AUM[:\\.\\s]+([\\d,]+\\.?\\d*)\\s*(?:Cr|Crore)/i,
                                /([\\d,]+\\.?\\d*)\\s*(?:Cr|Crore).*?Assets Under Management/i
                            ];
                            
                            for (let pattern of aumPatterns) {
                                const aumMatch = sectionText.match(pattern);
                                if (aumMatch) {
                                    return aumMatch[1];
                                }
                            }
                            
                            // Also check child elements for AUM
                            const children = objectiveSection.querySelectorAll('*');
                            for (let child of children) {
                                const childText = child.textContent || '';
                                if (childText.includes('AUM') || childText.includes('Assets Under Management')) {
                                    if (!childText.includes('Fund Size')) {
                                        for (let pattern of aumPatterns) {
                                            const match = childText.match(pattern);
                                            if (match) {
                                                return match[1];
                                            }
                                        }
                                    }
                                }
                            }
                            
                            // Check parent and siblings too
                            if (objectiveSection.parentElement) {
                                const parentText = objectiveSection.parentElement.textContent || '';
                                for (let pattern of aumPatterns) {
                                    const match = parentText.match(pattern);
                                    if (match) {
                                        return match[1];
                                    }
                                }
                            }
                        }
                        return null;
                    }
                """)
                
                if objective_aum:
                    try:
                        aum_num = str(objective_aum).replace(',', '')
                        aum_float = float(aum_num)
                        if 0.1 <= aum_float <= 1000000:  # More lenient range
                            aum_formatted = f"{aum_float:,.2f}".rstrip('0').rstrip('.')
                            aum_value = f"₹{aum_formatted}Cr"
                    except Exception as e:
                        print(f"Error parsing AUM value '{objective_aum}': {e}")
            except Exception as e:
                print(f"Error extracting AUM from Fund Objective: {e}")
        
        # Method 2: Extract from downloaded HTML file if available (more reliable)
        # This will be used when download_first=True
        if not aum_value:
            # Look for Fund Objective section in soup and extract AUM
            objective_sections = soup.find_all(['div', 'section', 'article'], string=re.compile(r'Fund Objective|Investment Objective', re.I))
            if not objective_sections:
                # Try finding by class/id
                objective_sections = soup.find_all(['div', 'section'], class_=re.compile(r'objective|Objective', re.I))
            
            for section in objective_sections:
                # Check parent and siblings
                parent = section.parent if section.parent else section
                section_text = parent.get_text()
                
                # Look specifically for AUM (not Fund Size) in Fund Objective section
                # Try multiple patterns
                aum_patterns = [
                    r'AUM[:\s]+₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore)',
                    r'Assets Under Management[:\s]+₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore)',
                    r'Assets Under Management[:\s]+([\d,]+\.?\d*)\s*(?:Cr|Crore)',
                    r'AUM[:\s]+([\d,]+\.?\d*)\s*(?:Cr|Crore)',
                    r'₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore).*?AUM',
                    r'([\d,]+\.?\d*)\s*(?:Cr|Crore).*?Assets Under Management',
                ]
                
                for pattern in aum_patterns:
                    aum_match = re.search(pattern, section_text, re.I)
                    if aum_match:
                        aum_num = aum_match.group(1).replace(',', '')
                        try:
                            aum_float = float(aum_num)
                            if 0.1 <= aum_float <= 1000000:  # More lenient range
                                aum_formatted = f"{aum_float:,.2f}".rstrip('0').rstrip('.')
                                aum_value = f"₹{aum_formatted}Cr"
                                break
                        except:
                            pass
                if aum_value:
                    break
        
        # Method 3: Last resort - search entire page text for AUM in context of Fund Objective
        if not aum_value:
            # Find position of "Fund Objective" in page text
            objective_pos = page_text.lower().find('fund objective')
            if objective_pos >= 0:
                # Get text around Fund Objective section (next 2000 characters)
                objective_context = page_text[objective_pos:objective_pos + 2000]
                aum_patterns = [
                    r'AUM[:\s]+₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore)',
                    r'Assets Under Management[:\s]+₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore)',
                    r'AUM[:\s]+([\d,]+\.?\d*)\s*(?:Cr|Crore)',
                ]
                for pattern in aum_patterns:
                    aum_match = re.search(pattern, objective_context, re.I)
                    if aum_match:
                        aum_num = aum_match.group(1).replace(',', '')
                        try:
                            aum_float = float(aum_num)
                            if 0.1 <= aum_float <= 1000000:
                                aum_formatted = f"{aum_float:,.2f}".rstrip('0').rstrip('.')
                                aum_value = f"₹{aum_formatted}Cr"
                                break
                        except:
                            pass
        
        data["aum"] = aum_value or ""
        
        # Extract FAQ questions from bottom of page
        faq_questions = []
        if page_obj:
            try:
                # Scroll to bottom multiple times to ensure FAQ section loads
                for _ in range(3):
                    page_obj.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page_obj.wait_for_timeout(1500)
                
                # Try clicking "Load More" or "Show More" buttons if present
                try:
                    load_more_buttons = page_obj.query_selector_all('button:has-text("Load More"), button:has-text("Show More"), button:has-text("View More")')
                    for btn in load_more_buttons[:2]:  # Click first 2
                        try:
                            btn.click()
                            page_obj.wait_for_timeout(1000)
                        except:
                            pass
                except:
                    pass
                
                # Extract FAQ questions
                faqs = page_obj.evaluate("""
                    () => {
                        const faqs = [];
                        
                        // Strategy 1: Look for FAQ section by text content
                        const allElements = Array.from(document.querySelectorAll('*'));
                        let faqSection = null;
                        
                        // Find FAQ section header
                        for (let el of allElements) {
                            const text = (el.textContent || '').toLowerCase();
                            if ((text.includes('frequently asked') || text.includes('faq')) && 
                                (el.tagName === 'H2' || el.tagName === 'H3' || el.tagName === 'H4')) {
                                // Find parent container
                                faqSection = el.closest('div, section, article, main') || el.parentElement;
                                break;
                            }
                        }
                        
                        // Strategy 2: Look for accordion/expandable sections at bottom
                        if (!faqSection) {
                            const accordions = document.querySelectorAll('[class*="accordion"], [class*="Accordion"], [class*="collapse"], [class*="Collapse"], details, summary');
                            if (accordions.length > 0) {
                                faqSection = accordions[0].closest('div, section, article') || accordions[0].parentElement;
                            }
                        }
                        
                        // Strategy 3: Look for question patterns in last 30% of page
                        if (!faqSection) {
                            const bodyHeight = document.body.scrollHeight;
                            const viewportHeight = window.innerHeight;
                            const startY = Math.max(0, bodyHeight * 0.7);
                            
                            for (let el of allElements) {
                                const rect = el.getBoundingClientRect();
                                const elY = rect.top + window.scrollY;
                                
                                if (elY >= startY) {
                                    const text = (el.textContent || '').trim();
                                    if (text.includes('?') && text.length > 15 && text.length < 200) {
                                        // Check if it starts with question words
                                        const questionWords = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'can', 'is', 'are', 'does', 'do'];
                                        const firstWord = text.toLowerCase().split(/[\\s?]/)[0];
                                        if (questionWords.includes(firstWord)) {
                                            faqSection = el.closest('div, section, article') || el.parentElement;
                                            break;
                                        }
                                    }
                                }
                            }
                        }
                        
                        if (faqSection) {
                            // Find all potential question elements
                            const questionSelectors = [
                                'h3', 'h4', 'h5', 'h6',
                                'button[aria-expanded]',
                                'summary',
                                '[class*="question"]',
                                '[class*="Question"]',
                                '[class*="faq"]',
                                '[class*="FAQ"]',
                                '[role="button"]'
                            ];
                            
                            const foundQuestions = new Set();
                            
                            for (let selector of questionSelectors) {
                                try {
                                    const elements = faqSection.querySelectorAll(selector);
                                    for (let q of elements) {
                                        const qText = (q.textContent || '').trim().replace(/\\s+/g, ' ');
                                        
                                        // Validate it's a question
                                        if (qText.includes('?') && 
                                            qText.length > 10 && 
                                            qText.length < 250 &&
                                            !foundQuestions.has(qText)) {
                                            
                                            foundQuestions.add(qText);
                                            
                                            // Try to find answer
                                            let answer = '';
                                            
                                            // Check next sibling
                                            let nextEl = q.nextElementSibling;
                                            if (nextEl) {
                                                answer = (nextEl.textContent || '').trim();
                                            }
                                            
                                            // Check parent's next sibling
                                            if (!answer && q.parentElement) {
                                                nextEl = q.parentElement.nextElementSibling;
                                                if (nextEl) {
                                                    answer = (nextEl.textContent || '').trim();
                                                }
                                            }
                                            
                                            // Extract from parent text
                                            if (!answer && q.parentElement) {
                                                const parentText = q.parentElement.textContent || '';
                                                const qIndex = parentText.indexOf(qText);
                                                if (qIndex >= 0) {
                                                    answer = parentText.substring(qIndex + qText.length).trim();
                                                    // Remove next question if present
                                                    const nextQIndex = answer.indexOf('?');
                                                    if (nextQIndex > 0) {
                                                        answer = answer.substring(0, nextQIndex).trim();
                                                    }
                                                    // Take first few sentences
                                                    answer = answer.split(/[.!?]/).slice(0, 3).join('. ').trim();
                                                }
                                            }
                                            
                                            faqs.push({
                                                question: qText,
                                                answer: answer.substring(0, 500).trim() || ''
                                            });
                                            
                                            if (faqs.length >= 10) break;
                                        }
                                    }
                                    if (faqs.length > 0) break;
                                } catch(e) {
                                    console.error('Error with selector ' + selector + ':', e);
                                }
                            }
                        }
                        
                        return faqs;
                    }
                """)
                
                if faqs:
                    faq_questions = faqs if isinstance(faqs, list) else []
            except Exception as e:
                print(f"Error extracting FAQs: {e}")
                import traceback
                traceback.print_exc()
        
        # Fallback: Extract FAQs from soup
        if not faq_questions:
            try:
                # Look for FAQ section
                faq_section = soup.find(['div', 'section'], class_=re.compile(r'faq', re.I))
                if not faq_section:
                    # Look for elements containing FAQ text
                    faq_headers = soup.find_all(['h2', 'h3', 'h4'], string=re.compile(r'FAQ|Frequently Asked', re.I))
                    if faq_headers:
                        faq_section = faq_headers[0].find_parent(['div', 'section'])
                
                if faq_section:
                    # Find question elements
                    questions = faq_section.find_all(['h3', 'h4', 'h5', 'button', 'summary', 'div'], 
                                                     class_=re.compile(r'question|faq-item|accordion', re.I))
                    
                    for q in questions[:10]:  # Limit to 10
                        q_text = q.get_text(strip=True)
                        if '?' in q_text and 10 < len(q_text) < 200:
                            # Try to find answer
                            answer = ''
                            next_sib = q.find_next_sibling()
                            if next_sib:
                                answer = next_sib.get_text(strip=True)
                            if not answer:
                                parent = q.parent
                                if parent:
                                    parent_text = parent.get_text(strip=True)
                                    q_index = parent_text.find(q_text)
                                    if q_index >= 0:
                                        answer = parent_text[q_index + len(q_text):].strip()
                                        # Take first few sentences
                                        answer = '. '.join(answer.split('.')[:3]).strip()
                            
                            faq_questions.append({
                                "question": q_text,
                                "answer": answer[:500] if answer else ""
                            })
            except Exception as e:
                print(f"Error extracting FAQs from soup: {e}")
        
        data["faq"] = faq_questions
        
        # Extract summary
        summary = {}
        
        # Fund category
        category_value = None
        category_elem = soup.find(string=re.compile(r'Category|Fund Category', re.I))
        if category_elem:
            parent_text = category_elem.parent.get_text() if category_elem.parent else ""
            category_match = re.search(r'Category[:\s]+([A-Z][^\n]{5,40}?)(?:\s|$)', parent_text, re.I)
            if category_match:
                category_value = self._clean_text(category_match.group(1), 50)
        
        if not category_value:
            category_match = re.search(r'Category[:\s]+([A-Z][^\n]{5,40}?)(?:\s|$)', page_text, re.I)
            if category_match:
                category_value = self._clean_text(category_match.group(1), 50)
        
        summary["fund_category"] = category_value or ""
        
        # Fund type (extract from category or fund name)
        fund_type = ""
        if "ELSS" in fund_name.upper():
            fund_type = "ELSS"
        elif "Large Cap" in fund_name:
            fund_type = "Large Cap"
        elif "Flexi Cap" in fund_name:
            fund_type = "Flexi Cap"
        elif "Mid Cap" in fund_name:
            fund_type = "Mid Cap"
        elif "Small Cap" in fund_name:
            fund_type = "Small Cap"
        summary["fund_type"] = fund_type
        
        # Risk level - try multiple extraction methods including page_obj
        risk_value = None
        
        # Method 1: Extract from page_obj if available (Playwright)
        if page_obj:
            try:
                risk_text = page_obj.evaluate("""
                    () => {
                        // Look for risk-related elements
                        const riskElements = document.querySelectorAll('[class*="risk"], [class*="Risk"], [id*="risk"], [id*="Risk"]');
                        let text = '';
                        riskElements.forEach(el => {
                            text += ' ' + el.textContent;
                        });
                        return document.body.innerText + ' ' + text;
                    }
                """)
                
                risk_patterns = [
                    r'Risk Level[:\s]+(Very High Risk|High Risk|Moderate Risk|Low Risk)',
                    r'Riskometer[:\s]+(Very High Risk|High Risk|Moderate Risk|Low Risk)',
                    r'Category.*?Risk[:\s]+(Very High Risk|High Risk|Moderate Risk|Low Risk)',
                    r'(Very High Risk|High Risk|Moderate Risk|Low Risk)',
                ]
                for pattern in risk_patterns:
                    risk_match = re.search(pattern, risk_text, re.I)
                    if risk_match:
                        risk_value = risk_match.group(1)
                        if "Risk" not in risk_value:
                            risk_value = risk_value + " Risk"
                        break
            except Exception as e:
                print(f"Error extracting risk level from page: {e}")
        
        # Method 2: Look for riskometer or risk level text in soup
        if not risk_value:
            risk_elem = soup.find(string=re.compile(r'Risk|Riskometer|Very High|High|Moderate|Low', re.I))
            if risk_elem:
                parent = risk_elem.parent
                # Get broader context
                while parent and len(parent.get_text()) < 200:
                    parent = parent.parent
                parent_text = parent.get_text() if parent else ""
                
                # Try to find risk level patterns
                risk_patterns = [
                    r'Risk Level[:\s]+(Very High Risk|High Risk|Moderate Risk|Low Risk)',
                    r'Riskometer[:\s]+(Very High Risk|High Risk|Moderate Risk|Low Risk)',
                    r'(Very High Risk|High Risk|Moderate Risk|Low Risk)',
                    r'Risk[:\s]+(Very High|High|Moderate|Low)',
                ]
                for pattern in risk_patterns:
                    risk_match = re.search(pattern, parent_text, re.I)
                    if risk_match:
                        risk_value = risk_match.group(1)
                        if "Risk" not in risk_value:
                            risk_value = risk_value + " Risk"
                        break
        
        # Method 3: Look in Pros/Cons section
        if not risk_value:
            pros_cons = soup.find(string=re.compile(r'Pros and cons|Risk', re.I))
            if pros_cons:
                parent_text = pros_cons.parent.get_text() if pros_cons.parent else ""
                risk_match = re.search(r'(Very High Risk|High Risk|Moderate Risk|Low Risk)', parent_text, re.I)
                if risk_match:
                    risk_value = risk_match.group(1)
        
        # Method 4: Regex on full page
        if not risk_value:
            risk_patterns = [
                r'Risk Level[:\s]+(Very High Risk|High Risk|Moderate Risk|Low Risk)',
                r'Category.*?Risk[:\s]+(Very High|High|Moderate|Low)',
                r'Category[:\s]+Equity.*?Risk[:\s]+(Very High|High|Moderate|Low)',
            ]
            for pattern in risk_patterns:
                risk_match = re.search(pattern, page_text, re.I)
                if risk_match:
                    risk_value = risk_match.group(1)
                    if "Risk" not in risk_value:
                        risk_value = risk_value + " Risk"
                    break
        
        # Method 5: Look for riskometer visual indicators or risk rating
        if not risk_value:
            # Look for riskometer scale indicators (1-5 scale)
            riskometer_elem = soup.find_all(['div', 'span', 'svg'], class_=re.compile(r'risk|riskometer', re.I))
            for elem in riskometer_elem:
                elem_text = elem.get_text()
                # Check for risk level text near riskometer
                risk_match = re.search(r'(Very High Risk|High Risk|Moderate Risk|Low Risk)', elem_text, re.I)
                if risk_match:
                    risk_value = risk_match.group(1)
                    break
        
        # Method 6: Infer from fund category
        if not risk_value:
            if "ELSS" in fund_name.upper() or "Equity" in summary.get("fund_category", ""):
                risk_value = "Very High Risk"
            elif "Debt" in summary.get("fund_category", "") or "Bond" in summary.get("fund_category", ""):
                risk_value = "Low Risk"
            elif "Hybrid" in summary.get("fund_category", ""):
                risk_value = "Moderate Risk"
        
        summary["risk_level"] = risk_value or ""
        
        # Lock-in period - improved extraction
        lockin_value = None
        
        # Method 1: Check fund name first (ELSS funds typically have 3 years)
        if "ELSS" in fund_name.upper():
            lockin_value = "3 years"
        
        # Method 2: Look for lock-in in various formats
        if not lockin_value:
            lockin_patterns = [
                r'Lock-in[:\s]+(\d+)\s*(?:years?|Y|year)',
                r'Lock In[:\s]+(\d+)\s*(?:years?|Y|year)',
                r'Lock-in Period[:\s]+(\d+)\s*(?:years?|Y|year)',
                r'Lock-in period[:\s]+(\d+)\s*(?:years?|Y|year)',
                r'(\d+)\s*years?\s*lock-in',
                r'(\d+)\s*years?\s*lock',
            ]
            for pattern in lockin_patterns:
                lockin_match = re.search(pattern, page_text, re.I)
                if lockin_match:
                    years = lockin_match.group(1)
                    lockin_value = f"{years} years"
                    break
        
        # Method 3: Look in specific HTML elements
        if not lockin_value:
            lockin_elem = soup.find(string=re.compile(r'Lock-in|Lock In|Lock-in period', re.I))
            if lockin_elem:
                # Get parent and siblings for context
                parent = lockin_elem.parent
                if parent:
                    # Check parent and next siblings
                    context_text = parent.get_text()
                    # Also check next sibling
                    next_sibling = parent.find_next_sibling()
                    if next_sibling:
                        context_text += " " + next_sibling.get_text()
                    
                    lockin_match = re.search(r'(\d+)\s*(?:years?|Y|year)', context_text, re.I)
                    if lockin_match:
                        years = lockin_match.group(1)
                        lockin_value = f"{years} years"
        
        summary["lock_in_period"] = lockin_value or ""
        
        # Rating (extract from page if available)
        rating = None
        rating_elem = soup.find(string=re.compile(r'Rating|Star', re.I))
        if rating_elem:
            parent_text = rating_elem.parent.get_text() if rating_elem.parent else ""
            rating_match = re.search(r'(\d+)', parent_text)
            if rating_match:
                try:
                    rating = int(rating_match.group(1))
                    if rating > 5:
                        rating = None
                except:
                    pass
        
        summary["rating"] = rating
        
        data["summary"] = summary
        
        # Extract minimum investments - improved extraction
        min_investments = {}
        
        # Use page_obj for comprehensive extraction
        if page_obj:
            try:
                invest_text = page_obj.evaluate("""
                    () => {
                        let text = document.body.innerText;
                        const investSections = document.querySelectorAll('[class*="investment"], [class*="minimum"], [class*="sip"]');
                        investSections.forEach(section => {
                            text += ' ' + section.innerText;
                        });
                        return text;
                    }
                """)
                
                # Extract Min SIP
                sip_match = re.search(r'Min(?:imum)?\s*SIP[:\s]+₹\s*([\d,]+)', invest_text, re.I)
                if sip_match:
                    min_investments["min_sip"] = "₹" + sip_match.group(1)
                
                # Extract First Investment
                first_match = re.search(r'(?:First|1st|Initial)\s*(?:Investment|Amount)[:\s]+₹\s*([\d,]+)', invest_text, re.I)
                if first_match:
                    min_investments["min_first_investment"] = "₹" + first_match.group(1)
                
                # Extract Subsequent Investment (2nd investment onwards)
                subsequent_match = re.search(r'(?:Subsequent|2nd|Additional)\s*(?:Investment|Amount)[:\s]+₹\s*([\d,]+)', invest_text, re.I)
                if subsequent_match:
                    min_investments["min_2nd_investment_onwards"] = "₹" + subsequent_match.group(1)
            except:
                pass
        
        # Fallback: Extract from soup
        # Min SIP
        if not min_investments.get("min_sip"):
            sip_value = None
            sip_elem = soup.find(string=re.compile(r'Min.*SIP|SIP.*Amount|Minimum.*SIP', re.I))
            if sip_elem:
                parent = sip_elem.parent
                for elem in [parent] + (parent.find_next_siblings() if parent else []):
                    text = elem.get_text() if elem else ""
                    sip_match = re.search(r'₹\s*([\d,]+)', text)
                    if sip_match:
                        sip_value = "₹" + sip_match.group(1)
                        break
            
            if not sip_value:
                sip_match = re.search(r'Min(?:imum)?\s*SIP[:\s]+₹\s*([\d,]+)', page_text, re.I)
                if not sip_match:
                    sip_match = re.search(r'SIP[:\s]+₹\s*([\d,]+)', page_text, re.I)
                if sip_match:
                    sip_value = "₹" + sip_match.group(1)
            
            min_investments["min_sip"] = sip_value or ""
        
        # First Investment
        if not min_investments.get("min_first_investment"):
            first_value = None
            first_elem = soup.find(string=re.compile(r'First|1st|Initial.*Investment', re.I))
            if first_elem:
                parent = first_elem.parent
                for elem in [parent] + (parent.find_next_siblings() if parent else []):
                    text = elem.get_text() if elem else ""
                    first_match = re.search(r'₹\s*([\d,]+)', text)
                    if first_match:
                        first_value = "₹" + first_match.group(1)
                        break
            
            if not first_value:
                first_match = re.search(r'(?:First|1st|Initial)\s*(?:Investment|Amount)[:\s]+₹\s*([\d,]+)', page_text, re.I)
                if first_match:
                    first_value = "₹" + first_match.group(1)
            
            min_investments["min_first_investment"] = first_value or min_investments.get("min_sip", "")
        
        # Subsequent Investment
        if not min_investments.get("min_subsequent_investment"):
            subsequent_value = None
            subsequent_elem = soup.find(string=re.compile(r'Subsequent|2nd|Additional.*Investment', re.I))
            if subsequent_elem:
                parent = subsequent_elem.parent
                for elem in [parent] + (parent.find_next_siblings() if parent else []):
                    text = elem.get_text() if elem else ""
                    subsequent_match = re.search(r'₹\s*([\d,]+)', text)
                    if subsequent_match:
                        subsequent_value = "₹" + subsequent_match.group(1)
                        break
            
            if not subsequent_value:
                subsequent_match = re.search(r'(?:Subsequent|2nd|Additional)\s*(?:Investment|Amount)[:\s]+₹\s*([\d,]+)', page_text, re.I)
                if subsequent_match:
                    subsequent_value = "₹" + subsequent_match.group(1)
            
            min_investments["min_2nd_investment_onwards"] = subsequent_value or min_investments.get("min_sip", "")
        
        data["minimum_investments"] = min_investments
        
        # Extract all tables once for reuse
        tables = self.extract_tables(soup)
        
        # Extract returns - improved table-based extraction
        returns_data = {}
        annualised = {}
        
        # Method 1: Extract from returns table
        for table in tables:
            table_str = str(table).lower()
            if 'return' in table_str or '1y' in table_str or '3y' in table_str:
                headers = table.get('headers', [])
                data_rows = table.get('data', [])
                
                # Find column indices
                col_1y = None
                col_3y = None
                col_5y = None
                col_all = None
                row_fund = None
                
                for i, header in enumerate(headers):
                    header_lower = str(header).lower()
                    if '1y' in header_lower or '1 year' in header_lower:
                        col_1y = i
                    elif '3y' in header_lower or '3 year' in header_lower:
                        col_3y = i
                    elif '5y' in header_lower or '5 year' in header_lower:
                        col_5y = i
                    elif 'all' in header_lower:
                        col_all = i
                
                # Find "Fund returns" row
                for row in data_rows:
                    if isinstance(row, dict):
                        row_text = ' '.join(str(v).lower() for v in row.values())
                        if 'fund return' in row_text:
                            row_fund = row
                            break
                    elif isinstance(row, list):
                        row_text = ' '.join(str(v).lower() for v in row)
                        if 'fund return' in row_text:
                            row_fund = row
                            break
                
                # Extract values
                if row_fund:
                    if isinstance(row_fund, dict):
                        for key, value in row_fund.items():
                            key_lower = str(key).lower()
                            value_str = str(value).strip()
                            if col_1y is not None and ('1y' in key_lower or '1 year' in key_lower):
                                match = re.search(r'([\d.]+)\s*%', value_str)
                                if match:
                                    annualised["1y"] = match.group(1) + "%"
                            elif col_3y is not None and ('3y' in key_lower or '3 year' in key_lower):
                                match = re.search(r'([\d.]+)\s*%', value_str)
                                if match:
                                    annualised["3y"] = match.group(1) + "%"
                            elif col_5y is not None and ('5y' in key_lower or '5 year' in key_lower):
                                match = re.search(r'([\d.]+)\s*%', value_str)
                                if match:
                                    annualised["5y"] = match.group(1) + "%"
                            elif col_all is not None and 'all' in key_lower:
                                match = re.search(r'([\d.]+)\s*%', value_str)
                                if match:
                                    annualised["all"] = match.group(1) + "%"
                    elif isinstance(row_fund, list) and len(row_fund) > 0:
                        if col_1y is not None and col_1y < len(row_fund):
                            match = re.search(r'([\d.]+)\s*%', str(row_fund[col_1y]))
                            if match:
                                annualised["1y"] = match.group(1) + "%"
                        if col_3y is not None and col_3y < len(row_fund):
                            match = re.search(r'([\d.]+)\s*%', str(row_fund[col_3y]))
                            if match:
                                annualised["3y"] = match.group(1) + "%"
                        if col_5y is not None and col_5y < len(row_fund):
                            match = re.search(r'([\d.]+)\s*%', str(row_fund[col_5y]))
                            if match:
                                annualised["5y"] = match.group(1) + "%"
                        if col_all is not None and col_all < len(row_fund):
                            match = re.search(r'([\d.]+)\s*%', str(row_fund[col_all]))
                            if match:
                                annualised["all"] = match.group(1) + "%"
        
        # Method 2: Regex on structured text
        if not annualised.get("1y") or not annualised.get("3y"):
            returns_section = soup.find(string=re.compile(r'Annualised returns|Fund returns', re.I))
            if returns_section:
                parent = returns_section.parent
                while parent and len(parent.get_text()) < 1000:
                    parent = parent.parent
                parent_text = parent.get_text() if parent else ""
                
                # Try pattern: Fund returns 6.9% 18.2% 22.4% 14.7%
                fund_returns_match = re.search(r'Fund returns\s+([\d.]+)%\s+([\d.]+)%\s+([\d.]+)%\s+([\d.]+)%', parent_text, re.I)
                if fund_returns_match:
                    if not annualised.get("1y"):
                        annualised["1y"] = fund_returns_match.group(1) + "%"
                    if not annualised.get("3y"):
                        annualised["3y"] = fund_returns_match.group(2) + "%"
                    if not annualised.get("5y"):
                        annualised["5y"] = fund_returns_match.group(3) + "%"
                    if not annualised.get("all"):
                        annualised["all"] = fund_returns_match.group(4) + "%"
        
        # Method 3: Fallback regex on full page text
        if not annualised.get("1y"):
            match = re.search(r'Fund returns.*?1\s*Y[:\s]+([\d.]+)\s*%', page_text, re.I)
            if not match:
                match = re.search(r'1\s*Y[:\s]+([\d.]+)\s*%', page_text, re.I)
            if match:
                annualised["1y"] = match.group(1) + "%"
        
        if not annualised.get("3y"):
            match = re.search(r'Fund returns.*?3\s*Y[:\s]+([\d.]+)\s*%', page_text, re.I)
            if not match:
                match = re.search(r'3\s*Y[:\s]+([\d.]+)\s*%', page_text, re.I)
            if match:
                annualised["3y"] = match.group(1) + "%"
        
        if not annualised.get("5y"):
            match = re.search(r'Fund returns.*?5\s*Y[:\s]+([\d.]+)\s*%', page_text, re.I)
            if not match:
                match = re.search(r'5\s*Y[:\s]+([\d.]+)\s*%', page_text, re.I)
            if match:
                annualised["5y"] = match.group(1) + "%"
        
        if not annualised.get("all"):
            match = re.search(r'Fund returns.*?All[:\s]+([\d.]+)\s*%', page_text, re.I)
            if not match:
                match = re.search(r'All[:\s]+([\d.]+)\s*%', page_text, re.I)
            if match:
                annualised["all"] = match.group(1) + "%"
        
        # Consolidate returns - use simple structure (1y, 3y, 5y, since_inception)
        returns_data = {}
        returns_data["1y"] = annualised.get("1y", "")
        returns_data["3y"] = annualised.get("3y", "")
        returns_data["5y"] = annualised.get("5y", "")
        returns_data["since_inception"] = annualised.get("all", "")
        
        data["returns"] = returns_data
        
        # Extract category info - improved extraction
        category_info = {}
        
        # Category name - try to get full category like "Equity ELSS"
        full_category = None
        category_elem = soup.find(string=re.compile(r'Category|Equity ELSS|Equity', re.I))
        if category_elem:
            parent_text = category_elem.parent.get_text() if category_elem.parent else ""
            # Look for "Equity ELSS" or similar
            cat_match = re.search(r'Category[:\s]+(Equity\s+ELSS|ELSS|Equity|Debt|Hybrid)', parent_text, re.I)
            if cat_match:
                full_category = cat_match.group(1)
        
        if not full_category:
            # Try to find in page text
            cat_match = re.search(r'Category[:\s]+(Equity\s+ELSS|Equity\s+[A-Z]+|ELSS)', page_text, re.I)
            if cat_match:
                full_category = cat_match.group(1)
        
        category_info["category"] = full_category or category_value or ""
        
        # Category averages - extract from returns table
        category_avg = {}
        
        # Look in returns table for category average row
        for table in tables:
            table_str = str(table).lower()
            if 'return' in table_str:
                data_rows = table.get('data', [])
                for row in data_rows:
                    if isinstance(row, dict):
                        row_text = ' '.join(str(v).lower() for v in row.values())
                        if 'category average' in row_text:
                            # Extract percentages
                            for key, value in row.items():
                                key_lower = str(key).lower()
                                value_str = str(value).strip()
                                match = re.search(r'([\d.]+)\s*%', value_str)
                                if match:
                                    if '1y' in key_lower or '1 year' in key_lower:
                                        category_avg["1y"] = match.group(1) + "%"
                                    elif '3y' in key_lower or '3 year' in key_lower:
                                        category_avg["3y"] = match.group(1) + "%"
                                    elif '5y' in key_lower or '5 year' in key_lower:
                                        category_avg["5y"] = match.group(1) + "%"
        
        # Fallback regex
        if not category_avg.get("1y"):
            cat_avg_match = re.search(r'Category average.*?1\s*Y[:\s]+([\d.]+)\s*%', page_text, re.I)
            if cat_avg_match:
                category_avg["1y"] = cat_avg_match.group(1) + "%"
        
        if not category_avg.get("3y"):
            cat_avg_match = re.search(r'Category average.*?3\s*Y[:\s]+([\d.]+)\s*%', page_text, re.I)
            if cat_avg_match:
                category_avg["3y"] = cat_avg_match.group(1) + "%"
        
        if not category_avg.get("5y"):
            cat_avg_match = re.search(r'Category average.*?5\s*Y[:\s]+([\d.]+)\s*%', page_text, re.I)
            if cat_avg_match:
                category_avg["5y"] = cat_avg_match.group(1) + "%"
        
        category_info["category_average_annualised"] = category_avg
        
        # Rank within category - extract from returns table
        rank = {}
        
        for table in tables:
            table_str = str(table).lower()
            if 'return' in table_str or 'rank' in table_str:
                data_rows = table.get('data', [])
                for row in data_rows:
                    if isinstance(row, dict):
                        row_text = ' '.join(str(v).lower() for v in row.values())
                        if 'rank' in row_text or 'fund return' in row_text:
                            # Look for rank values
                            for key, value in row.items():
                                key_lower = str(key).lower()
                                value_str = str(value).strip()
                                if 'rank' in key_lower:
                                    # Try to extract rank numbers
                                    rank_match = re.search(r'(\d+)', value_str)
                                    if rank_match:
                                        if '1y' in key_lower:
                                            try:
                                                rank["1y"] = int(rank_match.group(1))
                                            except:
                                                pass
                                        elif '3y' in key_lower:
                                            try:
                                                rank["3y"] = int(rank_match.group(1))
                                            except:
                                                pass
                                        elif '5y' in key_lower:
                                            try:
                                                rank["5y"] = int(rank_match.group(1))
                                            except:
                                                pass
        
        # Fallback regex - look for "Rank with in category 18 13 8"
        if not rank.get("1y") or not rank.get("3y"):
            rank_match = re.search(r'Rank.*?category\s+(\d+)\s+(\d+)\s+(\d+)', page_text, re.I)
            if rank_match:
                try:
                    rank["1y"] = int(rank_match.group(1))
                    rank["3y"] = int(rank_match.group(2))
                    rank["5y"] = int(rank_match.group(3))
                except:
                    pass
        
        # Additional fallback
        if not rank.get("1y"):
            rank_1y = re.search(r'Rank.*?1\s*Y[:\s]+(\d+)', page_text, re.I)
            if rank_1y:
                try:
                    rank["1y"] = int(rank_1y.group(1))
                except:
                    pass
        
        if not rank.get("3y"):
            rank_3y = re.search(r'Rank.*?3\s*Y[:\s]+(\d+)', page_text, re.I)
            if rank_3y:
                try:
                    rank["3y"] = int(rank_3y.group(1))
                except:
                    pass
        
        if not rank.get("5y"):
            rank_5y = re.search(r'Rank.*?5\s*Y[:\s]+(\d+)', page_text, re.I)
            if rank_5y:
                try:
                    rank["5y"] = int(rank_5y.group(1))
                except:
                    pass
        
        category_info["rank_within_category"] = rank
        data["category_info"] = category_info
        
        # Extract expense and exit load
        expense_data = {}
        
        # Current expense ratio
        expense_value = None
        expense_elem = soup.find(string=re.compile(r'Expense Ratio|Total Expense Ratio', re.I))
        if expense_elem:
            parent_text = expense_elem.parent.get_text() if expense_elem.parent else ""
            expense_match = re.search(r'([\d.]+)\s*%', parent_text)
            if expense_match:
                expense_value = expense_match.group(1) + "%"
        
        if not expense_value:
            expense_match = re.search(r'Expense Ratio[:\s]+([\d.]+)\s*%', page_text, re.I)
            if expense_match:
                expense_value = expense_match.group(1) + "%"
        
        expense_data["current_expense_ratio"] = expense_value or ""
        
        # Expense ratio effective from
        expense_date = nav_date or ""  # Use NAV date as proxy
        
        # Exit load - extract full descriptive text with improved extraction
        exit_load_value = None
        
        # Method 1: Use page_obj to get comprehensive text and extract full exit load description
        if page_obj:
            try:
                exit_load_text = page_obj.evaluate("""
                    () => {
                        // Get all text including hidden elements
                        let text = document.body.innerText;
                        
                        // Look for exit load sections - get more context
                        const exitLoadSections = document.querySelectorAll('[class*="exit"], [class*="load"], [id*="exit"], [class*="cost"]');
                        exitLoadSections.forEach(section => {
                            // Get parent container for more context
                            let parent = section;
                            for (let i = 0; i < 5 && parent; i++) {
                                parent = parent.parentElement;
                                if (parent) {
                                    text += ' ' + parent.innerText;
                                }
                            }
                        });
                        return text;
                    }
                """)
                
                # Try to extract full exit load description - comprehensive patterns
                # Pattern 1: "Exit load for units in excess of X% of the investment, Y% will be charged for redemption within Z days"
                exit_patterns = [
                    r'Exit load for units in excess of ([\d.]+)% of the investment[,\s]+([\d.]+)% will be charged for redemption within (\d+)\s*(?:days?|months?|years?)',
                    r'Exit load for units in excess of ([\d.]+)%[^,]{0,50}?([\d.]+)%[^,]{0,100}?redemption within (\d+)\s*(?:days?|months?|years?)',
                    r'Exit load[:\s]+for units in excess of ([\d.]+)%[^\.]{20,200}?([\d.]+)%[^\.]{20,200}?(\d+)\s*(?:days?|months?|years?)',
                    r'Exit load of ([\d.]+)% if redeemed within (\d+)\s*(?:days?|months?|years?)',
                    r'Exit load[:\s]+([\d.]+)%[^\.]{0,100}?(?:if|within|redeemed|days?|months?|years?)',
                ]
                for pattern in exit_patterns:
                    exit_match = re.search(pattern, exit_load_text, re.I)
                    if exit_match:
                        if len(exit_match.groups()) >= 3:
                            # Full pattern: "Exit load for units in excess of X% of the investment, Y% will be charged for redemption within Z days"
                            exit_load_value = f"Exit load for units in excess of {exit_match.group(1)}% of the investment, {exit_match.group(2)}% will be charged for redemption within {exit_match.group(3)} days"
                            break
                        elif len(exit_match.groups()) >= 2:
                            # Pattern: "Exit load of X% if redeemed within Y days"
                            exit_load_value = f"Exit load of {exit_match.group(1)}% if redeemed within {exit_match.group(2)} days"
                            break
                        elif exit_match.group(1).replace('.', '').isdigit():
                            # Found a percentage value
                            exit_load_value = f"Exit load of {exit_match.group(1)}%"
                            break
                
                # If not found, check for Nil
                if not exit_load_value:
                    if re.search(r'Exit load[:\s]+(Nil|N/A|None|0%)', exit_load_text, re.I):
                        exit_load_value = "Nil"
            except:
                pass
        
        # Method 2: Extract from soup with broader context
        if not exit_load_value:
            exit_elem = soup.find(string=re.compile(r'Exit load|Exit Load', re.I))
            if exit_elem:
                parent = exit_elem.parent
                # Get broader context (up to 1000 chars for full description)
                while parent and len(parent.get_text()) < 1000:
                    parent = parent.parent
                parent_text = parent.get_text() if parent else ""
                
                # Extract full description - comprehensive patterns
                exit_patterns = [
                    r'Exit load for units in excess of ([\d.]+)% of the investment[,\s]+([\d.]+)% will be charged for redemption within (\d+)\s*(?:days?|months?|years?)',
                    r'Exit load for units in excess of ([\d.]+)%[^,]{0,50}?([\d.]+)%[^,]{0,100}?redemption within (\d+)\s*(?:days?|months?|years?)',
                    r'Exit load[:\s]+for units in excess of ([\d.]+)%[^\.]{20,200}?([\d.]+)%[^\.]{20,200}?(\d+)\s*(?:days?|months?|years?)',
                    r'Exit load of ([\d.]+)% if redeemed within (\d+)\s*(?:days?|months?|years?)',
                    r'Exit load[:\s]+([\d.]+)%[^\.]{0,100}?(?:if|within|redeemed|days?|months?|years?)',
                ]
                for pattern in exit_patterns:
                    exit_match = re.search(pattern, parent_text, re.I)
                    if exit_match:
                        if len(exit_match.groups()) >= 3:
                            # Full pattern
                            exit_load_value = f"Exit load for units in excess of {exit_match.group(1)}% of the investment, {exit_match.group(2)}% will be charged for redemption within {exit_match.group(3)} days"
                            break
                        elif len(exit_match.groups()) >= 2:
                            exit_load_value = f"Exit load of {exit_match.group(1)}% if redeemed within {exit_match.group(2)} days"
                            break
                        elif exit_match.group(1).replace('.', '').isdigit():
                            exit_load_value = f"Exit load of {exit_match.group(1)}%"
                            break
                
                # If no detailed match, check for Nil
                if not exit_load_value:
                    if re.search(r'Exit load[:\s]+(Nil|N/A|None|0%)', parent_text, re.I):
                        exit_load_value = "Nil"
        
        # Method 3: Fallback regex on page text
        if not exit_load_value:
            exit_patterns = [
                r'Exit load for units in excess of ([\d.]+)% of the investment[,\s]+([\d.]+)% will be charged for redemption within (\d+)\s*(?:days?|months?|years?)',
                r'Exit load for units in excess of ([\d.]+)%[^,]{0,50}?([\d.]+)%[^,]{0,100}?redemption within (\d+)\s*(?:days?|months?|years?)',
                r'Exit load[:\s]+for units in excess of ([\d.]+)%[^\.]{20,200}?([\d.]+)%[^\.]{20,200}?(\d+)\s*(?:days?|months?|years?)',
                r'Exit load of ([\d.]+)% if redeemed within (\d+)\s*(?:days?|months?|years?)',
                r'Exit load[:\s]+([\d.]+)%[^\.]{0,100}?(?:if|within|redeemed|days?|months?|years?)',
                r'Exit load[:\s]+(Nil|N/A|None|0%)',
            ]
            for pattern in exit_patterns:
                exit_match = re.search(pattern, page_text, re.I)
                if exit_match:
                    if len(exit_match.groups()) >= 3:
                        exit_load_value = f"Exit load for units in excess of {exit_match.group(1)}% of the investment, {exit_match.group(2)}% will be charged for redemption within {exit_match.group(3)} days"
                        break
                    elif len(exit_match.groups()) >= 2:
                        if exit_match.group(1).lower() in ['nil', 'n/a', 'none']:
                            exit_load_value = "Nil"
                            break
                        exit_load_value = f"Exit load of {exit_match.group(1)}% if redeemed within {exit_match.group(2)} days"
                        break
                    elif exit_match.group(1).lower() in ['nil', 'n/a', 'none']:
                        exit_load_value = "Nil"
                        break
                    elif exit_match.group(1).replace('.', '').isdigit():
                        exit_load_value = f"Exit load of {exit_match.group(1)}%"
                        break
        
        # Extract Stamp Duty
        stamp_duty = None
        stamp_elem = soup.find(string=re.compile(r'Stamp duty|Stamp Duty', re.I))
        if stamp_elem:
            parent_text = stamp_elem.parent.get_text() if stamp_elem.parent else ""
            stamp_match = re.search(r'([\d.]+)\s*%', parent_text)
            if stamp_match:
                stamp_duty = stamp_match.group(1) + "%"
        
        if not stamp_duty:
            stamp_match = re.search(r'Stamp duty[:\s]+([\d.]+)\s*%', page_text, re.I)
            if stamp_match:
                stamp_duty = stamp_match.group(1) + "%"
        
        # Extract Tax Implication
        tax_implication = None
        tax_elem = soup.find(string=re.compile(r'Tax implication|Tax|Taxation', re.I))
        if tax_elem:
            parent = tax_elem.parent
            while parent and len(parent.get_text()) < 500:
                parent = parent.parent
            parent_text = parent.get_text() if parent else ""
            # Extract tax information
            tax_match = re.search(r'Tax.*?(?:If you redeem|returns are taxed|taxed at).*?([^\n]{20,200})', parent_text, re.I)
            if tax_match:
                tax_implication = self._clean_text(tax_match.group(1), 200)
        
        if not tax_implication:
            tax_match = re.search(r'Tax implication[:\s]+([^\n]{20,200})', page_text, re.I)
            if tax_match:
                tax_implication = self._clean_text(tax_match.group(1), 200)
        
        # Merge expense_and_exit_load and cost_and_tax into single section (remove expense_ratio_history_sample)
        cost_and_tax = {}
        cost_and_tax["expense_ratio"] = expense_value or ""
        cost_and_tax["expense_ratio_effective_from"] = expense_date or ""
        cost_and_tax["exit_load"] = exit_load_value or "Nil"
        cost_and_tax["stamp_duty"] = stamp_duty or ""
        cost_and_tax["tax_implication"] = tax_implication or ""
        
        data["cost_and_tax"] = cost_and_tax
        
        # Extract portfolio - improved table extraction
        portfolio_data = {}
        
        # Extract holdings from tables - better column identification
        top_holdings = []
        holdings_count = 0
        
        for table in tables:
            table_text = str(table).lower()
            if 'holding' in table_text or 'stock' in table_text or 'company' in table_text or 'instrument' in table_text:
                if table.get('data'):
                    headers = table.get('headers', [])
                    data_rows = table.get('data', [])
                    holdings_count = len(data_rows)
                    
                    # Identify column indices
                    name_col = None
                    pct_col = None
                    
                    for i, header in enumerate(headers):
                        header_lower = str(header).lower()
                        if any(term in header_lower for term in ['name', 'company', 'stock', 'holding', 'instrument', 'security']):
                            name_col = i
                        elif any(term in header_lower for term in ['weight', 'allocation', '%', 'percentage', 'asset', 'pct']):
                            pct_col = i
                    
                    # Extract holdings
                    for row in data_rows[:10]:  # Top 10 holdings
                        holding = {}
                        
                        if isinstance(row, dict):
                            # Try to find name and percentage
                            for key, value in row.items():
                                key_lower = str(key).lower()
                                value_str = str(value).strip()
                                
                                # Skip if value is "Equity" or generic terms
                                if value_str.lower() in ['equity', 'debt', 'cash', 'other']:
                                    continue
                                
                                if any(term in key_lower for term in ['name', 'company', 'stock', 'holding', 'instrument', 'security']):
                                    # Validate it's a company name (not generic)
                                    if len(value_str) > 3 and value_str.lower() not in ['equity', 'debt', 'cash']:
                                        holding["name"] = value_str
                                elif any(term in key_lower for term in ['weight', 'allocation', '%', 'percentage', 'asset', 'pct']):
                                    # Extract percentage
                                    pct_match = re.search(r'([\d.]+)\s*%', value_str)
                                    if pct_match:
                                        holding["asset_pct"] = pct_match.group(1) + "%"
                                    else:
                                        holding["asset_pct"] = value_str
                        
                        elif isinstance(row, list):
                            # Use column indices
                            if name_col is not None and name_col < len(row):
                                name_val = str(row[name_col]).strip()
                                if len(name_val) > 3 and name_val.lower() not in ['equity', 'debt', 'cash']:
                                    holding["name"] = name_val
                            
                            if pct_col is not None and pct_col < len(row):
                                pct_val = str(row[pct_col]).strip()
                                pct_match = re.search(r'([\d.]+)\s*%', pct_val)
                                if pct_match:
                                    holding["asset_pct"] = pct_match.group(1) + "%"
                                else:
                                    holding["asset_pct"] = pct_val
                        
                        # Only add if we have both name and percentage
                        if holding.get("name") and holding.get("asset_pct") and holding["name"].lower() not in ['equity', 'debt', 'cash', 'other']:
                            top_holdings.append(holding)
        
        # Extract top 5 holdings only (remove portfolio section)
        top_5_holdings = top_holdings[:5] if len(top_holdings) >= 5 else top_holdings
        data["top_5_holdings"] = top_5_holdings
        
        # Extract advanced ratios (P/E, P/B)
        advanced_ratios = {}
        
        # Initialize P/E and P/B ratios
        pe_ratio = None
        pb_ratio = None
        
        # P/E Ratio - initial extraction (avoid matching periods)
        pe_elem = soup.find(string=re.compile(r'P/E|PE Ratio|Price to Earnings', re.I))
        if pe_elem:
            parent_text = pe_elem.parent.get_text() if pe_elem.parent else ""
            # Match P/E followed by a number (not just a period)
            pe_match = re.search(r'P/E[:\s]+([\d]+\.?\d*)', parent_text, re.I)
            if pe_match:
                pe_val = pe_match.group(1)
                # Validate it's a number, not just a period
                if pe_val.replace('.', '').isdigit() and len(pe_val.replace('.', '')) > 0:
                    try:
                        pe_float = float(pe_val)
                        if 5 <= pe_float <= 100:
                            pe_ratio = pe_val
                    except:
                        pass
        
        if not pe_ratio:
            pe_match = re.search(r'P/E[:\s]+([\d]+\.?\d*)', page_text, re.I)
            if pe_match:
                pe_val = pe_match.group(1)
                # Validate it's a number, not just a period
                if pe_val.replace('.', '').isdigit() and len(pe_val.replace('.', '')) > 0:
                    try:
                        pe_float = float(pe_val)
                        if 5 <= pe_float <= 100:
                            pe_ratio = pe_val
                    except:
                        pass
        
        # P/B Ratio - initial extraction
        pb_elem = soup.find(string=re.compile(r'P/B|PB Ratio|Price to Book', re.I))
        if pb_elem:
            parent_text = pb_elem.parent.get_text() if pb_elem.parent else ""
            pb_match = re.search(r'P/B[:\s]+([\d.]+)', parent_text, re.I)
            if pb_match:
                pb_val = pb_match.group(1)
                try:
                    if 0.1 <= float(pb_val) <= 20:
                        pb_ratio = pb_val
                except:
                    pass
        
        if not pb_ratio:
            pb_match = re.search(r'P/B[:\s]+([\d.]+)', page_text, re.I)
            if pb_match:
                pb_val = pb_match.group(1)
                try:
                    if 0.1 <= float(pb_val) <= 20:
                        pb_ratio = pb_val
                except:
                    pass
        
        # Enhanced advanced ratios extraction - specifically target Advanced ratios section/table
        # Try to extract from page_obj if available (Playwright)
        if page_obj:
            try:
                # First, try to find and extract from the Advanced ratios table/section specifically
                advanced_ratios_data = page_obj.evaluate("""
                    () => {
                        // Find Advanced ratios section - look for section containing "Advanced ratios" or similar
                        let ratiosSection = null;
                        
                        // Method 1: Look for heading "Advanced ratios" or "Advanced Ratios"
                        const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6, [class*="heading"], [class*="title"]');
                        for (let heading of headings) {
                            const headingText = heading.innerText.toLowerCase();
                            if (headingText.includes('advanced') && headingText.includes('ratio')) {
                                // Find the parent container
                                let parent = heading.parentElement;
                                for (let i = 0; i < 5 && parent; i++) {
                                    if (parent.innerText.includes('P/E') || parent.innerText.includes('Top 5') || parent.innerText.includes('Alpha')) {
                                        ratiosSection = parent;
                                        break;
                                    }
                                    parent = parent.parentElement;
                                }
                                if (ratiosSection) break;
                            }
                        }
                        
                        // Method 2: Look for divs/sections containing both "P/E" and "Top 5" or "Alpha"
                        if (!ratiosSection) {
                            const allSections = document.querySelectorAll('div, section, [class*="ratio"], [class*="metric"], [class*="stat"]');
                            for (let section of allSections) {
                                const sectionText = section.innerText;
                                if ((sectionText.includes('P/E') || sectionText.includes('P/B')) && 
                                    (sectionText.includes('Top 5') || sectionText.includes('Alpha') || sectionText.includes('Beta'))) {
                                    ratiosSection = section;
                                    break;
                                }
                            }
                        }
                        
                        // Method 3: Look for tables containing Advanced ratios
                        if (!ratiosSection) {
                            const allTables = document.querySelectorAll('table');
                            for (let table of allTables) {
                                const tableText = table.innerText.toLowerCase();
                                if ((tableText.includes('p/e') || tableText.includes('p/b')) && 
                                    (tableText.includes('top 5') || tableText.includes('alpha') || tableText.includes('beta'))) {
                                    ratiosSection = table;
                                    break;
                                }
                            }
                        }
                        
                        if (ratiosSection) {
                            return ratiosSection.innerText;
                        }
                        
                        // Fallback: Get all text from body
                        return document.body.innerText;
                    }
                """)
                
                if advanced_ratios_data:
                    # Extract P/E ratio - improved patterns to match "P/E Ratio: 21.20" format
                    if not pe_ratio:
                        pe_patterns = [
                            r'P/E\s+Ratio[:\s]+([\d]+\.?\d*)',  # "P/E Ratio: 21.20"
                            r'P\/E\s+Ratio[:\s]+([\d]+\.?\d*)',  # "P/E Ratio: 21.20"
                            r'P/E[:\s]+([\d]+\.?\d*)',  # "P/E: 21.20"
                            r'P\/E[:\s]+([\d]+\.?\d*)',  # "P/E: 21.20"
                            r'PE\s+Ratio[:\s]+([\d]+\.?\d*)',  # "PE Ratio: 21.20"
                            r'PE[:\s]+([\d]+\.?\d*)',  # "PE: 21.20"
                            r'Price.*?Earnings[:\s]+([\d]+\.?\d*)',
                            r'P-E[:\s]+([\d]+\.?\d*)',
                        ]
                        for pattern in pe_patterns:
                            pe_match = re.search(pattern, advanced_ratios_data, re.I)
                            if pe_match:
                                pe_val = pe_match.group(1)
                                # Validate it's a number
                                if pe_val.replace('.', '').isdigit() and len(pe_val.replace('.', '')) > 0:
                                    try:
                                        pe_float = float(pe_val)
                                        if 5 <= pe_float <= 100:
                                            pe_ratio = pe_val
                                            break
                                    except:
                                        pass
                    
                    # Extract P/B ratio - improved patterns
                    if not pb_ratio:
                        pb_patterns = [
                            r'P/B\s+Ratio[:\s]+([\d.]+)',  # "P/B Ratio: 3.28"
                            r'P\/B\s+Ratio[:\s]+([\d.]+)',  # "P/B Ratio: 3.28"
                            r'P/B[:\s]+([\d.]+)',  # "P/B: 3.28"
                            r'P\/B[:\s]+([\d.]+)',  # "P/B: 3.28"
                            r'PB\s+Ratio[:\s]+([\d.]+)',  # "PB Ratio: 3.28"
                            r'PB[:\s]+([\d.]+)',  # "PB: 3.28"
                            r'Price.*?Book[:\s]+([\d.]+)',
                            r'P-B[:\s]+([\d.]+)',
                        ]
                        for pattern in pb_patterns:
                            pb_match = re.search(pattern, advanced_ratios_data, re.I)
                            if pb_match:
                                pb_val = pb_match.group(1)
                                try:
                                    pb_float = float(pb_val)
                                    if 0.1 <= pb_float <= 20:
                                        pb_ratio = pb_val
                                        break
                                except:
                                    pass
                    
                    # Extract Alpha
                    alpha = None
                    alpha_match = re.search(r'Alpha[:\s]+([\d.]+)', advanced_ratios_data, re.I)
                    if alpha_match:
                        alpha = alpha_match.group(1)
                    
                    # Extract Beta
                    beta = None
                    beta_match = re.search(r'Beta[:\s]+([\d.]+)', advanced_ratios_data, re.I)
                    if beta_match:
                        beta = beta_match.group(1)
                    
                    # Extract Sharpe Ratio
                    sharpe = None
                    sharpe_match = re.search(r'Sharpe[:\s]+([\d.]+)', advanced_ratios_data, re.I)
                    if sharpe_match:
                        sharpe = sharpe_match.group(1)
                    
                    # Extract Sortino Ratio
                    sortino = None
                    sortino_match = re.search(r'Sortino[:\s]+([\d.]+)', advanced_ratios_data, re.I)
                    if sortino_match:
                        sortino = sortino_match.group(1)
                    
                    # Update advanced ratios with all extracted values
                    if pe_ratio:
                        advanced_ratios["pe_ratio"] = pe_ratio
                    if pb_ratio:
                        advanced_ratios["pb_ratio"] = pb_ratio
                    if alpha:
                        advanced_ratios["alpha"] = alpha
                    if beta:
                        advanced_ratios["beta"] = beta
                    if sharpe:
                        advanced_ratios["sharpe_ratio"] = sharpe
                    if sortino:
                        advanced_ratios["sortino_ratio"] = sortino
            except Exception as e:
                print(f"Error extracting advanced ratios from page: {e}")
        
        # Update advanced_ratios with extracted values (if not already set from page_obj)
        if pe_ratio and "pe_ratio" not in advanced_ratios:
            advanced_ratios["pe_ratio"] = pe_ratio
        if pb_ratio and "pb_ratio" not in advanced_ratios:
            advanced_ratios["pb_ratio"] = pb_ratio
        
        # Ensure pe_ratio and pb_ratio keys exist (even if empty)
        if "pe_ratio" not in advanced_ratios:
            advanced_ratios["pe_ratio"] = ""
        if "pb_ratio" not in advanced_ratios:
            advanced_ratios["pb_ratio"] = ""
        
        # Fallback regex extraction for P/E and P/B - more comprehensive patterns
        if not pe_ratio or not advanced_ratios.get("pe_ratio"):
            pe_patterns = [
                r'P/E\s+Ratio[:\s]+([\d]+\.?\d*)',  # "P/E Ratio: 21.20"
                r'P\/E\s+Ratio[:\s]+([\d]+\.?\d*)',  # "P/E Ratio: 21.20"
                r'PE\s+Ratio[:\s]+([\d]+\.?\d*)',  # "PE Ratio: 21.20"
                r'P/E[:\s]+([\d]+\.?\d*)',  # "P/E: 21.20"
                r'P\/E[:\s]+([\d]+\.?\d*)',  # "P/E: 21.20"
                r'PE[:\s]+([\d]+\.?\d*)',  # "PE: 21.20"
                r'P/E\s+([\d]+\.?\d*)',  # "P/E 21.20"
                r'PE\s+([\d]+\.?\d*)',  # "PE 21.20"
                r'Price.*?Earnings[:\s]+([\d]+\.?\d*)',
            ]
            for pattern in pe_patterns:
                pe_match = re.search(pattern, page_text, re.I)
                if pe_match:
                    pe_val = pe_match.group(1)
                    # Validate it's a number
                    if pe_val and pe_val.replace('.', '').isdigit() and len(pe_val.replace('.', '')) > 0:
                        try:
                            pe_float = float(pe_val)
                            if 5 <= pe_float <= 100:
                                pe_ratio = pe_val
                                advanced_ratios["pe_ratio"] = pe_ratio
                                break
                        except:
                            pass
        
        if not pb_ratio or not advanced_ratios.get("pb_ratio"):
            pb_patterns = [
                r'P/B\s+Ratio[:\s]+([\d.]+)',  # "P/B Ratio: 3.28"
                r'P\/B\s+Ratio[:\s]+([\d.]+)',  # "P/B Ratio: 3.28"
                r'PB\s+Ratio[:\s]+([\d.]+)',  # "PB Ratio: 3.28"
                r'P/B[:\s]+([\d.]+)',  # "P/B: 3.28"
                r'P\/B[:\s]+([\d.]+)',  # "P/B: 3.28"
                r'PB[:\s]+([\d.]+)',  # "PB: 3.28"
                r'P/B\s+([\d.]+)',  # "P/B 3.28"
                r'PB\s+([\d.]+)',  # "PB 3.28"
                r'Price.*?Book[:\s]+([\d.]+)',
            ]
            for pattern in pb_patterns:
                pb_match = re.search(pattern, page_text, re.I)
                if pb_match:
                    pb_val = pb_match.group(1)
                    if pb_val:
                        try:
                            pb_float = float(pb_val)
                            if 0.1 <= pb_float <= 20:
                                pb_ratio = pb_val
                                advanced_ratios["pb_ratio"] = pb_ratio
                                break
                        except:
                            pass
        
        # Fallback regex extraction for other ratios
        if not advanced_ratios.get("alpha"):
            alpha_match = re.search(r'Alpha[:\s]+([\d.]+)', page_text, re.I)
            if alpha_match:
                advanced_ratios["alpha"] = alpha_match.group(1)
        
        if not advanced_ratios.get("beta"):
            beta_match = re.search(r'Beta[:\s]+([\d.]+)', page_text, re.I)
            if beta_match:
                advanced_ratios["beta"] = beta_match.group(1)
        
        if not advanced_ratios.get("sharpe_ratio"):
            sharpe_match = re.search(r'Sharpe[:\s]+([\d.]+)', page_text, re.I)
            if sharpe_match:
                advanced_ratios["sharpe_ratio"] = sharpe_match.group(1)
        
        if not advanced_ratios.get("sortino_ratio"):
            sortino_match = re.search(r'Sortino[:\s]+([\d.]+)', page_text, re.I)
            if sortino_match:
                advanced_ratios["sortino_ratio"] = sortino_match.group(1)
        
        # Extract Top 5 and Top 20 weight percentages from Advanced ratios table (not calculate)
        # Also extract P/E and P/B from the same section if not already found
        top_5_weight_pct = None
        top_20_weight_pct = None
        
        # Method 1: Extract from Advanced ratios table using page_obj (same section as P/E, P/B)
        if page_obj:
            try:
                ratios_table_data = page_obj.evaluate("""
                    () => {
                        // Find Advanced ratios section - same logic as above
                        let ratiosSection = null;
                        
                        // Look for heading "Advanced ratios"
                        const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6, [class*="heading"], [class*="title"]');
                        for (let heading of headings) {
                            const headingText = heading.innerText.toLowerCase();
                            if (headingText.includes('advanced') && headingText.includes('ratio')) {
                                let parent = heading.parentElement;
                                for (let i = 0; i < 5 && parent; i++) {
                                    if (parent.innerText.includes('P/E') || parent.innerText.includes('Top 5') || parent.innerText.includes('Alpha')) {
                                        ratiosSection = parent;
                                        break;
                                    }
                                    parent = parent.parentElement;
                                }
                                if (ratiosSection) break;
                            }
                        }
                        
                        // Look for divs/sections containing both "P/E" and "Top 5"
                        if (!ratiosSection) {
                            const allSections = document.querySelectorAll('div, section, [class*="ratio"], [class*="metric"]');
                            for (let section of allSections) {
                                const sectionText = section.innerText;
                                if ((sectionText.includes('P/E') || sectionText.includes('P/B')) && 
                                    (sectionText.includes('Top 5') || sectionText.includes('Alpha'))) {
                                    ratiosSection = section;
                                    break;
                                }
                            }
                        }
                        
                        // Look for tables
                        if (!ratiosSection) {
                            const allTables = document.querySelectorAll('table');
                            for (let table of allTables) {
                                const tableText = table.innerText.toLowerCase();
                                if ((tableText.includes('p/e') || tableText.includes('p/b')) && 
                                    (tableText.includes('top 5') || tableText.includes('alpha'))) {
                                    ratiosSection = table;
                                    break;
                                }
                            }
                        }
                        
                        return ratiosSection ? ratiosSection.innerText : null;
                    }
                """)
                
                if ratios_table_data:
                    # Extract Top 5 weight percentage
                    top5_match = re.search(r'Top\s*5[:\s]+([\d.]+)\s*%', ratios_table_data, re.I)
                    if top5_match:
                        top_5_weight_pct = top5_match.group(1) + "%"
                    
                    # Extract Top 20 weight percentage
                    top20_match = re.search(r'Top\s*20[:\s]+([\d.]+)\s*%', ratios_table_data, re.I)
                    if top20_match:
                        top_20_weight_pct = top20_match.group(1) + "%"
                    
                    # Also try to extract P/E and P/B from this same section if not already found
                    if not pe_ratio:
                        pe_match = re.search(r'P/E\s+Ratio[:\s]+([\d]+\.?\d*)|P\/E\s+Ratio[:\s]+([\d]+\.?\d*)|P/E[:\s]+([\d]+\.?\d*)', ratios_table_data, re.I)
                        if pe_match:
                            pe_val = pe_match.group(1) or pe_match.group(2) or pe_match.group(3)
                            if pe_val and pe_val.replace('.', '').isdigit():
                                try:
                                    pe_float = float(pe_val)
                                    if 5 <= pe_float <= 100:
                                        pe_ratio = pe_val
                                        advanced_ratios["pe_ratio"] = pe_ratio
                                except:
                                    pass
                    
                    if not pb_ratio:
                        pb_match = re.search(r'P/B\s+Ratio[:\s]+([\d.]+)|P\/B\s+Ratio[:\s]+([\d.]+)|P/B[:\s]+([\d.]+)', ratios_table_data, re.I)
                        if pb_match:
                            pb_val = pb_match.group(1) or pb_match.group(2) or pb_match.group(3)
                            if pb_val:
                                try:
                                    pb_float = float(pb_val)
                                    if 0.1 <= pb_float <= 20:
                                        pb_ratio = pb_val
                                        advanced_ratios["pb_ratio"] = pb_ratio
                                except:
                                    pass
            except:
                pass
        
        # Method 2: Extract from tables in soup - also look for P/E and P/B
        if not top_5_weight_pct or not top_20_weight_pct or not pe_ratio or not pb_ratio:
            for table in tables:
                table_text = str(table).lower()
                # Look for Advanced ratios table (contains P/E, P/B, Top 5, Alpha, etc.)
                if (('top 5' in table_text or 'top 20' in table_text or 'advanced' in table_text or 'ratio' in table_text) and
                    ('p/e' in table_text or 'p/b' in table_text or 'alpha' in table_text)):
                    headers = table.get('headers', [])
                    data_rows = table.get('data', [])
                    table_full_text = ' '.join(str(v).lower() for v in headers) + ' ' + ' '.join(str(v).lower() for row in data_rows for v in (row.values() if isinstance(row, dict) else row))
                    
                    # Extract P/E and P/B from table text
                    if not pe_ratio:
                        pe_match = re.search(r'p/e\s+ratio[:\s]+([\d]+\.?\d*)|p\/e\s+ratio[:\s]+([\d]+\.?\d*)|p/e[:\s]+([\d]+\.?\d*)', table_full_text, re.I)
                        if pe_match:
                            pe_val = pe_match.group(1) or pe_match.group(2) or pe_match.group(3)
                            if pe_val and pe_val.replace('.', '').isdigit():
                                try:
                                    pe_float = float(pe_val)
                                    if 5 <= pe_float <= 100:
                                        pe_ratio = pe_val
                                        advanced_ratios["pe_ratio"] = pe_ratio
                                except:
                                    pass
                    
                    if not pb_ratio:
                        pb_match = re.search(r'p/b\s+ratio[:\s]+([\d.]+)|p\/b\s+ratio[:\s]+([\d.]+)|p/b[:\s]+([\d.]+)', table_full_text, re.I)
                        if pb_match:
                            pb_val = pb_match.group(1) or pb_match.group(2) or pb_match.group(3)
                            if pb_val:
                                try:
                                    pb_float = float(pb_val)
                                    if 0.1 <= pb_float <= 20:
                                        pb_ratio = pb_val
                                        advanced_ratios["pb_ratio"] = pb_ratio
                                except:
                                    pass
                    
                    # Look for rows containing "Top 5" or "Top 20"
                    for row in data_rows:
                        row_text = ' '.join(str(v).lower() for v in (row.values() if isinstance(row, dict) else row))
                        if 'top 5' in row_text:
                            # Extract percentage value
                            if isinstance(row, dict):
                                for key, value in row.items():
                                    if 'top 5' in str(key).lower() or 'weight' in str(key).lower():
                                        pct_match = re.search(r'([\d.]+)\s*%', str(value))
                                        if pct_match:
                                            top_5_weight_pct = pct_match.group(1) + "%"
                                            break
                                    pct_match = re.search(r'([\d.]+)\s*%', str(value))
                                    if pct_match and not top_5_weight_pct:
                                        top_5_weight_pct = pct_match.group(1) + "%"
                            elif isinstance(row, list):
                                for cell in row:
                                    pct_match = re.search(r'([\d.]+)\s*%', str(cell))
                                    if pct_match:
                                        top_5_weight_pct = pct_match.group(1) + "%"
                                        break
                        
                        if 'top 20' in row_text:
                            # Extract percentage value
                            if isinstance(row, dict):
                                for key, value in row.items():
                                    if 'top 20' in str(key).lower() or 'weight' in str(key).lower():
                                        pct_match = re.search(r'([\d.]+)\s*%', str(value))
                                        if pct_match:
                                            top_20_weight_pct = pct_match.group(1) + "%"
                                            break
                                    pct_match = re.search(r'([\d.]+)\s*%', str(value))
                                    if pct_match and not top_20_weight_pct:
                                        top_20_weight_pct = pct_match.group(1) + "%"
                            elif isinstance(row, list):
                                for cell in row:
                                    pct_match = re.search(r'([\d.]+)\s*%', str(cell))
                                    if pct_match:
                                        top_20_weight_pct = pct_match.group(1) + "%"
                                        break
        
        # Method 3: Fallback regex on page text
        if not top_5_weight_pct:
            top5_match = re.search(r'Top\s*5[:\s]+([\d.]+)\s*%', page_text, re.I)
            if top5_match:
                top_5_weight_pct = top5_match.group(1) + "%"
        
        if not top_20_weight_pct:
            top20_match = re.search(r'Top\s*20[:\s]+([\d.]+)\s*%', page_text, re.I)
            if top20_match:
                top_20_weight_pct = top20_match.group(1) + "%"
        
        advanced_ratios["top_5_weight_pct"] = top_5_weight_pct or ""
        advanced_ratios["top_20_weight_pct"] = top_20_weight_pct or ""
        
        data["advanced_ratios"] = advanced_ratios
        
        # Extract peer comparison sample
        peer_comparison = []
        peer_section = soup.find(string=re.compile(r'Peer Comparison|Similar funds', re.I))
        if peer_section:
            parent_text = peer_section.parent.get_text() if peer_section.parent else ""
            # Look for peer fund entries
            # This is complex and may need refinement based on actual page structure
            peer_matches = re.findall(r'([A-Z][^\n]{10,50}?)\s+(\d+)\s+([\d.]+)%\s+([\d.]+)%\s+([\d,]+\.?\d*)', parent_text, re.I)
            for match in peer_matches[:2]:  # First 2 peers
                peer_comparison.append({
                    "fund": match[0].strip(),
                    "1y": match[2] + "%",
                    "3y": match[3] + "%",
                    "fund_size_cr": match[4]
                })
        
        data["peer_comparison_sample"] = peer_comparison
        
        # Source
        data["source"] = {
            "site": "Groww",
            "page_ref": "turn0view0"
        }
        
        return data
    
    def extract_parameters(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract all fund parameters from the page with improved structure parsing."""
        params = {
            "fund_category": "",
            "risk_level": "",
            "nav": "",
            "aum": "",
            "expense_ratio": "",
            "exit_load": "",
            "min_sip": "",
            "min_lumpsum": "",
            "lock_in": "",
            "benchmark": "",
            "returns": {
                "1y": "",
                "3y": "",
                "5y": ""
            },
            "portfolio": {
                "top_holdings": [],
                "sector_allocation": []
            }
        }
        
        # Get page text for regex fallback
        page_text = soup.get_text(separator=' ', strip=True)
        
        # Extract NAV - Look for "Latest NAV" or "NAV" with date context
        nav_value = None
        # Try structured extraction first - look for "Latest NAV as of" pattern
        nav_elem = soup.find(string=re.compile(r'Latest NAV|Current NAV|NAV.*as of', re.I))
        if nav_elem:
            # Get parent and surrounding context
            parent = nav_elem.parent
            if parent:
                # Look in parent and next siblings
                context_text = parent.get_text()
                # Match NAV value like ₹145.20 (should be after "as of" date)
                nav_match = re.search(r'as of.*?₹\s*([\d,]+\.?\d{2,})', context_text, re.I)
                if nav_match:
                    nav_value = nav_match.group(1).replace(',', '')
                    # Validate it's a reasonable NAV (between 1 and 10000)
                    try:
                        nav_float = float(nav_value)
                        if 1 <= nav_float <= 10000:
                            params["nav"] = nav_value
                            nav_value = nav_value  # Mark as found
                    except:
                        pass
        
        # Fallback to regex on page text (avoid matching dates and AUM)
        if not nav_value:
            nav_patterns = [
                r'Latest NAV.*?as of.*?₹\s*([\d,]+\.?\d{2,})',
                r'NAV.*?as of.*?₹\s*([\d,]+\.?\d{2,})',
                r'Latest NAV[:\s]+₹\s*([\d,]+\.?\d{2,})(?!\s*(?:Cr|Crore|Lakh))',
            ]
            for pattern in nav_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    nav_candidate = match.group(1).replace(',', '')
                    # Validate it's a reasonable NAV (between 1 and 10000, not AUM)
                    try:
                        nav_float = float(nav_candidate)
                        if 1 <= nav_float <= 10000:
                            nav_value = nav_candidate
                            break
                    except:
                        pass
        
        params["nav"] = nav_value or ""
        
        # Extract AUM - Look for "AUM" or "Assets Under Management"
        aum_value = None
        aum_elem = soup.find(string=re.compile(r'AUM|Assets Under Management|Fund Size', re.I))
        if aum_elem:
            parent_text = aum_elem.parent.get_text() if aum_elem.parent else ""
            aum_match = re.search(r'₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore|Cr\.)', parent_text, re.I)
            if aum_match:
                aum_value = aum_match.group(1).replace(',', '')
        
        if not aum_value:
            aum_patterns = [
                r'AUM[:\s]+₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore)',
                r'Assets Under Management[:\s]+₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore)',
                r'Total AUM[:\s]+₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore)',
            ]
            for pattern in aum_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    aum_value = match.group(1).replace(',', '')
                    break
        params["aum"] = aum_value or ""
        
        # Extract Expense Ratio
        expense_value = None
        expense_elem = soup.find(string=re.compile(r'Expense Ratio|Total Expense Ratio|TER', re.I))
        if expense_elem:
            parent_text = expense_elem.parent.get_text() if expense_elem.parent else ""
            expense_match = re.search(r'([\d.]+)\s*%', parent_text)
            if expense_match:
                expense_value = expense_match.group(1) + "%"
        
        if not expense_value:
            expense_patterns = [
                r'Expense Ratio[:\s]+([\d.]+)\s*%',
                r'Total Expense Ratio[:\s]+([\d.]+)\s*%',
            ]
            for pattern in expense_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    expense_value = match.group(1) + "%"
                    break
        params["expense_ratio"] = expense_value or ""
        
        # Extract Exit Load - Look for "Exit load" followed by "Nil" or percentage
        exit_load_value = None
        exit_elem = soup.find(string=re.compile(r'Exit load|Exit Load', re.I))
        if exit_elem:
            parent_text = exit_elem.parent.get_text() if exit_elem.parent else ""
            # Check for Nil first
            if re.search(r'Nil|N/A|None|0%', parent_text, re.I):
                exit_load_value = "Nil"
            else:
                exit_match = re.search(r'([\d.]+)\s*%', parent_text)
                if exit_match:
                    exit_load_value = exit_match.group(1) + "%"
        
        if not exit_load_value:
            exit_load_patterns = [
                r'Exit load[:\s]+(Nil|N/A|None|0%)',
                r'Exit load[:\s]+([\d.]+)\s*%',
            ]
            for pattern in exit_load_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    exit_load_value = match.group(1).strip()
                    if not exit_load_value.endswith('%'):
                        exit_load_value = exit_load_value + "%" if exit_load_value.replace('.', '').isdigit() else exit_load_value
                    break
        params["exit_load"] = exit_load_value or ""
        
        # Extract Min SIP
        sip_value = None
        sip_elem = soup.find(string=re.compile(r'Min.*SIP|SIP.*Amount|Minimum.*SIP', re.I))
        if sip_elem:
            parent_text = sip_elem.parent.get_text() if sip_elem.parent else ""
            sip_match = re.search(r'₹\s*([\d,]+)', parent_text)
            if sip_match:
                sip_value = "₹" + sip_match.group(1)
        
        if not sip_value:
            sip_patterns = [
                r'Min(?:imum)? SIP[:\s]+₹\s*([\d,]+)',
                r'SIP.*?₹\s*([\d,]+)',
            ]
            for pattern in sip_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    sip_value = "₹" + match.group(1)
                    break
        params["min_sip"] = sip_value or ""
        
        # Extract Min Lumpsum
        lumpsum_value = None
        lumpsum_elem = soup.find(string=re.compile(r'Min.*Lumpsum|Lumpsum|One-time', re.I))
        if lumpsum_elem:
            parent_text = lumpsum_elem.parent.get_text() if lumpsum_elem.parent else ""
            lumpsum_match = re.search(r'₹\s*([\d,]+)', parent_text)
            if lumpsum_match:
                lumpsum_value = "₹" + lumpsum_match.group(1)
        
        if not lumpsum_value:
            lumpsum_patterns = [
                r'Min(?:imum)? Lumpsum[:\s]+₹\s*([\d,]+)',
                r'One-time[:\s]+₹\s*([\d,]+)',
            ]
            for pattern in lumpsum_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    lumpsum_value = "₹" + match.group(1)
                    break
        params["min_lumpsum"] = lumpsum_value or ""
        
        # Extract Lock-in Period (for ELSS funds)
        lockin_value = None
        lockin_elem = soup.find(string=re.compile(r'Lock-in|Lock In', re.I))
        if lockin_elem:
            parent_text = lockin_elem.parent.get_text() if lockin_elem.parent else ""
            lockin_match = re.search(r'(\d+\s*(?:years?|months?|days?))', parent_text, re.I)
            if lockin_match:
                lockin_value = lockin_match.group(1)
        
        if not lockin_value:
            lockin_patterns = [
                r'Lock-in[:\s]+(\d+\s*(?:years?|months?|days?))',
                r'Lock.*?(\d+\s*years?)',
            ]
            for pattern in lockin_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    lockin_value = match.group(1)
                    break
        params["lock_in"] = lockin_value or ""
        
        # Extract Benchmark - Look for "Benchmark" or "Benchmark Index"
        benchmark_value = None
        benchmark_elem = soup.find(string=re.compile(r'Benchmark', re.I))
        if benchmark_elem:
            parent_text = benchmark_elem.parent.get_text() if benchmark_elem.parent else ""
            # Extract index name (usually first line after Benchmark)
            benchmark_match = re.search(r'Benchmark[:\s]+([^\n]+)', parent_text, re.I)
            if benchmark_match:
                benchmark_value = self._clean_text(benchmark_match.group(1), 100)
        
        if not benchmark_value:
            benchmark_patterns = [
                r'Benchmark[:\s]+([A-Z][^\n]{5,50}?)(?:\s|$)',
                r'Benchmark Index[:\s]+([A-Z][^\n]{5,50}?)(?:\s|$)',
            ]
            for pattern in benchmark_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    benchmark_value = self._clean_text(match.group(1), 100)
                    break
        params["benchmark"] = benchmark_value or ""
        
        # Extract Risk Level
        risk_value = None
        risk_elem = soup.find(string=re.compile(r'Risk|Riskometer|Risk Rating', re.I))
        if risk_elem:
            parent_text = risk_elem.parent.get_text() if risk_elem.parent else ""
            risk_match = re.search(r'(?:Risk|Riskometer)[:\s]+([A-Z][^\n]{0,30}?)(?:\s|$)', parent_text, re.I)
            if risk_match:
                risk_value = self._clean_text(risk_match.group(1), 50)
        
        if not risk_value:
            risk_patterns = [
                r'Risk Level[:\s]+([A-Z][^\n]{0,30}?)(?:\s|$)',
                r'Riskometer[:\s]+([A-Z][^\n]{0,30}?)(?:\s|$)',
            ]
            for pattern in risk_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    risk_value = self._clean_text(match.group(1), 50)
                    break
        params["risk_level"] = risk_value or ""
        
        # Extract Fund Category - Look for "Category" or "Fund Category"
        category_value = None
        category_elem = soup.find(string=re.compile(r'Category|Fund Category', re.I))
        if category_elem:
            parent_text = category_elem.parent.get_text() if category_elem.parent else ""
            # Extract category (usually first meaningful word after "Category")
            category_match = re.search(r'Category[:\s]+([A-Z][^\n]{5,40}?)(?:\s|$)', parent_text, re.I)
            if category_match:
                category_value = self._clean_text(category_match.group(1), 50)
        
        if not category_value:
            category_patterns = [
                r'Category[:\s]+([A-Z][^\n]{5,40}?)(?:\s|$)',
                r'Fund Category[:\s]+([A-Z][^\n]{5,40}?)(?:\s|$)',
            ]
            for pattern in category_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    category_value = self._clean_text(match.group(1), 50)
                    break
        params["fund_category"] = category_value or ""
        
        # Extract Returns from structured sections or tables
        # Look for returns table or section
        returns_section = soup.find(string=re.compile(r'Annualised returns|Returns|1Y|3Y|5Y', re.I))
        if returns_section:
            parent_text = returns_section.parent.get_text() if returns_section.parent else ""
            # Try to extract 1Y, 3Y, 5Y returns
            returns_1y = re.search(r'1\s*Y(?:ear)?[:\s]+([\d.]+)\s*%', parent_text, re.I)
            returns_3y = re.search(r'3\s*Y(?:ear)?[:\s]+([\d.]+)\s*%', parent_text, re.I)
            returns_5y = re.search(r'5\s*Y(?:ear)?[:\s]+([\d.]+)\s*%', parent_text, re.I)
            
            if returns_1y:
                params["returns"]["1y"] = returns_1y.group(1) + "%"
            if returns_3y:
                params["returns"]["3y"] = returns_3y.group(1) + "%"
            if returns_5y:
                params["returns"]["5y"] = returns_5y.group(1) + "%"
        
        # Fallback regex for returns
        if not params["returns"]["1y"]:
            match = re.search(r'1\s*Y(?:ear)?[:\s]+([\d.]+)\s*%', page_text, re.IGNORECASE)
            if match:
                params["returns"]["1y"] = match.group(1) + "%"
        
        if not params["returns"]["3y"]:
            match = re.search(r'3\s*Y(?:ear)?[:\s]+([\d.]+)\s*%', page_text, re.IGNORECASE)
            if match:
                params["returns"]["3y"] = match.group(1) + "%"
        
        if not params["returns"]["5y"]:
            match = re.search(r'5\s*Y(?:ear)?[:\s]+([\d.]+)\s*%', page_text, re.IGNORECASE)
            if match:
                params["returns"]["5y"] = match.group(1) + "%"
        
        # Extract Top Holdings from tables
        tables = self.extract_tables(soup)
        for table in tables:
            table_text = str(table).lower()
            if 'holding' in table_text or 'stock' in table_text or 'company' in table_text:
                if table['data']:
                    for row in table['data'][:10]:  # Top 10 holdings
                        if isinstance(row, dict):
                            holding = {}
                            for key, value in row.items():
                                key_lower = key.lower()
                                if any(term in key_lower for term in ['name', 'company', 'stock', 'holding', 'instrument']):
                                    holding['name'] = value.strip()
                                elif any(term in key_lower for term in ['weight', 'allocation', '%', 'percentage']):
                                    holding['weight'] = value.strip()
                            if holding.get('name'):
                                params["portfolio"]["top_holdings"].append(holding)
        
        # Extract Sector Allocation
        for table in tables:
            table_text = str(table).lower()
            if 'sector' in table_text:
                if table['data']:
                    for row in table['data']:
                        if isinstance(row, dict):
                            sector = {}
                            for key, value in row.items():
                                key_lower = key.lower()
                                if 'sector' in key_lower:
                                    sector['sector'] = value.strip()
                                elif any(term in key_lower for term in ['weight', 'allocation', '%', 'percentage']):
                                    sector['weight'] = value.strip()
                            if sector.get('sector'):
                                params["portfolio"]["sector_allocation"].append(sector)
        
        return params
    
    def parse_fund_data(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Main function to parse fund data from URL with dynamic content discovery.
        
        Args:
            url: URL of the mutual fund page
            
        Returns:
            Dictionary with fund data in the required structure, or None if failed
        """
        print(f"Fetching: {url}")
        
        # Try Playwright first for dynamic content if enabled
        playwright_instance = None
        page_obj = None
        browser = None
        
        if self.use_interactive and PLAYWRIGHT_AVAILABLE:
            playwright_result = self._fetch_with_playwright(url, interactive=True)
            if playwright_result:
                html, page_obj, browser, playwright_instance = playwright_result
                soup = BeautifulSoup(html, 'lxml')
            else:
                # Fallback to regular fetch
                html = self.fetch_page(url)
                if not html:
                    print(f"Failed to fetch {url}")
                    return None
                soup = BeautifulSoup(html, 'lxml')
        else:
            # Use regular fetch
            html = self.fetch_page(url)
            if not html:
                print(f"Failed to fetch {url}")
                return None
            soup = BeautifulSoup(html, 'lxml')
        
        page_text = soup.get_text(separator=' ', strip=True)
        
        # Extract detailed data using new method with page object
        try:
            data = self.extract_detailed_data(soup, page_text, page_obj)
        finally:
            # Close browser and playwright instance if opened
            if browser:
                try:
                    browser.close()
                except:
                    pass
            if playwright_instance:
                try:
                    playwright_instance.stop()
                except:
                    pass
        
        # Add source_url and last_scraped
        data["source_url"] = url
        data["last_scraped"] = datetime.now().strftime("%Y-%m-%d")
        
        return data
    
    def save_json(self, data: Dict[str, Any], fund_slug: str) -> str:
        """
        Save fund data to JSON file as an array.
        
        Args:
            data: Fund data dictionary
            fund_slug: Slug for filename
            
        Returns:
            Path to saved file
        """
        filename = f"{fund_slug}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        # Save as array with single fund object
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump([data], f, indent=2, ensure_ascii=False)
        
        print(f"Saved: {filepath}")
        return filepath
    
    def download_html(self, url: str) -> Optional[str]:
        """
        Download HTML content and save to file for later scraping.
        Ensures Fund Objective section is loaded by scrolling.
        Prioritizes Playwright (best for cloud), then Selenium, then requests.
        
        Args:
            url: URL to download
            
        Returns:
            Path to saved HTML file, or None if failed
        """
        print(f"Downloading HTML: {url}")
        
        html = None
        
        # Try Playwright first (works best on cloud environments)
        if self.use_interactive and PLAYWRIGHT_AVAILABLE:
            try:
                print("Using Playwright to download webpage with dynamic content...")
                playwright_result = self._fetch_with_playwright(url, interactive=True)
                if playwright_result:
                    html, page_obj, browser, playwright_instance = playwright_result
                    try:
                        browser.close()
                        playwright_instance.stop()
                    except:
                        pass
            except Exception as e:
                print(f"Playwright failed: {e}, trying alternatives...")
        
        # Try Selenium as fallback if Playwright failed or not available
        if not html and self.use_interactive and SELENIUM_AVAILABLE:
            try:
                print("Using Selenium to download webpage with dynamic content...")
                html = self._fetch_with_selenium(url)
            except Exception as e:
                print(f"Selenium failed: {e}, trying requests...")
        
        # Fallback to requests if browser automation failed
        if not html:
            print("Using requests to download webpage...")
            html = self.fetch_page(url)
        
        if not html:
            print(f"Failed to download HTML from {url}")
            return None
        
        # Save HTML to file
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        fund_slug = path_parts[-1] if path_parts else "unknown"
        html_filename = f"{fund_slug}.html"
        html_filepath = os.path.join(self.download_dir, html_filename)
        
        os.makedirs(self.download_dir, exist_ok=True)
        with open(html_filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"Saved HTML: {html_filepath}")
        
        return html_filepath
    
    def scrape_from_file(self, html_filepath: str, url: str) -> Optional[str]:
        """
        Scrape data from a downloaded HTML file.
        Uses comprehensive extraction including AUM from Fund Objective section.
        Deletes the HTML file after successful scraping.
        
        Args:
            html_filepath: Path to HTML file
            url: Original URL (for metadata)
            
        Returns:
            Path to saved JSON file, or None if failed
        """
        print(f"Scraping from file: {html_filepath}")
        
        try:
            with open(html_filepath, 'r', encoding='utf-8') as f:
                html = f.read()
        except Exception as e:
            print(f"Error reading HTML file: {e}")
            return None
        
        soup = BeautifulSoup(html, 'lxml')
        page_text = soup.get_text(separator=' ', strip=True)
        
        # Extract detailed data (page_obj is None when scraping from file)
        # But we have the full HTML, so extraction should work
        try:
            data = self.extract_detailed_data(soup, page_text, None)
            
            if not data:
                print("Error: extract_detailed_data returned None")
                return None
            
            # Additional AUM extraction from downloaded HTML if not found
            if not data.get("aum") or data.get("aum") == "":
                print("AUM not found in initial extraction, trying enhanced extraction from downloaded HTML...")
                # Enhanced AUM extraction from Fund Objective section
                aum_value = self._extract_aum_from_objective_section(soup, page_text)
                if aum_value:
                    data["aum"] = aum_value
                    print(f"Found AUM: {aum_value}")
        except Exception as e:
            print(f"Error extracting data: {e}")
            import traceback
            traceback.print_exc()
            # Don't delete HTML file if extraction failed
            return None
        
        # Add source_url and last_scraped
        data["source_url"] = url
        data["last_scraped"] = datetime.now().strftime("%Y-%m-%d")
        
        # Save JSON
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        fund_slug = path_parts[-1] if path_parts else "unknown"
        
        json_filepath = self.save_json(data, fund_slug)
        
        # Delete HTML file after successful scraping (it's just an intermediate step)
        if json_filepath and os.path.exists(html_filepath):
            try:
                os.remove(html_filepath)
                print(f"Deleted intermediate HTML file: {html_filepath}")
            except Exception as e:
                print(f"Warning: Could not delete HTML file {html_filepath}: {e}")
        
        return json_filepath
    
    def _extract_aum_from_objective_section(self, soup: BeautifulSoup, page_text: str) -> Optional[str]:
        """
        Enhanced AUM extraction specifically from Fund Objective section.
        Used when scraping from downloaded HTML file.
        
        Args:
            soup: BeautifulSoup object
            page_text: Full page text
            
        Returns:
            AUM value as string (e.g., "₹48,870.6Cr") or None
        """
        # Strategy 1: Find Fund Objective section by various methods
        objective_section = None
        
        # Method 1a: Find by header text
        objective_headers = soup.find_all(['h2', 'h3', 'h4', 'h5', 'h6'], 
                                          string=re.compile(r'Fund Objective|Investment Objective', re.I))
        if objective_headers:
            objective_section = objective_headers[0].find_parent(['div', 'section', 'article'])
            if not objective_section:
                objective_section = objective_headers[0].parent
        
        # Method 1b: Find by class/id containing "objective"
        if not objective_section:
            objective_section = soup.find(['div', 'section'], 
                                         class_=re.compile(r'objective|Objective', re.I))
        
        # Method 1c: Find by text content containing "Fund Objective"
        if not objective_section:
            for tag in soup.find_all(['div', 'section', 'article']):
                text = tag.get_text().lower()
                if 'fund objective' in text or 'investment objective' in text:
                    if len(text) < 5000:  # Avoid matching entire page
                        objective_section = tag
                        break
        
        # Strategy 2: Extract AUM from objective section
        if objective_section:
            # Get full text of objective section including children
            section_text = objective_section.get_text(separator=' ', strip=True)
            
            # Also check parent if section is small
            if len(section_text) < 500:
                parent = objective_section.parent
                if parent:
                    section_text = parent.get_text(separator=' ', strip=True)
            
            # Try multiple AUM patterns
            aum_patterns = [
                r'AUM[:\s]+₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore|Cr\.)',
                r'Assets Under Management[:\s]+₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore|Cr\.)',
                r'Assets Under Management[:\s]+([\d,]+\.?\d*)\s*(?:Cr|Crore|Cr\.)',
                r'AUM[:\s]+([\d,]+\.?\d*)\s*(?:Cr|Crore|Cr\.)',
                r'₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore|Cr\.).*?AUM',
                r'₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore|Cr\.).*?Assets Under Management',
                r'([\d,]+\.?\d*)\s*(?:Cr|Crore|Cr\.).*?Assets Under Management',
            ]
            
            for pattern in aum_patterns:
                aum_match = re.search(pattern, section_text, re.I)
                if aum_match:
                    aum_num = aum_match.group(1).replace(',', '')
                    try:
                        aum_float = float(aum_num)
                        if 0.1 <= aum_float <= 1000000:
                            aum_formatted = f"{aum_float:,.2f}".rstrip('0').rstrip('.')
                            return f"₹{aum_formatted}Cr"
                    except:
                        pass
        
        # Strategy 3: Search page text around "Fund Objective" keyword
        objective_pos = page_text.lower().find('fund objective')
        if objective_pos >= 0:
            # Get context around Fund Objective (3000 characters)
            start_pos = max(0, objective_pos - 500)
            end_pos = min(len(page_text), objective_pos + 3000)
            objective_context = page_text[start_pos:end_pos]
            
            aum_patterns = [
                r'AUM[:\s]+₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore|Cr\.)',
                r'Assets Under Management[:\s]+₹\s*([\d,]+\.?\d*)\s*(?:Cr|Crore|Cr\.)',
                r'AUM[:\s]+([\d,]+\.?\d*)\s*(?:Cr|Crore|Cr\.)',
            ]
            
            for pattern in aum_patterns:
                aum_match = re.search(pattern, objective_context, re.I)
                if aum_match:
                    aum_num = aum_match.group(1).replace(',', '')
                    try:
                        aum_float = float(aum_num)
                        if 0.1 <= aum_float <= 1000000:
                            aum_formatted = f"{aum_float:,.2f}".rstrip('0').rstrip('.')
                            return f"₹{aum_formatted}Cr"
                    except:
                        pass
        
        return None
    
    def scrape(self, url: str) -> Optional[str]:
        """
        Scrape a single fund page and save to JSON.
        ALWAYS downloads/pre-computes the webpage first, then scrapes from downloaded file.
        This ensures all dynamic content is loaded before extraction.
        
        Args:
            url: URL to scrape
            
        Returns:
            Path to saved JSON file, or None if failed
        """
        # ALWAYS download/pre-compute the webpage first, then scrape from downloaded file
        # This ensures all dynamic content is loaded before extraction
        print(f"Step 1: Downloading/pre-computing webpage for {url}")
        html_filepath = self.download_html(url)
        
        if not html_filepath:
            print(f"Failed to download HTML from {url}. Cannot proceed with scraping.")
            return None
        
        # Step 2: Scrape from downloaded HTML file
        print(f"Step 2: Scraping from downloaded HTML file: {html_filepath}")
        return self.scrape_from_file(html_filepath, url)


def load_config(config_path: str = "scraper_config.json") -> Dict[str, Any]:
    """
    Load scraper configuration from JSON file.
    
    Args:
        config_path: Path to config JSON file
        
    Returns:
        Configuration dictionary
    """
    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}, using defaults")
        return {
            "scraper_settings": {
                "output_dir": "data/mutual_funds",
                "download_dir": "data/downloaded_html",
                "use_interactive": True,
                "download_first": False
            },
            "urls": []
        }
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    """Main function to run the scraper with config-driven URLs."""
    config = load_config()
    
    scraper_settings = config.get("scraper_settings", {})
    urls_config = config.get("urls", [])
    
    # Initialize scraper with settings
    scraper = GrowwScraper(
        output_dir=scraper_settings.get("output_dir", "data/mutual_funds"),
        use_interactive=scraper_settings.get("use_interactive", True),
        download_dir=scraper_settings.get("download_dir", "data/downloaded_html"),
        download_first=scraper_settings.get("download_first", False)
    )
    
    # Process all URLs from config
    if not urls_config:
        print("No URLs found in config")
        return
    
    print(f"Found {len(urls_config)} URL(s) to scrape")
    
    results = []
    for item in urls_config:
        url = item.get("url")
        if not url:
            continue
        
        try:
            print(f"\n{'='*60}")
            print(f"Scraping: {url}")
            print(f"{'='*60}")
            filepath = scraper.scrape(url)
            if filepath:
                results.append({"url": url, "status": "success", "filepath": filepath})
                print(f"✓ Successfully scraped: {filepath}")
            else:
                results.append({"url": url, "status": "failed", "reason": "No file generated"})
                print(f"✗ Failed to scrape: {url}")
        except Exception as e:
            results.append({"url": url, "status": "error", "error": str(e)})
            print(f"✗ Error scraping {url}: {e}")
            continue
    
    # Print summary
    print(f"\n{'='*60}")
    print("Scraping Summary")
    print(f"{'='*60}")
    successful = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - successful
    print(f"Total URLs: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    return results


if __name__ == "__main__":
    main()

