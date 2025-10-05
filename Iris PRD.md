ClaimReady: Complete Cashless Claims Co-Pilot
High-Level Product Requirements Document

Problem Statement
India dreams of 100% cashless healthcare, but the system is collapsing under its own friction. Major insurers like Bajaj and Care are denying cashless approvals to patients at network hospitals, forcing families to pay lakhs upfront during medical emergencies. Even when cashless is initially approved, patients face hours-long discharge delays while insurers scrutinize final bills, often resulting in surprise deductions.
The Crisis in Numbers (FY 2023-24):

₹26,000 crore in claims rejected or stuck in limbo (19% increase YoY)
12.9% of claims rejected due to incomplete documentation - errors that could have been prevented
Reimbursement claimants report 3x higher dissatisfaction (12% vs 4% for cashless) due to upfront financial burden
68% of reimbursement patients lack liquid savings to pay hospital bills upfront

Two Critical Failure Points in Cashless Flow:
1. Pre-Authorization Stage (Before Treatment):

Insurers have 1 hour to approve/query/reject
Incomplete documentation or weak medical justification triggers queries
Rejection forces patients into reimbursement (pay everything upfront)
Hospital-insurer communication gap: doctors don't know what insurers need

2. Discharge Authorization Stage (After Treatment):

Insurers have 3 hours to approve final bills
Patients wait hours/days for discharge while insurer scrutinizes every line item
Surprise deductions discovered only at discharge (room upgrades, non-covered items)
No reconciliation between pre-auth estimate and actual costs
Disputes over cost escalations with no clear justification

Root Cause: No validation layer exists between hospitals and insurers. Submissions are blind - hospitals hope for approval, insurers default to skepticism. Patients caught in the middle with zero visibility into what their policy actually covers or what they'll ultimately pay.

Solution: A Three-Sided Co-Pilot for Complete Cashless Journey
ClaimReady is not a spell-checker for insurance forms. It's an intelligent co-pilot that transforms the cashless claims process by acting as:
1. Hospital's Own Claims Adjudicator
Hospitals get their own "first reviewer" before submitting to insurers - catching errors, validating against policy rules, and strengthening medical justifications at BOTH pre-auth and discharge stages.
2. The Missing Bridge Between Medical and Insurance Language
Doctors write for clinical purposes; insurers need financial justification. ClaimReady translates between these worlds, helping doctors understand what insurers need and helping insurers receive standardized, complete submissions.
3. Patient's First Understandable Insurance Guide
Patients get plain-language explanations of what's happening, what their policy covers, what they'll pay, and why - BEFORE surprises happen. Manages anxiety and eliminates opacity.
What Makes It Different:

Complete journey coverage: Only tool addressing both pre-auth AND discharge friction points
Proactive validation: Catches problems before submission, not after rejection
Multi-stakeholder value: Helps hospitals submit better, doctors write better, patients understand better, insurers adjudicate faster
AI-powered intelligence: Uses LLMs for complex medical reasoning and plain-language translation, not just rule-checking


MVP Scope
What's Included:

Pre-authorization validation (before treatment)
Discharge bill validation (after treatment)
3 insurers, 2 policies each (6 total policies)
Top 10 common procedures
Structured forms + PDF upload for medical documents
Plain-language patient summaries at both stages
Email notifications to doctors for medical note improvements
Web interface (Streamlit-based for speed)

What's Deferred to Future:

Reimbursement claims
Emergency hospitalizations
OCR for handwritten/unstructured documents
All insurers/policies coverage
Real-time insurer API integration
Advanced ML-based fraud detection
Mobile app
Bidirectional doctor feedback portal


Core Features
Feature 1: Pre-Authorization Validation Module
Purpose: Ensure pre-auth requests are complete, policy-compliant, and medically justified before submission
User Input:

Insurance provider, policy type
Patient policy details (number, start date, sum insured, previous claims)
Procedure type, hospital name, planned admission date
Estimated costs (itemized: room, doctor, tests, medicines)
Doctor's medical note (PDF upload following template)

What It Checks:

