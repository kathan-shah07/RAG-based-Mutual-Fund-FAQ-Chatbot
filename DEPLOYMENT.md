# Deploying to Streamlit Cloud

This guide will walk you through deploying your Mutual Fund FAQ Assistant to Streamlit Cloud.

## Prerequisites

1. **GitHub Account**: Your code needs to be in a GitHub repository
2. **Streamlit Cloud Account**: Sign up at [share.streamlit.io](https://share.streamlit.io) (free)
3. **Google Gemini API Key**: Get one from [Google AI Studio](https://makersuite.google.com/app/apikey)

## Step-by-Step Deployment Guide

### Step 1: Prepare Your Repository

1. **Ensure your code is on GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git push -u origin main
   ```

2. **Important files to include**:
   - ✅ `app.py` (main Streamlit app)
   - ✅ `requirements.txt` (dependencies)
   - ✅ `config.py` (configuration)
   - ✅ All module files (`api/`, `retrieval/`, `vector_store/`, etc.)
   - ✅ `scraper_config.json` (optional, for scraper)
   - ✅ `.streamlit/config.toml` (optional, for Streamlit settings)

3. **Files to exclude** (add to `.gitignore`):
   ```
   venv/
   __pycache__/
   *.pyc
   .env
   .streamlit/secrets.toml
   chroma_db/
   data/downloaded_html/
   node_modules/
   ```

### Step 2: Create Streamlit Cloud Account

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **"Sign in"** and authorize with your GitHub account
3. You'll be redirected to the Streamlit Cloud dashboard

### Step 3: Deploy Your App

1. **Click "New app"** button in the dashboard
2. **Fill in the deployment form**:
   - **Repository**: Select your GitHub repository
   - **Branch**: Select `main` (or your default branch)
   - **Main file path**: Enter `app.py`
   - **App URL**: Choose a custom subdomain (optional)
3. **Click "Deploy"**

### Step 4: Configure Secrets

**IMPORTANT**: Your app requires a Gemini API key to work. Add it via Streamlit Cloud secrets:

1. In your app dashboard, go to **"Settings"** (⚙️ icon)
2. Click on **"Secrets"** tab
3. Add the following secrets:

```toml
GEMINI_API_KEY = "your-gemini-api-key-here"
```

**Optional secrets** (if you want to override defaults):
```toml
GEMINI_MODEL = "gemini-1.5-flash"
GEMINI_EMBEDDING_MODEL = "models/embedding-001"
CHROMA_DB_PATH = "./chroma_db"
COLLECTION_NAME = "mutual_funds"
DATA_DIR = "./data/mutual_funds"
CHUNK_SIZE = "1000"
CHUNK_OVERLAP = "200"
TOP_K_RESULTS = "5"
```

4. **Save** the secrets
5. The app will automatically **rerun** with the new secrets

### Step 5: Initial Data Setup

Since Streamlit Cloud starts with a fresh environment, you'll need to ingest data:

**Option A: Pre-populate data before deployment**
- Add your JSON data files to `data/mutual_funds/` in your repository
- The app will automatically ingest them on first run

**Option B: Use the scraper (if enabled)**
- The scraper will run automatically if configured in `scraper_config.json`
- Note: Playwright/Selenium scrapers may have limitations on Streamlit Cloud

**Option C: Manual ingestion script**
- You can create a one-time setup script that runs on deployment
- Add it to your repository and run it manually via Streamlit Cloud's terminal (if available)

### Step 6: Verify Deployment

1. **Check the logs**: Click on "Manage app" → "Logs" to see if there are any errors
2. **Test the app**: Open your app URL and try asking a question
3. **Check sidebar**: Verify that the backend initialized successfully

## Important Considerations

### ⚠️ Limitations on Streamlit Cloud

1. **Ephemeral Storage**: 
   - Files written to disk are temporary and will be lost when the app restarts
   - ChromaDB data will persist only during the session
   - Consider using a persistent database service (e.g., PostgreSQL with pgvector) for production

2. **Scraper Limitations**:
   - Playwright/Selenium require browser installations which may not work on Streamlit Cloud
   - Consider disabling the scraper or using a headless browser service
   - Alternative: Run scrapers separately and sync data to your app

3. **Resource Limits**:
   - Free tier has memory and CPU limits
   - Large vector databases may cause memory issues
   - Consider optimizing chunk sizes and limiting document count

4. **Cold Starts**:
   - First load after inactivity may be slow
   - Consider using `@st.cache_resource` (already implemented) to cache initialization

### 🔧 Troubleshooting

#### "GEMINI_API_KEY not found" Error
- ✅ Verify secrets are saved correctly in Streamlit Cloud
- ✅ Check that the secret name matches exactly: `GEMINI_API_KEY`
- ✅ Restart the app after adding secrets

#### "Backend not initialized" Error
- ✅ Check logs for detailed error messages
- ✅ Verify API key is valid and has sufficient quota
- ✅ Ensure all dependencies in `requirements.txt` are compatible

#### App Crashes on Startup
- ✅ Check logs for Python errors
- ✅ Verify all required files are in the repository
- ✅ Ensure `requirements.txt` includes all dependencies

#### ChromaDB Issues
- ✅ ChromaDB data is ephemeral on Streamlit Cloud
- ✅ Consider using a persistent vector database for production
- ✅ Or pre-populate data in the repository

#### Scraper Not Working
- ✅ Playwright/Selenium may not work on Streamlit Cloud
- ✅ Disable scraper in `scraper_config.json` if not needed
- ✅ Use external scraping service and sync data

### 📝 Recommended Production Setup

For a production deployment, consider:

1. **Persistent Database**: Use PostgreSQL with pgvector or a cloud vector database
2. **External Scraping**: Run scrapers on a separate service (e.g., GitHub Actions, AWS Lambda)
3. **Data Sync**: Sync scraped data to your Streamlit app via API or database
4. **Monitoring**: Set up error tracking and monitoring
5. **Caching**: Use Redis or similar for session caching

## Updating Your App

After making changes:

1. **Commit and push** to GitHub:
   ```bash
   git add .
   git commit -m "Your update message"
   git push
   ```

2. **Streamlit Cloud will automatically detect** the changes and redeploy
3. **Monitor the logs** to ensure successful deployment

## Custom Domain (Optional)

Streamlit Cloud supports custom domains:

1. Go to app settings → "General"
2. Click "Add custom domain"
3. Follow the DNS configuration instructions

## Support

- **Streamlit Cloud Docs**: [docs.streamlit.io/streamlit-cloud](https://docs.streamlit.io/streamlit-cloud)
- **Streamlit Community**: [discuss.streamlit.io](https://discuss.streamlit.io)
- **GitHub Issues**: Open an issue in your repository

---

**Happy Deploying! 🚀**

