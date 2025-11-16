# Quick Start: End-to-End Testing

## 🚀 Quick Start

### Windows (PowerShell)
```powershell
# Activate venv and run tests
.\venv\Scripts\Activate.ps1
python scripts/test_e2e_real_data.py
```

### Linux/Mac
```bash
# Activate venv and run tests
source venv/bin/activate
python scripts/test_e2e_real_data.py
```

## 📋 Test Options

| Option | Description |
|--------|-------------|
| `--scrape` | Run actual web scraping (requires internet) |
| `--skip-ingestion` | Skip ingestion step (use existing vector DB) |
| `--verbose` or `-v` | Print detailed output |

## 🎯 Common Use Cases

### 1. Test with Existing Data (Recommended First Run)
```bash
python scripts/test_e2e_real_data.py
```
- Uses existing scraped data in `data/mutual_funds/`
- Runs full ingestion pipeline
- Tests all components

### 2. Test with Fresh Scraping
```bash
python scripts/test_e2e_real_data.py --scrape
```
- Scrapes fresh data from web
- Requires internet connection
- Takes longer (~2-5 minutes)

### 3. Quick Test (Skip Ingestion)
```bash
python scripts/test_e2e_real_data.py --skip-ingestion
```
- Uses existing vector database
- Skips embedding generation
- Faster execution (~30 seconds)

### 4. Debug Mode
```bash
python scripts/test_e2e_real_data.py --verbose
```
- Shows detailed output
- Useful for troubleshooting
- Includes stack traces on errors

## ✅ What Gets Tested

1. ✅ **Config Loading** - Validates `scraper_config.json`
2. ✅ **Data Availability** - Checks for JSON files
3. ✅ **Scraping** (optional) - Real web scraping
4. ✅ **Document Loading** - Loads JSON files
5. ✅ **Chunking** - Creates document chunks
6. ✅ **Ingestion** - Loads into vector DB
7. ✅ **Vector Database** - Validates DB contents
8. ✅ **Similarity Search** - Tests retrieval
9. ✅ **RAG Queries** - Tests answer generation
10. ✅ **End-to-End** - Complete query flow

## 📊 Expected Output

```
================================================================================
                   End-to-End Test Suite - Real Data Pipeline
================================================================================

▶ Test 1: Config Loading
--------------------------------------------------------------------------------
✓ Config file found: scraper_config.json
✓ Config structure validated
✓ Found 3 enabled URL(s)

▶ Test 2: Data Availability
--------------------------------------------------------------------------------
✓ Data directory exists: ./data/mutual_funds
✓ Found 3 JSON file(s)

... (more tests) ...

================================================================================
                              Test Summary
================================================================================
✓ PASS: Config Loading - Config loaded and validated
✓ PASS: Data Availability - 3 files found
✓ PASS: Document Loading - 3 documents
✓ PASS: Chunking - 21 chunks
✓ PASS: Ingestion - 21 new, 21 total
✓ PASS: Vector Database - 21 docs
✓ PASS: Similarity Search - 5/5
✓ PASS: RAG Queries - 5/5
✓ PASS: End-to-End Queries - 3/3

Total: 9/9 tests passed
All tests passed! ✓
```

## ⚠️ Prerequisites

1. **API Key**: Set `GEMINI_API_KEY` in `.env` file
2. **Data**: Existing data in `data/mutual_funds/` OR internet for scraping
3. **Dependencies**: All packages installed in venv

## 🔧 Troubleshooting

### "GEMINI_API_KEY not configured"
- Create `.env` file with your API key
- Or set environment variable: `export GEMINI_API_KEY=your_key`

### "No JSON files found"
- Run with `--scrape` to fetch new data
- Or ensure `data/mutual_funds/` contains JSON files

### "API quota exceeded"
- Wait for quota reset (usually daily)
- Or use `--skip-ingestion` to skip embedding generation

### Unicode/Encoding Issues (Windows)
- The script handles Windows console encoding automatically
- If issues persist, use PowerShell or Windows Terminal

## 📚 More Information

See `scripts/E2E_TESTING_GUIDE.md` for detailed documentation.

