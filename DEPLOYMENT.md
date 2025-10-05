# 🚀 Deployment Guide for Iris

This document provides detailed instructions for deploying Iris for hackathon demonstration.

---

## 📋 Deployment Options Comparison

### Option 1: Streamlit Community Cloud ⭐ RECOMMENDED FOR HACKATHON

| Aspect | Details |
|--------|---------|
| **Cost** | ✅ **FREE** (with limitations) |
| **Setup Time** | ✅ **5-10 minutes** (fastest) |
| **Public URL** | ✅ `https://yourapp.streamlit.app` |
| **Storage** | ⚠️ **Ephemeral** (resets on app restart) |
| **Best For** | Hackathon demos, quick prototypes |

**Pros:**
- ✅ **Zero cost** - Perfect for hackathon budget
- ✅ **Automatic deployment** from GitHub
- ✅ **Built-in secrets management** for API keys
- ✅ **No server management** required
- ✅ **Fast deployment** - Push to GitHub, auto-deploys
- ✅ **Good for demos** - Judges can test immediately

**Cons:**
- ❌ **Ephemeral storage** - `data/stored_claims/` resets on app restart
  - **Workaround**: Demo flow still works, just Reference IDs won't persist between restarts
- ❌ **Resource limits** - 1GB RAM, can sleep after inactivity
- ❌ **Single instance** - No load balancing

---

### Option 2: Railway / Render

| Aspect | Details |
|--------|---------|
| **Cost** | ⚠️ **$5-10/month** (free tier available but limited) |
| **Setup Time** | ⚠️ **15-30 minutes** |
| **Public URL** | ✅ `https://yourapp.up.railway.app` |
| **Storage** | ✅ **Persistent** (with volume mount) |
| **Best For** | Production, persistent data needed |

**Pros:**
- ✅ **Persistent storage** - Can mount volumes for `data/stored_claims/`
- ✅ **More resources** - Better performance
- ✅ **PostgreSQL integration** - Can upgrade storage easily
- ✅ **Custom domains** - Professional URLs

**Cons:**
- ❌ **Costs money** - Not ideal for hackathon
- ❌ **More complex setup** - Requires Dockerfile
- ❌ **Slower iteration** - Rebuild on every change

---

## 🎯 RECOMMENDED: Streamlit Cloud Deployment

### Step 1: Prepare Repository

```bash
# 1. Initialize git repository (if not already done)
cd Iris
git init

# 2. Add all files
git add .

# 3. Create initial commit
git commit -m "Initial commit: Iris Claims Co-Pilot MVP"

# 4. Create GitHub repository (on github.com)
# - Go to github.com
# - Click "New Repository"
# - Name: "iris-claims-copilot" (or your choice)
# - Make it PUBLIC (required for Streamlit Cloud free tier)
# - DO NOT initialize with README (you already have one)

# 5. Push to GitHub
git remote add origin https://github.com/YOUR_USERNAME/iris-claims-copilot.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Streamlit Cloud

1. **Go to:** https://share.streamlit.io/

2. **Sign in** with your GitHub account

3. **Click "New app"**

4. **Configure deployment:**
   - **Repository:** `YOUR_USERNAME/iris-claims-copilot`
   - **Branch:** `main`
   - **Main file path:** `src/app.py`
   - **App URL:** Choose a custom URL (e.g., `iris-demo`)

5. **Add secrets** (Environment Variables):
   - Click "Advanced settings"
   - Under "Secrets", add:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-your-key-here"
   ```

6. **Click "Deploy"** - Wait 2-3 minutes

7. **Your app is live!** Share URL with judges: `https://iris-demo.streamlit.app`

### Step 3: Test Deployment

1. Visit your deployed URL
2. Test Pre-Authorization flow
3. Test Discharge flow with manual input
4. **Note:** Reference ID feature will work WITHIN a session, but won't persist across app restarts

---

## 🔧 Handling Persistent Storage Issue

### The Problem

`data/stored_claims/` is stored locally. On Streamlit Cloud, this resets on app restart.

### Solution 1: Demo-Friendly Workaround ⭐ RECOMMENDED

**Accept ephemeral storage for hackathon demo:**

✅ **What WORKS:**
- Pre-Authorization validation ✅
- Discharge validation with manual input ✅
- PDF generation ✅
- All AI agents ✅
- **Reference ID save & load WITHIN same session** ✅

⚠️ **What DOESN'T persist:**
- Reference IDs saved in one session won't be available after app restart
- **Impact:** Judges testing in different sessions can't share Reference IDs
- **Mitigation:** Each judge session is independent anyway - they complete full flow themselves

