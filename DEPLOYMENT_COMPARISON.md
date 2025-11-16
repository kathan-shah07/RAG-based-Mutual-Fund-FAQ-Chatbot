# Free Tier Deployment Platform Comparison

## Overview

This document compares the free tier offerings of **Netlify**, **Vercel**, and **GitHub** (Pages/Actions) for deploying the RAG-based Mutual Fund Chatbot.

## Important Note: Platform Limitations

⚠️ **Critical Consideration**: Netlify, Vercel, and GitHub Pages are primarily designed for:
- Static websites
- Serverless functions (short-lived, stateless)
- JAMstack applications

Your FastAPI application has specific requirements that may not fit these platforms:
- **Long-running Python process** (FastAPI server)
- **Persistent storage** (ChromaDB database)
- **Browser automation** (Playwright with Chromium)
- **Scheduled tasks** (background scraper service)
- **Large dependencies** (ML libraries, browser binaries)

## Detailed Comparison

### 1. Netlify Free Tier

#### Features
- **Bandwidth**: 100 GB/month
- **Build Minutes**: 300 minutes/month
- **Serverless Functions**: 125,000 invocations/month
- **Function Execution Time**: 10 seconds (free tier), 26 seconds (pro)
- **Function Memory**: 1GB
- **Concurrent Functions**: 15
- **Custom Domains**: Unlimited
- **SSL Certificates**: Automatic
- **Continuous Deployment**: GitHub, GitLab, Bitbucket
- **Commercial Use**: ✅ Allowed

#### Python Support
- ✅ Supports Python serverless functions
- ✅ Can deploy FastAPI as serverless functions
- ⚠️ **10-second timeout** (free tier) - may be insufficient for RAG queries
- ⚠️ **Cold starts** - functions spin down after inactivity
- ⚠️ **No persistent storage** - ChromaDB would need external storage
- ⚠️ **No long-running processes** - scheduled scraper won't work

#### Limitations for Your App
1. **Function Timeout**: 10 seconds may not be enough for complex RAG queries
2. **No Persistent Storage**: ChromaDB needs external database (e.g., Supabase, MongoDB)
3. **No Background Tasks**: Scheduled scraper service cannot run
4. **Playwright Issues**: Browser dependencies may exceed function size limits
5. **Cold Starts**: First request after inactivity can be slow (5-10 seconds)

#### Workarounds
- Use Netlify Functions for API endpoints
- Store ChromaDB data in external service (Supabase, MongoDB Atlas free tier)
- Use external cron service (cron-job.org, GitHub Actions) for scheduled tasks
- Split application: Frontend on Netlify, Backend on Railway/Render

#### Cost to Upgrade
- **Pro Plan**: $19/month
  - 25-second function timeout
  - 500 build minutes/month
  - Better performance

---

### 2. Vercel Free Tier

#### Features
- **Bandwidth**: 100 GB/month
- **Build Minutes**: 6,000 minutes/month (generous!)
- **Serverless Functions**: 100 GB-hours/month
- **Function Execution Time**: 10 seconds (free tier), 60 seconds (pro)
- **Function Memory**: 1GB
- **Concurrent Functions**: 100
- **Custom Domains**: Unlimited
- **SSL Certificates**: Automatic
- **Continuous Deployment**: GitHub, GitLab, Bitbucket
- **Commercial Use**: ❌ **Restricted** (personal/hobby projects only)

#### Python Support
- ✅ Excellent Python serverless function support
- ✅ Optimized for Next.js but supports any framework
- ✅ Can deploy FastAPI as serverless functions
- ⚠️ **10-second timeout** (free tier)
- ⚠️ **No persistent storage** - needs external database
- ⚠️ **No long-running processes**

#### Limitations for Your App
1. **Commercial Use Restriction**: Free tier is for personal/hobby projects only
2. **Function Timeout**: 10 seconds limit
3. **No Persistent Storage**: Requires external database
4. **No Background Tasks**: Cannot run scheduled scraper
5. **Playwright Challenges**: Browser dependencies may be problematic

#### Workarounds
- Similar to Netlify: external storage, external cron jobs
- Better build minutes (6,000 vs 300) for frequent deployments

#### Cost to Upgrade
- **Pro Plan**: $20/month
  - 60-second function timeout
  - Commercial use allowed
  - Better performance

---

### 3. GitHub (Pages + Actions)

#### GitHub Pages Free Tier

