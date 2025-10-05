# 🏥 Iris - Health Insurance Claims Co-Pilot

**India's First AI-Powered Cashless Claims Validation Platform**

Iris helps patients and hospitals validate insurance claim documentation **before** submission to insurers, reducing the 12.9% rejection rate in India's cashless healthcare system.

---

## 🎯 Problem Statement

India's cashless health insurance system faces a critical challenge:
- **12.9% rejection rate** due to incomplete or non-compliant documentation
- Patients discover issues **after treatment** when insurers reject claims
- Hospitals struggle with back-and-forth documentation fixes
- **Patients bear financial stress** from unexpected out-of-pocket expenses

**Iris acts as your "first reviewer"** - catching errors before the insurer sees them.

---

## ✨ Key Features

### 📋 Pre-Authorization Validation (Before Treatment)
**Validates claim documentation BEFORE you submit to your insurer**

✅ **4-Agent AI System:**
1. **Completeness Checker** - Ensures all required fields and documents are present
2. **Policy Validator** - Checks waiting periods, exclusions, coverage limits, room rent sub-limits
3. **Medical Review Agent** - LLM-powered assessment of medical justification quality
4. **FWA Detector** - Fraud/waste/abuse detection with context-aware cost validation

✅ **Outputs:**
- **Readiness Score (0-100)** - Know exactly how ready your claim is
- **Status:** Ready (80-100) | Needs Revision (60-79) | Critical Issues (0-59)
- **Actionable Recommendations** - Specific fixes, not vague suggestions
- **Reference ID** - Save your validated data for later discharge validation

