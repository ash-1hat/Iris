# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Iris** is a cashless health insurance claims co-pilot for India. It validates pre-authorization and discharge claims before submission to insurers, reducing rejections and patient anxiety by catching errors, validating policy compliance, and providing plain-language explanations.

**Key Problem Solved**: India's cashless healthcare system has a 12.9% rejection rate due to incomplete documentation. Iris acts as the hospital's "first reviewer" before insurer submission.

## Architecture

### Service-Based Design

**Core Principle**: Direct service layer calls from Streamlit UI. Services orchestrate agents and handle business logic.

**Architecture Layers:**
```
┌─────────────────────────────────────┐
│   UI Layer (Streamlit)               │  ← app.py with module navigation
│   - preauth_module.py                │
│   - discharge_module.py              │
└─────────────────────────────────────┘
                 ↓ Direct calls
┌─────────────────────────────────────┐
│   Service Layer                      │  ← Business logic orchestration
│   - PreAuthService                   │
│   - DischargeService                 │
│   - ClaimStorageService              │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│   Aggregator Layer                   │  ← Combines agent results
│   - PreAuthAggregator                │
│   - DischargeAggregator              │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│   Agent Layer                        │  ← Validation agents
│   - Completeness, Policy, Medical,  │
│     FWA, Bill Reconciliation, etc.  │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│   Data Layer                         │  ← JSON data
│   - Policy data, Medical data        │
└─────────────────────────────────────┘
```

### Two-Stage Validation Pipeline

1. **Pre-Authorization Module** (before treatment) ✅ COMPLETE
   - Validates claim completeness, policy compliance, medical justification
   - Uses 4 agents: Completeness Checker, Policy Validator, Medical Review Agent, FWA Detector
   - Outputs: Readiness score (0-100), actionable recommendations, plain-language patient summary
   - Can save validated claims with unique ID for later discharge validation

2. **Discharge Bill Module** (after treatment) ✅ COMPLETE
   - Reconciles actual costs vs pre-auth estimate
   - Uses 3 agents: Bill Reconciliation Agent, Cost Escalation Analyzer, Medical Guidance Generator
   - Two input modes: With saved claim ID OR manual pre-auth cost entry
   - Outputs: Documentation completeness score, cost variance analysis, patient medical guidance
   - **Philosophy**: NO payment predictions, NO approval predictions - focus on documentation completeness and patient care instructions

### Multi-Agent System

**Pre-Auth Agents:**
- `completeness_checker.py` - Rule-based validation of required fields and documents
- `policy_validator.py` - Structured lookup against policy JSON (waiting periods, exclusions, sub-limits)
- `medical_reviewer.py` - LLM-powered assessment of treatment-diagnosis alignment
- `fwa_detector.py` - Hybrid rule-based + LLM fraud/waste/abuse detection

**Discharge Agents:**
- `bill_reconciliation.py` - Rule-based comparison of pre-auth vs actual costs, variance categorization
- `cost_escalation_analyzer.py` - LLM analysis of whether cost variances are documented in discharge summary
- `medical_guidance_generator.py` - LLM extraction of post-discharge care instructions for patient

**Orchestration:**
- `preauth_service.py` - Orchestrates pre-auth validation, returns tuple (ValidationResult, medical_note_dict)
- `discharge_service.py` - Orchestrates discharge validation flow
- `preauth_aggregator.py` - Combines pre-auth agent outputs, calculates final score
- `discharge_aggregator.py` - Combines discharge agent outputs, formats results

## Data Structure

### Policy Data (`policy_data/*.json` and `reference/*.json`)
JSON files containing insurer-specific rules:
- Waiting periods (initial, pre-existing disease, procedure-specific)
- Exclusions list
- Coverage limits by sum insured tier
- Room rent sub-limits and co-payment rules
- Special features (cumulative bonus, restoration, PED buyback)

**Format**: Each policy is a separate JSON with nested structure for `waiting_periods`, `exclusions`, `coverage_by_sum_insured`, `room_rent`, `co_payment`, etc.
### Policy JSON Critical Fields for Agents

