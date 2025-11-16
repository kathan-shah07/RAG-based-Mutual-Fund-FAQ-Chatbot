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

### Railway Deployment (Free Tier)

This application is configured for easy deployment on Railway with automatic deployments from GitHub.

#### Prerequisites

- GitHub account with repository
- Railway account (free tier available)
- Gemini API key

#### Deployment Steps

1. **Prepare Your Repository**
   - Ensure all code is committed and pushed to GitHub
   - The repository should include:
     - `Dockerfile`
     - `requirements.txt`
     - `railway.json` (optional)
     - All application code

2. **Create Railway Account**
   - Go to [railway.app](https://railway.app)
   - Sign up using your GitHub account
   - Verify your email

3. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Authorize Railway to access your GitHub account
   - Select your repository

4. **Configure Environment Variables**
   In Railway dashboard → Service → Variables, add:
   
   **Required:**
   - `GEMINI_API_KEY`: Your Gemini API key (mark as secret)
   - `API_HOST`: `0.0.0.0` (required for Railway)
   
   **Optional (with defaults):**
   - `GEMINI_MODEL`: `gemini-1.5-flash`
   - `GEMINI_EMBEDDING_MODEL`: `models/embedding-001`
   - `CHROMA_DB_PATH`: `/app/chroma_db`
   - `DATA_DIR`: `/app/data/mutual_funds`
   - `COLLECTION_NAME`: `mutual_funds`
   - `CHUNK_SIZE`: `1000`
   - `CHUNK_OVERLAP`: `200`
   - `TOP_K_RESULTS`: `5`

   **Note:** Railway automatically sets `PORT` - do not override it.

5. **Configure Persistent Storage**
   - In Railway dashboard → Service → Volumes
   - Click "Add Volume"
   - Mount path: `/app/chroma_db`
   - This ensures ChromaDB data persists across deployments

   (Optional) Add volume for data directory:
   - Mount path: `/app/data`

6. **Enable Auto-Deploy**
   - In Railway dashboard → Service → Settings
   - Ensure "Auto Deploy" is enabled (default)
   - Select branch: `main` or `master`
   - Railway will automatically deploy on every push

7. **Deploy**
   - Railway will automatically detect the Dockerfile and start building
   - Monitor the deployment logs in the Railway dashboard
   - Once deployed, Railway will provide a URL like: `your-service.up.railway.app`

8. **Verify Deployment**
   - Test health endpoint: `https://your-service.up.railway.app/health`
   - Test frontend: `https://your-service.up.railway.app/`
   - Test API: `https://your-service.up.railway.app/api/v1/query`

#### Post-Deployment

1. **Ingest Initial Data**
   ```bash
   curl -X POST "https://your-service.up.railway.app/api/v1/ingest" \
     -H "Content-Type: application/json" \
     -d '{"upsert": true}'
   ```

2. **Configure Scheduled Scraper (Optional)**
   - Edit `scraper_config.json` in your repository
   - Set schedule settings (consider longer intervals on free tier)
   - Push changes to trigger auto-deploy

#### Railway Free Tier Limits

- **RAM**: 512MB
- **Storage**: 1GB (including volumes)
- **Bandwidth**: 100GB/month
- **Deployments**: Unlimited

**Recommendations for Free Tier:**
- Disable or use longer intervals for scheduled scraper
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

