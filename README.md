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

### Railway Deployment

This application is fully configured for deployment on Railway with automatic deployments from GitHub.

**📚 Deployment Documentation:**
- **[Quick Start Guide](RAILWAY_DEPLOYMENT_GUIDE.md)** - Get deployed in 5 minutes
- **[Complete Deployment Plan](RAILWAY_DEPLOYMENT_PLAN.md)** - Detailed step-by-step guide
- **[Deployment Checklist](DEPLOYMENT_CHECKLIST.md)** - Pre-flight checklist

#### Quick Start

1. **Connect Repository to Railway**
   - Go to [railway.app](https://railway.app) and sign in with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository

2. **Set Environment Variables**
   - Go to Service → Variables
   - Add `GEMINI_API_KEY` (mark as secret)
   - Optional: Set other variables (defaults work fine)

3. **Add Persistent Storage** (CRITICAL)
   - Go to Service → Volumes
   - Add volume with mount path: `/app/chroma_db`
   - Size: 100MB (can increase later)

4. **Deploy**
   - Railway will auto-detect Dockerfile and start building
   - Wait ~5-10 minutes for first build
   - Get your URL: `your-service.up.railway.app`

5. **Ingest Data**
   ```bash
   curl -X POST "https://your-service.up.railway.app/api/v1/ingest" \
     -H "Content-Type: application/json" \
     -d '{"upsert": true}'
   ```

**For detailed instructions, see [RAILWAY_DEPLOYMENT_GUIDE.md](RAILWAY_DEPLOYMENT_GUIDE.md)**

#### Railway Free Tier Limits

- **RAM**: 512MB
- **Storage**: 1GB (including volumes)
- **Bandwidth**: 100GB/month
- **Deployments**: Unlimited

**Recommendations for Free Tier:**
- Disable scheduled scraper or use longer intervals (24+ hours)
- Monitor resource usage in Railway dashboard
- Consider optimizing chunk sizes if needed

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
├── api/                    # FastAPI application
├── ingestion/              # Document processing
├── vector_store/           # ChromaDB integration
├── retrieval/              # RAG implementation
├── scrapers/               # Web scraping
├── scripts/                # Utility scripts
├── static/                 # Frontend files
├── data/                   # Source data
├── chroma_db/              # Vector database (local)
├── Dockerfile              # Container definition
├── railway.json            # Railway configuration
└── requirements.txt        # Python dependencies
```

## Configuration

See `ARCHITECTURE.md` for detailed architecture documentation.

Environment variables are configured in `.env` file (local) or Railway dashboard (production).

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

