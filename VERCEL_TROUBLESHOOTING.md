# Vercel 404 NOT_FOUND Troubleshooting Guide

## Error: DEPLOYMENT_NOT_FOUND (404)

This error typically means Vercel cannot find or build your deployment. Here are the steps to fix it:

## Step 1: Check Project Settings in Vercel Dashboard

1. Go to your Vercel project dashboard
2. Click on **Settings** → **General**
3. Verify:
   - **Root Directory**: Should be `./` (root of repo)
   - **Framework Preset**: Should be **Other** or **Python**
   - **Build Command**: Leave empty (Vercel auto-detects)
   - **Output Directory**: Leave empty
   - **Install Command**: `pip install -r requirements.txt`

## Step 2: Verify File Structure

Make sure your repository has:
```
MF-Chatbot/
├── api/
│   ├── __init__.py
│   ├── index.py          ← Vercel handler (must exist)
│   └── main.py           ← FastAPI app
├── vercel.json           ← Vercel config (must exist)
└── requirements.txt      ← Dependencies (must exist)
```

## Step 3: Check vercel.json

Your `vercel.json` should look like:
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ],
  "functions": {
    "api/index.py": {
      "maxDuration": 10
    }
  }
}
```

## Step 4: Verify api/index.py Handler

Your `api/index.py` should export a `handler`:
```python
from api.main import app
from mangum import Mangum

handler = Mangum(app, lifespan="off")
```

## Step 5: Check Build Logs

1. Go to Vercel dashboard → Your project → **Deployments**
2. Click on the failed deployment
3. Check **Build Logs** for errors:
   - Import errors?
   - Missing dependencies?
   - Syntax errors?

## Step 6: Common Issues & Fixes

### Issue 1: Import Errors
**Error**: `ModuleNotFoundError: No module named 'api'`

**Fix**: Make sure `api/__init__.py` exists and the import path is correct.

### Issue 2: Missing Dependencies
**Error**: `ModuleNotFoundError: No module named 'mangum'`

**Fix**: Verify `mangum>=0.17.0` is in `requirements.txt`

### Issue 3: Build Fails
**Error**: Build process fails

**Fix**: 
- Check Python version (Vercel uses Python 3.9+)
- Verify all dependencies in `requirements.txt`
- Check for syntax errors in Python files

### Issue 4: Handler Not Found
**Error**: Handler function not found

**Fix**: Make sure `api/index.py` exports `handler` variable

## Step 7: Alternative Configuration (If Above Doesn't Work)

Try this simplified `vercel.json`:
```json
{
  "functions": {
    "api/index.py": {
      "maxDuration": 10
    }
  }
}
```

Vercel will auto-detect Python files in `api/` directory.

## Step 8: Manual Deployment Test

1. **Delete the project** in Vercel dashboard
2. **Re-import** the repository
3. **Set environment variables** before deploying:
   - `GEMINI_API_KEY` (required)
4. **Deploy** and watch build logs

## Step 9: Check GitHub Repository

Make sure all files are committed and pushed:
```bash
git status
git add .
git commit -m "Fix Vercel configuration"
git push origin main
```

## Step 10: Verify Requirements.txt

Make sure `requirements.txt` includes:
```
mangum>=0.17.0
fastapi>=0.104.1
# ... other dependencies
```

## Still Having Issues?

1. **Check Vercel Build Logs** - Look for specific error messages
2. **Test Locally** - Try running the handler locally first
3. **Simplify** - Try deploying a minimal FastAPI app first
4. **Vercel Support** - Contact Vercel support with build logs

## Quick Test Handler

If nothing works, try this minimal `api/index.py`:
```python
from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello from Vercel"}

@app.get("/health")
def health():
    return {"status": "healthy"}

handler = Mangum(app)
```

If this works, then gradually add back your full application.

---

**Next Steps:**
1. Check build logs in Vercel dashboard
2. Verify file structure matches above
3. Test with minimal handler first
4. Gradually add complexity

