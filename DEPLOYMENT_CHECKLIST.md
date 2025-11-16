# Railway Deployment Checklist

Use this checklist to ensure a smooth deployment on Railway.

## Pre-Deployment

### Code Preparation
- [ ] All code is committed to Git
- [ ] Code is pushed to GitHub
- [ ] `.gitignore` excludes `.env`, `chroma_db/`, `venv/`, etc.
- [ ] `Dockerfile` exists and is optimized
- [ ] `railway.json` is configured
- [ ] `requirements.txt` includes all dependencies

### Credentials Ready
- [ ] Gemini API key obtained from [Google AI Studio](https://makersuite.google.com/app/apikey)
- [ ] Railway account created (sign up at [railway.app](https://railway.app))

## Railway Setup

### Project Creation
- [ ] Created new Railway project
- [ ] Connected GitHub repository
- [ ] Railway detected Dockerfile automatically

### Environment Variables
- [ ] `GEMINI_API_KEY` set (marked as Secret)
- [ ] `API_HOST` set to `0.0.0.0` (optional, defaults work)
- [ ] Optional variables set if needed (see deployment plan)

### Persistent Storage (CRITICAL)
- [ ] Volume created for `/app/chroma_db`
- [ ] Volume size set (start with 100MB)
- [ ] Optional: Volume created for `/app/data` if needed

### Build & Deploy Settings
- [ ] Auto-deploy enabled
- [ ] Correct branch selected (main/master)
- [ ] Healthcheck path set to `/health`
- [ ] Healthcheck timeout set to 100 seconds

## Deployment

### Build Process
- [ ] Build started automatically
- [ ] Build logs show no errors
- [ ] Build completes successfully (~5-10 minutes)

### Application Startup
- [ ] Container starts successfully
- [ ] Health check passes
- [ ] Application URL generated
- [ ] No crash loops in logs

## Post-Deployment Verification

### Basic Checks
- [ ] Health endpoint works: `https://your-service.up.railway.app/health`
- [ ] Frontend loads: `https://your-service.up.railway.app/`
- [ ] API docs accessible: `https://your-service.up.railway.app/docs`

### Data Ingestion
- [ ] Data ingestion endpoint works
- [ ] Initial data ingested successfully
- [ ] ChromaDB collection has documents

### Functionality Tests
- [ ] Query endpoint responds correctly
- [ ] Frontend can send queries
- [ ] Answers are returned with sources
- [ ] No critical errors in logs

## Monitoring Setup

### Logs
- [ ] Can view application logs in Railway dashboard
- [ ] Logs show successful startup
- [ ] No error messages in logs

### Metrics
- [ ] Memory usage monitored (< 512MB on free tier)
- [ ] Storage usage monitored (< 1GB on free tier)
- [ ] CPU usage reasonable

## Optimization (Optional)

### Performance
- [ ] Scheduled scraper disabled or optimized for free tier
- [ ] Chunk sizes optimized if needed
- [ ] Resource usage within limits

### Security
- [ ] Sensitive variables marked as Secret
- [ ] No API keys in code or logs
- [ ] CORS configured appropriately

## Troubleshooting (If Issues)

### Build Fails
- [ ] Check build logs for specific errors
- [ ] Verify `requirements.txt` is correct
- [ ] Check Dockerfile syntax

### App Crashes
- [ ] Check environment variables
- [ ] Verify `GEMINI_API_KEY` is correct
- [ ] Check application logs for errors

### Data Not Persisting
- [ ] Verify volume is mounted correctly
- [ ] Check volume mount path matches config
- [ ] Ensure volume has space

### Slow Performance
- [ ] Check Railway region
- [ ] Monitor resource usage
- [ ] Consider upgrading to Pro tier if needed

## Success Criteria

✅ Deployment is successful when:
1. Build completes without errors
2. Container runs continuously
3. Health check returns 200 OK
4. Frontend loads and works
5. API endpoints respond correctly
6. Data ingestion works
7. Query endpoint returns answers
8. No critical errors in logs

---

**Quick Reference:**
- Full Plan: `RAILWAY_DEPLOYMENT_PLAN.md`
- Quick Guide: `RAILWAY_DEPLOYMENT_GUIDE.md`
- Railway Docs: https://docs.railway.app

**Need Help?**
- Check Railway logs in dashboard
- Review deployment plan document
- Check Railway Discord: https://discord.gg/railway

