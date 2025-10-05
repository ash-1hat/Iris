"""
Medical Reviewer Agent
LLM-powered assessment of medical necessity and treatment-diagnosis alignment
"""

import json
from typing import Dict, List, Optional
from src.models.schemas import MedicalReviewResult, MedicalConcern, MedicalNote
from src.utils.llm_client import call_llm_with_retry


# Prompt template for medical review
PROMPT_TEMPLATE = """You are a medical claim reviewer for health insurance in India.

COMPLETE MEDICAL NOTE (Personal details removed):
{medical_note_data}

CONTEXT FROM PROCEDURE GUIDELINES:
{contextual_notes}

ASSESSMENT CRITERIA:
1. Treatment-Diagnosis Alignment: Does treatment logically follow from diagnosis?
2. Hospitalization Necessity:
   - For day surgeries: 1 day is normal (for prep, surgery, recovery). Only flag if >1 day OR "overnight stay" is mentioned without medical reason.
   - For procedures typically requiring overnight stay: Check if duration matches procedure guidelines.
   - Focus on whether the admission itself is medically necessary, not the duration if it's 1 day.
3. Documentation Completeness: Is justification specific with patient details (not template language)?
4. Functional Impact: Are specific affected activities mentioned (not just "patient wants")?

IMPORTANT NOTES:
- This is a documentation review at the pre-authorization stage. Be fair, flexible and reasonable in assessment.
- Don't be overly restrictive - focus on whether there are major gaps or concerns, not minor imperfections or infractions.
- Do not bother about Hospital Name and Hospital Address.
- **DO NOT COMMENT ON COSTS** - Cost analysis, implant pricing, room charges, surgeon fees, etc. are handled by the Quality Check agent. Your focus is ONLY on medical documentation and clinical justification.
- As for Pre-Operative Checks, it is not necessary for all the tests in the mandatory section of medical_data json to be done. Consider passed even if one test from the mandatory section is done. 
- 1-day admission for surgical procedures is standard practice even for day surgery (includes prep and recovery time).
- If cost breakdown shows ₹0 for implants or other items, ignore it - this is a cost analysis matter, not a medical documentation concern.

Return ONLY a valid JSON object with this exact structure:
{{
  "assessment": "strong" | "acceptable" | "weak" | "concerning",
  "concerns": [
    {{
      "type": "treatment_mismatch" | "insufficient_justification" | "missing_evidence" | "template_language",
      "description": "specific issue",
      "suggestion": "what to add/clarify"
    }}
  ]
}}

IMPORTANT: Return ONLY the JSON object, no other text."""


# Scoring logic
ASSESSMENT_SCORES = {
    "strong": 0,
    "acceptable": -5,
    "weak": -10,
    "concerning": -15
}


