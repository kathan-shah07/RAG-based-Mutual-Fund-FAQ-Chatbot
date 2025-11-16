# Mutual Fund FAQ Assistant

A Streamlit-based chatbot that provides factual information about mutual funds using RAG (Retrieval-Augmented Generation) with Google Gemini AI and ChromaDB.

## Features

- 💬 Interactive chat interface for asking questions about mutual funds
- 🔍 RAG-powered responses with source citations
- 🕷️ Automatic web scraping at configured intervals
- 📊 Vector database for efficient document retrieval
- ✅ PII detection and validation
- 🚫 Investment advice restrictions (facts-only)

## How to Use

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))
- Git (optional, for cloning the repository)

### Step 1: Clone or Download the Repository

```bash
git clone <your-repository-url>
cd MF-Chatbot
```

Or download and extract the ZIP file.

### Step 2: Create Virtual Environment (Recommended)

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure API Key

You have two options for setting your Gemini API key:

#### Option A: Using Streamlit Secrets (Recommended for Streamlit Cloud)

Create `.streamlit/secrets.toml` file:

```toml
GEMINI_API_KEY = "your-gemini-api-key-here"
```

#### Option B: Using Environment Variables (For Local Development)

Create a `.env` file in the root directory:

```env
GEMINI_API_KEY=your-gemini-api-key-here
```

**Important:** Never commit your API key to version control!

### Step 5: Configure Scraper (Optional)

The scraper automatically runs at intervals defined in `scraper_config.json`. Edit this file to:

- Change scraping intervals
- Add/remove URLs to scrape
- Configure scraper settings

Example `scraper_config.json`:

```json
{
  "scraper_settings": {
    "output_dir": "./data/mutual_funds",
    "download_dir": "./data/downloaded_html",
    "use_interactive": true,
    "download_first": true,
    "retry_failed": true,
    "max_retries": 3
  },
  "urls": [
    {
      "url": "https://groww.in/mutual-funds/nippon-india-elss-tax-saver-fund-direct-growth"
    }
  ],
  "schedule": {
    "enabled": true,
    "interval_type": "hourly",
    "interval_hours": 1,
    "auto_ingest_after_scrape": true
  }
}
```

### Step 6: Ingest Initial Data (Optional)

If you have existing JSON data files, ingest them into the vector database:

```bash
python scripts/ingest_data.py
```

Or use the ingestion script directly:

```python
from scripts.ingest_data import main
main()
```

### Step 7: Run the Application

Start the Streamlit app:

```bash
streamlit run app.py
```

The app will:
- Open automatically in your default browser at `http://localhost:8501`
- Initialize the vector database and RAG chain
- Start the scheduled scraper service in the background (if enabled)

### Step 8: Use the Chat Interface

1. **Ask Questions**: Type your question in the chat input at the bottom
2. **Example Questions**: Click on example questions in the sidebar to try them out
3. **View Sources**: Expand the "Sources" section to see where the information came from
4. **Clear Chat**: Use the "Clear Chat History" button in the sidebar to reset the conversation

## Example Questions

- "What is the expense ratio of Nippon India Large Cap Fund?"
- "What is the lock-in period for ELSS funds?"
- "What is the minimum SIP amount?"
- "What are the returns of Nippon India Flexi Cap Fund?"
- "What is the AUM of Nippon India Growth Mid Cap Fund?"

## Project Structure

```
MF-Chatbot/
├── app.py                 # Main Streamlit application
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── scraper_config.json    # Scraper configuration
├── .streamlit/
│   ├── config.toml       # Streamlit configuration
│   └── secrets.toml      # API keys (not in git)
├── api/
│   └── validation.py      # Input validation functions
├── ingestion/
│   ├── document_loader.py # Load JSON documents
│   └── chunker.py         # Document chunking
├── retrieval/
│   └── rag_chain.py       # RAG chain implementation
├── scrapers/
│   └── groww_scraper.py   # Web scraper
├── scripts/
│   ├── ingest_data.py     # Data ingestion script
│   └── scheduled_scraper.py # Scheduled scraper service
└── vector_store/
    └── chroma_store.py    # ChromaDB vector store
```

## Configuration

### Environment Variables

- `GEMINI_API_KEY` - Required: Your Google Gemini API key
- `GEMINI_MODEL` - Optional: Model name (default: "gemini-1.5-flash")
- `GEMINI_EMBEDDING_MODEL` - Optional: Embedding model (default: "models/embedding-001")
- `CHROMA_DB_PATH` - Optional: Path to ChromaDB (default: "./chroma_db")
- `COLLECTION_NAME` - Optional: Collection name (default: "mutual_funds")
- `DATA_DIR` - Optional: Data directory (default: "./data/mutual_funds")
- `CHUNK_SIZE` - Optional: Chunk size (default: 1000)
- `CHUNK_OVERLAP` - Optional: Chunk overlap (default: 200)
- `TOP_K_RESULTS` - Optional: Top K results (default: 5)

### Streamlit Secrets

For Streamlit Cloud deployment, add secrets via the dashboard:

1. Go to your app → Settings → Secrets
2. Add your `GEMINI_API_KEY` and other configuration values

## Deployment to Streamlit Cloud

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app"
4. Connect your GitHub repository
5. Set the main file path to `app.py`
6. Add secrets via Settings → Secrets
7. Deploy!

## Troubleshooting

### "GEMINI_API_KEY not found" Error

- Make sure you've created `.streamlit/secrets.toml` or `.env` file
- Verify the API key is correct
- For Streamlit Cloud, add it via the Secrets dashboard

### "Backend not initialized" Error

- Check that your API key is valid
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check the terminal for detailed error messages

### Scraper Not Running

- Check `scraper_config.json` - ensure `schedule.enabled` is `true`
- Verify Playwright browsers are installed: `playwright install`
- Check the sidebar for scraper status

### No Documents in Database

- Run the ingestion script: `python scripts/ingest_data.py`
- Ensure JSON files exist in `./data/mutual_funds/`
- Check that the scraper has run and created data files

## Development

### Running Tests

```bash
pytest tests/
```

### Adding New Data Sources

1. Add JSON files to `./data/mutual_funds/`
2. Run ingestion: `python scripts/ingest_data.py`
3. The data will be automatically available in the chat

### Modifying Scraper

Edit `scraper_config.json` to:
- Change URLs to scrape
- Adjust scraping intervals
- Modify scraper behavior

## License

[Add your license here]

## Support

For issues or questions, please open an issue on GitHub.
