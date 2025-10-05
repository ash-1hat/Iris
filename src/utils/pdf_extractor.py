"""
PDF extraction utilities for medical notes
Uses pdfplumber for basic extraction, falls back to Claude API for intelligent parsing
"""

import re
from typing import Dict, Optional
import pdfplumber

from src.models.schemas import (
    MedicalNote, PatientInfo, DiagnosisInfo, ClinicalHistory,
    DiagnosticTest, ProposedTreatment, MedicalJustification,
    HospitalizationDetails, CostBreakdown, DoctorDetails, HospitalDetails
)
from src.utils.llm_client import get_llm_client


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract raw text from PDF using pdfplumber

    Args:
        pdf_bytes: PDF file as bytes

    Returns:
        Extracted text as string
    """
    import io

    text_parts = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    return "\n".join(text_parts)


def extract_medical_note_with_llm(pdf_text: str) -> Dict:
    """
    Use Claude API to intelligently extract structured data from medical note text

    Args:
        pdf_text: Raw text extracted from PDF

    Returns:
        Dictionary with extracted fields
    """
    client = get_llm_client()

    prompt = f"""You are a medical data extraction specialist. Extract structured information from this pre-authorization medical note.

MEDICAL NOTE TEXT:
{pdf_text}

Extract the following information and return as JSON. If a field is not found, use null:

{{
  "patient_info": {{
    "name": "string",
    "age": integer,
    "gender": "Male" | "Female" | "Other",
    "patient_id": "string or null",
    "contact_number": "string or null"
  }},
  "diagnosis": {{
    "primary_diagnosis": "string",
    "icd_10_code": "string",
    "diagnosis_date": "string or null",
    "secondary_diagnoses": ["string"] or null
  }},
  "clinical_history": {{
    "chief_complaints": "string",
    "duration_of_symptoms": "string or null",
    "relevant_medical_history": "string or null",
    "comorbidities": ["string"] or null
  }},
  "diagnostic_tests": [
    {{
      "test_name": "string",
      "date_performed": "string or null",
      "key_findings": "string or null"
    }}
  ],
  "proposed_treatment": {{
    "procedure_name": "string",
    "procedure_code": "string or null",
    "surgical_approach": "string or null",
    "anesthesia_type": "General" | "Spinal" | "Local" | "Regional" | null
  }},
  "medical_justification": {{
    "why_hospitalization_required": "string",
    "why_treatment_necessary": "string",
    "how_treatment_addresses_diagnosis": "string or null",
    "expected_outcomes": "string or null"
  }},
  "hospitalization_details": {{
    "planned_admission_date": "string (YYYY-MM-DD format)",
    "expected_length_of_stay": integer (days),
    "icu_required": boolean,
    "icu_duration": integer or null
  }},
  "cost_breakdown": {{
    "room_charges": float,
    "surgeon_fees": float,
    "anesthetist_fees": float,
    "ot_charges": float,
    "icu_charges": float,
    "investigations": float,
    "medicines_consumables": float,
    "implants": float,
    "other_charges": float,
    "total_estimated_cost": float
  }},
  "doctor_details": {{
    "name": "string",
    "qualification": "string or null",
    "specialty": "string or null",
    "registration_number": "string or null",
    "email": "string or null",
    "phone": "string or null"
  }},
  "hospital_details": {{
    "name": "string",
    "address": "string or null",
    "registration_number": "string or null",
    "contact_number": "string or null"
  }}
}}

IMPORTANT EXTRACTION RULES:
1. For patient age: Extract numeric value only (e.g., if "65 years", return 65)
2. For dates: Convert to YYYY-MM-DD format
3. For costs: Extract numeric values only (remove ₹ symbol and commas)
4. For ICD codes: Extract the code (e.g., "H25.9")
5. For medical justification: Extract the full explanation text
6. If cost breakdown items are missing, estimate based on total if provided
7. For boolean fields: Use true/false (not "Yes"/"No")

Return ONLY the JSON, no additional text."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )

        # Extract JSON from response
        response_text = message.content[0].text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = re.sub(r"```json?\n?", "", response_text)
            response_text = re.sub(r"\n?```$", "", response_text)

        import json
        extracted_data = json.loads(response_text)

        return extracted_data

    except Exception as e:
        raise ValueError(f"LLM extraction failed: {str(e)}")


def extract_medical_note(pdf_bytes: bytes, use_llm_fallback: bool = True) -> MedicalNote:
    """
    Main extraction function
    1. Extract text with pdfplumber
    2. Use Claude API to parse structured data
    3. Validate with Pydantic models

    Args:
        pdf_bytes: PDF file as bytes
        use_llm_fallback: Whether to use LLM if basic extraction fails

    Returns:
        MedicalNote object

    Raises:
        ValueError: If extraction fails
    """
    # Step 1: Extract text
    try:
        pdf_text = extract_text_from_pdf(pdf_bytes)
    except Exception as e:
        raise ValueError(f"PDF text extraction failed: {str(e)}")

    if not pdf_text or len(pdf_text.strip()) < 100:
        raise ValueError("PDF appears to be empty or unreadable")

    # Step 2: Use LLM to extract structured data
    if use_llm_fallback:
        try:
            extracted_data = extract_medical_note_with_llm(pdf_text)
        except Exception as e:
            raise ValueError(f"LLM-based extraction failed: {str(e)}")
    else:
        # For testing: can implement basic regex-based extraction here
        raise NotImplementedError("Basic extraction not yet implemented. Use LLM fallback.")

    # Step 3: Validate and construct Pydantic models
    try:
        medical_note = MedicalNote(**extracted_data)
        return medical_note
    except Exception as e:
        raise ValueError(f"Failed to validate extracted data: {str(e)}")


def extract_medical_note_from_file(file_path: str) -> MedicalNote:
    """
    Convenience function to extract from file path

    Args:
        file_path: Path to PDF file

    Returns:
        MedicalNote object
    """
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()

    return extract_medical_note(pdf_bytes)
