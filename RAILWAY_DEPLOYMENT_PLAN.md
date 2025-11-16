# Railway Deployment Plan for MF-Chatbot

## Overview
This document outlines the complete plan for deploying the MF-Chatbot application on Railway, including prerequisites, step-by-step instructions, configuration, and post-deployment tasks.

## Application Architecture

### Components
- **Backend**: FastAPI application (`api/main.py`)
- **Vector Database**: ChromaDB (persistent storage required)
- **Frontend**: Static HTML/CSS/JS files served by FastAPI
- **Scraper**: Playwright-based web scraper (optional scheduled runs)
- **LLM**: Google Gemini API (external service)

### Key Dependencies
- Python 3.11
- Playwright (Chromium browser)
- ChromaDB (vector database)
- FastAPI + Uvicorn (web server)

## Pre-Deployment Checklist

### 1. Repository Preparation
- [x] Code is committed to Git
- [x] Repository is pushed to GitHub
- [x] `.gitignore` excludes sensitive files (`.env`, `chroma_db/`, etc.)
- [x] `Dockerfile` is present and optimized
- [x] `railway.json` is configured
- [x] `requirements.txt` includes all dependencies

### 2. Required Credentials
- [ ] Gemini API Key (from Google AI Studio)
- [ ] Railway account (GitHub OAuth)

### 3. Configuration Files Status
- [x] `Dockerfile` - Ready
- [x] `railway.json` - Ready
- [x] `requirements.txt` - Ready
- [x] `scraper_config.json` - Ready (optional)

## Deployment Steps

### Phase 1: Railway Setup

