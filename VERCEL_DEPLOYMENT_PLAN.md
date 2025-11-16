# Complete Vercel Deployment Plan

## Overview

This document provides a comprehensive plan for deploying the MF-Chatbot FastAPI application on Vercel's serverless platform.

## Architecture Considerations

### Vercel Serverless Model

Vercel uses a **serverless function** model where:
- Each API request invokes a separate function instance
- Functions are stateless and ephemeral
- No persistent file system (except `/tmp` which is cleared)
- Functions have execution time limits (10s free, 60s pro)
- Cold starts occur after inactivity

### Application Adaptations Required

Your FastAPI app needs these adaptations:

1. **ChromaDB Storage**
   - ❌ Cannot use local file storage (ephemeral)
   - ✅ Must use external database or `/tmp` (temporary)

2. **Startup Events**
   - ❌ `@app.on_event("startup")` runs on every cold start
   - ✅ Consider lazy initialization instead

3. **Scheduled Tasks**
   - ❌ Cannot run background processes
   - ✅ Use external cron service (GitHub Actions)

4. **Playwright Scraper**
   - ⚠️ May not work due to size/execution limits
   - ✅ Consider disabling or using external service

## Pre-Deployment Checklist

### Code Preparation
- [x] `vercel.json` configuration file created
- [x] `api/index.py` handler created
- [x] `mangum` added to requirements.txt
- [x] FastAPI app compatible with serverless
- [ ] External database configured (if using persistent storage)
- [ ] Scheduled scraper disabled or externalized

### Configuration Files
- [x] `vercel.json` - Vercel configuration
- [x] `api/index.py` - Serverless handler
- [x] `requirements.txt` - Includes mangum
- [ ] `.env.example` - Environment variable template

### Environment Variables Needed
- [ ] `GEMINI_API_KEY` (required)
- [ ] `CHROMA_DB_PATH=/tmp/chroma_db` (ephemeral)
- [ ] `DATA_DIR=/tmp/data/mutual_funds` (ephemeral)
- [ ] Other optional variables

## Deployment Steps

### Phase 1: Repository Preparation

#### Step 1: Verify Code Structure
```
MF-Chatbot/
├── api/
│   ├── index.py          # Vercel handler (NEW)
│   ├── main.py           # FastAPI app
│   └── ...
├── vercel.json           # Vercel config (NEW)
├── requirements.txt      # Includes mangum
└── ...
```

#### Step 2: Commit and Push
```bash
git add .
git commit -m "Configure for Vercel deployment"
git push origin main
```

### Phase 2: Vercel Setup

