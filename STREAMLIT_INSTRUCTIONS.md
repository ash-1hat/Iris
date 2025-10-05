# ClaimReady Streamlit App - User Guide

## 🚀 Quick Start

### 1. Start the Application

```bash
# Activate virtual environment
venv\Scripts\activate

# Run Streamlit app
streamlit run src/streamlit_app.py
```

The app will open in your browser at: **http://localhost:8501**

---

## 📋 How to Use

### Step 1: Enter Policy Details

**Left Column:**
- **Insurance Company**: Select from dropdown (Star Health, HDFC ERGO, Bajaj Allianz)
- **Policy Type**: Select policy type based on insurer
- **Policy Number**: Enter policy number (e.g., SH12345678)
- **Sum Insured**: Enter coverage amount (₹100,000 - ₹10,000,000)

**Right Column:**
- **Policy Start Date**: When policy was purchased
- **Planned Admission Date**: When hospitalization is planned
- **Patient Age at Policy Start**: Patient's age when policy started
- **Previous Claims This Year**: Amount already claimed (₹)

### Step 2: Select Procedure

Choose the procedure from dropdown:
- Cataract Surgery
- Total Knee Replacement
- Coronary Angioplasty
- And more...

### Step 3: Upload Medical Note PDF

- Click "Browse files" button
- Select pre-authorization medical note PDF
- Supported format: PDF only
- Use template format for best results

### Step 4: Validate Documentation

- Click **"🔍 Validate Documentation"** button
- Wait for processing (5-10 seconds)
- Review results

---

## 📊 Understanding Results

### Overall Metrics

1. **Documentation Score** (0-100)
   - 80-100: Complete ✅
   - 60-79: Needs Review ⚠️
   - 0-59: Incomplete ❌

2. **Status**
   - ✅ Complete: All checks passed
   - ⚠️ Needs Review: Minor issues found
   - ❌ Incomplete: Critical issues found

3. **Readiness**
   - 🟢 High: Ready for submission
   - 🟡 Medium: Address minor issues first
   - 🔴 Low: Critical issues must be fixed

### Section-wise Analysis

The app validates 4 key areas:

#### 📋 Documentation Completeness
- Checks if all required fields are present
- Validates cost breakdown
- Ensures all sections are filled

**Common Issues:**
- Missing patient ID
- Incomplete cost breakdown
- Missing doctor contact details

#### 📜 Policy Compliance
- Validates waiting periods (initial, procedure-specific)
- Checks policy exclusions
- Verifies sum insured adequacy
- Validates room rent limits

**Common Issues:**
- Waiting period not met (e.g., 24 months for cataract)
- Procedure excluded under policy
- Cost exceeds sum insured

#### 🏥 Medical Review
- Assesses treatment-diagnosis alignment
- Validates hospitalization necessity
- Reviews documentation quality
- Checks functional impact evidence

**Common Issues:**
- Weak medical justification (generic language)
- Missing diagnostic test results
- Insufficient functional impact documentation

#### 🔍 Fraud/Quality Check
- Detects cost outliers
- Identifies duration anomalies
- Flags suspicious patterns

**Common Issues:**
- Cost significantly above typical range
- Unnecessary extended stay
- Missing justification for premium items

---

## ✅ Action Items

The app provides specific recommendations to fix issues:

**Priority Order:**
1. 🚫 CRITICAL: Policy violations (blockers)
2. 📋 Required: Missing mandatory information
3. 🏥 Medical: Documentation improvements
4. ⚠️ Policy: Warnings that need attention
5. 🔍 FWA: Quality concerns requiring explanation

---

## 📝 Sample Test Cases

### Test Case 1: Cataract Surgery (Complete)

**Policy Details:**
- Insurer: Star Health
- Policy: Comprehensive
- Policy Number: SH12345678
- Policy Start: 2023-01-01 (>24 months ago)
- Sum Insured: ₹5,00,000
- Planned Admission: 2025-10-05
- Patient Age at Start: 65
- Previous Claims: ₹0

**PDF:** `medical_note_pdf Template.pdf`

**Expected Result:**
- Score: 85-95
- Status: Complete/Needs Review
- Minor issues in optional fields

### Test Case 2: Knee Replacement

**Policy Details:**
- Insurer: Star Health
- Policy: Comprehensive
- Policy Number: SH98765432
- Policy Start: 2022-01-01
- Sum Insured: ₹5,00,000
- Planned Admission: 2025-10-10
- Patient Age at Start: 62
- Previous Claims: ₹0

**PDF:** `test2.pdf`

**Expected Result:**
- Score: 80-90
- Higher cost (₹3.35L) triggers quality checks
- Should pass all validations

---

## 🎯 Key Features

### ✅ What the App DOES:
- Validates documentation completeness
- Identifies missing information
- Checks policy compliance
- Assesses medical justification quality
- Detects potential quality issues
- Provides actionable recommendations

### ❌ What the App DOES NOT DO:
- Make approval/rejection decisions
- Guarantee claim acceptance
- Replace insurer review process
- Provide medical advice

---

## 🐛 Troubleshooting

### PDF Upload Issues
- **Error:** "Failed to extract text from PDF"
  - **Fix:** Ensure PDF is text-based (not scanned image)
  - **Fix:** Use template format for best results

### Validation Errors
- **Error:** "Procedure not found in registry"
  - **Fix:** Check procedure ID in dropdown matches PDF

- **Error:** "Policy file not found"
  - **Fix:** Ensure policy JSON exists in `policy_data/` folder

### Score Issues
- **Score lower than expected:**
  - Check all mandatory fields are filled
  - Review medical justification language
  - Ensure diagnostic tests are documented
  - Verify cost breakdown is complete

---

## 📁 File Structure

```
Iris/
├── src/
│   └── streamlit_app.py          # Main Streamlit application
├── medical_note_pdf Template.pdf  # Sample template
├── test2.pdf                      # Sample knee replacement case
└── policy_data/                   # Policy JSON files
    ├── star_comprehensive.json
    └── ...
```

---

## 🔄 Next Steps After Validation

1. **If Score > 80 (Complete):**
   - Review any minor recommendations
   - Submit to insurer

2. **If Score 60-80 (Needs Review):**
   - Address identified issues
   - Strengthen medical justification
   - Re-validate after fixes

3. **If Score < 60 (Incomplete):**
   - Fix all critical issues first
   - Complete missing mandatory fields
   - Consult doctor for medical concerns
   - Re-validate before submission

---

## 💡 Tips for Best Results

1. **Use Template Format:**
   - Follow the standard pre-auth template
   - Fill all sections completely
   - Include specific medical details

2. **Medical Justification:**
   - Use patient-specific language (not generic)
   - Document objective measurements (VA 6/60)
   - Describe functional impact (specific activities)
   - Include diagnostic test results

3. **Policy Compliance:**
   - Check waiting periods BEFORE planning surgery
   - Verify procedure is not excluded
   - Ensure sum insured is adequate

4. **Cost Documentation:**
   - Provide itemized breakdown
   - Justify any premium items (IOL type, etc.)
   - Match costs to hospital tier and complexity

---

## 📞 Support

For issues or questions:
1. Check this guide first
2. Review error messages carefully
3. Verify PDF format and policy details
4. Contact development team if issues persist

---

**Version:** 1.0.0
**Last Updated:** October 2025
**Framework:** Streamlit 1.31.0