**Demo Script for Judges:**
```
1. Pre-Auth Validation
2. Save Reference ID (CR-20251005-XXXXX)
3. Copy the Reference ID
4. Discharge Validation
5. Paste Reference ID → Load pre-auth data
6. Complete discharge validation
7. Download Recovery PDF

All within ONE session - works perfectly!
```

### Solution 2: Upgrade to Cloud Database (Post-Hackathon)

If persistent storage is critical:

**Option A: Streamlit Cloud + SQLite on Railway**
- Deploy SQLite database on Railway (free tier)
- Modify `ClaimStorageService` to use SQLite instead of JSON files
- ~2 hours implementation time

**Option B: Full Railway Deployment**
- Deploy entire app on Railway with volume mount
- $5-10/month cost
- See "Railway Deployment" section below

---

## 🐳 Railway Deployment (Optional)

### Prerequisites
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login
```

### Step 1: Create Dockerfile

```dockerfile
# File: Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create persistent directory
RUN mkdir -p /app/data/stored_claims

# Expose port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Step 2: Deploy to Railway

```bash
# Initialize Railway project
railway init

# Add environment variable
railway variables set ANTHROPIC_API_KEY=sk-ant-your-key-here

# Deploy
railway up

# Get public URL
railway domain
```

### Step 3: Add Persistent Volume

1. Go to Railway dashboard
2. Select your project
3. Click "Variables" tab
4. Add volume mount: `/app/data/stored_claims`
5. Redeploy

**Cost:** ~$5/month (with volume)

---

## 📊 Storage Comparison

| Storage Type | Streamlit Cloud | Railway | Local Dev |
|--------------|----------------|---------|-----------|
| **Persistence** | ❌ Ephemeral | ✅ Persistent | ✅ Persistent |
| **Cost** | ✅ Free | ⚠️ $5-10/mo | ✅ Free |
| **Setup Time** | ✅ 5 min | ⚠️ 30 min | ✅ 1 min |
| **Good for Demo?** | ✅ Yes | ✅ Yes | ⚠️ No (not public) |

---

## 🎯 Recommended Deployment Strategy for Hackathon

### Phase 1: Demo Day (Use Streamlit Cloud)

✅ **Deploy on Streamlit Cloud**
- Zero cost
- Public URL for judges
- Fast setup
- **Accept ephemeral storage limitation**

**Demo Flow:**
1. Judge opens your Streamlit Cloud URL
2. Judge completes Pre-Auth → Gets Reference ID
3. **Judge copies Reference ID** (important!)
4. Judge does Discharge Validation → Pastes Reference ID
5. Judge downloads Recovery PDF
6. **All works perfectly in single session!**

### Phase 2: Post-Hackathon (Upgrade if Needed)

If you win/advance:
1. Migrate to Railway with persistent storage
2. Implement PostgreSQL database
3. Add user authentication
4. Deploy production-grade version

---

## 🔐 Security Checklist

### Before Deploying:

- [ ] ✅ `.env` is in `.gitignore` (never commit API keys!)
- [ ] ✅ Created `.env.example` without actual secrets
- [ ] ✅ API key added to Streamlit Cloud secrets
- [ ] ✅ Removed any hardcoded credentials
- [ ] ✅ `.gitignore` includes `__pycache__/`, `*.pyc`

### On Streamlit Cloud:

- [ ] ✅ Repository is PUBLIC (required for free tier)
- [ ] ✅ Secrets configured in Streamlit Cloud dashboard
- [ ] ✅ Test app with sample data (not real patient info)

---

## 🧪 Pre-Deployment Testing

```bash
# Test locally first
streamlit run src/app.py

# Test all flows:
# 1. Pre-Auth validation ✓
# 2. Save Reference ID ✓
# 3. Discharge with Reference ID ✓
# 4. Discharge with manual input ✓
# 5. PDF download ✓
```

---

## 🚨 Common Deployment Issues

### Issue 1: ModuleNotFoundError

**Cause:** Missing dependency in `requirements.txt`

**Fix:**
```bash
# Add missing package to requirements.txt
echo "package-name==version" >> requirements.txt
git commit -am "Add missing dependency"
git push
```

### Issue 2: Anthropic API Key Not Found

**Cause:** Secret not configured in Streamlit Cloud

**Fix:**
1. Go to Streamlit Cloud dashboard
2. Select your app
3. Click "Settings" → "Secrets"
4. Add: `ANTHROPIC_API_KEY = "sk-ant-..."`
5. Click "Save"
6. App will restart automatically

### Issue 3: App Sleeping/Slow Startup