Document Completeness: All required fields present, PDF contains necessary sections
Policy Compliance: Waiting periods met, procedure covered, sum insured adequate, no exclusions
Medical Justification: Treatment aligns with diagnosis, hospitalization justified, diagnostics appropriate
Basic FWA Detection: Cost outliers, overtreatment patterns, unnecessary hospitalization flags

Outputs:

Readiness score (0-100)
Status: Ready for Submission / Needs Minor Revisions / Critical Issues
Category-wise breakdown with specific flags
Actionable recommendations
Email to doctor if medical note has gaps
Plain-language patient summary explaining what will happen

Patient Summary Example:
Before Your Surgery: What to Expect

Your Procedure: Cataract Surgery (Right Eye)
Hospital: Apollo Hospital
Planned Date: October 15, 2025

What Your Policy Covers:
✓ Surgery cost fully covered
✓ 1-2 day hospital stay covered
✓ Standard room included
✓ Pre and post-op medications covered

What You'll Pay:
Estimated: ₹5,000 security deposit (refundable)
If you choose deluxe room: Additional ₹15,000

Approval Likelihood: High (88/100)
Your policy is active, no waiting periods apply.

What Happens Next:
1. Hospital submits this to your insurer
2. Insurer will review (within 1 hour)
3. Once approved, surgery proceeds as planned
4. You'll get another summary after treatment

Feature 2: Discharge Bill Validation Module
Purpose: Reconcile actual costs with pre-auth, identify non-payable items, eliminate surprise deductions before final insurer submission
User Input:

Pre-auth approval letter (PDF)
Final itemized hospital bill (PDF)
Discharge summary (PDF)
Additional reports/medicines used during treatment

What It Checks:

Bill Reconciliation: Does final bill match pre-auth estimate? If higher, is escalation justified?
Non-Payable Items Detection: Scan for commonly excluded items (admin fees, room upgrades, certain disposables)
Documentation Completeness: All discharge documents present (summary, reports, pharmacy bills, implant stickers)
Cost Escalation Justification: Extended stay, additional procedures, ICU usage - are they medically documented?

Outputs:

Discharge readiness score (0-100)
Reconciliation report (pre-auth vs actual)
Non-payable items flagged with patient's exact out-of-pocket amount
Missing justifications for cost increases
Complete vs incomplete documentation checklist
Plain-language patient summary of final bill

Patient Summary Example:
After Your Surgery: Final Bill Breakdown

Total Hospital Bill: ₹78,000
What Insurance Pays: ₹65,000
What You Pay: ₹13,000

Why You're Paying ₹13,000:
- Room upgrade (deluxe vs standard): ₹10,000
- Administrative fees (not covered): ₹3,000

