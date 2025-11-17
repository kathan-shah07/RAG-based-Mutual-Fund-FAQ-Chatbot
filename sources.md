# 📚 Data Sources

This document lists all the mutual fund data sources used in the Mutual Fund FAQ Assistant. All data is scraped from Groww mutual fund pages and ingested into the vector database.

---

## Source Information

| ID | AMC Name | Scheme Category | Scheme Type | Source URL |
|----|----------|----------------|-------------|------------|
| 1 | Nippon | Equity | Large Cap | [Nippon India Large Cap Fund Direct Growth](https://groww.in/mutual-funds/nippon-india-large-cap-fund-direct-growth) |
| 2 | Nippon | Equity | Mid Cap | [Nippon India Growth Mid Cap Fund Direct Growth](https://groww.in/mutual-funds/nippon-india-growth-mid-cap-fund-direct-growth) |
| 3 | Nippon | Equity | Small Cap | [Nippon India Small Cap Fund Direct Growth](https://groww.in/mutual-funds/nippon-india-small-cap-fund-direct-growth) |
| 4 | Nippon | Equity | Flexi Cap | [Nippon India Flexi Cap Fund Direct Growth](https://groww.in/mutual-funds/nippon-india-flexi-cap-fund-direct-growth) |
| 5 | Nippon | Equity | ELSS | [Nippon India ELSS Tax Saver Fund Direct Growth](https://groww.in/mutual-funds/nippon-india-elss-tax-saver-fund-direct-growth) |

---

## Detailed Source List

### 1. Nippon India Large Cap Fund Direct Growth

- **AMC:** Nippon India Asset Management Company
- **Category:** Equity
- **Type:** Large Cap
- **Source URL:** https://groww.in/mutual-funds/nippon-india-large-cap-fund-direct-growth
- **Data Includes:** NAV, AUM, expense ratio, returns, holdings, performance metrics

---

### 2. Nippon India Growth Mid Cap Fund Direct Growth

- **AMC:** Nippon India Asset Management Company
- **Category:** Equity
- **Type:** Mid Cap
- **Source URL:** https://groww.in/mutual-funds/nippon-india-growth-mid-cap-fund-direct-growth
- **Data Includes:** NAV, AUM, expense ratio, returns, holdings, performance metrics

---

### 3. Nippon India Small Cap Fund Direct Growth

- **AMC:** Nippon India Asset Management Company
- **Category:** Equity
- **Type:** Small Cap
- **Source URL:** https://groww.in/mutual-funds/nippon-india-small-cap-fund-direct-growth
- **Data Includes:** NAV, AUM, expense ratio, returns, holdings, performance metrics

---

### 4. Nippon India Flexi Cap Fund Direct Growth

- **AMC:** Nippon India Asset Management Company
- **Category:** Equity
- **Type:** Flexi Cap
- **Source URL:** https://groww.in/mutual-funds/nippon-india-flexi-cap-fund-direct-growth
- **Data Includes:** NAV, AUM, expense ratio, returns, holdings, performance metrics

---

### 5. Nippon India ELSS Tax Saver Fund Direct Growth

- **AMC:** Nippon India Asset Management Company
- **Category:** Equity
- **Type:** ELSS (Equity Linked Savings Scheme)
- **Source URL:** https://groww.in/mutual-funds/nippon-india-elss-tax-saver-fund-direct-growth
- **Data Includes:** NAV, AUM, expense ratio, returns, holdings, performance metrics, lock-in period

---

## Data Collection Method

All data is collected through automated web scraping using:
- **Scraper:** GrowwScraper (Playwright/Selenium)
- **Frequency:** Configurable (default: hourly)
- **Storage:** JSON files in `data/mutual_funds/`
- **Vector Database:** ChromaDB (after ingestion)

## Data Freshness

- Data is scraped automatically based on the schedule defined in `scraper_config.json`
- Last update timestamps are tracked in the vector database
- Users can see the last update time in the Streamlit app sidebar

## Notes

- All URLs point to Groww mutual fund pages
- Data accuracy depends on the source website structure
- If Groww changes their page structure, scraping may need updates
- All schemes listed are Direct Growth plans

---

**Last Updated:** See individual fund pages for latest data timestamps

**Scraper Configuration:** See `scraper_config.json` for scraping schedule and settings

