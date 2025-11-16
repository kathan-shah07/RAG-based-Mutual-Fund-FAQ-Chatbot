# Vercel Deployment Guide

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- GitHub repository with your code
- Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- Vercel account (sign up at [vercel.com](https://vercel.com))

### Step-by-Step Deployment

#### 1. Connect Repository to Vercel
1. Go to [vercel.com](https://vercel.com) and sign in with GitHub
2. Click **"Add New"** → **"Project"**
3. Import your `MF-Chatbot` repository
4. Vercel will auto-detect the Python project

#### 2. Configure Build Settings
Vercel should auto-detect:
- **Framework Preset**: Other
- **Root Directory**: `./` (default)
- **Build Command**: (leave empty, Vercel handles it)
- **Output Directory**: (leave empty)
- **Install Command**: `pip install -r requirements.txt`

#### 3. Set Environment Variables
Go to **Settings → Environment Variables** and add:

**Required:**
```
GEMINI_API_KEY=your_api_key_here
```

**Optional (defaults work fine):**
```
API_HOST=0.0.0.0
CHROMA_DB_PATH=/tmp/chroma_db
DATA_DIR=/tmp/data/mutual_funds
GEMINI_MODEL=gemini-1.5-flash
GEMINI_EMBEDDING_MODEL=models/embedding-001
```

**Important Notes:**
- Use `/tmp` paths for ChromaDB (ephemeral storage)
- Vercel functions have 10-second timeout (free tier)
- No persistent storage available

#### 4. Deploy
1. Click **"Deploy"**
2. Wait ~2-5 minutes for build
3. Get your URL: `your-project.vercel.app`

#### 5. Verify Deployment
- Frontend: `https://your-project.vercel.app/`
- Health: `https://your-project.vercel.app/health`
- API Docs: `https://your-project.vercel.app/docs`

## ⚠️ Important Limitations

### Vercel Serverless Constraints

1. **No Persistent Storage**
   - ChromaDB data is stored in `/tmp` (ephemeral)
   - Data is lost between function invocations
   - **Solution**: Use external database (Supabase, MongoDB Atlas free tier)

2. **10-Second Timeout** (Free Tier)
   - Functions timeout after 10 seconds
   - Complex RAG queries may exceed this
   - **Solution**: Upgrade to Pro ($20/month) for 60-second timeout

3. **Cold Starts**
   - First request after inactivity: 5-10 seconds
   - Subsequent requests: <1 second
   - **Solution**: Use Vercel Pro for better performance

4. **No Background Tasks**
   - Scheduled scraper cannot run
   - **Solution**: Use external cron service (GitHub Actions, cron-job.org)

5. **Playwright Challenges**
   - Browser dependencies may exceed function size limits
   - **Solution**: Disable scraper or use external service

6. **Commercial Use**
   - Free tier: Personal/hobby projects only
   - **Solution**: Upgrade to Pro ($20/month) for commercial use

## 🔧 Required Modifications

### For Production Use on Vercel

1. **Use External Database for ChromaDB**
   - Option A: Supabase (free tier available)
   - Option B: MongoDB Atlas (free tier available)
   - Option C: Pinecone (vector database, free tier available)

2. **Disable Scheduled Scraper**
   - Edit `scraper_config.json`:
     ```json
     {
       "schedule": {
         "enabled": false
       }
     }
     ```

3. **Optimize for Serverless**
   - Initialize vector store lazily (on first request)
   - Cache frequently used data
   - Minimize startup time

## 📊 Vercel Free Tier Limits

- **Bandwidth**: 100 GB/month
- **Build Minutes**: 6,000/month (very generous!)
- **Function Invocations**: 100 GB-hours/month
- **Function Timeout**: 10 seconds
- **Function Memory**: 1GB
- **Concurrent Functions**: 100
- **Commercial Use**: ❌ Restricted (personal/hobby only)

## 💰 Upgrading to Pro ($20/month)

**Benefits:**
- ✅ 60-second function timeout
- ✅ Commercial use allowed
- ✅ Better performance
- ✅ More bandwidth
- ✅ Priority support

## 🆘 Troubleshooting

### Build Fails
- Check build logs in Vercel dashboard
- Verify `requirements.txt` is correct
- Check Python version (Vercel uses Python 3.9+)

### Function Timeout
- Optimize query processing
- Reduce `k` value in RAG queries
- Upgrade to Pro for 60-second timeout

### Data Not Persisting
- Expected behavior - Vercel has no persistent storage
- Use external database (see Required Modifications)

### Cold Starts Too Slow
- First request is always slow (5-10 seconds)
- Subsequent requests are fast (<1 second)
- Consider Vercel Pro for better performance

### Playwright Not Working
- Browser dependencies may be too large
- Consider disabling scraper functionality
- Use external scraping service if needed

## 📚 Alternative: Hybrid Approach

**Recommended for Production:**

1. **Frontend + API**: Deploy on Vercel
2. **Database**: Use Supabase/MongoDB Atlas (free tier)
3. **Scheduled Tasks**: Use GitHub Actions (cron workflow)
4. **Scraping**: Use external service or disable

This gives you:
- ✅ Fast CDN for frontend
- ✅ Serverless API scaling
- ✅ Persistent database
- ✅ Scheduled tasks
- ✅ Free tier options

## 🎯 Next Steps

1. **Deploy to Vercel** (follow steps above)
2. **Set up external database** (if needed)
3. **Test all endpoints**
4. **Monitor function logs**
5. **Optimize for serverless** (if needed)

## 📖 Additional Resources

- Vercel Python Docs: https://vercel.com/docs/concepts/functions/serverless-functions/runtimes/python
- Vercel Deployment Docs: https://vercel.com/docs/deployments/overview
- FastAPI on Vercel: https://vercel.com/guides/deploying-fastapi-with-vercel

---

**Need Help?**
- Vercel Docs: https://vercel.com/docs
- Vercel Discord: https://vercel.com/discord
- Check deployment logs in Vercel dashboard

