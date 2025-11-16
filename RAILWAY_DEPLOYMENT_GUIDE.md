# Quick Railway Deployment Guide

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- GitHub repository with your code
- Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- Railway account (sign up at [railway.app](https://railway.app))

### Step-by-Step Deployment

#### 1. Connect Repository to Railway
1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your `MF-Chatbot` repository
4. Railway will auto-detect the Dockerfile and start building

#### 2. Set Environment Variables
Go to **Service → Variables** and add:

**Required:**
```
GEMINI_API_KEY=your_api_key_here
```
*(Click the lock icon to mark as secret)*

**Optional (defaults work fine):**
```
API_HOST=0.0.0.0
CHROMA_DB_PATH=/app/chroma_db
DATA_DIR=/app/data/mutual_funds
```

#### 3. Add Persistent Storage (IMPORTANT!)
Go to **Service → Volumes** and add:

- **Mount Path**: `/app/chroma_db`
- **Size**: 100MB (can increase later)

This ensures your vector database persists across deployments.

#### 4. Wait for Deployment
- Build takes ~5-10 minutes (first time)
- Watch the logs in Railway dashboard
- You'll get a URL like: `your-service.up.railway.app`

#### 5. Verify Deployment
Visit your Railway URL:
- Frontend: `https://your-service.up.railway.app/`
- Health: `https://your-service.up.railway.app/health`
- API Docs: `https://your-service.up.railway.app/docs`

#### 6. Ingest Data
```bash
curl -X POST "https://your-service.up.railway.app/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{"upsert": true}'
```

#### 7. Test It!
Visit your Railway URL and ask a question like:
*"What is the expense ratio of Nippon India Large Cap Fund?"*

## ✅ That's It!

Your application is now live on Railway. Every time you push to GitHub, Railway will automatically redeploy.

## 🔧 Common Issues

### Build Fails
- Check Railway logs for specific errors
- Verify `requirements.txt` is correct
- Ensure Dockerfile is in root directory

### App Crashes
- Check environment variables are set
- Verify `GEMINI_API_KEY` is correct
- Check logs for error messages

### Data Not Persisting
- Ensure volume is mounted at `/app/chroma_db`
- Check volume is not full
- Verify volume mount path matches config

### Slow Performance
- Free tier may sleep after inactivity (cold start)
- First request after sleep takes ~30-60 seconds
- Consider Railway Pro for always-on instances

## 📊 Monitoring

- **Logs**: Railway dashboard → Deployments → View Logs
- **Metrics**: Railway dashboard → Metrics
- **Health**: Visit `/health` endpoint

## 💰 Free Tier Limits

- **RAM**: 512MB
- **Storage**: 1GB total (including volumes)
- **Bandwidth**: 100GB/month
- **$5 credit/month** for overages

## 🎯 Pro Tips

1. **Disable scheduled scraper** on free tier (edit `scraper_config.json`):
   ```json
   "schedule": { "enabled": false }
   ```

2. **Monitor resource usage** in Railway dashboard

3. **Use manual scraping** via API endpoint instead of scheduled

4. **Set up custom domain** (optional) in Service → Settings → Networking

## 📚 Need More Help?

- Full deployment plan: See `RAILWAY_DEPLOYMENT_PLAN.md`
- Railway docs: https://docs.railway.app
- Application README: See `README.md`

---

**Ready to deploy?** Follow steps 1-7 above and you're done! 🎉