✅ **Smart Validation:**
- Checks against actual policy rules (3 insurers, 6 policies, 10 procedures)
- Range-aware cost validation (doesn't flag costs within acceptable ranges)
- Prevents false positives (high cost ≠ automatic fraud)

---

### 🏥 Discharge Validation (After Treatment)
**Validates discharge documentation and compares actual costs vs estimates**

✅ **3-Agent AI System:**
1. **Bill Reconciliation** - Line-by-line cost comparison (pre-auth vs actual)
2. **Cost Escalation Analyzer** - LLM analysis of whether variances are documented
3. **Medical Guidance Generator** - Extracts patient recovery instructions from discharge summary

✅ **Two Input Modes:**
- **With Reference ID** - Load pre-auth data automatically
- **Manual Entry** - Enter pre-auth costs manually if you don't have a Reference ID

✅ **Outputs:**
- **Documentation Completeness Score (0-100)**
- **Cost Variance Analysis** - Categorized as documented/undocumented (not justified/unjustified)
- **Bill Comparison** - Expected vs actual breakdown
- **Recovery Instructions PDF** - Professional, printable patient guidance with:
  - 💊 Medications table (Name, Dosage, Duration, Purpose)
  - 📅 Follow-up appointments schedule
  - ✅🚫 DO's and DON'Ts side-by-side
  - ⚠️ Warning signs to watch for
  - 🕐 Recovery timeline

✅ **Philosophy:**
- **NO payment predictions** - We don't calculate what you'll pay
- **NO approval predictions** - We don't predict if insurer will approve
- **Focus:** Documentation completeness + Patient care instructions

---

## 🚀 What Makes Iris Unique

| Feature | Iris | Traditional Approach |
|---------|------|---------------------|
| **Validation Timing** | BEFORE insurer submission | AFTER rejection (too late) |
| **Actionable Feedback** | Specific fixes ("Add VA measurement") | Vague ("Insufficient justification") |
| **Cost Validation** | Range-aware, context-sensitive | Binary (high = fraud) |
| **Policy Rules** | Checks actual policy JSONs | Manual policy reading |
| **Patient Language** | Plain language summaries | Medical jargon |
| **Recovery Guide** | Professional PDF with tables | Copy-paste text |

---

## 🛠️ Technology Stack

### Core
- **Python 3.11** - Primary language
- **Streamlit** - User interface
- **Claude Sonnet 4.5** (Anthropic API) - LLM for medical reasoning

### AI Agents
- **LLM-Powered:** Medical Review, FWA Detection, Cost Escalation Analysis, Medical Guidance
- **Rule-Based:** Completeness Checking, Policy Validation, Bill Reconciliation

### Data Processing
- **pdfplumber** - PDF text extraction
- **ReportLab** - Professional PDF generation
- **Pydantic** - Data validation

### Data
- **Policy Data:** 3 insurers, 6 policies (Star Health, HDFC ERGO, Bajaj Allianz)
- **Medical Data:** 10 procedures with detailed reference guidelines
- **Procedure Registry:** ICD-10 codes, cost ranges, documentation requirements

---

## 📊 Supported Coverage

### Insurers & Policies
1. **Star Health** - Comprehensive, Senior Citizen Red Carpet
2. **HDFC ERGO** - MyOptima
3. **Bajaj Allianz** - Health Guard, Silver Health

### Procedures (10 MVP)
1. Cataract Surgery
2. Coronary Angioplasty
3. Total Knee Replacement (TKR)
4. Appendectomy
5. Cholecystectomy (Gallbladder Removal)
6. Hernia Repair
7. Hysterectomy
8. Cesarean Section
9. TURP (Prostate Surgery)
10. Tonsillectomy

---

## 🎯 Use Cases

### For Patients
- ✅ Validate pre-auth documentation before hospital admission
- ✅ Get plain-language summary of potential issues
- ✅ Download professional recovery instructions PDF
- ✅ Understand cost variances (documented vs undocumented)

### For Hospitals
- ✅ Catch documentation errors before insurer submission
- ✅ Reduce claim rejection rates
- ✅ Provide patients with validated recovery instructions
- ✅ Improve documentation quality over time

### For Hackathon Judges
- ✅ Test with sample PDFs (provided in `templates/examples/`)
- ✅ See AI-powered medical reasoning in action
- ✅ Experience complete pre-auth → discharge flow
- ✅ Generate professional recovery PDFs

---

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│   UI Layer (Streamlit)               │
│   - preauth_module.py                │
│   - discharge_module.py              │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│   Service Layer                      │
│   - PreAuthService                   │
│   - DischargeService                 │
│   - ClaimStorageService              │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│   Agent Layer (4 Pre-auth + 3 Discharge) │
│   - Completeness, Policy, Medical,   │
│     FWA, Bill Reconciliation, etc.   │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│   Data Layer (JSON)                  │
│   - Policy rules, Medical guidelines │
└─────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Anthropic API Key ([Get one here](https://console.anthropic.com/))

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd Iris

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Running the Application

```bash
# Run Streamlit app
streamlit run src/app.py

# Application opens at http://localhost:8501
```

---

## 📝 How to Use

### Pre-Authorization Validation

1. **Select Module:** Choose "📋 Pre-Authorization"
2. **Enter Policy Details:**
   - Select insurer and policy type
   - Enter policy number, sum insured, policy start date
   - Select procedure
3. **Upload Medical Note PDF** (from doctor)
4. **Click "🔍 Validate Documentation"**
5. **Review Results:**
   - Overall score and status
   - Section-wise analysis (Completeness, Policy, Medical, FWA)
   - Actionable recommendations
6. **Optional:** Click "💾 Save for Discharge Validation" to get a Reference ID

### Discharge Validation

1. **Select Module:** Choose "🏥 Discharge Validation"
2. **Choose Input Mode:**
   - **With Reference ID:** Enter your CR-XXXXXXXX ID from pre-auth
   - **Manual:** Enter pre-auth costs manually
3. **Upload Documents:**
   - Final Hospital Bill PDF
   - Discharge Summary PDF
4. **Click "🔍 Validate Discharge Documents"**
5. **Review Results:**
   - Completeness score and status
   - Cost variance analysis
   - Bill comparison
6. **Download Recovery Instructions PDF** - Professional patient guide

---

## 📂 Project Structure

```
Iris/
├── data/
│   ├── procedure_registry.json          # Procedure metadata
│   └── stored_claims/                   # Saved pre-auth validations (CR-*.json)
├── medical_data/                        # 10 procedure reference guides
│   ├── cataract.json
│   ├── appendectomy.json
│   └── ...
├── policy_data/                         # 6 insurer policy rules
│   ├── star_comprehensive.json
│   ├── hdfcergo_myoptima.json
│   └── ...
├── templates/                           # Medical note templates
│   └── examples/                        # Sample test PDFs
├── src/
│   ├── agents/                          # 7 validation agents
│   ├── services/                        # Orchestration layer
│   ├── modules/                         # UI modules
│   ├── utils/                           # PDF extraction, data loading
│   └── app.py                           # Main Streamlit app
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🎓 Key Design Principles

### 1. Patient-First Language
- All summaries in simple, non-technical language
- Clear cost breakdowns, not jargon

### 2. Hospital Utility
- Actionable recommendations, not just scores
- Specific fixes: "Add VA measurement" (not "Insufficient justification")

### 3. No False Positives
- High cost alone is not fraud
- Range-aware validation (costs within medical_data ranges = acceptable)
- Context matters (bilateral surgery ≠ unilateral surgery)

### 4. Insurer Alignment
- Validates against actual policy rules (no assumptions)
- Waiting periods are hard rejections
- Room rent sub-limits calculated correctly

### 5. No Predictions (Discharge)
- We document WHAT HAPPENED (not if it's justified)
- We show variance analysis (not approval prediction)
- We provide medical guidance (not financial promises)

---

## 🧪 Testing

### Sample Test Cases
Located in `templates/examples/`:
- ✅ Complete pre-auth note (should score 90-95)
- ⚠️ Weak justification (should score 70-75)
- ❌ Policy violation (should score 60-65)

### Run Tests
```bash
pytest tests/
```

---

## 🔒 Privacy & Security

- **No data stored on external servers** (local file storage only)
- **PDFs processed temporarily** (deleted after extraction)
- **LLM calls sanitized** (no PII sent beyond necessary medical context)
- **Reference IDs are local** (stored in `data/stored_claims/`)

---

## 🌟 Future Roadmap

### Phase 2 (Post-Hackathon)
- [ ] Reimbursement claims support
- [ ] Real-time insurer API integration
- [ ] OCR for handwritten medical notes
- [ ] Mobile app (React Native)
- [ ] Multi-language support (Hindi, Tamil, Telugu)
- [ ] Database integration (PostgreSQL)
- [ ] User authentication

### Phase 3 (Production)
- [ ] Hospital dashboard (batch validation)
- [ ] Analytics & insights
- [ ] Insurance company portal
- [ ] Blockchain for audit trail

---

## 📊 Impact Metrics (Projected)

| Metric | Current (Without Iris) | With Iris |
|--------|------------------------|-----------|
| Claim Rejection Rate | 12.9% | **<3%** |
| Documentation Fix Time | 3-5 days | **<1 hour** |
| Patient Anxiety | High | **Low** (know issues before submission) |
| Hospital Admin Cost | High | **50% reduction** |

---

## 📚 Documentation

- **[CLAUDE.md](CLAUDE.md)** - Complete architecture, development guidelines, prompt engineering best practices
- **[Iris PRD.md](Iris%20PRD.md)** - Product requirements document
- **[Iris_backend_logic.md](Iris_backend_logic.md)** - Detailed implementation logic

---

## 📄 License

Proprietary - Iris MVP

---

## 🤝 Contributing

This is a hackathon project. For questions or collaboration, open an issue on GitHub.

---

## 🙏 Acknowledgments

- **Anthropic** - Claude API for medical reasoning
- **Star Health, HDFC ERGO, Bajaj Allianz** - Policy documentation
- **Medical reference data** - Based on standard treatment protocols
- **India's healthcare community** - For highlighting the cashless claims problem

---

## ⚡ Quick Demo

**Try it now:**
1. `streamlit run src/app.py`
2. Select "Pre-Authorization"
3. Choose "Star Health - Comprehensive" + "Cataract Surgery"
4. Upload sample PDF from `templates/examples/`
5. See AI-powered validation in action!

---

**Built for India. Built for patients. Built to reduce claim rejections.**

🏥 **Iris - Your Claims Co-Pilot** 🏥