#### Step 1: Create Railway Account
1. Go to [railway.app](https://railway.app)
2. Click "Start a New Project"
3. Sign up with GitHub (recommended for auto-deploy)
4. Verify email if required

#### Step 2: Create New Project
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Authorize Railway to access your GitHub account (if first time)
4. Select your repository: `MF-Chatbot`
5. Railway will automatically detect the Dockerfile

#### Step 3: Configure Environment Variables
Navigate to: **Service → Variables**

**Required Variables:**
```
GEMINI_API_KEY=your_gemini_api_key_here
```

**Optional Variables (with defaults):**
```
GEMINI_MODEL=gemini-1.5-flash
GEMINI_EMBEDDING_MODEL=models/embedding-001
CHROMA_DB_PATH=/app/chroma_db
DATA_DIR=/app/data/mutual_funds
COLLECTION_NAME=mutual_funds
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RESULTS=5
API_HOST=0.0.0.0
```

**Important Notes:**
- Mark `GEMINI_API_KEY` as **Secret** (click the lock icon)
- Do NOT set `PORT` variable - Railway sets this automatically
- All paths should use `/app/` prefix for container paths

#### Step 4: Configure Persistent Storage (CRITICAL)
Navigate to: **Service → Volumes**

**Required Volume:**
- **Mount Path**: `/app/chroma_db`
- **Name**: `chroma_db` (or any name)
- **Size**: Start with 100MB (can increase later)

**Optional Volume (for data persistence):**
- **Mount Path**: `/app/data`
- **Name**: `data`
- **Size**: 50MB

**Why This Matters:**
- Without volumes, ChromaDB data will be lost on every deployment
- Volumes persist data across deployments and restarts

#### Step 5: Configure Build Settings
Navigate to: **Service → Settings**

**Build Settings:**
- **Builder**: Dockerfile (auto-detected)
- **Dockerfile Path**: `Dockerfile` (default)
- **Build Command**: (leave empty, uses Dockerfile)

**Deploy Settings:**
- **Start Command**: (leave empty, uses Dockerfile CMD)
- **Healthcheck Path**: `/health` (configured in railway.json)
- **Healthcheck Timeout**: 100 seconds

#### Step 6: Enable Auto-Deploy
Navigate to: **Service → Settings → Source**

- **Auto Deploy**: Enabled (default)
- **Branch**: `main` or `master` (your default branch)
- Railway will automatically deploy on every push

### Phase 2: Initial Deployment

#### Step 7: Trigger First Deployment
1. Railway will automatically start building after project creation
2. Monitor build logs in Railway dashboard
3. Expected build time: 5-10 minutes (first build)
   - Installing system dependencies: ~2 min
   - Installing Python packages: ~3-5 min
   - Installing Playwright Chromium: ~2-3 min

#### Step 8: Monitor Deployment
Watch for:
- ✅ Build completes successfully
- ✅ Container starts
- ✅ Health check passes (`/health` endpoint)
- ✅ Application URL is generated

**Common Issues:**
- Build fails: Check logs for missing dependencies
- Container crashes: Check logs for runtime errors
- Health check fails: Verify `/health` endpoint works

### Phase 3: Post-Deployment

#### Step 9: Verify Deployment
1. **Health Check:**
   ```bash
   curl https://your-service.up.railway.app/health
   ```
   Expected: `{"status":"healthy","collection_info":{...}}`

2. **Frontend:**
   - Visit: `https://your-service.up.railway.app/`
   - Should see the chat interface

3. **API Docs:**
   - Visit: `https://your-service.up.railway.app/docs`
   - Should see Swagger UI

#### Step 10: Ingest Initial Data
The application needs data in ChromaDB to answer questions.

**Option A: Using API (Recommended)**
```bash
curl -X POST "https://your-service.up.railway.app/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{"upsert": true}'
```

**Option B: Using Scraper (if data files exist)**
```bash
curl -X POST "https://your-service.up.railway.app/api/v1/scrape"
```

**Note:** If no data files exist in `/app/data/mutual_funds`, you'll need to:
1. Either push data files to your repository, OR
2. Use the scraper endpoint to fetch data first

#### Step 11: Test Query Endpoint
```bash
curl -X POST "https://your-service.up.railway.app/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the expense ratio of Nippon India Large Cap Fund?",
    "return_sources": true
  }'
```

#### Step 12: Configure Custom Domain (Optional)
Navigate to: **Service → Settings → Networking**
- Click "Generate Domain" for a custom Railway domain
- Or add your own custom domain

## Configuration Optimization for Railway

### Memory Optimization (Free Tier: 512MB RAM)

**Recommended Settings:**
1. **Disable Scheduled Scraper** (or use longer intervals):
   ```json
   {
     "schedule": {
       "enabled": false  // or set interval_hours to 24+
     }
   }
   ```

2. **Optimize ChromaDB:**
   - Use smaller chunk sizes if needed
   - Limit collection size

3. **Monitor Resource Usage:**
   - Check Railway dashboard → Metrics
   - Watch for memory spikes

### Storage Optimization (Free Tier: 1GB)

**Storage Breakdown:**
- Application code: ~100MB
- Python packages: ~300MB
- Playwright Chromium: ~200MB
- ChromaDB data: ~100-300MB (grows with data)
- **Total**: ~700-900MB (within 1GB limit)

**Recommendations:**
- Clean up old data periodically
- Use data compression if possible
- Monitor volume usage

### Performance Optimization

1. **Startup Time:**
   - First startup: ~30-60 seconds (initializes ChromaDB, RAG chain)
   - Subsequent startups: ~20-30 seconds

2. **Cold Starts:**
   - Railway free tier may sleep after inactivity
   - First request after sleep: ~30-60 seconds
   - Consider Railway Pro for always-on instances

3. **Scraper Performance:**
   - Disable on free tier (resource intensive)
   - Or run manually via API endpoint

## Monitoring & Maintenance

### Key Metrics to Monitor

1. **Health Endpoint:**
   - `/health` - Should return 200 OK
   - Check collection_info for document count

2. **Resource Usage:**
   - Memory: Should stay under 512MB
   - CPU: Monitor spikes during queries
   - Storage: Monitor volume usage

3. **Application Logs:**
   - Railway dashboard → Deployments → View Logs
   - Check for errors, warnings
   - Monitor API request logs

### Regular Maintenance Tasks

1. **Weekly:**
   - Check application health
   - Review error logs
   - Monitor resource usage

2. **Monthly:**
   - Review and update dependencies
   - Check for security updates
   - Review storage usage

3. **As Needed:**
   - Update Gemini API key if expired
   - Add/remove data sources
   - Adjust scraper schedule

## Troubleshooting Guide

### Issue: Build Fails
**Symptoms:** Build logs show errors
**Solutions:**
- Check `requirements.txt` for version conflicts
- Verify Dockerfile syntax
- Check for missing system dependencies

### Issue: Container Crashes on Startup
**Symptoms:** Container starts then immediately stops
**Solutions:**
- Check application logs for errors
- Verify environment variables are set
- Check if ChromaDB path is writable
- Verify GEMINI_API_KEY is set correctly

### Issue: Health Check Fails
**Symptoms:** `/health` returns 503 or timeout
**Solutions:**
- Check if vector store initializes correctly
- Verify ChromaDB volume is mounted
- Check startup logs for initialization errors
- Increase healthcheck timeout if needed

### Issue: Out of Memory
**Symptoms:** Container restarts frequently, logs show OOM
**Solutions:**
- Disable scheduled scraper
- Reduce chunk sizes
- Upgrade to Railway Pro plan
- Optimize ChromaDB collection size

### Issue: Data Not Persisting
**Symptoms:** Data lost after deployment
**Solutions:**
- Verify volumes are mounted correctly
- Check volume mount paths match config
- Ensure volumes are not being cleared

### Issue: Slow Response Times
**Symptoms:** API requests take >10 seconds
**Solutions:**
- Check Railway region (use closest to users)
- Optimize query parameters (reduce `k` value)
- Check Gemini API response times
- Consider caching frequently asked questions

## Security Considerations

### Environment Variables
- ✅ Never commit `.env` file (already in `.gitignore`)
- ✅ Mark sensitive variables as "Secret" in Railway
- ✅ Rotate API keys periodically

### API Security
- Consider adding API authentication for production
- Rate limiting (Railway Pro includes this)
- CORS configuration (currently allows all origins)

### Data Security
- ChromaDB data is stored in volumes (encrypted at rest by Railway)
- No PII should be stored (application validates this)

## Cost Estimation

### Railway Free Tier
- **Cost**: $0/month
- **Limits:**
  - 512MB RAM
  - 1GB Storage
  - 100GB Bandwidth/month
  - $5 credit/month (for overages)

### Railway Pro Tier (if needed)
- **Cost**: $20/month
- **Benefits:**
  - 8GB RAM
  - 100GB Storage
  - Always-on instances (no cold starts)
  - Better performance

### External Costs
- **Gemini API**: Pay-per-use (check Google AI pricing)
- **Domain**: Optional, ~$10-15/year

## Rollback Plan

If deployment fails or issues occur:

1. **Immediate Rollback:**
   - Railway dashboard → Deployments
   - Find previous successful deployment
   - Click "Redeploy"

2. **Code Rollback:**
   - Revert problematic commit in Git
   - Push to trigger auto-deploy
   - Or manually deploy previous version

3. **Configuration Rollback:**
   - Revert environment variable changes
   - Revert volume configuration if needed

## Success Criteria

✅ Deployment is successful when:
1. Build completes without errors
2. Container starts and stays running
3. Health check returns 200 OK
4. Frontend loads correctly
5. API endpoints respond correctly
6. Data ingestion works
7. Query endpoint returns answers
8. No critical errors in logs

## Next Steps After Deployment

1. **Set up monitoring alerts** (Railway Pro feature)
2. **Configure custom domain** (optional)
3. **Set up CI/CD** (already done with auto-deploy)
4. **Document API usage** for end users
5. **Plan for scaling** if needed

## Support Resources

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Application Issues: Check GitHub repository issues

---

**Last Updated:** [Current Date]
**Deployment Status:** Ready for Production
**Estimated Deployment Time:** 15-20 minutes (first time)