**For Policy Validator:**
- `waiting_periods.initial_days`: Usually 30
- `waiting_periods.pre_existing_disease_months`: Usually 36
- `waiting_periods.specific_conditions.{procedure}`: Check this!
- `exclusions`: Array of strings - do substring match
- `coverage_by_sum_insured.{SI}.{benefit}`: Get limits per SI tier

### Medical Procedure Data (`medical_data/*.json`)
Comprehensive procedure-specific reference data:
- ICD-10 codes, typical costs, hospitalization standards
- Required diagnostics (mandatory vs optional/situational)
- Medical necessity criteria and documentation requirements
- FWA detection patterns (cost inflation, overtreatment, diagnosis-treatment mismatches)
- Common complications and their legitimate cost impacts

**Example**: `cataract.json` contains 856 lines of detailed guidance on cataract surgery, including cost breakdowns, red flags for overnight admission, premium IOL justification requirements, etc.

### Procedure Registry (`data/procedure_registry.json`)

### Procedure Registry Format

The `data/procedure_registry.json` is the lookup table:
```json
{
  "procedures": [
    {
      "procedure_id": "cataract_surgery",
      "user_display_name": "Cataract Surgery",
      "common_synonyms": ["cataract operation", "lens replacement", "phaco"],
      "medical_data_file": "cataract.json",
      "policy_waiting_period_key": "cataract_surgery",
      "icd_10_codes": ["H25.9", "H26.9"]
    }
  ]
}
Maps user-facing procedure names to medical data files and policy keys.
- `procedure_id`: Internal identifier
- `user_display_name': What is shown as a drop down to users
- `common synonmys` : In the medical note or somewhere, if the procedure is not in the exact same name, check the common synonmys for matching. The procedure can also called by names mentioned in common synonmys.
- `medical_data_file`: Points to detailed JSON in `medical_data/`
- `policy_waiting_period_key`: Maps to policy JSON waiting period field
- `icd_10_codes`: For cross-referencing diagnoses

## Recent Optimizations (October 2025)

### Agent Prompt Engineering Refinements

**Critical Principle: Agent Separation of Concerns**
- **Agent 3 (Medical Reviewer)** = Medical documentation quality and clinical justification ONLY
- **Agent 4 (FWA Detector)** = Cost analysis and fraud/waste/abuse detection ONLY
- Never mix responsibilities - prevents double-flagging and confusion

**Agent 3 (Medical Reviewer) - Cost Separation Optimization**:
- Added explicit instruction: **"DO NOT COMMENT ON COSTS"**
- Costs, implant pricing, room charges, surgeon fees are Agent 4's responsibility
- Agent 3 focuses exclusively on:
  - Treatment-diagnosis alignment
  - Medical justification quality (specific vs template language)
  - Functional impact documentation
  - Required diagnostic tests
- Now receives complete medical note in structured format (all sections: diagnosis, clinical history, diagnostic tests, justification, hospitalization details)
- Relaxed pre-operative test requirements: "Consider passed if at least one test from mandatory section is done"
- Clarified that 1-day admission for day surgery is standard practice (includes prep, surgery, recovery)

**Agent 4 (FWA Detector) - Range-Aware Validation Optimization**:
- Added explicit instruction: **"DO NOT FLAG costs that are WITHIN the stated range"**
- **Only flag if costs EXCEED the maximum** from medical_data JSON ranges
- Example: If anesthesia range is ₹3,000-10,000 and quoted is ₹8,000 → PASS (within range)
- Example: If room charges range is ₹7,000-20,000 and quoted is ₹18,000 → PASS (within range)
- Only flag costs >2x typical maximum without clear justification
- Now receives complete `cost_analysis` JSON and `fraud_waste_abuse_patterns` JSON from medical_data
- Added instruction: "Be FAIR, FLEXIBLE and REASONABLE - costs at upper end of range are acceptable for pre-authorization stage"
- Recognizes implants can be in different line items:
  - Separate line: "Implants: ₹X"
  - Combined: "Medicines/Consumables/Implants: ₹X"
  - Embedded: "Other: ₹X"
- 1-day admission for day surgery explicitly marked as NORMAL