Why Bill is Higher Than Estimate (₹65,000):
- You stayed 2 days instead of planned 1 day
- Reason: Post-op observation required (doctor's note attached)
- Insurer will likely approve this as medically necessary

Good News:
- No surprise charges discovered
- All documents complete
- Expected discharge approval: Within 3 hours
- You can arrange exact payment now (₹13,000)

Next Steps:
1. Hospital submits final bill to insurer
2. Insurer reviews (should take < 3 hours per regulation)
3. Once approved, pay ₹13,000 and you're discharged
4. No waiting, no surprises

Feature 3: Multi-Agent Validation Engine
Four Specialized AI Agents (Both Modules):
1. Completeness Checker (Rule-based)

Verifies all mandatory fields present
Checks document sections exist
Validates data formats and consistency

2. Policy Validator (Structured lookup)

Loads specific policy rules from JSON
Checks waiting periods, exclusions, limits
Validates sum insured adequacy
Applies sub-limits (room rent, procedure caps)

3. Medical Review Agent (LLM-powered)

Assesses treatment-diagnosis alignment
Evaluates hospitalization necessity
Reviews justification strength
Identifies missing clinical information

4. FWA Detector (LLM + Rules)

Flags cost outliers (>50% above typical)
Identifies overtreatment patterns
Detects unnecessary procedures
Compares against standard protocols

Additional for Discharge Module:
5. Bill Reconciliation Agent (Rule-based)

Compares pre-auth vs actual costs
Calculates variances
Flags significant deviations

6. Non-Payable Items Scanner (LLM-assisted)

Scans bill for common exclusions
Calculates patient's share
Categorizes deductions by policy clause


Feature 4: Stakeholder-Specific Notifications
Doctor Email (When Medical Issues Found):
Automated email with specific gaps in medical note:

Missing diagnostic references
Weak hospitalization justification
Treatment-diagnosis alignment concerns
Suggestions for strengthening submission

Patient Communications:

Plain-language summaries at both stages
No medical jargon
Clear cost breakdowns
Anxiety-reducing explanations
"What happens next" guidance

Hospital Dashboard:

Technical validation results
Insurer-ready submission package
Risk flags and mitigation steps
Document checklist


User Flow
Primary Users: Hospital TPA Desk & Patient
Complete Journey Flow:
STAGE 1: PRE-AUTHORIZATION (Before Treatment)

Patient scheduled for surgery
    ↓
Patient/TPA desk accesses ClaimReady
    ↓
FORM SECTION 1: Policy Information
- Select insurer and policy type
- Enter policy number, start date
- Enter sum insured, previous claims
    ↓
FORM SECTION 2: Procedure Details
- Select procedure from dropdown
- Enter hospital name
- Enter planned admission date
- Input estimated costs breakdown
    ↓
FORM SECTION 3: Medical Documentation
- Upload doctor's medical note (PDF)
- Template provided for download
    ↓
Click "Validate Pre-Authorization"
    ↓
[Processing: 20-30 seconds]
"Analyzing completeness... Checking policy rules... 
 Reviewing medical justification... Scanning for issues..."
    ↓
RESULTS DASHBOARD
- Overall readiness score (e.g., 82/100)
- Status indicator (Green/Yellow/Red)
- Four category cards:
  • Document Completeness: PASS
  • Policy Compliance: WARNING (room rent concern)
  • Medical Review: PASS
  • FWA Check: PASS
- Detailed findings per category
- Specific recommendations
- Patient summary (downloadable PDF)
    ↓
If medical issues found → Email sent to doctor automatically
    ↓
User Actions:
- Download validation report
- Revise and recheck if needed
- Print patient summary
- Submit to insurer with confidence
    ↓
Treatment proceeds...

═══════════════════════════════════════════════════

STAGE 2: DISCHARGE VALIDATION (After Treatment)

Treatment completed, patient ready for discharge
    ↓
Patient/TPA desk accesses ClaimReady again
    ↓
FORM SECTION 1: Reference Information
- Link to previous pre-auth validation (auto-loads policy details)
OR enter claim reference number
    ↓
FORM SECTION 2: Post-Treatment Documents
- Upload pre-auth approval letter (PDF)
- Upload final itemized hospital bill (PDF)
- Upload discharge summary (PDF)
- Upload additional reports if any
    ↓
Click "Validate Discharge Bill"
    ↓
[Processing: 15-20 seconds]
"Reconciling bills... Detecting non-payable items...
 Checking documentation... Calculating your payment..."
    ↓
RESULTS DASHBOARD
- Discharge readiness score (e.g., 78/100)
- Bill reconciliation summary:
  • Pre-auth estimate: ₹65,000
  • Actual bill: ₹78,000
  • Variance: +₹13,000 (+20%)
- Non-payable items breakdown:
  • Room upgrade: ₹10,000
  • Admin fees: ₹3,000
  • Total patient pays: ₹13,000
- Cost escalation analysis:
  • Extended stay: Justified (medical note present)
  • Additional tests: Within protocol
- Document completeness: All present
- Patient summary (exact payment amount)
    ↓
User Actions:
- Download discharge report
- Share exact payment amount with patient
- Address any gaps before insurer submission
- Submit final bill to insurer
    ↓
Patient pays known amount and leaves
No waiting, no surprises

Backend Flow
INPUT LAYER
User submits form + PDF documents
    ↓
Input Validation & Preprocessing
- Form field validation
- PDF text extraction (LLM-based)
- Data normalization
    ↓

VALIDATION LAYER

For Pre-Authorization:
    ↓
[Parallel Processing]
    ↓
┌──────────────────────────────────────────────────────┐
│  Agent 1: Completeness Checker                       │
│  - Check all required fields                         │
│  - Verify PDF sections present                       │
│  Output: Missing items list, score deduction         │
└──────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────┐
│  Agent 2: Policy Validator                           │
│  - Load policy JSON for selected insurer/policy      │
│  - Check waiting periods, exclusions, limits         │
│  - Verify sum insured adequacy                       │
│  Output: Policy violations list, score deduction     │
└──────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────┐
│  Agent 3: Medical Review Agent (Claude API)          │
│  - Analyze treatment-diagnosis alignment             │
│  - Assess hospitalization necessity                  │
│  - Evaluate justification strength                   │
│  Output: Medical concerns, suggestions, score impact │
└──────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────┐
│  Agent 4: FWA Detector (Claude API + Rules)          │
│  - Compare costs vs typical range                    │
│  - Flag overtreatment patterns                       │
│  - Identify unnecessary procedures                   │
│  Output: FWA flags, risk level, score deduction      │
└──────────────────────────────────────────────────────┘
    ↓
Aggregator
- Combine all agent outputs
- Calculate overall score (100 - deductions)
- Determine status (ready/needs revision/critical)
- Generate prioritized recommendations
    ↓

For Discharge Bill Validation:
    ↓
[Parallel Processing]
    ↓
┌──────────────────────────────────────────────────────┐
│  Agent 5: Bill Reconciliation Agent                  │
│  - Extract pre-auth approved amount                  │
│  - Extract final bill amount                         │
│  - Calculate variance                                │
│  - Flag significant deviations (>20%)                │
│  Output: Reconciliation report                       │
└──────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────┐
│  Agent 6: Non-Payable Items Scanner (Claude API)     │
│  - Scan bill line items                              │
│  - Identify excluded items per policy                │
│  - Calculate patient's out-of-pocket                 │
│  Output: Itemized patient payment breakdown          │
└──────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────┐
│  Agent 7: Cost Escalation Analyzer (Claude API)      │
│  - Check if extended stay has justification          │
│  - Verify additional procedures documented           │
│  - Flag unjustified increases                        │
│  Output: Escalation flags and missing justifications │
└──────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────┐
│  Agent 1: Completeness Checker (Reused)              │
│  - Check discharge document completeness             │
│  Output: Missing documents list                      │
└──────────────────────────────────────────────────────┘
    ↓
Aggregator
- Combine all agent outputs
- Calculate discharge readiness score
- Generate patient payment summary
- Create submission recommendations
    ↓

OUTPUT LAYER
    ↓
Results Formatter
- Structure data for dashboard display
- Generate plain-language patient summary
- Create technical report for hospital
    ↓
Notification Service
- If medical gaps found → Send doctor email via MCP
- If patient summary ready → Display prominently
    ↓
User Interface (Streamlit)
- Display results dashboard
- Provide download options
- Enable re-validation if needed
Scoring Logic:
Pre-Authorization:
Base score: 100
- Missing required fields: -5 points each
- Critical policy violations: -20 points each
- Policy warnings: -10 points each
- Medical concerns: -10 points each
- High FWA risk: -20 points
- Medium FWA risk: -10 points

Discharge Bill:
Base score: 100
- Missing discharge documents: -10 points each
- Unjustified cost escalations: -15 points each
- Significant variance without explanation: -20 points
- Documentation discrepancies: -10 points each

Final Status:
80-100: Ready for Submission (Green)
60-79: Needs Minor Revisions (Yellow)
0-59: Critical Issues Found (Red)

Tech Stack
Frontend:

Streamlit (Python-based web framework)

Rapid prototyping
Built-in form widgets and file upload
No separate frontend code needed
Automatic responsive design



Backend:

Python 3.10+
LangChain / LangGraph (agent orchestration - choose based on complexity needs)
Anthropic Claude API (Sonnet 4.5) for LLM reasoning
Pydantic (data validation and schemas)

Document Processing:

pdfplumber or PyPDF2 (basic PDF text extraction)
Claude API (intelligent extraction from semi-structured PDFs)

Data Storage:

JSON files for policy data (no database needed for MVP)
Session state for user data (no persistent storage)
Local file system for templates

Integration:

MCP (Model Context Protocol) for email notifications
SMTP for actual email sending

Development Tools:

Claude Code / Windsurf / Cursor (AI-assisted development)
Git + GitHub (version control)
pytest (testing framework)

Deployment:

Local execution (no cloud deployment for MVP)
Streamlit runs on localhost:8501


Data Requirements
1. Policy Data (Manual Collection & Structuring)
Source: Insurance company websites, policy wording documents
Insurers to Cover:

Star Health Insurance
HDFC ERGO
ICICI Lombard

Policies per Insurer: 2 (individual + family floater)
Data to Extract per Policy:
json{
  "policy_id": "unique_identifier",
  "insurer": "Company name",
  "policy_name": "Product name",
  "base_rules": {
    "initial_waiting_period_days": 30,
    "sum_insured_options": [500000, 1000000, ...],
    "room_rent_limit_type": "percentage | fixed",
    "room_rent_limit_value": 1,
    "copayment_percentage": 0
  },
  "waiting_periods": {
    "procedure_name": days
  },
  "exclusions": ["list of excluded treatments"],
  "medication_coverage": {
    "generic_mandatory": true/false
  },
  "procedures": {
    "procedure_name": {
      "covered": true/false,
      "typical_cost_range": [min, max],
      "typical_stay_days": [min, max],
      "hospitalization_required": true/false
    }
  }
}
Format: 6 JSON files (one per policy)

2. Procedure Master Data
Top 10 Procedures to Cover:

Cataract Surgery (Ophthalmology)
Coronary Angioplasty (Cardiology)
Knee Replacement (Orthopedics)
Hernia Repair (General Surgery)
Gallbladder Removal (Cholecystectomy)
Hysterectomy (Gynecology)
Appendectomy (General Surgery)
Caesarean Section (Obstetrics)
Coronary Bypass Surgery (Cardiology)
Hip Replacement (Orthopedics)

Data per Procedure:
json{
  "procedure_id": "unique_identifier",
  "name": "Full procedure name",
  "category": "Medical specialty",
  "icd_codes": ["H25", "H26"],
  "typical_cost_range": [40000, 80000],
  "typical_duration_days": [1, 2],
  "requires_hospitalization": true,
  "standard_diagnostics": ["tests required"],
  "common_justifications": ["typical medical reasons"]
}
Source: Medical literature, CGHS rate lists, hospital surveys
Format: Single JSON file with all 10 procedures

3. Document Templates
Medical Note Template (PDF):

Structured format for doctors to fill
Sections: Patient info, diagnosis, clinical history, diagnostic tests, proposed treatment, justification, cost estimate, doctor details
Provide as downloadable blank template
Create 3-4 filled examples for testing

Common Non-Payable Items List:
json{
  "non_payable_items": [
    {
      "item": "Administrative charges",
      "typical_amount_range": [500, 2000],
      "reason": "Policy exclusion - admin fees"
    },
    {
      "item": "Room upgrade charges",
      "calculation": "actual_room_rent - policy_limit_room_rent",
      "reason": "Exceeds policy sub-limit"
    },
    {
      "item": "Disposables (certain)",
      "coverage": "partial",
      "reason": "Policy covers only 50% of disposables"
    }
  ]
}

4. Test Cases
Purpose: Validate system behavior across scenarios
Categories:

Happy path (all checks pass)
Policy violations (waiting period, exclusions)
Incomplete documentation
Weak medical justification
FWA risk scenarios
Bill reconciliation mismatches
Non-payable items detection

Format:
json{
  "test_case_id": "TC001",
  "scenario": "Happy path pre-auth",
  "stage": "pre-authorization",
  "expected_score_range": [85, 95],
  "expected_status": "ready",
  "input_data": {...},
  "expected_flags": []
}
Total: 15-20 test cases covering both modules

This PRD provides a complete, two-stage solution that addresses the entire cashless journey. The discharge module completes the value proposition by eliminating the second major friction point patients face. Build both - the discharge validation is simpler than pre-auth and makes your story complete.