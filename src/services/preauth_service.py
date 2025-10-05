"""
PreAuth Service (Orchestrator)
Main orchestration layer that runs all 4 agents and aggregates results
"""

from typing import Dict
from src.models.schemas import (
    PreAuthRequest,
    ValidationResult,
    MedicalNote,
    ProcedureData,
    PolicyData
)
from src.agents.completeness_checker import CompletenessChecker
from src.agents.policy_validator import PolicyValidator
from src.agents.medical_reviewer import MedicalReviewer
from src.agents.fwa_detector import FWADetector
from src.services.aggregator import Aggregator
from src.services.pdf_extractor import PDFExtractor
from src.utils.data_loader import load_policy_data, load_procedure_data


class PreAuthService:
    """
    Main orchestration service for pre-authorization validation

    Coordinates all 4 agents:
    1. Completeness Checker - validates required fields
    2. Policy Validator - checks policy rules and exclusions
    3. Medical Reviewer - assesses medical necessity (LLM)
    4. FWA Detector - detects fraud/waste/abuse (hybrid)

    Then aggregates results into final validation decision.
    """

    def __init__(self, enable_llm_fallback: bool = False):
        """Initialize all agents, aggregator, and PDF extractor

        Args:
            enable_llm_fallback: Enable LLM fallback for PDF extraction if rule-based fails
        """
        self.completeness_checker = CompletenessChecker()
        self.policy_validator = PolicyValidator()
        self.medical_reviewer = MedicalReviewer()
        self.fwa_detector = FWADetector()
        self.aggregator = Aggregator()
        self.pdf_extractor = PDFExtractor(enable_llm_fallback=enable_llm_fallback)

    def validate_preauth(
        self,
        medical_note: MedicalNote,
        policy_data: PolicyData,
        procedure_data: ProcedureData,
        form_data: Dict
    ) -> ValidationResult:
        """
        Run full pre-authorization validation pipeline

        Args:
            medical_note: Extracted medical note from PDF
            policy_data: Policy data loaded from policy_data/*.json
            procedure_data: Procedure data loaded from medical_data/*.json
            form_data: Form data containing policy info and metadata

        Returns:
            ValidationResult with final score, status, and recommendations

        Example:
            >>> service = PreAuthService()
            >>> result = service.validate_preauth(note, policy, procedure, form)
            >>> print(result.final_score)  # 85
            >>> print(result.approval_likelihood)  # "high"
        """
        # Agent 1: Completeness Checker
        completeness_result = self.completeness_checker.validate(
            form_data=form_data,
            medical_note=medical_note
        )

        # Agent 2: Policy Validator
        # Pass policy_data as-is (PolicyData object), validator will use it for utilities
        policy_result = self.policy_validator.validate(
            policy_data=policy_data,
            procedure_id=form_data['procedure_id'],
            form_data=form_data,
            medical_note=medical_note
        )

        # Agent 3: Medical Reviewer
        # Convert procedure_data to dict for LLM prompt construction
        procedure_dict = procedure_data if isinstance(procedure_data, dict) else procedure_data.model_dump()
        medical_result = self.medical_reviewer.review(
            diagnosis=medical_note.diagnosis.primary_diagnosis,
            treatment=medical_note.proposed_treatment.procedure_name,
            justification=self._build_justification_text(medical_note),
            procedure_data=procedure_dict,
            medical_note=medical_note
        )

        # Agent 4: FWA Detector
        # Convert procedure_data to dict for LLM prompt construction
        fwa_result = self.fwa_detector.detect(
            diagnosis=medical_note.diagnosis.primary_diagnosis,
            treatment=medical_note.proposed_treatment.procedure_name,
            costs=medical_note.cost_breakdown.model_dump(),
            procedure_data=procedure_dict,
            stay_duration=medical_note.hospitalization_details.expected_length_of_stay,
            medical_note=medical_note
        )

        # Aggregate all results
        final_result = self.aggregator.aggregate(
            completeness=completeness_result,
            policy=policy_result,
            medical=medical_result,
            fwa=fwa_result
        )

        return final_result

    def _build_justification_text(self, medical_note: MedicalNote) -> str:
        """
        Build complete justification text from medical note

        Args:
            medical_note: Medical note

        Returns:
            Combined justification text
        """
        mj = medical_note.medical_justification

        return f"""
Why Hospitalization Required: {mj.why_hospitalization_required}
Why Treatment Necessary: {mj.why_treatment_necessary}
How Treatment Addresses Diagnosis: {mj.how_treatment_addresses_diagnosis or 'Not specified'}
Expected Outcomes: {mj.expected_outcomes or 'Not specified'}
        """.strip()

    def validate_preauth_from_pdf(
        self,
        pdf_path: str,
        insurer: str,
        policy_type: str,
        procedure_id: str,
        form_data: Dict
    ) -> tuple:
        """
        Complete end-to-end pre-authorization validation from PDF

        Args:
            pdf_path: Path to medical note PDF file
            insurer: Insurance company name (e.g., "Star Health")
            policy_type: Policy type (e.g., "Comprehensive")
            procedure_id: Procedure identifier (e.g., "cataract_surgery")
            form_data: Additional form data (policy number, start date, etc.)

        Returns:
            Tuple of (ValidationResult, medical_note_dict) - validation result and extracted medical note data

        Example:
            >>> service = PreAuthService()
            >>> result, medical_note = service.validate_preauth_from_pdf(
            ...     pdf_path="medical_note.pdf",
            ...     insurer="Star Health",
            ...     policy_type="Comprehensive",
            ...     procedure_id="cataract_surgery",
            ...     form_data={
            ...         'policy_number': 'SH12345678',
            ...         'policy_start_date': '2023-01-01',
            ...         'sum_insured': 500000,
            ...         'previous_claims_total': 0,
            ...         'planned_admission_date': '2025-05-10',
            ...         'patient_age_at_policy_start': 63
            ...     }
            ... )
            >>> print(result.final_score)
        """
        # Step 1: Extract medical note from PDF
        medical_note = self.pdf_extractor.extract_from_pdf(pdf_path)
        
        # Print extracted data for debugging
        print("\n" + "="*80)
        print("DATA EXTRACTED FROM PDF")
        print("="*80)
        print(medical_note.model_dump_json(indent=2))
        print("="*80 + "\n")

        # Step 2: Load policy and procedure data
        policy_data = load_policy_data(insurer, policy_type)
        procedure_data = load_procedure_data(procedure_id)

        # Step 3: Update form_data with additional fields from medical note
        complete_form_data = {
            **form_data,
            'insurer': insurer,
            'policy_type': policy_type,
            'procedure_id': procedure_id,
            'hospital_name': medical_note.hospital_details.name
        }

        # Step 4: Run validation pipeline
        validation_result = self.validate_preauth(
            medical_note=medical_note,
            policy_data=policy_data,
            procedure_data=procedure_data,
            form_data=complete_form_data
        )

        # Return both validation result and medical note data
        return validation_result, medical_note.model_dump()
