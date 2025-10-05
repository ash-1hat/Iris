"""
Discharge PDF Extractor
Extracts data from final hospital bills and discharge summaries
"""

import re
import pdfplumber
from typing import Dict, Optional, List
from src.utils.llm_client import call_llm_with_retry


def extract_final_bill(pdf_path: str, use_llm_fallback: bool = True) -> Dict:
    """
    Extract data from final hospital bill PDF

    Args:
        pdf_path: Path to final bill PDF
        use_llm_fallback: Whether to use LLM if regex extraction fails

    Returns:
        Dictionary with extracted bill data

    Example output:
        {
            "bill_number": "APL/BLR/2025/012345",
            "bill_date": "07/10/2025",
            "patient_name": "Mr. Rajesh Kumar",
            "authorization_number": "AUTH-2025-54321",
            "authorized_amount": 52000.0,
            "admission_date": "05/10/2025",
            "discharge_date": "07/10/2025",
            "total_days": 2,
            "itemized_costs": {
                "room_charges": 7000.0,
                "nursing_charges": 1000.0,
                "surgeon_fees": 18000.0,
                "anesthetist_fees": 5000.0,
                "ot_charges": 12000.0,
                "ot_consumables": 1500.0,
                "medicines": 12000.0,
                "implants": 15000.0,
                "investigations": 2000.0,
                "other_charges": 600.0
            },
            "total_bill_amount": 79500.0,
            "gst_amount": 1475.0,
            "net_payable_amount": 80975.0,
            "patient_paid": 28975.0,
            "insurance_claimed": 52000.0
        }
    """
    # Try text extraction first
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""

        # Try regex extraction
        result = _extract_bill_with_regex(text)

        # Validate extraction
        if result.get("total_bill_amount", 0) > 0:
            return result

    except Exception as e:
        print(f"Error in pdfplumber extraction: {e}")

    # Fallback to LLM
    if use_llm_fallback:
        try:
            return _extract_bill_with_llm(pdf_path)
        except Exception as e:
            print(f"Error in LLM extraction: {e}")

    # Return empty structure if all fails
    return _get_empty_bill_structure()