class MedicalReviewer:
    """
    LLM-powered medical review agent

    Assesses:
    - Medical necessity and treatment-diagnosis alignment
    - Documentation quality and specificity
    - Functional impact evidence
    - Template language detection
    """

    def __init__(self):
        """Initialize medical reviewer"""
        pass

    def review(
        self,
        diagnosis: str,
        treatment: str,
        justification: str,
        procedure_data: Dict,
        medical_note: MedicalNote
    ) -> MedicalReviewResult:
        """
        Review medical necessity and documentation quality

        Args:
            diagnosis: Primary diagnosis
            treatment: Proposed treatment/procedure
            justification: Medical justification text
            procedure_data: Procedure data with contextual_notes_for_llm
            medical_note: Complete medical note for additional context

        Returns:
            MedicalReviewResult with assessment, concerns, and score impact

        Example:
            >>> reviewer = MedicalReviewer()
            >>> result = reviewer.review(diagnosis, treatment, justification, procedure_data, note)
            >>> print(result.assessment)  # "strong", "acceptable", "weak", "concerning"
        """
        try:
            # Construct prompt
            prompt = self._construct_prompt(
                diagnosis,
                treatment,
                justification,
                procedure_data,
                medical_note
            )
            
            # Print prompt for debugging
            print("\n" + "="*80)
            print("PROMPT SENT TO AGENT-3 (MEDICAL REVIEWER)")
            print("="*80)
            print(prompt)
            print("="*80 + "\n")

            # Call LLM
            llm_response = self._call_llm(prompt)

            # Parse response
            assessment, concerns = self._parse_llm_response(llm_response)

            # Calculate score impact
            score_impact = self._calculate_score_impact(assessment, concerns)

            # Determine if doctor feedback required
            requires_doctor_feedback = (
                assessment in ["weak", "concerning"] or
                len(concerns) > 2
            )

            # Determine status
            status = self._determine_status(assessment, concerns)

            return MedicalReviewResult(
                status=status,
                concerns=concerns,
                score_impact=score_impact,
                doctor_feedback_required=requires_doctor_feedback
            )

        except Exception as e:
            # Graceful degradation - return warning status if LLM fails
            return MedicalReviewResult(
                status="warning",
                concerns=[
                    MedicalConcern(
                        type="insufficient_justification",
                        description=f"Unable to perform LLM review: {str(e)}",
                        suggestion="Manual review recommended"
                    )
                ],
                score_impact=-5,
                doctor_feedback_required=True
            )

    def _construct_prompt(
        self,
        diagnosis: str,
        treatment: str,
        justification: str,
        procedure_data: Dict,
        medical_note: MedicalNote
    ) -> str:
        """
        Construct LLM prompt with all relevant context

        Args:
            diagnosis: Primary diagnosis (not used, kept for compatibility)
            treatment: Proposed treatment (not used, kept for compatibility)
            justification: Medical justification (not used, kept for compatibility)
            procedure_data: Procedure data
            medical_note: Medical note

        Returns:
            Formatted prompt string
        """
        # Get specific sections from procedure data
        overnight_justifications = procedure_data.get('hospitalization', {}).get('overnight_justifications', {})
        medical_necessity = procedure_data.get('medical_necessity_criteria', {})
        required_diagnostics = procedure_data.get('required_diagnostics', {})
        
        # Format these sections for the LLM
        medical_guidelines = self._format_medical_guidelines(
            overnight_justifications,
            medical_necessity,
            required_diagnostics
        )

        # Create complete medical note data (excluding personal details)
        medical_note_dict = medical_note.model_dump()
        
        # Remove personal identifiable information
        if 'patient_info' in medical_note_dict:
            medical_note_dict['patient_info'] = {
                'age': medical_note_dict['patient_info'].get('age'),
                'gender': medical_note_dict['patient_info'].get('gender'),
                # Removed: name, contact_number, patient_id
            }
        
        # Format the medical note data in a readable way
        medical_note_formatted = f"""
=== DIAGNOSIS ===
Primary Diagnosis: {medical_note.diagnosis.primary_diagnosis}
ICD-10 Code: {medical_note.diagnosis.icd_10_code}
Secondary Diagnoses: {', '.join(medical_note.diagnosis.secondary_diagnoses) if medical_note.diagnosis.secondary_diagnoses else 'None'}
Diagnosis Date: {medical_note.diagnosis.diagnosis_date or 'Not specified'}

=== PATIENT DEMOGRAPHICS ===
Age: {medical_note.patient_info.age} years
Gender: {medical_note.patient_info.gender}

=== CLINICAL HISTORY ===
Chief Complaints: {medical_note.clinical_history.chief_complaints}
Duration of Symptoms: {medical_note.clinical_history.duration_of_symptoms or 'Not specified'}
Relevant Medical History: {medical_note.clinical_history.relevant_medical_history or 'Not specified'}
Comorbidities: {', '.join(medical_note.clinical_history.comorbidities) if medical_note.clinical_history.comorbidities else 'None'}

=== DIAGNOSTIC TESTS/INVESTIGATIONS ===
{self._format_diagnostic_tests(medical_note.diagnostic_tests)}

=== PROPOSED TREATMENT ===
Procedure: {medical_note.proposed_treatment.procedure_name}
Procedure Code: {medical_note.proposed_treatment.procedure_code or 'Not specified'}
Anesthesia Type: {medical_note.proposed_treatment.anesthesia_type or 'Not specified'}
Surgical Approach: {medical_note.proposed_treatment.surgical_approach or 'Not specified'}

=== MEDICAL JUSTIFICATION ===
Why Hospitalization Required: {medical_note.medical_justification.why_hospitalization_required}
Why Treatment Necessary: {medical_note.medical_justification.why_treatment_necessary}
How Treatment Addresses Diagnosis: {medical_note.medical_justification.how_treatment_addresses_diagnosis or 'Not specified'}
Expected Outcomes: {medical_note.medical_justification.expected_outcomes or 'Not specified'}

=== HOSPITALIZATION DETAILS ===
Hospitalization Type: {medical_note.hospitalization_details.hospitalization_type or 'Not specified'}
Planned Admission Date: {medical_note.hospitalization_details.planned_admission_date}
Expected Length of Stay: {medical_note.hospitalization_details.expected_length_of_stay} days
ICU Required: {'Yes' if medical_note.hospitalization_details.icu_required else 'No'}
ICU Duration: {medical_note.hospitalization_details.icu_duration or 0} days

=== COST BREAKDOWN ===
Room Charges: ₹{medical_note.cost_breakdown.room_charges:,.0f}
Surgeon Fees: ₹{medical_note.cost_breakdown.surgeon_fees:,.0f}
Anesthetist Fees: ₹{medical_note.cost_breakdown.anesthetist_fees:,.0f}
OT Charges: ₹{medical_note.cost_breakdown.ot_charges:,.0f}
ICU Charges: ₹{medical_note.cost_breakdown.icu_charges or 0:,.0f}
Investigations: ₹{medical_note.cost_breakdown.investigations:,.0f}
Medicines/Consumables: ₹{medical_note.cost_breakdown.medicines_consumables:,.0f}
Implants: ₹{medical_note.cost_breakdown.implants or 0:,.0f}
Other Charges: ₹{medical_note.cost_breakdown.other_charges or 0:,.0f}
Total Estimated Cost: ₹{medical_note.cost_breakdown.total_estimated_cost:,.0f}

=== DOCTOR DETAILS ===
Doctor Name: {medical_note.doctor_details.name}
Qualification: {medical_note.doctor_details.qualification or 'Not specified'}
Registration Number: {medical_note.doctor_details.registration_number or 'Not specified'}

=== HOSPITAL DETAILS ===
Hospital Name: {medical_note.hospital_details.name}
Address: {medical_note.hospital_details.address or 'Not specified'}
        """.strip()

        return PROMPT_TEMPLATE.format(
            medical_note_data=medical_note_formatted,
            contextual_notes=medical_guidelines
        )
    
    def _format_medical_guidelines(
        self,
        overnight_justifications: Dict,
        medical_necessity: Dict,
        required_diagnostics: Dict
    ) -> str:
        """
        Format medical guidelines from procedure data
        
        Args:
            overnight_justifications: Overnight stay justifications
            medical_necessity: Medical necessity criteria
            required_diagnostics: Required diagnostic tests
            
        Returns:
            Formatted string of guidelines
        """
        import json
        
        guidelines = []
        
        # Add overnight justifications
        if overnight_justifications:
            guidelines.append("=== OVERNIGHT HOSPITALIZATION GUIDELINES ===")
            guidelines.append(json.dumps(overnight_justifications, indent=2))
            guidelines.append("")
        
        # Add medical necessity criteria
        if medical_necessity:
            guidelines.append("=== MEDICAL NECESSITY CRITERIA ===")
            guidelines.append(json.dumps(medical_necessity, indent=2))
            guidelines.append("")
        
        # Add required diagnostics
        if required_diagnostics:
            guidelines.append("=== REQUIRED DIAGNOSTIC TESTS ===")
            guidelines.append(json.dumps(required_diagnostics, indent=2))
            guidelines.append("")
        
        return "\n".join(guidelines) if guidelines else "No specific guidelines available."
    
    def _format_diagnostic_tests(self, tests: List) -> str:
        """
        Format diagnostic tests for display
        
        Args:
            tests: List of diagnostic test objects
            
        Returns:
            Formatted string of tests
        """
        if not tests:
            return "No diagnostic tests documented"
        
        formatted = []
        for i, test in enumerate(tests, 1):
            test_str = f"{i}. {test.test_name}"
            if hasattr(test, 'date_performed') and test.date_performed:
                test_str += f" (Date: {test.date_performed})"
            if hasattr(test, 'key_findings') and test.key_findings:
                test_str += f"\n   Findings: {test.key_findings}"
            formatted.append(test_str)
        
        return "\n".join(formatted)

    def _call_llm(self, prompt: str, max_retries: int = 2) -> str:
        """
        Call LLM with retry logic

        Args:
            prompt: Prompt string
            max_retries: Maximum retry attempts

        Returns:
            LLM response string
        """
        response = call_llm_with_retry(
            prompt=prompt,
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            temperature=0.3,
            max_retries=max_retries
        )
        return response

    def _parse_llm_response(self, response: str) -> tuple:
        """
        Parse LLM JSON response

        Args:
            response: LLM response string

        Returns:
            Tuple of (assessment, concerns_list)
        """
        try:
            # Extract JSON from response (handle cases where LLM adds extra text)
            response = response.strip()

            # Find JSON object in response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON object found in response")

            json_str = response[start_idx:end_idx]
            data = json.loads(json_str)

            assessment = data.get('assessment', 'acceptable')
            concerns_data = data.get('concerns', [])

            # Convert to MedicalConcern objects
            concerns = [
                MedicalConcern(
                    type=c.get('type', 'insufficient_justification'),
                    description=c.get('description', 'No description provided'),
                    suggestion=c.get('suggestion', 'Review documentation')
                )
                for c in concerns_data
            ]

            return assessment, concerns

        except json.JSONDecodeError as e:
            # If JSON parsing fails, return default values
            return "acceptable", [
                MedicalConcern(
                    type="insufficient_justification",
                    description=f"Unable to parse LLM response: {str(e)}",
                    suggestion="Manual review recommended"
                )
            ]

    def _calculate_score_impact(self, assessment: str, concerns: List[MedicalConcern]) -> int:
        """
        Calculate score deduction based on assessment and concerns

        Args:
            assessment: Assessment level
            concerns: List of concerns

        Returns:
            Negative integer representing score deduction
        """
        base_score = ASSESSMENT_SCORES.get(assessment, -5)
        concern_penalty = len(concerns) * -5

        return base_score + concern_penalty

    def _determine_status(self, assessment: str, concerns: List[MedicalConcern]) -> str:
        """
        Determine overall status based on assessment

        Args:
            assessment: Assessment level
            concerns: List of concerns

        Returns:
            Status: "pass", "warning", or "fail"
        """
        if assessment == "concerning":
            return "fail"
        elif assessment == "weak" or len(concerns) > 2:
            return "warning"
        elif assessment == "acceptable" and len(concerns) <= 1:
            return "warning"
        elif assessment == "strong":
            return "pass"
        else:
            return "warning"

    def get_summary(self, result: MedicalReviewResult) -> str:
        """
        Generate human-readable summary of medical review

        Args:
            result: MedicalReviewResult object

        Returns:
            Plain-language summary string
        """
        if result.status == "pass":
            return "✓ Medical necessity well-documented"

        concern_summary = f"{len(result.concerns)} concern(s)" if result.concerns else "no specific concerns"

        if result.doctor_feedback_required:
            return f"✗ Medical review: {concern_summary}. Doctor feedback required."
        else:
            return f"⚠ Medical review: {concern_summary}."
