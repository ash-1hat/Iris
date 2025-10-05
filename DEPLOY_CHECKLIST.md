# 🚀 Quick Deployment Checklist

## ⏱️ 10-Minute Streamlit Cloud Deployment

### Step 1: GitHub Setup (2 minutes)
```bash
- [ ] cd Iris
- [ ] git init
- [ ] git add .
- [ ] git commit -m "Initial commit: Iris MVP"
- [ ] Create GitHub repo at github.com (PUBLIC repo)
- [ ] git remote add origin https://github.com/YOUR_USERNAME/iris-claims-copilot.git
- [ ] git push -u origin main
```

### Step 2: Streamlit Cloud (5 minutes)
```
- [ ] Go to https://share.streamlit.io/
- [ ] Sign in with GitHub
- [ ] Click "New app"
- [ ] Repository: YOUR_USERNAME/iris-claims-copilot
- [ ] Branch: main
- [ ] Main file: src/app.py
- [ ] App URL: iris-demo (or your choice)
- [ ] Advanced Settings → Secrets:
      ANTHROPIC_API_KEY = "sk-ant-your-actual-key-here"
- [ ] Click "Deploy"
- [ ] Wait 2-3 minutes
```

### Step 3: Test & Share (3 minutes)
```
- [ ] Visit your app URL
- [ ] Test Pre-Auth flow
- [ ] Test Discharge flow
- [ ] Share URL with judges/team
```

---

## ✅ Pre-Deployment Verification

### Code Review
- [ ] All files committed to git
- [ ] `.env` is in `.gitignore` ✓
- [ ] No hardcoded API keys in code
- [ ] `requirements.txt` has all dependencies
- [ ] `src/app.py` runs locally without errors

### Files Created (should exist)
- [ ] `.gitignore` ✓
- [ ] `.streamlit/config.toml` ✓
- [ ] `packages.txt` ✓
- [ ] `README.md` (updated) ✓
- [ ] `.env.example` ✓

### Test Locally First
```bash
- [ ] streamlit run src/app.py
- [ ] Test Pre-Auth → Works ✓
- [ ] Test Discharge (manual) → Works ✓
- [ ] Test Discharge (with Reference ID) → Works ✓
- [ ] Test PDF download → Works ✓
```

---

## 🎯 Deployment Options Summary

### ⭐ RECOMMENDED: Streamlit Cloud
**Cost:** FREE | **Time:** 10 min | **For:** Hackathon Demo
```
✅ Zero cost
✅ Public URL instantly
✅ Auto-deploys from GitHub
❌ Ephemeral storage (Reference IDs reset on restart)
   ↳ Workaround: Works fine within single session
```

### Alternative: Railway
**Cost:** $5-10/month | **Time:** 30 min | **For:** Production
```
✅ Persistent storage
✅ Better performance
❌ Costs money
❌ More complex setup
```

---

## 📝 Important URLs

After deployment, add these to your README:
- **Live Demo:** https://iris-demo.streamlit.app (replace with actual)
- **GitHub:** https://github.com/YOUR_USERNAME/iris-claims-copilot
- **Docs:** See DEPLOYMENT.md for full guide

---

## 🚨 Common Issues & Quick Fixes

| Issue | Fix |
|-------|-----|
| **ModuleNotFoundError** | Add package to `requirements.txt`, commit, push |
| **API Key error** | Check Streamlit Cloud → Settings → Secrets |
| **App sleeping** | Normal for free tier. First load takes 30s after sleep |
| **File not found** | Ensure paths are relative: `data/...` not `/Users/...` |

---

## 🎬 Demo Day Script (5 min)

### Intro (30s)
> "Iris reduces India's 12.9% insurance claim rejection rate by validating documentation BEFORE insurer submission."

### Pre-Auth Demo (2 min)
1. Select Star Health - Comprehensive
2. Choose Appendectomy
3. Upload medical note PDF
4. **Show AI validation:** 4 agents analyzing in real-time
5. **Result:** Score 85/100, 2 warnings, specific fixes
6. Click "Save for Discharge Validation"
7. **Get Reference ID:** CR-20251005-XXXXX

### Discharge Demo (2 min)
1. Enter Reference ID → Auto-loads pre-auth data
2. Upload final bill + discharge summary
3. **Show variance analysis:** +14.7% documented variance
4. **Download Recovery PDF:** Professional patient guide
5. Open PDF → Show formatted tables

### Impact (30s)
> "Catches errors before submission. Hospitals reduce rejection rate from 12.9% to <3%. Patients get clear recovery instructions. All powered by Claude AI."

---

## 💡 Pro Tips

### Before Demo:
- [ ] Visit app 10 min early (wakes it up)
- [ ] Prepare backup screenshots
- [ ] Have local version ready (if internet fails)
- [ ] Check Anthropic API quota

### During Demo:
- [ ] Speak to problem first (12.9% rejection rate)
- [ ] Show AI agents working (not just results)
- [ ] Emphasize PDF quality (professional output)
- [ ] Compare to manual approach (time saved)

### After Demo:
- [ ] Monitor Streamlit Cloud logs
- [ ] Check Anthropic API usage
- [ ] Get judge feedback
- [ ] Update based on questions

---

## 📊 Quick Stats for Pitch

- **Problem:** 12.9% rejection rate in India's cashless system
- **Solution:** AI-powered pre-submission validation
- **Tech:** 7 AI agents (4 pre-auth + 3 discharge)
- **Coverage:** 3 insurers, 6 policies, 10 procedures
- **Impact:** <3% rejection rate (projected)
- **Time Saved:** 3-5 days → <1 hour

---

**Ready to deploy? Just follow Step 1, 2, 3 above. Good luck! 🚀**
