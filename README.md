# RAG-based Mutual Fund Chatbot

A RAG (Retrieval-Augmented Generation) based chatbot system for querying mutual fund information. The system uses Google Gemini as the LLM and embedding model, ChromaDB as the vector database, and LangChain for orchestration.

## Features

- **RAG-based Q&A**: Ask questions about mutual funds and get accurate answers with source citations
- **Web Scraping**: Automated scraping of mutual fund data from Groww
- **Scheduled Updates**: Automatic data refresh with configurable schedules
- **Web Interface**: Modern, responsive chat interface
- **PII Protection**: Built-in detection and blocking of personally identifiable information
- **Factual Only**: Validates questions to prevent investment advice, focuses on factual information

## Technology Stack

- **FastAPI**: Modern, fast web framework
- **LangChain**: LLM application framework
- **Google Gemini**: LLM and embedding model
- **ChromaDB**: Vector database for embeddings
- **Playwright**: Web scraping automation
- **Python 3.11+**: Backend runtime

## Quick Start

### Local Development

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

3. **Start the Server**
   ```bash
   python start_frontend.py
   ```
   This will start the FastAPI server and open the browser automatically.

4. **Access the Application**
   - Frontend: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Ingest Data

```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{"upsert": true}'
```

## Deployment

### Streamlit Cloud Deployment

This application is configured for deployment on Streamlit Cloud.

**📚 Deployment Documentation:**
- **[Streamlit Deployment Guide](STREAMLIT_DEPLOYMENT_GUIDE.md)** - Complete deployment guide

#### Quick Start

1. **Push to GitHub**
   - Ensure all code is committed and pushed to GitHub
   - Repository should include `app.py` (Streamlit app)

2. **Deploy on Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app"
   - Select your repository
   - Main file: `app.py`
   - Click "Deploy"

3. **Set Secrets** (Environment Variables)
   - Go to Settings → Secrets
   - Add `GEMINI_API_KEY` (your Gemini API key)
   - Add `API_BASE_URL` (if using separate FastAPI backend)

4. **Access Your App**
   - Your app will be live at: `https://your-app-name.streamlit.app`
   - Streamlit Cloud auto-redeploys on every push

**For detailed instructions, see [STREAMLIT_DEPLOYMENT_GUIDE.md](STREAMLIT_DEPLOYMENT_GUIDE.md)**

#### Streamlit Cloud Features

- ✅ **Free tier** - Unlimited apps
- ✅ **Auto-deploy** - Deploys on every Git push
- ✅ **Easy setup** - Just connect GitHub repo
- ✅ **Custom domains** - Available in Pro tier
- ✅ **Private repos** - Available in Pro tier

#### Architecture Options

**Option 1: Streamlit + Separate FastAPI Backend** (Recommended)
- Deploy Streamlit app on Streamlit Cloud
- Deploy FastAPI backend separately (Railway, Render, etc.)
- Streamlit calls FastAPI API endpoints

**Option 2: Pure Streamlit**
- Run everything in Streamlit (requires code refactoring)
- Single deployment, simpler setup

## API Endpoints

### Health Check
```
GET /health
```

### Ingest Documents
```
POST /api/v1/ingest
Body: {"upsert": true}
```

### Query RAG System
```
POST /api/v1/query
Body: {
  "question": "What is the expense ratio of Nippon India Large Cap Fund?",
  "return_sources": true
}
```

### Search Similar Documents
```
POST /api/v1/search
Body: {
  "query": "large cap funds",
  "k": 5
}
```

### Scraper Status
```
GET /api/v1/scraper-status
```

### Trigger Scraping
```
POST /api/v1/scrape
```

See `/docs` endpoint for interactive API documentation.

## Project Structure

```
MF-Chatbot/
├── app.py                  # Streamlit app (main entry point)
├── api/                    # FastAPI application
│   └── main.py            # FastAPI app
├── ingestion/              # Document processing
├── vector_store/           # ChromaDB integration
├── retrieval/              # RAG implementation
├── scrapers/               # Web scraping
├── scripts/                # Utility scripts
├── static/                 # Frontend files (HTML/JS/CSS)
├── data/                   # Source data
├── chroma_db/              # Vector database (local)
├── .streamlit/             # Streamlit configuration
│   └── config.toml
├── Dockerfile              # Optional (for other platforms)
└── requirements.txt        # Python dependencies
```

## Configuration

See `ARCHITECTURE.md` for detailed architecture documentation.

Environment variables are configured in `.env` file (local) or Streamlit Cloud secrets (production).

## Development

### Running Tests
```bash
pytest tests/
```

### Local Development Server
```bash
python start_frontend.py
# Or
uvicorn api.main:app --reload
```

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions, please open an issue on GitHub.