#### Features
- **Bandwidth**: 100 GB/month (soft limit)
- **Build Minutes**: Via GitHub Actions (2,000 minutes/month for free)
- **Custom Domains**: Supported
- **SSL Certificates**: Automatic
- **Continuous Deployment**: Direct from GitHub repos
- **Commercial Use**: ✅ Allowed

#### Limitations
- ❌ **Static sites only** - No server-side processing
- ❌ **No serverless functions**
- ❌ **Cannot host FastAPI backend**

#### GitHub Actions Free Tier

#### Features
- **Build Minutes**: 2,000 minutes/month (public repos)
- **Concurrent Jobs**: 20
- **Workflow Runs**: Unlimited
- **Commercial Use**: ✅ Allowed (public repos)

#### Use Cases
- ✅ CI/CD pipelines
- ✅ Automated testing
- ✅ Scheduled tasks (cron jobs)
- ⚠️ **Not for hosting** - Actions run temporarily, not continuously

#### Limitations for Your App
1. **GitHub Pages**: Cannot host FastAPI (static only)
2. **GitHub Actions**: Not designed for hosting applications
3. **No persistent storage**: Actions are ephemeral
4. **No long-running processes**: Actions have time limits

#### Possible Architecture
- Frontend (static) → GitHub Pages
- Backend API → External service (Railway, Render, etc.)
- Scheduled tasks → GitHub Actions (cron workflow)

---

## Side-by-Side Comparison Table

| Feature | Netlify Free | Vercel Free | GitHub Pages | GitHub Actions |
|---------|-------------|-------------|--------------|----------------|
| **Bandwidth** | 100 GB/month | 100 GB/month | 100 GB/month | N/A |
| **Build Minutes** | 300/month | 6,000/month | Via Actions | 2,000/month |
| **Serverless Functions** | ✅ 125K/month | ✅ 100K/day | ❌ No | ❌ No |
| **Function Timeout** | 10 seconds | 10 seconds | N/A | N/A |
| **Python Support** | ✅ Yes | ✅ Yes | ❌ Static only | ✅ Yes (CI/CD) |
| **Persistent Storage** | ❌ No | ❌ No | ❌ No | ❌ No |
| **Long-running Processes** | ❌ No | ❌ No | ❌ No | ❌ No |
| **Scheduled Tasks** | ❌ No | ❌ No | ❌ No | ✅ Yes (cron) |
| **Custom Domains** | ✅ Unlimited | ✅ Unlimited | ✅ Yes | N/A |
| **SSL Certificates** | ✅ Auto | ✅ Auto | ✅ Auto | N/A |
| **Auto-Deploy (Git Push)** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Commercial Use** | ✅ Allowed | ❌ Restricted | ✅ Allowed | ✅ Allowed |
| **Best For** | Static + Serverless | Next.js + Serverless | Static Sites | CI/CD |

---

## Suitability Analysis for Your FastAPI App

### Netlify: ⚠️ **Partially Suitable** (with modifications)

**Pros:**
- ✅ Commercial use allowed
- ✅ Serverless functions support Python
- ✅ Good free tier limits
- ✅ Easy Git integration

**Cons:**
- ❌ 10-second timeout may be insufficient
- ❌ No persistent storage (need external DB)
- ❌ No background tasks
- ❌ Playwright may be challenging

**Required Modifications:**
1. Refactor FastAPI to serverless functions
2. Use external database (Supabase/MongoDB free tier)
3. Use external cron service for scheduled tasks
4. Optimize Playwright usage or remove scraper

**Effort Level**: 🔴 High (significant refactoring needed)

---

### Vercel: ⚠️ **Partially Suitable** (with modifications)

**Pros:**
- ✅ Excellent Python support
- ✅ 6,000 build minutes (very generous)
- ✅ Better performance than Netlify
- ✅ Good developer experience

**Cons:**
- ❌ **Commercial use restricted** (free tier)
- ❌ 10-second timeout
- ❌ No persistent storage
- ❌ No background tasks

**Required Modifications:**
Same as Netlify, plus:
- Need Pro plan ($20/month) for commercial use

**Effort Level**: 🔴 High (significant refactoring + cost for commercial use)

---

### GitHub Pages + Actions: ❌ **Not Suitable** (for hosting)

**Pros:**
- ✅ Free for public repos
- ✅ Commercial use allowed
- ✅ GitHub Actions can handle scheduled tasks