def _extract_bill_with_regex(text: str) -> Dict:
    """Extract bill data using regex patterns"""

    result = _get_empty_bill_structure()

    # Bill number and date
    bill_num_match = re.search(r'Bill\s+No[:\s]+([A-Z0-9/]+)', text, re.IGNORECASE)
    if bill_num_match:
        result["bill_number"] = bill_num_match.group(1).strip()

    bill_date_match = re.search(r'Bill.*?Date[:\s]+(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
    if bill_date_match:
        result["bill_date"] = bill_date_match.group(1).strip()

    # Patient name
    patient_match = re.search(r'Patient\s+Name[:\s]+(.+?)(?:\n|Age)', text, re.IGNORECASE)
    if patient_match:
        result["patient_name"] = patient_match.group(1).strip()

    # Authorization number and amount
    auth_num_match = re.search(r'Authorization\s+Number[:\s]+([A-Z0-9-]+)', text, re.IGNORECASE)
    if auth_num_match:
        result["authorization_number"] = auth_num_match.group(1).strip()

    auth_amt_match = re.search(r'Authorized\s+Amount[:\s]+(?:₹|Rs\.?|■)?\s*([\d,]+)', text, re.IGNORECASE)
    if auth_amt_match:
        result["authorized_amount"] = float(auth_amt_match.group(1).replace(',', ''))

    # Admission and discharge dates
    admission_match = re.search(r'(?:Date\s+of\s+)?Admission[:\s]+(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
    if admission_match:
        result["admission_date"] = admission_match.group(1).strip()

    discharge_match = re.search(r'(?:Date\s+of\s+)?Discharge[:\s]+(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
    if discharge_match:
        result["discharge_date"] = discharge_match.group(1).strip()

    # Total days
    days_match = re.search(r'Total\s+Days[:\s]+(\d+)', text, re.IGNORECASE)
    if days_match:
        result["total_days"] = int(days_match.group(1))

    # Extract itemized costs - look for specific line items
    # Room charges
    room_match = re.search(r'Room\s+Rent[^\n]*?(?:₹|Rs\.?|■)?\s*([\d,]+\.?\d*)\s*$', text, re.MULTILINE | re.IGNORECASE)
    if room_match:
        result["itemized_costs"]["room_charges"] = float(room_match.group(1).replace(',', ''))

    # Nursing charges
    nursing_match = re.search(r'Nursing\s+Charges[^\n]*?(?:₹|Rs\.?|■)?\s*([\d,]+\.?\d*)\s*$', text, re.MULTILINE | re.IGNORECASE)
    if nursing_match:
        result["itemized_costs"]["nursing_charges"] = float(nursing_match.group(1).replace(',', ''))

    # Surgeon fees
    surgeon_match = re.search(r'Surgeon[\'\']?s?\s+Fee[^\n]*?(?:₹|Rs\.?|■)?\s*([\d,]+\.?\d*)\s*$', text, re.MULTILINE | re.IGNORECASE)
    if surgeon_match:
        result["itemized_costs"]["surgeon_fees"] = float(surgeon_match.group(1).replace(',', ''))

    # Anesthetist fees
    anesth_match = re.search(r'Anesthe[st]ist[\'\']?s?\s+Fee[^\n]*?(?:₹|Rs\.?|■)?\s*([\d,]+\.?\d*)\s*$', text, re.MULTILINE | re.IGNORECASE)
    if anesth_match:
        result["itemized_costs"]["anesthetist_fees"] = float(anesth_match.group(1).replace(',', ''))

    # OT charges
    ot_match = re.search(r'OT\s+Charges[^\n]*?(?:₹|Rs\.?|■)?\s*([\d,]+\.?\d*)\s*$', text, re.MULTILINE | re.IGNORECASE)
    if ot_match:
        result["itemized_costs"]["ot_charges"] = float(ot_match.group(1).replace(',', ''))

    # Medicines (look for total medicine amount)
    med_match = re.search(r'Medicines[^\n]*?(?:₹|Rs\.?|■)?\s*([\d,]+\.?\d*)\s*$', text, re.MULTILINE | re.IGNORECASE)
    if med_match:
        result["itemized_costs"]["medicines"] = float(med_match.group(1).replace(',', ''))

    # Implants
    implant_match = re.search(r'Implant[^\n]*?(?:₹|Rs\.?|■)?\s*([\d,]+\.?\d*)\s*$', text, re.MULTILINE | re.IGNORECASE)
    if implant_match:
        result["itemized_costs"]["implants"] = float(implant_match.group(1).replace(',', ''))

    # Investigations
    invest_match = re.search(r'(?:Pre-operative\s+)?[Ii]nvestigations?[^\n]*?(?:₹|Rs\.?|■)?\s*([\d,]+\.?\d*)\s*$', text, re.MULTILINE | re.IGNORECASE)
    if invest_match:
        result["itemized_costs"]["investigations"] = float(invest_match.group(1).replace(',', ''))

    # Total bill amount (before GST)
    total_match = re.search(r'(?:TOTAL\s+BILL\s+AMOUNT|GROSS\s+BILL)[^\n]*?(?:₹|Rs\.?|■)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
    if total_match:
        result["total_bill_amount"] = float(total_match.group(1).replace(',', ''))

    # GST
    gst_match = re.search(r'GST[^\n]*?(?:₹|Rs\.?|■)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
    if gst_match:
        result["gst_amount"] = float(gst_match.group(1).replace(',', ''))

    # Net payable
    net_match = re.search(r'NET\s+PAYABLE[^\n]*?(?:₹|Rs\.?|■)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
    if net_match:
        result["net_payable_amount"] = float(net_match.group(1).replace(',', ''))

    # Patient paid amount
    patient_paid_match = re.search(r'(?:Amount\s+Paid\s+by\s+Patient|Patient\s+Responsibility)[^\n]*?(?:₹|Rs\.?|■)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
    if patient_paid_match:
        result["patient_paid"] = float(patient_paid_match.group(1).replace(',', ''))

    # Insurance claimed
    ins_match = re.search(r'(?:Amount\s+Claimed\s+from\s+TPA|TPA\s+Authorized)[^\n]*?(?:₹|Rs\.?|■)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
    if ins_match:
        result["insurance_claimed"] = float(ins_match.group(1).replace(',', ''))

    return result


def _extract_bill_with_llm(pdf_path: str) -> Dict:
    """Extract bill data using LLM"""

    # Read PDF text
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""

    prompt = f"""Extract information from this final hospital bill and return as JSON.

BILL TEXT:
{text[:8000]}  # Limit to avoid token limits

Return JSON with this structure (use 0 for missing numeric values):
{{
    "bill_number": "string",
    "bill_date": "DD/MM/YYYY",
    "patient_name": "string",
    "authorization_number": "string",
    "authorized_amount": number,
    "admission_date": "DD/MM/YYYY",
    "discharge_date": "DD/MM/YYYY",
    "total_days": number,
    "itemized_costs": {{
        "room_charges": number,
        "nursing_charges": number,
        "surgeon_fees": number,
        "anesthetist_fees": number,
        "ot_charges": number,
        "ot_consumables": number,
        "medicines": number,
        "implants": number,
        "investigations": number,
        "other_charges": number
    }},
    "total_bill_amount": number,
    "gst_amount": number,
    "net_payable_amount": number,
    "patient_paid": number,
    "insurance_claimed": number
}}

IMPORTANT: Return ONLY the JSON object, no other text."""

    response = call_llm_with_retry(
        prompt=prompt,
        model="claude-sonnet-4-5-20250929",
        max_tokens=3000,
        temperature=0.2
    )

    # Parse JSON
    import json
    response = response.strip()
    start_idx = response.find('{')
    end_idx = response.rfind('}') + 1
    json_str = response[start_idx:end_idx]

    return json.loads(json_str)


def extract_discharge_summary(pdf_path: str, use_llm: bool = True) -> Dict:
    """
    Extract data from discharge summary PDF

    Args:
        pdf_path: Path to discharge summary PDF
        use_llm: Whether to use LLM for extraction (recommended for discharge summaries)

    Returns:
        Dictionary with extracted discharge data

    Example output:
        {
            "patient_info": {...},
            "admission_discharge_details": {...},
            "diagnosis": "Age-related cataract, Right eye",
            "icd_code": "H25.9",
            "procedure_performed": "Phacoemulsification with IOL",
            "days_stayed": 2,
            "postop_course": "...",
            "complications": "Post-operative nausea and vomiting...",
            "medications": [...],
            "follow_up_schedule": [...],
            "activity_restrictions": [...],
            "warning_signs": [...],
            "discharge_condition": "stable"
        }
    """
    if use_llm:
        return _extract_discharge_with_llm(pdf_path)
    else:
        # Basic text extraction fallback
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""

        return _extract_discharge_with_regex(text)


def _extract_discharge_with_llm(pdf_path: str) -> Dict:
    """Extract discharge summary using LLM - most reliable for complex documents"""

    # Read PDF text
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""

    # Limit text to avoid token limits - prioritize key sections
    # Extract section 6 (post-op course), 7 (complications), 9-12
    text_sample = text[:15000]  # Take first 15000 chars which usually covers key sections

    prompt = f"""Extract information from this discharge summary and return as JSON.

DISCHARGE SUMMARY TEXT:
{text_sample}

Extract these key sections:

1. Patient & Admission Details
2. Final diagnosis and ICD code
3. Procedure performed
4. Days stayed
5. POST-OPERATIVE COURSE (Section 6) - full text
6. COMPLICATIONS (Section 7) - full text, this is CRITICAL for explaining cost variances
7. DISCHARGE MEDICATIONS (Section 9) - list with dosage and duration
8. FOLLOW-UP INSTRUCTIONS (Section 10) - schedule
9. ACTIVITY RESTRICTIONS (Section 11) - DO's and DON'Ts
10. WARNING SIGNS (Section 12) - when to contact doctor

Return JSON with this structure:
{{
    "patient_name": "string",
    "admission_date": "DD/MM/YYYY",
    "discharge_date": "DD/MM/YYYY",
    "days_stayed": number,
    "diagnosis": "string",
    "icd_code": "string",
    "procedure_performed": "string",
    "postop_course": "full text from Section 6",
    "complications": "full text from Section 7 - include ALL details about complications",
    "discharge_condition": "string",
    "medications": [
        {{"name": "string", "dosage": "string", "duration": "string", "purpose": "string"}}
    ],
    "follow_up_schedule": [
        {{"timing": "string", "purpose": "string"}}
    ],
    "activity_restrictions": {{
        "dos": ["list of things to do"],
        "donts": ["list of things to avoid"]
    }},
    "warning_signs": ["list of warning signs requiring immediate attention"]
}}

IMPORTANT:
- For complications section, extract COMPLETE text - this explains why costs increased
- Return ONLY the JSON object, no other text."""

    response = call_llm_with_retry(
        prompt=prompt,
        model="claude-sonnet-4-5-20250929",
        max_tokens=4000,
        temperature=0.2
    )

    # Parse JSON
    import json
    response = response.strip()
    start_idx = response.find('{')
    end_idx = response.rfind('}') + 1
    json_str = response[start_idx:end_idx]

    return json.loads(json_str)


def _extract_discharge_with_regex(text: str) -> Dict:
    """Basic regex extraction for discharge summary - fallback only"""

    result = {
        "patient_name": "",
        "admission_date": "",
        "discharge_date": "",
        "days_stayed": 0,
        "diagnosis": "",
        "icd_code": "",
        "procedure_performed": "",
        "postop_course": "",
        "complications": "",
        "discharge_condition": "",
        "medications": [],
        "follow_up_schedule": [],
        "activity_restrictions": {"dos": [], "donts": []},
        "warning_signs": []
    }

    # Patient name
    patient_match = re.search(r'Patient\s+Name[:\s]+(.+?)(?:\n|Age)', text, re.IGNORECASE)
    if patient_match:
        result["patient_name"] = patient_match.group(1).strip()

    # Dates
    admission_match = re.search(r'(?:Date.*?)?Admission[:\s]+(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
    if admission_match:
        result["admission_date"] = admission_match.group(1)

    discharge_match = re.search(r'(?:Date.*?)?Discharge[:\s]+(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
    if discharge_match:
        result["discharge_date"] = discharge_match.group(1)

    # Days stayed
    days_match = re.search(r'Total\s+Duration[:\s]+(\d+)\s+Days?', text, re.IGNORECASE)
    if days_match:
        result["days_stayed"] = int(days_match.group(1))

    # ICD code
    icd_match = re.search(r'ICD-?10\s+(?:CODE)?[:\s]+([A-Z]\d+\.?\d*)', text, re.IGNORECASE)
    if icd_match:
        result["icd_code"] = icd_match.group(1)

    return result


def _get_empty_bill_structure() -> Dict:
    """Return empty bill structure"""
    return {
        "bill_number": "",
        "bill_date": "",
        "patient_name": "",
        "authorization_number": "",
        "authorized_amount": 0.0,
        "admission_date": "",
        "discharge_date": "",
        "total_days": 0,
        "itemized_costs": {
            "room_charges": 0.0,
            "nursing_charges": 0.0,
            "surgeon_fees": 0.0,
            "anesthetist_fees": 0.0,
            "ot_charges": 0.0,
            "ot_consumables": 0.0,
            "medicines": 0.0,
            "implants": 0.0,
            "investigations": 0.0,
            "other_charges": 0.0
        },
        "total_bill_amount": 0.0,
        "gst_amount": 0.0,
        "net_payable_amount": 0.0,
        "patient_paid": 0.0,
        "insurance_claimed": 0.0
    }
