# Streamlit Cloud Quick Start Guide

## 🚀 Quick Deployment Checklist

### Before Deployment
- [ ] Code is pushed to GitHub
- [ ] `requirements.txt` is up to date
- [ ] `.streamlit/config.toml` exists (optional)
- [ ] `.gitignore` excludes sensitive files

### Deployment Steps

1. **Go to [share.streamlit.io](https://share.streamlit.io)**
2. **Click "New app"**
3. **Fill in:**
   - Repository: Your GitHub repo
   - Branch: `main`
   - Main file: `app.py`
4. **Click "Deploy"**
5. **Add Secrets** (Settings → Secrets):
   ```toml
   GEMINI_API_KEY = "your-api-key-here"
   ```
6. **Wait for deployment** (check logs if issues)

### Required Secret
- `GEMINI_API_KEY` - Your Google Gemini API key

### Optional Secrets
- `GEMINI_MODEL` - Default: "gemini-1.5-flash"
- `GEMINI_EMBEDDING_MODEL` - Default: "models/embedding-001"
- `CHROMA_DB_PATH` - Default: "./chroma_db"
- `COLLECTION_NAME` - Default: "mutual_funds"
- `DATA_DIR` - Default: "./data/mutual_funds"

## ⚠️ Important Notes

1. **ChromaDB is ephemeral** - Data resets on app restart
2. **Scraper may not work** - Playwright/Selenium limitations
3. **Pre-populate data** - Add JSON files to `data/mutual_funds/` in repo

## 🔍 Troubleshooting

**App won't start?**
- Check logs in Streamlit Cloud dashboard
- Verify `GEMINI_API_KEY` secret is set correctly

**"Backend not initialized" error?**
- Check API key is valid
- Verify all dependencies installed (check logs)

**No data in database?**
- Add JSON files to `data/mutual_funds/` before deployment
- Or run ingestion script manually

## 📚 Full Guide

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