#### Step 3: Create Vercel Account
1. Go to [vercel.com](https://vercel.com)
2. Sign up with GitHub (recommended)
3. Verify email if required

#### Step 4: Import Project
1. Click **"Add New"** → **"Project"**
2. Select your GitHub repository: `MF-Chatbot`
3. Vercel will auto-detect Python

#### Step 5: Configure Build Settings
**Framework Preset:** Other
**Root Directory:** `./` (default)
**Build Command:** (leave empty)
**Output Directory:** (leave empty)
**Install Command:** `pip install -r requirements.txt`

**Note:** Vercel automatically detects Python and installs dependencies.

#### Step 6: Set Environment Variables
Navigate to: **Settings → Environment Variables**

**Required:**
```
GEMINI_API_KEY=your_gemini_api_key_here
```

**Recommended:**
```
CHROMA_DB_PATH=/tmp/chroma_db
DATA_DIR=/tmp/data/mutual_funds
GEMINI_MODEL=gemini-1.5-flash
GEMINI_EMBEDDING_MODEL=models/embedding-001
API_HOST=0.0.0.0
```

**Important:**
- Mark `GEMINI_API_KEY` as **Secret**
- Use `/tmp` paths for ephemeral storage
- Variables are available in all environments (Production, Preview, Development)

#### Step 7: Configure Function Settings
Navigate to: **Settings → Functions**

**For `api/index.py`:**
- **Max Duration**: 10 seconds (free tier) or 60 seconds (pro)
- **Memory**: 1024 MB (default)

**Note:** These can also be set in `vercel.json`.

### Phase 3: Deployment

#### Step 8: Deploy
1. Click **"Deploy"** button
2. Monitor build logs
3. Expected build time: 2-5 minutes
   - Installing dependencies: ~2-3 min
   - Building functions: ~1-2 min

#### Step 9: Monitor Deployment
Watch for:
- ✅ Build completes successfully
- ✅ Functions deploy correctly
- ✅ No errors in logs
- ✅ Application URL generated

**Common Issues:**
- Build fails: Check requirements.txt
- Import errors: Verify Python version
- Timeout errors: Check function duration settings

### Phase 4: Post-Deployment

#### Step 10: Verify Deployment
1. **Health Check:**
   ```bash
   curl https://your-project.vercel.app/health
   ```
   Expected: `{"status":"healthy",...}`

2. **Frontend:**
   - Visit: `https://your-project.vercel.app/`
   - Should see chat interface

3. **API Docs:**
   - Visit: `https://your-project.vercel.app/docs`
   - Should see Swagger UI

#### Step 11: Test Endpoints
```bash
# Health check
curl https://your-project.vercel.app/health

# Query endpoint
curl -X POST "https://your-project.vercel.app/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the expense ratio?"}'
```

**Note:** First request may be slow (cold start: 5-10 seconds)

#### Step 12: Ingest Data (if using /tmp storage)
```bash
curl -X POST "https://your-project.vercel.app/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{"upsert": true}'
```

**Important:** Data in `/tmp` is ephemeral and will be lost. For production, use external database.

## Production Considerations

### Option 1: Use External Database (Recommended)

**For ChromaDB, consider:**

1. **Supabase** (Free Tier)
   - PostgreSQL with vector extension
   - 500 MB storage
   - Good for small projects

2. **MongoDB Atlas** (Free Tier)
   - 512 MB storage
   - Can store ChromaDB data
   - Easy integration

3. **Pinecone** (Free Tier)
   - Purpose-built vector database
   - 1 index, 100K vectors
   - Best for vector search

**Implementation Steps:**
1. Set up external database
2. Modify `vector_store/chroma_store.py` to use remote storage
3. Update environment variables
4. Redeploy

### Option 2: Accept Ephemeral Storage

**For Development/Testing:**
- Use `/tmp/chroma_db` (ephemeral)
- Data resets on each cold start
- Good for testing only

**Limitations:**
- Data lost between cold starts
- Not suitable for production
- Each cold start requires re-ingestion

### Option 3: Hybrid Approach

**Recommended Architecture:**
- **Frontend + API**: Vercel (serverless)
- **Database**: External service (Supabase/MongoDB)
- **Scraping**: External service or GitHub Actions
- **Scheduled Tasks**: GitHub Actions (cron)

## Configuration Optimization

### Performance Optimization

1. **Reduce Cold Starts**
   - Keep functions warm (Pro tier helps)
   - Minimize startup code
   - Lazy initialization

2. **Optimize Function Size**
   - Remove unnecessary dependencies
   - Use smaller models if possible
   - Minimize Playwright usage

3. **Query Optimization**
   - Reduce `k` value in RAG queries
   - Cache frequent queries
   - Optimize Gemini API calls

### Cost Optimization

1. **Free Tier Limits**
   - 100 GB-hours/month functions
   - 100 GB bandwidth/month
   - Monitor usage in dashboard

2. **Pro Tier Benefits** ($20/month)
   - 60-second timeout (vs 10s)
   - Commercial use allowed
   - Better performance
   - More bandwidth

## Monitoring & Maintenance

### Key Metrics to Monitor

1. **Function Invocations**
   - Check Vercel dashboard → Analytics
   - Monitor usage vs limits

2. **Function Duration**
   - Check logs for timeout errors
   - Optimize slow endpoints

3. **Error Rate**
   - Monitor error logs
   - Check for cold start issues

4. **Cold Start Frequency**
   - Track first request latency
   - Consider Pro tier if frequent

### Regular Maintenance

1. **Weekly:**
   - Check function logs
   - Monitor error rates
   - Review usage metrics

2. **Monthly:**
   - Review and update dependencies
   - Check for security updates
   - Optimize slow endpoints

3. **As Needed:**
   - Update Gemini API key if expired
   - Adjust function settings
   - Scale up if needed

## Troubleshooting Guide

### Issue: Build Fails
**Symptoms:** Build logs show errors
**Solutions:**
- Check `requirements.txt` for version conflicts
- Verify Python version compatibility
- Check for missing dependencies
- Review build logs for specific errors

### Issue: Function Timeout
**Symptoms:** Requests timeout after 10 seconds
**Solutions:**
- Optimize query processing
- Reduce `k` value in RAG queries
- Upgrade to Pro for 60-second timeout
- Consider caching strategies

### Issue: Data Not Persisting
**Symptoms:** Data lost between requests
**Solutions:**
- Expected with `/tmp` storage (ephemeral)
- Use external database for persistence
- Consider Supabase/MongoDB Atlas

### Issue: Cold Starts Too Slow
**Symptoms:** First request takes 5-10 seconds
**Solutions:**
- Normal behavior for serverless
- Subsequent requests are fast
- Consider Vercel Pro for better performance
- Optimize startup code

### Issue: Import Errors
**Symptoms:** Function fails with import errors
**Solutions:**
- Verify all dependencies in `requirements.txt`
- Check Python version compatibility
- Ensure `mangum` is installed
- Review function logs

### Issue: Playwright Not Working
**Symptoms:** Scraper fails or times out
**Solutions:**
- Browser dependencies may be too large
- Consider disabling scraper
- Use external scraping service
- Check function size limits

## Security Considerations

### Environment Variables
- ✅ Mark sensitive variables as "Secret" in Vercel
- ✅ Never commit `.env` file (already gitignored)
- ✅ Rotate API keys periodically

### API Security
- Consider adding API authentication
- Rate limiting (Vercel Pro includes this)
- CORS configuration (currently allows all origins)

### Data Security
- No persistent storage on Vercel (use external DB)
- Encrypt sensitive data in external database
- Use HTTPS (automatic on Vercel)

## Cost Estimation

### Vercel Free Tier
- **Cost**: $0/month
- **Limits:**
  - 100 GB-hours/month functions
  - 100 GB bandwidth/month
  - 10-second function timeout
  - Personal/hobby use only

### Vercel Pro Tier (if needed)
- **Cost**: $20/month
- **Benefits:**
  - 60-second function timeout
  - Commercial use allowed
  - Better performance
  - More bandwidth
  - Priority support

### External Services (if using)
- **Supabase**: Free tier available
- **MongoDB Atlas**: Free tier available
- **Pinecone**: Free tier available

## Rollback Plan

If deployment fails or issues occur:

1. **Immediate Rollback:**
   - Vercel dashboard → Deployments
   - Find previous successful deployment
   - Click "Promote to Production"

2. **Code Rollback:**
   - Revert problematic commit in Git
   - Push to trigger auto-deploy
   - Vercel will deploy new version

3. **Configuration Rollback:**
   - Revert environment variable changes
   - Revert function settings if needed

## Success Criteria

✅ Deployment is successful when:
1. Build completes without errors
2. Functions deploy correctly
3. Health check returns 200 OK
4. Frontend loads correctly
5. API endpoints respond correctly
6. No critical errors in logs
7. Cold starts are acceptable (<10 seconds)

## Next Steps After Deployment

1. **Set up external database** (if needed for production)
2. **Configure monitoring** (Vercel Analytics)
3. **Set up custom domain** (optional)
4. **Optimize for serverless** (if needed)
5. **Set up external cron** (for scheduled tasks)

## Support Resources

- Vercel Docs: https://vercel.com/docs
- Vercel Discord: https://vercel.com/discord
- FastAPI Docs: https://fastapi.tiangolo.com
- Mangum Docs: https://mangum.io

---

**Last Updated:** [Current Date]
**Deployment Status:** Ready for Vercel
**Estimated Deployment Time:** 10-15 minutes (first time)