**Impact of Optimizations**:
- ✅ Eliminates false positives for costs within acceptable ranges
- ✅ Prevents Agent 3 from flagging cost issues (not their job)
- ✅ Prevents Agent 4 from flagging missing implant line items when embedded in medicines/consumables
- ✅ More nuanced, context-aware validation aligned with medical practice standards

**Current Status (October 2025)**:
- **Pre-Authorization Module: ✅ 100% Complete**
  - All 4 agents implemented and optimized
  - PDF extraction working (with encoding fixes for ₹ symbol)
  - Streamlit UI functional with module navigation
  - Claim storage system implemented
- **Discharge Module: ✅ 100% Complete**
  - All 3 agents implemented (Bill Reconciliation, Cost Escalation Analyzer, Medical Guidance Generator)
  - PDF extractors for bill and discharge summary
  - Streamlit UI with two input modes (claim ID lookup or manual entry)
  - Aggregator and service layer complete

### UI Improvements (October 2025)

**Problem 1: Terminology Confusion**
- UI terminology made it appear we are the insurance company accepting claims
- Users saw "Save Claim", "Claim Reference ID" and thought they were submitting to us

**Solution 1: Terminology Neutrality**
- Removed all "Claim" references that imply claim submission/acceptance
- Updated to neutral, accurate terminology focused on data validation

**Changes Made:**
```
OLD                                    → NEW
"Save Claim for Discharge Tracking"   → "Save Data for Discharge Validation"
"Claim Reference ID"                   → "Reference ID"
"Claim saved successfully!"            → "Data saved successfully!"
"Do you have a Claim ID?"             → "Do you have a Reference ID?"
"Save Claim" button                    → "Save for Discharge Validation" button
```

**Files Modified:**
- `src/modules/preauth_module.py` (lines 276-329): Updated save section terminology
- `src/modules/discharge_module.py` (lines 132-252): Updated discharge form terminology

---

**Problem 2: Information Overload in Recovery Instructions**
- Discharge validation UI displayed extremely long, detailed recovery instructions on-screen
- Multiple expanded sections (medications, follow-ups, do's, don'ts, warning signs)
- Required excessive scrolling, overwhelming for patients
- No printable takeaway format

**Solution 2: Summary View + Professional PDF Download**
- Replaced detailed on-screen sections with concise 4-bullet summary
- Added prominent "Download Complete Recovery Guide (PDF)" button
- Created professional PDF generator with proper formatting and tables

**UI Changes:**
```
BEFORE:
💊 Medications Schedule (expanded)
  - Long detailed list of 4+ medications with dosage, duration, purpose
  - Key reminders section
📅 Follow-up Appointments (expanded)
  - Detailed appointment list
  - What to bring section
✅ DO's (collapsed)
  - Long list of recommended activities
🚫 DON'Ts (collapsed)
  - Long list of restricted activities
⚠️ Warning Signs (expanded)
  - Long list of warning signs
🕐 Recovery Timeline

AFTER:
💊 Your Recovery Instructions

📋 Summary:
  - You need to take 4 medication(s)
  - 2 follow-up appointment(s) scheduled
  - 5 recommended activities, 6 activities to avoid
  - 4 warning signs to watch for

[📄 Download Complete Recovery Guide (PDF)] ← Prominent primary button

💡 Download the PDF for a complete, printable recovery guide...

🕐 Recovery Timeline
  - (Timeline kept visible)
```

**Files Modified:**
- `src/modules/discharge_module.py` (lines 63-96): Simplified recovery instructions UI

**New File Created:**
- `src/utils/recovery_pdf_generator.py` (300+ lines)
  - Professional PDF generation using ReportLab
  - Well-formatted sections with color coding:
    - **Medications Table**: 5 columns (Name, Dosage, Duration, Purpose) with green header
    - **Follow-up Appointments Table**: 3 columns (When, Purpose) with blue header and [IMPORTANT] tags
    - **Activity Guidelines**: Side-by-side table (DO's in light green | DON'Ts in light red)
    - **Warning Signs**: Highlighted yellow/orange box with bullet list
    - **Recovery Timeline**: Paragraph text from Agent 8
  - Auto-generated filename: `recovery_instructions_{patient_name}.pdf`
  - Professional styling with proper margins, fonts, spacing

