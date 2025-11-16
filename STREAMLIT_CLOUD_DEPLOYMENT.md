# Streamlit Cloud Deployment Guide

## Changes Made for Streamlit Cloud Compatibility

### 1. Enabled Scraper on Streamlit Cloud
- **File**: `app.py`
- **Changes**: Removed the check that disabled scraper on Streamlit Cloud
- The scraper now runs on Streamlit Cloud and will attempt to scrape periodically

### 2. Fixed Browser Automation
- **File**: `scrapers/groww_scraper.py`
- **Changes**:
  - Enabled Playwright (works better on cloud environments)
  - Updated fetch logic to try Playwright first, then Selenium, then requests
  - Improved Selenium configuration for Streamlit Cloud compatibility
  - Added proper Chrome binary path detection

### 3. Added System Dependencies
- **File**: `packages.txt`
- **Purpose**: Installs Chrome/Chromium and required system libraries for browser automation on Streamlit Cloud

### 4. Updated Requirements
- **File**: `requirements.txt`
- **Added**: `chromedriver-autoinstaller>=0.6.2` for automatic ChromeDriver setup

## Deployment Steps

### 1. Install Playwright Browsers
After deploying to Streamlit Cloud, you may need to ensure Playwright browsers are installed. You can do this by:

**Option A**: Add a post-install script (if supported by Streamlit Cloud):
```bash
playwright install chromium
```

**Option B**: The scraper will automatically fall back to Selenium if Playwright browsers aren't available.

### 2. Configure Streamlit Secrets
Make sure to set the following in Streamlit Cloud secrets:
- `GEMINI_API_KEY`: Your Google Gemini API key

### 3. Verify Scraper Configuration
Ensure `scraper_config.json` is properly configured with:
- URLs to scrape
- Schedule settings (enabled: true, interval_hours: 1)
- Scraper settings (use_interactive: true)

### 4. Monitor Scraper Status
The scraper will:
- Run automatically on startup if no data exists
- Run periodically based on schedule configuration
- Log all activities (check Streamlit Cloud logs)
- Show status in the sidebar

## Troubleshooting

### If Scraping Fails:

1. **Check Playwright Installation**:
   - Playwright browsers may need to be installed manually
   - Check logs for Playwright-related errors

2. **Check Chrome/Chromium Availability**:
   - Verify `packages.txt` is being processed by Streamlit Cloud
   - Check if Chrome binaries are available at expected paths

3. **Fallback Behavior**:
   - The scraper will try Playwright → Selenium → requests
   - If all fail, check network connectivity and URL accessibility

4. **Check Logs**:
   - Streamlit Cloud logs will show detailed error messages
   - Look for "Failed to scrape" warnings

### Common Issues:

1. **"Playwright browsers not installed"**:
   - Solution: Playwright browsers need to be installed. This may require manual intervention or a build script.

2. **"ChromeDriver not found"**:
   - Solution: `chromedriver-autoinstaller` should handle this automatically, but verify Chrome is installed via `packages.txt`

3. **"All URLs failing to scrape"**:
   - Check network connectivity from Streamlit Cloud
   - Verify URLs are accessible
   - Check if the target site blocks automated access

## Notes

- The scraper runs in a background thread and won't block the Streamlit app
- Scraping failures are logged but won't crash the app
- The app will continue to work even if scraping fails (using existing data)
- Data persistence: Scraped data is saved to `./data/mutual_funds/` directory

## Testing Locally Before Deployment

Before deploying to Streamlit Cloud, test locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run the app
streamlit run app.py
```

Check that:
1. Scraper initializes successfully
2. Scraping works (at least one URL succeeds)
3. Data is saved correctly
4. Ingestion works

