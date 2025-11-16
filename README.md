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

### Vercel Deployment

This application is configured for deployment on Vercel as serverless functions.

**📚 Deployment Documentation:**
- **[Quick Start Guide](VERCEL_DEPLOYMENT_GUIDE.md)** - Get deployed in 5 minutes
- **[Complete Deployment Plan](VERCEL_DEPLOYMENT_PLAN.md)** - Detailed step-by-step guide

#### Quick Start

1. **Connect Repository to Vercel**
   - Go to [vercel.com](https://vercel.com) and sign in with GitHub
   - Click "Add New" → "Project"
   - Import your repository

2. **Set Environment Variables**
   - Go to Settings → Environment Variables
   - Add `GEMINI_API_KEY` (mark as secret)
   - Optional: Set other variables (defaults work fine)

3. **Deploy**
   - Vercel will auto-detect Python and start building
   - Wait ~2-5 minutes for first build
   - Get your URL: `your-project.vercel.app`

4. **Verify Deployment**
   - Frontend: `https://your-project.vercel.app/`
   - Health: `https://your-project.vercel.app/health`
   - API Docs: `https://your-project.vercel.app/docs`

**For detailed instructions, see [VERCEL_DEPLOYMENT_GUIDE.md](VERCEL_DEPLOYMENT_GUIDE.md)**

#### ⚠️ Important Limitations

**Vercel Serverless Constraints:**
- **No Persistent Storage**: ChromaDB data is ephemeral (use `/tmp` or external database)
- **10-Second Timeout**: Free tier functions timeout after 10 seconds
- **Cold Starts**: First request after inactivity: 5-10 seconds
- **No Background Tasks**: Scheduled scraper cannot run
- **Commercial Use**: Free tier restricted to personal/hobby projects

**Recommendations:**
- Use external database (Supabase, MongoDB Atlas) for production
- Disable scheduled scraper or use external cron service
- Consider Vercel Pro ($20/month) for 60-second timeout and commercial use
- Optimize queries to stay under 10-second limit

#### Vercel Free Tier Limits

- **Bandwidth**: 100 GB/month
- **Build Minutes**: 6,000/month
- **Function Invocations**: 100 GB-hours/month
- **Function Timeout**: 10 seconds
- **Function Memory**: 1GB
- **Commercial Use**: ❌ Restricted (personal/hobby only)

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
│   ├── index.py           # Vercel serverless handler
│   └── main.py            # FastAPI app
├── ingestion/              # Document processing
├── vector_store/           # ChromaDB integration
├── retrieval/              # RAG implementation
├── scrapers/               # Web scraping
├── scripts/                # Utility scripts
├── static/                 # Frontend files
├── data/                   # Source data
├── chroma_db/              # Vector database (local)
├── vercel.json             # Vercel configuration
├── Dockerfile              # Optional (for other platforms)
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