**PDF Structure:**
```
┌─────────────────────────────────────────┐
│   Recovery Instructions                 │
│   Patient: XXX | Generated: Date        │
├─────────────────────────────────────────┤
│ 💊 Medications Schedule                 │
│   [5-column table with green header]    │
│   ⚠️ Important Reminders (bullets)       │
├─────────────────────────────────────────┤
│ 📅 Follow-up Appointments               │
│   [3-column table with blue header]     │
│   What to Bring (bullets)               │
├─────────────────────────────────────────┤
│ 🏃 Activity Guidelines                  │
│   [2-column: DO's | DON'Ts]            │
├─────────────────────────────────────────┤
│ ⚠️ Warning Signs                         │
│   [Yellow highlighted box with bullets] │
├─────────────────────────────────────────┤
│ 🕐 Recovery Timeline                    │
│   [Paragraph text]                      │
├─────────────────────────────────────────┤
│ IMPORTANT NOTES: [Disclaimer]           │
└─────────────────────────────────────────┘
```

**Impact of UI Improvements:**
- ✅ Clear role separation - users understand we validate, not submit claims
- ✅ Reduced cognitive load - concise summary instead of overwhelming detail
- ✅ Better patient experience - downloadable PDF for home reference
- ✅ Professional output - properly formatted tables and color-coded sections
- ✅ Backwards compatible - existing saved data works without changes (CR-XXXXXXXX format unchanged)

**Dependencies:**
- Uses `reportlab` library (already in requirements.txt) for PDF generation

**Documentation:**
- See `UI_IMPROVEMENTS_SUMMARY.md` for complete before/after comparison and testing checklist

## Key Technical Details

### LLM Integration
- Uses **Claude Sonnet 4.5** (Anthropic API) for medical reasoning tasks
- Temperature: 0.3 for validation tasks, 0.5-0.6 for patient summaries
- Prompts include structured input format, specific assessment criteria, and request JSON output for parsing
- All LLM calls should include error handling with graceful degradation (if medical review fails, still show other agent results)

### PDF Processing
- Uses `pdfplumber` for basic text extraction first
- Falls back to Claude API for intelligent extraction from semi-structured medical notes
- **Template**: Standard pre-authorization medical note format with 10 sections (A-J)
- **Key sections to extract**:
  - Section A: Patient Information (name, age, gender, contact)
  - Section B: Diagnosis (primary diagnosis, ICD-10 code)
  - Section C: Clinical History (complaints, duration, co-morbidities)
  - Section D: Diagnostic Tests (test name, date, findings)
  - Section E: Proposed Treatment (procedure name, surgical approach, anesthesia)
  - Section F: Medical Justification (why hospitalization needed, why necessary, expected outcomes)
  - Section G: Hospitalization Details (admission date, length of stay, ICU needs)
  - Section H: Cost Breakdown (room, surgeon, OT, ICU, investigations, medicines, implants)
  - Section I: Doctor Details (name, qualification, registration number, email, phone)
  - Section J: Hospital Details (name, address, registration number)
- Extraction must handle both filled forms (with values) and partially filled PDFs

**PDF Extraction Fixes (October 2025)**:
- **Character Encoding Issue**: ReportLab-generated PDFs render ₹ symbol as ■ (black square)
  - Solution: Updated all regex patterns to accept `(?:₹|Rs\.?|■)?`
- **Section-Specific Extraction**: Numbers from earlier sections (e.g., "TLC 18,500/cumm") were being matched by cost regex
  - Solution: Extract cost section first (`11. ESTIMATED COST` to `12. DECLARATION`), then apply regex only to that section
  - All cost extraction now searches `cost_text` (isolated cost section) instead of full document text
- **Result**: Correctly extracts costs from properly formatted PDFs even with encoding issues

### Scoring Logic
**Pre-Authorization:**
- Base: 100 points
- Deductions: Missing fields (-5 each), critical policy violations (-20), warnings (-10), medical concerns (-10), high FWA risk (-20)
- Status: 80-100 = Ready (Green), 60-79 = Needs Revision (Yellow), 0-59 = Critical Issues (Red)