**Cons:**
- ❌ Pages: Static sites only (cannot host FastAPI)
- ❌ Actions: Not for hosting applications
- ❌ No serverless functions
- ❌ No persistent storage

**Possible Hybrid Approach:**
- Frontend → GitHub Pages
- Backend → External service (Railway/Render)
- Scheduled tasks → GitHub Actions

**Effort Level**: 🟡 Medium (hybrid architecture)

---

## Recommendations

### Option 1: Stay with Railway (Recommended) ✅

**Why:**
- ✅ Designed for long-running applications
- ✅ Supports persistent storage (volumes)
- ✅ No function timeout limits
- ✅ Can run background services
- ✅ Free tier available ($5 credit/month)
- ✅ Commercial use allowed
- ✅ Easy Docker deployment
- ✅ Auto-deploy from GitHub

**Best Match**: Your current architecture works perfectly

---

### Option 2: Render Free Tier (Alternative)

**Why:**
- ✅ Similar to Railway
- ✅ Free tier available
- ✅ Supports persistent storage
- ✅ Long-running processes
- ⚠️ Free tier spins down after 15 minutes inactivity
- ⚠️ Slower cold starts

**Best Match**: Good alternative if Railway doesn't work

---

### Option 3: Hybrid Approach (Complex)

**Architecture:**
- **Frontend** → Netlify/Vercel (static files)
- **Backend API** → Railway/Render (FastAPI)
- **Database** → Supabase/MongoDB Atlas (free tier)
- **Scheduled Tasks** → GitHub Actions or cron-job.org

**Pros:**
- ✅ Frontend benefits from CDN
- ✅ Backend on proper platform

**Cons:**
- ❌ More complex setup
- ❌ Multiple services to manage
- ❌ CORS configuration needed
- ❌ Higher maintenance

**Effort Level**: 🔴 Very High

---

### Option 4: Refactor to Serverless (Major Changes)

**Required Changes:**
1. Convert FastAPI to serverless functions
2. Move ChromaDB to external service
3. Remove scheduled scraper (use external cron)
4. Optimize Playwright usage

**Platforms:**
- Netlify Functions (if commercial use needed)
- Vercel Functions (if willing to pay $20/month for commercial)

**Effort Level**: 🔴 Very High (complete refactoring)

---

## Final Recommendation

### 🏆 **Best Choice: Railway** (Your Original Plan)

**Reasons:**
1. ✅ **Perfect Fit**: Designed exactly for your use case
2. ✅ **No Refactoring**: Current code works as-is
3. ✅ **Free Tier**: $5 credit/month (usually enough for small apps)
4. ✅ **Persistent Storage**: Volumes included
5. ✅ **Long-running**: No timeout limits
6. ✅ **Background Tasks**: Scheduled scraper works
7. ✅ **Commercial Use**: Allowed
8. ✅ **Auto-Deploy**: GitHub integration

### 🥈 **Second Choice: Render**

Similar to Railway but with 15-minute inactivity spin-down on free tier.

### 🥉 **Third Choice: Hybrid (Frontend on Netlify, Backend on Railway)**

Only if you want CDN benefits for static files, but adds complexity.

---

## Cost Comparison (If Upgrading)

| Platform | Free Tier | Paid Tier | Best For |
|----------|-----------|-----------|----------|
| **Railway** | $5 credit/month | Pay-as-you-go | Long-running apps ✅ |
| **Render** | Free (spins down) | $7/month | Long-running apps |
| **Netlify** | Free | $19/month | Static + Serverless |
| **Vercel** | Free (non-commercial) | $20/month | Next.js + Serverless |
| **GitHub** | Free | N/A | Static sites only |

---

## Conclusion

For your FastAPI application with:
- Long-running server
- Persistent database (ChromaDB)
- Background scheduled tasks
- Playwright browser automation

**Railway remains the best choice** because:
1. It's designed for this exact use case
2. Requires zero code changes
3. Free tier is sufficient for small projects
4. Commercial use is allowed
5. Auto-deploy from GitHub works perfectly

Netlify, Vercel, and GitHub Pages are excellent platforms, but they're optimized for different architectures (static sites, serverless functions) and would require significant refactoring of your application.

---

## Next Steps

If you want to proceed with Railway (recommended):
- ✅ All deployment files are already created
- ✅ Ready to deploy immediately
- ✅ Follow the README.md deployment guide

If you want to explore other options:
- Review the "Required Modifications" sections above
- Consider the effort vs. benefit trade-off
- Test with a small prototype first

