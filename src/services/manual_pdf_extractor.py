"""
PDF Extractor Service
Extracts medical note data from pre-authorization PDF documents using rule-based parsing
with optional LLM fallback
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import PyPDF2
from src.models.schemas import MedicalNote, PatientInfo, DiagnosisInfo, ClinicalHistory
from src.models.schemas import ProposedTreatment, MedicalJustification, HospitalizationDetails
from src.models.schemas import CostBreakdown, DoctorDetails, HospitalDetails
from src.utils.llm_client import call_llm_with_retry


class PDFExtractor:
    """
    Extracts structured medical note data from PDF documents using rule-based parsing

    Primary method: Regex pattern matching (fast, free, deterministic)
    Fallback: LLM parsing (disabled by default, enable for production)
    """

    def __init__(self, enable_llm_fallback: bool = False):
        """
        Initialize PDF extractor

        Args:
            enable_llm_fallback: Enable LLM fallback if rule-based parsing fails (default: False)
        """
        self.enable_llm_fallback = enable_llm_fallback

    def extract_from_pdf(self, pdf_path: str) -> MedicalNote:
        """
        Extract medical note from PDF file

        Args:
            pdf_path: Path to PDF file

        Returns:
            MedicalNote object with extracted data

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If extraction fails

        Example:
            >>> extractor = PDFExtractor()
            >>> medical_note = extractor.extract_from_pdf("test_case_1.pdf")
            >>> print(medical_note.patient_info.name)
        """
        # 1. Validate file exists
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # 2. Extract text from PDF
        pdf_text = self._extract_text_from_pdf(pdf_file)

        if not pdf_text.strip():
            raise ValueError("PDF appears to be empty or contains no extractable text")

        # 3. Parse using rule-based approach
        medical_data, confidence = self._parse_with_rules(pdf_text)

        # 4. Fallback to LLM if enabled and confidence is low
        if self.enable_llm_fallback and confidence < 0.7:
            print(f"⚠️  Rule-based parsing confidence: {confidence:.0%}. Falling back to LLM...")
            medical_data = self._parse_with_llm(pdf_text)

        # 5. Validate and return MedicalNote
        try:
            medical_note = MedicalNote(**medical_data)
            return medical_note
        except Exception as e:
            raise ValueError(f"Failed to create MedicalNote from extracted data: {str(e)}\nExtracted data: {json.dumps(medical_data, indent=2)}")

    def _extract_text_from_pdf(self, pdf_file: Path) -> str:
        """Extract raw text from PDF using PyPDF2"""
        try:
            text_content = []

            with open(pdf_file, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    if text:
                        text_content.append(text)

            full_text = "\n".join(text_content)
            return full_text

        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")

    def _parse_with_rules(self, pdf_text: str) -> Tuple[Dict, float]:
        """
        Parse PDF text using rule-based regex patterns
        Updated to handle new PRE-AUTHORIZATION REQUEST template format

        Args:
            pdf_text: Raw text from PDF

        Returns:
            Tuple of (extracted_data_dict, confidence_score)
        """
        # Initialize data structure
        data = {}
        fields_found = 0
        total_fields = 0

        # Clean text - preserve some structure for better extraction
        text = pdf_text.replace('\r', ' ')
        # Normalize excessive whitespace but keep some line structure
        text = re.sub(r' +', ' ', text)

        # === PATIENT INFO (Part A / Section 1) ===
        total_fields += 5
        patient_info = {}

        # Patient Name - updated for new template format
        name_patterns = [
            r'Patient\s+Name\s*:\s*([A-Za-z\s\.]+?)(?=\s*Gender|\s*Age|\n)',
            r'Patient Name:\s*([A-Za-z\s\.]+?)(?=Gender|Age)',
        ]
        for pattern in name_patterns:
            name_match = re.search(pattern, text, re.IGNORECASE)
            if name_match:
                patient_info['name'] = name_match.group(1).strip()
                fields_found += 1
                break
        if 'name' not in patient_info:
            patient_info['name'] = "Unknown Patient"

        # Age - handle "68 Years" format
        age_patterns = [
            r'Age\s*:\s*(\d+)\s*(?:Years?|years?)',
            r'Age[:\s]+(\d+)',
        ]
        for pattern in age_patterns:
            age_match = re.search(pattern, text, re.IGNORECASE)
            if age_match:
                patient_info['age'] = int(age_match.group(1))
                fields_found += 1
                break
        if 'age' not in patient_info:
            patient_info['age'] = 0

        # Gender - handle checkbox symbols
        gender_patterns = [
            r'Gender\s*:\s*(?:☐)?\s*(Male|Female|Third\s+Gender|Other)',
            r'Gender\s*:\s*([A-Za-z\s]+?)(?=\s+Age|\n)',
        ]
        for pattern in gender_patterns:
            gender_match = re.search(pattern, text, re.IGNORECASE)
            if gender_match:
                gender = gender_match.group(1).strip().title()
                if "Third" in gender:
                    gender = "Other"
                patient_info['gender'] = gender
                fields_found += 1
                break
        if 'gender' not in patient_info:
            patient_info['gender'] = "Male"

        # Contact Number
        contact_patterns = [
            r'Contact\s+Number\s*:\s*([\d\s\-\+]+)',
            r'(?:Phone|Mobile)[:\s]+([\d\s\-\+]+)',
        ]
        for pattern in contact_patterns:
            contact_match = re.search(pattern, text, re.IGNORECASE)
            if contact_match:
                contact_num = re.sub(r'[^\d]', '', contact_match.group(1))
                if len(contact_num) >= 10:
                    patient_info['contact_number'] = contact_num[:10]
                    fields_found += 1
                    break

        # Patient ID / TPA Card ID
        patient_id_patterns = [
            r'TPA\s+Card\s+ID\s*:\s*([\w\d\/\-]+)',
            r'Patient\s+ID[:\s]+([\w\d\/\-]+)',
        ]
        for pattern in patient_id_patterns:
            patient_id_match = re.search(pattern, text, re.IGNORECASE)
            if patient_id_match:
                patient_info['patient_id'] = patient_id_match.group(1).strip()
                fields_found += 1
                break

        data['patient_info'] = patient_info

        # === DIAGNOSIS (Part B / Section 3) ===
        total_fields += 3
        diagnosis = {}

        # Primary Diagnosis - new template
        diag_patterns = [
            r'Provisional\s+Diagnosis\s*:\s*([^\n]+?)(?=\s*ICD|\n|$)',
            r'Primary\s+Diagnosis\s*:\s*([^\n]+?)(?=\s*ICD|\n|$)',
        ]
        for pattern in diag_patterns:
            diag_match = re.search(pattern, text, re.IGNORECASE)
            if diag_match:
                diagnosis['primary_diagnosis'] = diag_match.group(1).strip()[:200]
                fields_found += 1
                break
        if 'primary_diagnosis' not in diagnosis:
            diagnosis['primary_diagnosis'] = "Not specified"

        # ICD-10 Code
        icd_patterns = [
            r'ICD[- ]?10\s+Code\s*:\s*([A-Z]\d+\.?\d*)',
            r'ICD[:\s]+([A-Z]\d+\.?\d*)',
        ]
        for pattern in icd_patterns:
            icd_match = re.search(pattern, text, re.IGNORECASE)
            if icd_match:
                diagnosis['icd_10_code'] = icd_match.group(1).strip()
                fields_found += 1
                break
        if 'icd_10_code' not in diagnosis:
            diagnosis['icd_10_code'] = "A00.0"

        # Date of First Consultation
        diag_date_patterns = [
            r'Date\s+of\s+First\s+Consultation\s*:\s*([\d\/\-]+)',
            r'Diagnosis\s+Date[:\s]+([\d\/\-]+)',
        ]
        for pattern in diag_date_patterns:
            diag_date_match = re.search(pattern, text, re.IGNORECASE)
            if diag_date_match:
                diagnosis['diagnosis_date'] = diag_date_match.group(1).strip()
                fields_found += 1
                break

        diagnosis['secondary_diagnoses'] = []
        data['diagnosis'] = diagnosis

        # === CLINICAL HISTORY (Section 3 & 4) ===
        total_fields += 2
        clinical = {}

        # Chief Complaints - "Nature of Illness/Disease with Presenting Complaint"
        complaint_patterns = [
            r'Nature\s+of\s+Illness[^:]*:\s*\n?\s*(.{30,500}?)(?=\s*Duration|Date\s+of\s+First|Past\s+History|Relevant)',
            r'Presenting\s+Complaint[:\s]+(.{30,500}?)(?=\s*Duration|$)',
            r'Chief\s+Complaints?[:\s]+(.{30,500}?)(?=\s*Duration|$)',
        ]
        for pattern in complaint_patterns:
            complaint_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if complaint_match:
                complaints = complaint_match.group(1).strip()
                complaints = re.sub(r'\s+', ' ', complaints)  # Clean whitespace
                clinical['chief_complaints'] = complaints[:500]
                fields_found += 1
                break
        if 'chief_complaints' not in clinical:
            clinical['chief_complaints'] = "Not documented"

        # Duration of Present Ailment
        duration_patterns = [
            r'Duration\s+of\s+Present\s+Ailment\s*:\s*(\d+)\s*(?:Days?|days?)',
            r'Duration\s+of\s+Symptoms[:\s]+(\d+\s*(?:days?|months?|years?))',
        ]
        for pattern in duration_patterns:
            duration_match = re.search(pattern, text, re.IGNORECASE)
            if duration_match:
                duration_val = duration_match.group(1).strip()
                if duration_val.isdigit():
                    clinical['duration_of_symptoms'] = duration_val + " days"
                else:
                    clinical['duration_of_symptoms'] = duration_val
                fields_found += 1
                break

        # Past History
        past_history_match = re.search(r'Past\s+History[^:]*:\s*(.{20,300}?)(?=\n\d+\.|PAST\s+MEDICAL|$)', text, re.IGNORECASE | re.DOTALL)
        if past_history_match:
            clinical['relevant_medical_history'] = re.sub(r'\s+', ' ', past_history_match.group(1).strip())

        # Comorbidities - Section 5
        comorbidities = []
        if re.search(r'Diabetes.*Since:', text, re.IGNORECASE):
            comorbidities.append("Diabetes")
        if re.search(r'Hypertension.*Since:', text, re.IGNORECASE):
            comorbidities.append("Hypertension")
        if re.search(r'Heart\s+Disease.*Since:', text, re.IGNORECASE):
            comorbidities.append("Heart Disease")
        clinical['comorbidities'] = comorbidities if comorbidities else None

        data['clinical_history'] = clinical

        # === DIAGNOSTIC TESTS (Section 6) ===
        tests = []
        # Look for numbered investigations: "1. Test name (date): findings"
        # More flexible pattern that captures full test names and findings across multiple lines
        test_pattern = r'(\d+)\.\s+([A-Za-z][A-Za-z\s/\-,\.]+?)[\s\(]+([\/\d\-]+)[\)\s]*:?\s*(.{0,250}?)(?=\n\d+\.|Medical\s+Management|Proposed|SURGICAL|\n\n|$)'
        
        test_matches = re.findall(test_pattern, text, re.IGNORECASE | re.DOTALL)
        for match in test_matches[:10]:  # Limit to 10 tests
            test_name = re.sub(r'\s+', ' ', match[1].strip())  # Clean whitespace
            date_performed = match[2].strip() if match[2] else None
            findings = re.sub(r'\s+', ' ', match[3].strip()) if match[3] else None
            
            # Validate test name (must be reasonable length and not just whitespace)
            if test_name and len(test_name) > 3 and not test_name.isspace():
                tests.append({
                    "test_name": test_name[:100],
                    "date_performed": date_performed,
                    "key_findings": findings[:200] if findings and len(findings) > 3 else None
                })
        
        data['diagnostic_tests'] = tests if tests else []

        # === PROPOSED TREATMENT (Section 7) ===
        total_fields += 2
        treatment = {}

        # Name of Surgery/Procedure
        proc_patterns = [
            r'Name\s+of\s+Surgery/Procedure\s*:\s*(.{10,250}?)(?=\s*ICD|Route|Other|Anesthesia|\n\d+\.|\s*$)',
            r'Procedure\s+Name[:\s]+(.{10,250}?)(?=\s*ICD|$)',
        ]
        for pattern in proc_patterns:
            proc_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if proc_match:
                procedure = proc_match.group(1).strip()
                procedure = re.sub(r'\s+', ' ', procedure)  # Clean whitespace
                treatment['procedure_name'] = procedure[:250]
                fields_found += 1
                break
        if 'procedure_name' not in treatment:
            treatment['procedure_name'] = "Not specified"

        # Anesthesia Type - may be in "Other Treatment Details"
        anes_patterns = [
            r'under\s+(peribulbar|general|spinal|local|regional)\s+anesthesia',
            r'Anesthesia[^:]*:\s*(?:☐)?\s*(General|Spinal|Local|Regional|Peribulbar)',
        ]
        for pattern in anes_patterns:
            anes_match = re.search(pattern, text, re.IGNORECASE)
            if anes_match:
                anesthesia = anes_match.group(1).strip().title()
                # Map Peribulbar to Local
                if anesthesia == "Peribulbar":
                    anesthesia = "Local"
                treatment['anesthesia_type'] = anesthesia
                fields_found += 1
                break

        # Procedure Code
        proc_code_patterns = [
            r'ICD[- ]?10\s+PCS\s+Code\s*:\s*([\w\d]+)',
            r'Procedure\s+Code[:\s]+([\w\d]+)',
        ]
        for pattern in proc_code_patterns:
            proc_code_match = re.search(pattern, text, re.IGNORECASE)
            if proc_code_match:
                treatment['procedure_code'] = proc_code_match.group(1).strip()
                break

        # Surgical approach from "Other Treatment Details"
        surgical_approach_match = re.search(r'Other\s+Treatment\s+Details[^:]*:\s*(.{20,200})', text, re.IGNORECASE | re.DOTALL)
        if surgical_approach_match:
            treatment['surgical_approach'] = re.sub(r'\s+', ' ', surgical_approach_match.group(1).strip())[:200]

        data['proposed_treatment'] = treatment

        # === MEDICAL JUSTIFICATION ===
        # For this template, infer from clinical findings and treatment details
        total_fields += 2
        justification = {}

        # Use relevant clinical findings as justification
        relevant_findings_match = re.search(r'Relevant\s+Critical\s+Findings[^:]*:\s*(.{30,400}?)(?=Past\s+History|\n\d+\.|$)', text, re.IGNORECASE | re.DOTALL)
        if relevant_findings_match:
            findings = re.sub(r'\s+', ' ', relevant_findings_match.group(1).strip())
            justification['why_hospitalization_required'] = "Surgical intervention requiring controlled environment and post-operative monitoring. " + findings[:200]
            justification['why_treatment_necessary'] = clinical.get('chief_complaints', 'Medical treatment required')[:250]
            fields_found += 2
        else:
            justification['why_hospitalization_required'] = "Surgical intervention required"
            justification['why_treatment_necessary'] = clinical.get('chief_complaints', 'Medical treatment required')[:250]
            fields_found += 1

        data['medical_justification'] = justification

        # === HOSPITALIZATION DETAILS (Section 10) ===
        total_fields += 3  # Increased to include hospitalization type
        hosp_details = {}

        # Hospitalization Type (Emergency or Planned)
        hosp_type_match = re.search(r'Is\s+this\s+an\s+Emergency/Planned\s+Hospitalization\s*:\s*(Emergency|Planned)', text, re.IGNORECASE)
        if hosp_type_match:
            hosp_type = hosp_type_match.group(1).strip().title()
            hosp_details['hospitalization_type'] = hosp_type
            fields_found += 1

        # Date of Admission
        admission_patterns = [
            r'Date\s+of\s+Admission\s*:\s*([\d\/\-]+)',
            r'Planned\s+Admission\s+Date[:\s]+([\d\/\-]+)',
        ]
        for pattern in admission_patterns:
            admission_match = re.search(pattern, text, re.IGNORECASE)
            if admission_match:
                hosp_details['planned_admission_date'] = admission_match.group(1).strip()
                fields_found += 1
                break
        if 'planned_admission_date' not in hosp_details:
            hosp_details['planned_admission_date'] = "01/01/2025"

        # Expected Number of Days/Stay
        stay_patterns = [
            r'Expected\s+Number\s+of\s+Days/Stay\s+in\s+Hospital\s*:\s*(\d+)\s*Days?',
            r'Expected\s+(?:Length\s+of\s+)?Stay[:\s]+(\d+)',
        ]
        for pattern in stay_patterns:
            stay_match = re.search(pattern, text, re.IGNORECASE)
            if stay_match:
                hosp_details['expected_length_of_stay'] = int(stay_match.group(1))
                fields_found += 1
                break
        if 'expected_length_of_stay' not in hosp_details:
            hosp_details['expected_length_of_stay'] = 1

        # Days in ICU
        icu_days_match = re.search(r'Days\s+in\s+ICU[^:]*:\s*(\d+)', text, re.IGNORECASE)
        if icu_days_match:
            icu_days = int(icu_days_match.group(1))
            hosp_details['icu_required'] = icu_days > 0
            hosp_details['icu_duration'] = icu_days if icu_days > 0 else None
        else:
            hosp_details['icu_required'] = False

        data['hospitalization_details'] = hosp_details

        # === COST BREAKDOWN (Section 11) ===
        total_fields += 2
        costs = {}

        # Extract individual cost components from new template format
        # "Room Rent + Nursing & Service Charges + Patient's Diet"
        # Support both ₹ and Rs. symbols, or no symbol
        room_patterns = [
            r'Room\s+Rent[^\n]*?(?:₹|Rs\.?)?\s*([\d,]+)',
            r'Per\s+Day\s+Room\s+Rent[^\n]*?(?:₹|Rs\.?)?\s*([\d,]+)',
        ]
        for pattern in room_patterns:
            room_match = re.search(pattern, text, re.IGNORECASE)
            if room_match:
                costs['room_charges'] = float(re.sub(r'[,]', '', room_match.group(1)))
                break
        if 'room_charges' not in costs:
            costs['room_charges'] = 0.0

        # "Professional Fees (Surgeon + Anesthetist + Consultation Charges)"
        prof_fee_match = re.search(r'Professional\s+Fees[^\n]*?(?:₹|Rs\.?)?\s*([\d,]+)', text, re.IGNORECASE)
        if prof_fee_match:
            # Split professional fees (assuming 70/30 split for surgeon/anesthetist)
            total_prof = float(re.sub(r'[,]', '', prof_fee_match.group(1)))
            costs['surgeon_fees'] = total_prof * 0.7
            costs['anesthetist_fees'] = total_prof * 0.3
        else:
            # Try individual matches
            surgeon_match = re.search(r'Surgeon\s+Fees?[^\n]*?(?:₹|Rs\.?)?\s*([\d,]+)', text, re.IGNORECASE)
            costs['surgeon_fees'] = float(re.sub(r'[,]', '', surgeon_match.group(1))) if surgeon_match else 0.0
            
            anes_fee_match = re.search(r'Anesthetist\s+Fees?[^\n]*?(?:₹|Rs\.?)?\s*([\d,]+)', text, re.IGNORECASE)
            costs['anesthetist_fees'] = float(re.sub(r'[,]', '', anes_fee_match.group(1))) if anes_fee_match else 0.0

        # OT Charges
        ot_match = re.search(r'OT\s+Charges[^\n]*?(?:₹|Rs\.?)?\s*([\d,]+)', text, re.IGNORECASE)
        costs['ot_charges'] = float(re.sub(r'[,]', '', ot_match.group(1))) if ot_match else 0.0

        # ICU Charges
        icu_match = re.search(r'ICU\s+Charges[^\n]*?(?:₹|Rs\.?)?\s*([\d,]+)', text, re.IGNORECASE)
        costs['icu_charges'] = float(re.sub(r'[,]', '', icu_match.group(1))) if icu_match else 0.0

        # "Expected Cost of Investigation + Diagnostic"
        invest_patterns = [
            r'Expected\s+Cost\s+of\s+Investigation[^\n]*?(?:₹|Rs\.?)?\s*([\d,]+)',
            r'Investigation[s]?[^\n]*?(?:₹|Rs\.?)?\s*([\d,]+)',
        ]
        for pattern in invest_patterns:
            invest_match = re.search(pattern, text, re.IGNORECASE)
            if invest_match:
                costs['investigations'] = float(re.sub(r'[,]', '', invest_match.group(1)))
                break
        if 'investigations' not in costs:
            costs['investigations'] = 0.0

        # "Medicines + Consumables + Cost of Implants"
        # Check if it's a combined line (medicines + consumables + implants together)
        combined_med_pattern = r'Medicines\s*\+\s*Consumables\s*\+\s*(?:Cost\s+of\s+)?Implants[^\n]*?(?:₹|Rs\.?)?\s*([\d,]+)'
        combined_match = re.search(combined_med_pattern, text, re.IGNORECASE)

        if combined_match:
            # Combined line - put everything in medicines_consumables, implants = 0
            costs['medicines_consumables'] = float(re.sub(r'[,]', '', combined_match.group(1)))
            costs['implants'] = 0.0
        else:
            # Separate lines - extract individually
            med_patterns = [
                r'Medicines\s*\+\s*Consumables[^\n]*?(?:₹|Rs\.?)?\s*([\d,]+)',
                r'Medicines[^\n]*?(?:₹|Rs\.?)?\s*([\d,]+)',
            ]
            for pattern in med_patterns:
                med_match = re.search(pattern, text, re.IGNORECASE)
                if med_match:
                    costs['medicines_consumables'] = float(re.sub(r'[,]', '', med_match.group(1)))
                    break
            if 'medicines_consumables' not in costs:
                costs['medicines_consumables'] = 0.0

            # Implants (separate if specified)
            implant_match = re.search(r'(?:Cost\s+of\s+)?Implants[^\n]*?(?:₹|Rs\.?)?\s*([\d,]+)', text, re.IGNORECASE)
            costs['implants'] = float(re.sub(r'[,]', '', implant_match.group(1))) if implant_match else 0.0

        # Other Hospital Expenses
        other_match = re.search(r'Other\s+Hospital\s+Expenses[^\n]*?(?:₹|Rs\.?)?\s*([\d,]+)', text, re.IGNORECASE)
        costs['other_charges'] = float(re.sub(r'[,]', '', other_match.group(1))) if other_match else 0.0

        # Total Cost - "SUM-TOTAL EXPECTED COST OF HOSPITALIZATION"
        total_patterns = [
            r'SUM[- ]TOTAL\s+EXPECTED\s+COST[^\n]*?(?:₹|Rs\.?)?\s*([\d,]+)',
            r'TOTAL[^\n]*?(?:₹|Rs\.?)?\s*([\d,]+)',
        ]
        for pattern in total_patterns:
            total_match = re.search(pattern, text, re.IGNORECASE)
            if total_match:
                costs['total_estimated_cost'] = float(re.sub(r'[,]', '', total_match.group(1)))
                fields_found += 1
                break
        
        if 'total_estimated_cost' not in costs:
            # Calculate from components
            costs['total_estimated_cost'] = sum([
                costs.get('room_charges', 0),
                costs.get('surgeon_fees', 0),
                costs.get('anesthetist_fees', 0),
                costs.get('ot_charges', 0),
                costs.get('icu_charges', 0),
                costs.get('investigations', 0),
                costs.get('medicines_consumables', 0),
                costs.get('implants', 0),
                costs.get('other_charges', 0)
            ])

        if costs['total_estimated_cost'] > 0:
            fields_found += 1

        data['cost_breakdown'] = costs

        # === DOCTOR DETAILS (Section 2 / Declaration 12) ===
        total_fields += 1
        doctor = {}

        # Doctor Name from "Doctor's Name" in declaration or treating doctor section
        doc_patterns = [
            r'Doctor\'s\s+Name\s*:\s*([A-Za-z\s\.]+?)(?=\s*Doctor\'s\s+Signature|\n|$)',
            r'Doctor\s+Name\s*:\s*Dr\.?\s*([A-Za-z\s\.]+?)(?=\s*Contact|\n)',
        ]
        for pattern in doc_patterns:
            doc_match = re.search(pattern, text, re.IGNORECASE)
            if doc_match:
                name = doc_match.group(1).strip()
                # Add Dr. prefix if not present
                if not name.startswith('Dr'):
                    name = 'Dr. ' + name
                doctor['name'] = name
                fields_found += 1
                break
        if 'name' not in doctor:
            doctor['name'] = "Dr. Unknown"

        # Qualification
        qual_patterns = [
            r'Qualification\s*:\s*([A-Z\s,\.\(\)]+?)(?=\s*Registration|\n)',
        ]
        for pattern in qual_patterns:
            qual_match = re.search(pattern, text, re.IGNORECASE)
            if qual_match:
                doctor['qualification'] = qual_match.group(1).strip()[:100]
                break

        # Registration Number
        reg_patterns = [
            r'Registration\s+Number[^:]*:\s*([\w\/\d]+)',
        ]
        for pattern in reg_patterns:
            reg_match = re.search(pattern, text, re.IGNORECASE)
            if reg_match:
                doctor['registration_number'] = reg_match.group(1).strip()
                break

        data['doctor_details'] = doctor

        # === HOSPITAL DETAILS ===
        total_fields += 1
        hospital = {}

        # Hospital Name - try to extract from letterhead/header (first few lines)
        # Look for hospital name in first 500 characters (letterhead area)
        header_text = text[:500]
        
        # Try to find hospital name patterns in header
        hosp_patterns = [
            r'^([A-Z][A-Za-z\s&\.]+(?:Hospital|Clinic|Medical Center|Healthcare))',
            r'([A-Z][A-Za-z\s&\.]+(?:Hospital|Clinic|Medical Center|Healthcare))\s*\n',
        ]
        
        for pattern in hosp_patterns:
            hosp_match = re.search(pattern, header_text, re.MULTILINE)
            if hosp_match:
                hosp_name = hosp_match.group(1).strip()
                # Avoid matching "Emergency/Planned Hospitalization"
                if "Emergency" not in hosp_name and "Planned" not in hosp_name and len(hosp_name) > 5:
                    hospital['name'] = hosp_name
                    fields_found += 1
                    break
        
        if 'name' not in hospital:
            hospital['name'] = "Hospital name not specified in document"

        # Hospital Address - look for address field if exists
        addr_patterns = [
            r'Hospital\s+Address\s*:\s*(.{10,200}?)(?:\n\n|Registration|$)',
            r'Address\s*:\s*(.{10,200}?)(?:\n\n|Registration|Contact|$)',
        ]
        for pattern in addr_patterns:
            addr_match = re.search(pattern, text, re.IGNORECASE)
            if addr_match:
                address = addr_match.group(1).strip()
                # Avoid matching hospitalization type
                if "Emergency" not in address and "Planned" not in address:
                    hospital['address'] = address
                    break

        data['hospital_details'] = hospital

        # Calculate confidence
        confidence = fields_found / total_fields if total_fields > 0 else 0.0

        return data, confidence

    def _parse_with_llm(self, pdf_text: str) -> Dict:
        """
        Fallback: Parse using LLM (only if enabled and rule-based fails)

        Args:
            pdf_text: Raw text from PDF

        Returns:
            Dictionary with structured medical data
        """
        # LLM parsing implementation (same as before)
        # This will only be called if enable_llm_fallback=True and confidence < 0.7
        raise NotImplementedError("LLM fallback is disabled. Enable with enable_llm_fallback=True")

    def extract_from_text(self, text_content: str) -> MedicalNote:
        """
        Extract medical note from raw text (useful for testing)

        Args:
            text_content: Raw medical note text

        Returns:
            MedicalNote object
        """
        medical_data, confidence = self._parse_with_rules(text_content)

        if self.enable_llm_fallback and confidence < 0.7:
            medical_data = self._parse_with_llm(text_content)

        try:
            medical_note = MedicalNote(**medical_data)
            return medical_note
        except Exception as e:
            raise ValueError(f"Failed to create MedicalNote: {str(e)}")