**Discharge:**
- Base: 100 points
- Deductions: Missing documents (-10 each), undocumented cost escalations (-15), significant variance without explanation (up to -20)
- Focus on documentation completeness, not payment prediction

### Pydantic Model Handling

**Critical Pattern**: Services returning multiple values use tuples
- `preauth_service.validate_preauth_from_pdf()` returns `(ValidationResult, medical_note_dict)`
- Unpack in UI: `result, medical_note = service.validate_preauth_from_pdf(...)`
- Pydantic models are immutable - cannot dynamically add fields
- Use `getattr(obj, 'field', default)` for safe attribute access
- Use `hasattr(obj, 'field')` before accessing optional attributes

### Import Path Conventions

**From within src/ directory:**
- ❌ Wrong: `from src.modules import preauth_module`
- ✅ Correct: `from modules import preauth_module`
- When running from src/, import paths don't include "src." prefix

## Development Workflow

### Running the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable
# Create .env file with: ANTHROPIC_API_KEY=your_key

# Run Streamlit app
streamlit run src/app.py

# Application opens at localhost:8501
```

### Testing
- Unit tests for each agent in `tests/`
- Test cases defined in `tests/test_cases.json` (15-20 scenarios covering happy path, policy violations, FWA patterns)
- Test PDFs in `templates/examples/` (complete, incomplete, weak justification samples)

### Common Development Tasks

**Adding a new procedure:**
1. Create detailed JSON in `medical_data/{procedure_name}.json` following the cataract.json structure
2. Add entry to `data/procedure_registry.json` with ICD codes and policy mapping
3. Update policy JSONs to include procedure in waiting periods or coverage sections

**Adding a new insurer/policy:**
1. Extract policy wording PDF from insurer website
2. Manually create JSON in `data/policies/{insurer}_{policy}.json`
3. Map all 10 MVP procedures to policy rules (covered/excluded, waiting periods, sub-limits)
4. Add to dropdown options in Streamlit UI

**Modifying scoring logic:**
- Pre-auth: Edit `aggregate()` method in `preauth_aggregator.py`
- Discharge: Edit `aggregate()` method in `discharge_aggregator.py`
- Individual agent scoring: Update `score_impact` calculation in respective agent file

**Improving LLM prompts:**
- Medical review: `medical_reviewer.py` - includes assessment criteria and common pitfalls
- FWA detection: `fwa_detector.py` - includes red flag patterns from medical data JSONs
- Patient summaries: `patient_summary.py` - emphasizes plain language, anxiety reduction

**Best Practices for LLM Prompt Engineering (Learned from October 2025 Optimizations)**:
1. **Explicit Negative Instructions**: Don't just say what to do - explicitly say what NOT to do
   - Example: "DO NOT COMMENT ON COSTS" prevents scope creep
   - Example: "DO NOT FLAG costs WITHIN range" prevents false positives
2. **Provide Complete Context**: Send full medical_data JSON sections, not just extracted values
   - Agents can cross-reference ranges and patterns themselves
   - Reduces hardcoding in prompts
3. **Be Fair, Flexible, Reasonable**: Add explicit tone guidance
   - "Pre-authorization stage" → more lenient than discharge review
   - "Upper end of range is acceptable" → context-aware validation
4. **Use Examples in Prompts**: Concrete examples prevent misinterpretation
   - "If range is ₹7,000-20,000 and quoted is ₹18,000 → PASS"
5. **Separate Agent Responsibilities**: One agent = one concern area
   - Medical quality ≠ Cost analysis
   - Prevents confusion and double-flagging

## Important Constraints & Design Decisions

### MVP Scope
- **Included**: Pre-auth + discharge validation, 3 insurers (6 policies), 10 procedures, web UI
- **Deferred**: Reimbursement claims, OCR for handwritten docs, real-time insurer API integration, mobile app

### Policy Compliance Focus
- Waiting periods are **hard rejections** (critical violations)
- Room rent sub-limits apply proportionate deductions to specific line items only (not pharmacy/implants/ICU)
- Co-payment rules vary by age at entry and policy sections

### Medical Necessity Philosophy
- Requires **both** objective evidence (VA measurements) AND functional impact (specific activities affected)
- Template/generic language triggers red flags
- Premium IOL is patient choice, not medical necessity (unless toric for documented astigmatism >1.5D)

### FWA Detection Nuance
- High cost alone is NOT fraud (tier-1 hospital with premium IOL can legitimately be ₹80,000)
- Context matters: Same cost may be appropriate for bilateral surgery, excessive for unilateral
- Always break down: base cost + justified add-ons + questionable items

### Error Handling Strategy
- **Graceful degradation**: If one agent fails, show partial results with warning
- Never block entire validation due to single agent failure
- PDF extraction failures → ask user to check format and retry
- Claude API timeouts → retry once, then degrade

## File Organization

```
Iris/
├── data/
│   ├── procedure_registry.json          # Procedure metadata registry
│   └── stored_claims/                   # Saved pre-auth validations (CR-{date}-{id}.json)
├── medical_data/                        # Detailed procedure references
│   ├── cataract.json
│   ├── coronory_angioplasty.json
│   ├── total_knee_replacement.json
│   └── ...
├── policy_data/                         # User policy JSON files
│   ├── hdfcergo_myoptima.json
│   ├── star_comprehensive.json
│   └── ...
├── reference/                           # Reference policy JSONs
│   ├── star_comprehensive_c.json
│   ├── bajaj_healthcare.json
│   └── ...
├── templates/                           # Medical note templates & examples
├── tests/                               # Test cases and test PDFs
├── src/
│   ├── agents/                          # Individual validation agents
│   │   ├── completeness_checker.py      # Pre-auth Agent 1
│   │   ├── policy_validator.py          # Pre-auth Agent 2
│   │   ├── medical_reviewer.py          # Pre-auth Agent 3
│   │   ├── fwa_detector.py              # Pre-auth Agent 4
│   │   ├── bill_reconciliation.py       # Discharge Agent 5
│   │   ├── cost_escalation_analyzer.py  # Discharge Agent 6
│   │   └── medical_guidance_generator.py # Discharge Agent 8
│   ├── services/                        # Orchestration and business logic
│   │   ├── preauth_service.py           # Pre-auth orchestration
│   │   ├── discharge_service.py         # Discharge orchestration
│   │   ├── preauth_aggregator.py        # Combines pre-auth results
│   │   ├── discharge_aggregator.py      # Combines discharge results
│   │   └── claim_storage.py             # Save/load claims
│   ├── utils/                           # Utilities
│   │   ├── data_loader.py               # Load JSON data files
│   │   ├── pdf_extractor.py             # Pre-auth medical note extraction
│   │   ├── discharge_pdf_extractor.py   # Discharge bill & summary extraction
│   │   └── recovery_pdf_generator.py    # Recovery instructions PDF generator
│   ├── models/                          # Pydantic schemas
│   │   └── schemas.py                   # All data models
│   ├── modules/                         # UI modules
│   │   ├── preauth_module.py            # Pre-auth UI
│   │   └── discharge_module.py          # Discharge UI
│   └── app.py                           # Main Streamlit app with navigation
├── Iris PRD.md                          # Complete product requirements
├── Iris_backend_logic.md                # Detailed implementation logic
├── discharge_flow.md                    # Discharge module specifications
├── policy_data_extractor.py             # Utility script
├── policy_details_structure.txt         # Policy JSON schema template
└── medical_reference_structure.txt      # Medical data JSON schema template
```

## Reference Documents

- **Iris PRD.md**: Full product vision, user flows, backend architecture, tech stack
- **Iris_backend_logic.md**: Line-by-line implementation logic for every function, agent, and aggregator
- **policy_details_structure.txt**: Template for creating new policy JSONs
- **medical_reference_structure.txt**: Template for creating new procedure reference data

## Key Principles

1. **Patient-first language**: All patient summaries must be in simple, non-technical language with clear cost breakdowns
2. **Doctor feedback**: Email notifications should be advisory, not accusatory (help strengthen submission, not criticize)
3. **Hospital utility**: Provide actionable recommendations, not just scores (specific fixes, not vague suggestions)
4. **Insurer alignment**: Validate against actual policy rules, not assumptions (reference policy JSONs as ground truth)
5. **No false positives**: High cost alone is not fraud; require pattern matching from medical data red flags

## Common Pitfalls to Avoid

- Don't flag premium IOL as fraud if patient has documented astigmatism >1.5D and toric IOL chosen
- Don't approve overnight stay just because patient is elderly - need specific medical reason
- Don't reject just because cost is high - check if items match complexity and hospital tier
- Don't approve "patient wants better vision" as justification - needs objective VA impairment
- Don't mark complications as fraud - they're legitimate if documented contemporaneously with appropriate timeline

## CRITICAL RULES FOR CLAUDE CODE

### Medical Necessity Assessment Rules

1. **Never approve based on patient preference alone**
   - "Patient wants surgery" = REJECT
   - "Better vision desired" = REJECT
   - Need BOTH: Objective impairment (VA < 6/18) AND functional impact (specific activities)

2. **Premium IOL is patient choice, NOT medical necessity**
   - Exception: Toric IOL for documented astigmatism >1.5D
   - Must have corneal topography report showing astigmatism
   - Otherwise flag as "elective upgrade, patient pays difference"

3. **Template language = Red flag**
   - "Standard protocol followed" = insufficient
   - "As per guidelines" = insufficient
   - Need specific patient details, not generic statements

### FWA Detection Rules

1. **High cost ≠ automatic fraud**
   - Tier-1 hospital + premium IOL + bilateral = ₹80,000 is legitimate
   - Same cost for unilateral basic surgery = fraud flag

2. **Context always matters**
   - Read medical_data JSON `justifiable_variations` section
   - Check if cost add-ons match documented conditions
   - Bilateral surgery legitimately costs 1.5-1.8x unilateral, not 2x

3. **Complications are NOT fraud**
   - If documented contemporaneously (same day/next day)
   - If timeline makes sense (PCO after 6 months = legitimate, PCO same day = suspicious)
   - Extended stay due to complication = legitimate IF medical note documents it

4. **Range-based validation is mandatory** (October 2025)
   - Always check against medical_data JSON cost ranges BEFORE flagging
   - **Only flag if cost EXCEEDS the maximum** of the stated range
   - Example: Anesthesia ₹8,000 with range ₹3,000-10,000 → PASS (within range)
   - Example: Room charges ₹18,000 with range ₹7,000-20,000 → PASS (within range)
   - Being at the "upper end" of a range is NOT a red flag - it's acceptable
   - Only flag costs >2x typical maximum without clear medical justification

### Policy Validation Rules

1. **Waiting periods are HARD stops**
   - If procedure waiting period not met = CRITICAL violation
   - No exceptions, no "might be approved"
   - Clear message: "Claim will be rejected. Wait X more days."

2. **Room rent proportionate deduction applies ONLY to specific items**
   - Applies to: room, nursing, surgeon fees, anesthetist fees
   - Does NOT apply to: pharmacy, consumables, implants, diagnostics, ICU
   - Never say "entire claim reduced by X%" - be specific about which line items

3. **Sum insured check includes previous claims**
   - available_sum_insured = total_SI - previous_claims_this_year
   - If new claim exceeds available = WARNING (not rejection)
   - Patient pays difference

### Error Handling Rules

1. **Graceful degradation is mandatory**
   - If medical review agent fails: Show other 3 agent results + warning
   - Never return 500 error for single agent failure
   - Log error, continue with partial results

2. **PDF extraction failure handling**
   - Try pdfplumber first
   - If fails, try Claude API extraction
   - If both fail: Return clear error + ask user to check PDF format
   - Suggest: "PDF may be scanned image. Please use template format."

3. **LLM timeout handling**
   - Retry once with exponential backoff
   - If still fails: Return partial validation without that agent
   - Show message: "Medical review unavailable. Other checks completed."

### Patient Summary Rules

1. **Always use plain language**
   - Never use: "Pre-existing disease waiting period"
   - Instead use: "You need to wait 24 months after buying policy for this surgery"

2. **Be anxiety-reducing, not alarming**
   - Never: "Your claim will probably be rejected"
   - Instead: "There's an issue we should fix before submission"

3. **Give specific next steps**
   - Never: "Justification insufficient"
   - Instead: "Ask your doctor to add: (1) Your current vision measurement, (2) Which daily activities are affected"

### Code Quality Rules

1. **Type hints are mandatory**
   - Every function must have input and return type hints
   - Use Pydantic models for complex objects

2. **No hardcoded values**
   - All thresholds in medical_data JSONs
   - All policy rules in policy_data JSONs
   - Never hardcode "if cost > 50000" - use procedure JSON typical_cost_max

3. **Logging for debugging**
   - Log every agent decision with reasoning
   - Log LLM prompts and responses (sanitized)
   - Log scoring calculations

### Streamlit Session State Management

**Critical for Module Navigation:**
- Store validation results in session state for persistence across form submissions
- Pre-auth results: `st.session_state.preauth_validation_result`, `st.session_state.preauth_medical_note`
- Discharge results: `st.session_state.discharge_validation_result`
- Form data: `st.session_state.preauth_form_data`, `st.session_state.discharge_form_data`
- Use session state to share data between modules (e.g., claim ID from pre-auth to discharge)

### Debugging Guide

**Validation score seems wrong:**
1. Print each agent's score_impact
2. Verify base_score = 100
3. Check if deductions are being applied correctly
4. Compare against test cases in tests/

**LLM gives weird results:**
1. Print the exact prompt being sent
2. Check if contextual_notes_for_llm from medical JSON is included
3. Verify temperature is 0.3 for validation (not 0.7)
4. Check if response is valid JSON

**PDF extraction fails:**
1. Verify PDF is text-based (not scanned image)
2. Try pdfplumber.extract_text() directly to see output
3. Check if section headers match template (SECTION A:, SECTION B:, etc.)
4. Fall back to Claude API with full PDF text

**Agent details not showing in UI:**
1. Check if agent result has `issues`, `violations`, `concerns`, or `flags`
2. Use `hasattr(agent_result, 'concerns')` before accessing
3. Different agents return different result structures - handle all types

## Implementation Notes

### Completed Implementation (October 2025)

**Both modules are fully implemented:**

1. **Pre-Authorization Module** ✅
   - All 4 agents working (Completeness, Policy, Medical Review, FWA)
   - PDF extraction with ₹ encoding fixes
   - Streamlit UI with validation results display
   - Claim storage system with unique IDs (CR-{date}-{id})

2. **Discharge Module** ✅
   - All 3 agents working (Bill Reconciliation, Cost Escalation Analyzer, Medical Guidance Generator)
   - PDF extractors for bill and discharge summary
   - Two input modes: claim ID lookup OR manual pre-auth cost entry
   - Streamlit UI with variance analysis and medical guidance display

3. **Module Navigation** ✅
   - Sidebar + main area radio buttons for switching between Pre-Auth and Discharge
   - Session state management for result persistence
   - Claim data sharing between modules

### Key Implementation Patterns Learned

**Service Returns:**
- Services returning multiple values use tuple unpacking
- Example: `result, medical_note = preauth_service.validate_preauth_from_pdf(...)`

**Pydantic Immutability:**
- Cannot dynamically add fields to Pydantic models
- Use `getattr(obj, 'field', default)` for safe access
- Use `hasattr(obj, 'field')` before accessing optional attributes

**Import Paths:**
- From within src/, don't use "src." prefix in imports
- Example: `from modules import preauth_module` (not `from src.modules`)

**Agent Result Display:**
- Different agents return different result structures
- Check for: `issues`, `violations`, `concerns`, `flags`
- Always use `hasattr()` before accessing agent-specific attributes

---

## Reference: Key Project Documents

For comprehensive details, always refer to:
- **CODEBASE_REVIEW.md**: Latest optimization analysis, current status, suggestions (October 2025)
- **Iris PRD.md**: Full product vision, user flows, backend architecture, tech stack
- **Iris_backend_logic.md**: Line-by-line implementation logic for every function, agent, aggregator
- **discharge_flow.md**: Discharge module specifications and design principles
- **policy_details_structure.txt**: Template for creating new policy JSONs
- **medical_reference_structure.txt**: Template for creating new procedure reference data