**Cause:** Streamlit Cloud sleeps apps after inactivity (free tier)

**Fix:**
- Accept this limitation for hackathon
- First request after sleep takes ~30 seconds to wake up
- Tell judges: "App may take 30s to load on first visit"

### Issue 4: File Not Found Errors

**Cause:** File paths assuming local structure

**Fix:** All paths in code use relative paths from project root
- ✅ `data/procedure_registry.json` (correct)
- ❌ `/Users/yourname/Iris/data/...` (wrong)

---

## 📝 Deployment Checklist

### Pre-Deployment
- [ ] All code committed to GitHub
- [ ] `.gitignore` configured correctly
- [ ] `requirements.txt` up to date
- [ ] README.md updated
- [ ] Tested locally with `streamlit run src/app.py`
- [ ] API key in `.env` (not committed)

### During Deployment
- [ ] GitHub repository is PUBLIC
- [ ] Streamlit Cloud app created
- [ ] Main file path set to `src/app.py`
- [ ] ANTHROPIC_API_KEY added to Secrets
- [ ] Deployment successful

### Post-Deployment
- [ ] Tested Pre-Auth flow on live URL
- [ ] Tested Discharge flow on live URL
- [ ] Tested PDF download
- [ ] Verified Reference ID works in same session
- [ ] Shared URL with team/judges

---

## 🎬 Demo Day Preparation

### 1 Day Before:

1. **Deploy to Streamlit Cloud** - Get public URL
2. **Test thoroughly** - All flows working
3. **Prepare demo script** - Practice walkthrough
4. **Create fallback** - Have local version ready (if internet fails)

### Demo Day:

1. **Share URL** with judges via:
   - Presentation slide
   - GitHub README
   - Hackathon submission form

2. **Demo Script (5 minutes):**
   - Introduction (30s): "Iris reduces 12.9% claim rejection rate"
   - Pre-Auth Demo (2min): Upload PDF → Show validation → Get Reference ID
   - Discharge Demo (2min): Load Reference ID → Upload bills → Get PDF
   - Impact (30s): "Catches errors BEFORE insurer sees them"

3. **Backup Plan:**
   - If Streamlit Cloud is down → Run locally + screen share
   - If API key exhausted → Show screenshots/video

---

## 🔗 Deployment URLs

After deployment, update these URLs:

### Streamlit Cloud:
- **Live App:** `https://iris-demo.streamlit.app` (replace with your actual URL)
- **GitHub Repo:** `https://github.com/YOUR_USERNAME/iris-claims-copilot`
- **API Status:** No separate API (Streamlit handles everything)

### Railway (if used):
- **Live App:** `https://iris.up.railway.app`
- **Database:** Railway PostgreSQL instance
- **Monitoring:** Railway dashboard

---

## 💡 Pro Tips

1. **Warm up the app** before judges test:
   - Visit URL yourself 10 minutes before demo
   - Keeps app "awake" on Streamlit Cloud

2. **Create demo account:**
   - Use generic data (not real patient info)
   - Pre-fill some Reference IDs to show

3. **Monitor usage:**
   - Check Streamlit Cloud analytics
   - Watch for errors in logs

4. **Have screenshots ready:**
   - In case live demo fails
   - Show backup evidence of working app

5. **Cost management:**
   - Anthropic API has rate limits
   - Monitor usage at console.anthropic.com
   - For hackathon: ~100 validations = ~$5-10 in API costs

---

## 📊 Estimated Costs

### Hackathon (1 week):
- **Streamlit Cloud:** $0 (free tier)
- **Anthropic API:** ~$10-20 (100-200 validations)
- **GitHub:** $0 (free public repo)
- **Domain (optional):** $0 (use streamlit.app subdomain)

**Total:** ~$10-20 for entire hackathon

### Post-Hackathon Production (monthly):
- **Railway + PostgreSQL:** $10-15/month
- **Anthropic API:** $50-100/month (depends on usage)
- **Domain:** $12/year (~$1/month)

**Total:** ~$60-120/month for small-scale production

---

## 🆘 Need Help?

**Streamlit Cloud Issues:**
- Docs: https://docs.streamlit.io/streamlit-community-cloud
- Community: https://discuss.streamlit.io/

**Railway Issues:**
- Docs: https://docs.railway.app/
- Discord: https://discord.gg/railway

**Iris-Specific Issues:**
- Check `CLAUDE.md` for architecture details
- Review error logs in Streamlit Cloud dashboard

---

**Good luck with your deployment! 🚀**

**Remember:** For hackathon, Streamlit Cloud is your best friend. Fast, free, and works beautifully for demos!
