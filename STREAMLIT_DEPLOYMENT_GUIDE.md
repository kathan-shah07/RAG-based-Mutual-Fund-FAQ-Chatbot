# Streamlit Cloud Deployment Guide

## 🚀 Quick Start

Deploy your Mutual Fund FAQ Assistant on Streamlit Cloud in minutes!

### Prerequisites
- GitHub repository with your code
- Streamlit Cloud account (free) - [share.streamlit.io](https://share.streamlit.io)
- Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

## Step-by-Step Deployment

### Step 1: Prepare Your Repository

Make sure your repository has:
- ✅ `app.py` - Streamlit app entry point
- ✅ `requirements.txt` - Python dependencies
- ✅ `.streamlit/config.toml` - Streamlit configuration (optional)
- ✅ All application code (api/, ingestion/, retrieval/, etc.)

### Step 2: Push to GitHub

```bash
git add .
git commit -m "Configure for Streamlit deployment"
git push origin main
```

### Step 3: Deploy on Streamlit Cloud

1. **Sign up/Login**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with your GitHub account

2. **New App**
   - Click **"New app"** button
   - Select your repository: `MF-Chatbot`
   - Select branch: `main` (or your default branch)
   - Main file path: `app.py`

3. **Configure**
   - **App URL**: Choose your custom subdomain (optional)
   - **Python version**: 3.11 (recommended)

4. **Set Secrets** (Environment Variables)
   - Click **"Advanced settings"**
   - Go to **"Secrets"** tab
   - Add your secrets:
   ```toml
   GEMINI_API_KEY=your_gemini_api_key_here
   API_BASE_URL=http://localhost:8000
   ```
   
   **Note:** For Streamlit-only deployment, you can also run the FastAPI backend within Streamlit or use a separate service.

5. **Deploy**
   - Click **"Deploy"**
   - Wait 2-5 minutes for deployment
   - Your app will be live at: `https://your-app-name.streamlit.app`

## Architecture Options

### Option 1: Streamlit + Separate FastAPI Backend (Recommended)

**Setup:**
- Streamlit app (`app.py`) calls FastAPI API endpoints
- FastAPI backend runs separately (Railway, Render, etc.)
- Set `API_BASE_URL` in Streamlit secrets to your FastAPI URL

**Pros:**
- ✅ Separation of concerns
- ✅ Can scale independently
- ✅ FastAPI API can be used by other clients

**Cons:**
- ⚠️ Requires two deployments

### Option 2: Streamlit with Embedded Backend

**Setup:**
- Run FastAPI server within Streamlit app
- Use subprocess or threading to start FastAPI
- Streamlit calls localhost API

**Pros:**
- ✅ Single deployment
- ✅ Simpler setup

**Cons:**
- ⚠️ More complex code
- ⚠️ Resource sharing between Streamlit and FastAPI

### Option 3: Pure Streamlit (No FastAPI)

**Setup:**
- Rewrite backend logic directly in Streamlit
- No FastAPI dependency

**Pros:**
- ✅ Simplest deployment
- ✅ Single codebase

**Cons:
- ⚠️ Requires code refactoring
- ⚠️ Lose FastAPI API endpoints

## Current Setup

The current `app.py` uses **Option 1** - it calls FastAPI endpoints. You have two choices:

### Choice A: Deploy Both Separately
1. Deploy FastAPI backend on Railway/Render
2. Deploy Streamlit app on Streamlit Cloud
3. Set `API_BASE_URL` in Streamlit secrets

### Choice B: Run FastAPI in Streamlit
I can create a version that runs FastAPI within Streamlit. Let me know if you want this!

## Environment Variables (Secrets)

In Streamlit Cloud → Settings → Secrets, add:

```toml
GEMINI_API_KEY=your_api_key_here
API_BASE_URL=https://your-fastapi-backend.com
CHROMA_DB_PATH=./chroma_db
DATA_DIR=./data/mutual_funds
```

## Streamlit Cloud Free Tier

- ✅ **Unlimited apps**
- ✅ **Unlimited usage**
- ✅ **Custom domains** (Pro feature)
- ✅ **Private repos** (Pro feature)
- ⚠️ **Apps sleep after 7 days of inactivity** (Pro: always on)

## Troubleshooting

### App Won't Deploy
- Check `app.py` exists in root directory
- Verify `requirements.txt` is correct
- Check build logs in Streamlit Cloud dashboard

### API Connection Errors
- Verify `API_BASE_URL` is set correctly in secrets
- Make sure FastAPI backend is running and accessible
- Check CORS settings if needed

### Import Errors
- Verify all dependencies in `requirements.txt`
- Check Python version compatibility (use 3.11)

### App Crashes
- Check Streamlit Cloud logs
- Verify environment variables are set
- Test locally first: `streamlit run app.py`

## Local Testing

Before deploying, test locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Run Streamlit app
streamlit run app.py

# Or run with custom port
streamlit run app.py --server.port 8501
```

## Updating Your App

1. Make changes to your code
2. Commit and push to GitHub
3. Streamlit Cloud automatically redeploys
4. Or manually trigger redeploy in dashboard

## Custom Domain (Pro Feature)

1. Go to Settings → Custom domain
2. Add your domain
3. Update DNS records as instructed
4. SSL certificate is automatic

## Monitoring

- **View logs**: Streamlit Cloud dashboard → Your app → Logs
- **View metrics**: Dashboard shows usage statistics
- **Error tracking**: Errors appear in logs

## Next Steps

1. ✅ Deploy on Streamlit Cloud
2. ✅ Set environment variables
3. ✅ Test your app
4. ✅ Share your app URL!

---

**Need Help?**
- Streamlit Docs: https://docs.streamlit.io
- Streamlit Community: https://discuss.streamlit.io
- Check deployment logs in Streamlit Cloud dashboard

