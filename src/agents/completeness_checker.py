"""
Completeness Checker Agent
Rule-based validation of required fields and document completeness
"""

from typing import Dict, List
from src.models.schemas import CompletenessResult, MedicalNote


# Required fields for pre-authorization form
REQUIRED_FORM_FIELDS = [
    'policy_number',
    'policy_start_date',
    'sum_insured',
    'planned_admission_date',
    'hospital_name',
    'insurer',
    'policy_type',
    'procedure_id'
]

# Required sections in medical note
REQUIRED_MEDICAL_NOTE_SECTIONS = [
    'patient_info',
    'diagnosis',
    'clinical_history',
    'proposed_treatment',
    'medical_justification',
    'hospitalization_details',
    'cost_breakdown',
    'doctor_details',
    'hospital_details'
]

# Score deduction per missing field
SCORE_DEDUCTION_PER_FIELD = 5


class CompletenessChecker:
    """
    Validates completeness of pre-authorization request

    Checks:
    - All required form fields are present and non-empty
    - All required medical note sections are present
    - Cost breakdown is not empty/zero
    """

    def __init__(self):
        """Initialize completeness checker"""
        pass

    def validate(self, form_data: Dict, medical_note: MedicalNote) -> CompletenessResult:
        """
        Validate completeness of pre-authorization request

        Args:
            form_data: Dictionary with form fields (policy info, procedure, etc.)
            medical_note: Extracted and validated MedicalNote object

        Returns:
            CompletenessResult with status, issues list, and score impact

        Example:
            >>> checker = CompletenessChecker()
            >>> result = checker.validate(form_data, medical_note)
            >>> print(result.status)  # "pass" or "fail"
            >>> print(result.score_impact)  # 0 or negative
        """
        issues = []

        # Check form fields
        form_issues = self._check_form_fields(form_data)
        issues.extend(form_issues)

        # Check medical note sections
        medical_note_issues = self._check_medical_note_sections(medical_note)
        issues.extend(medical_note_issues)

        # Check cost breakdown
        cost_issues = self._check_cost_breakdown(medical_note)
        issues.extend(cost_issues)

        # Calculate score impact
        score_impact = self._calculate_score_impact(issues)

        # Determine status
        status = "pass" if len(issues) == 0 else "fail"

        return CompletenessResult(
            status=status,
            issues=issues,
            score_impact=score_impact
        )

    def _check_form_fields(self, form_data: Dict) -> List[str]:
        """
        Check that all required form fields are present and non-empty

        Args:
            form_data: Form data dictionary

        Returns:
            List of missing field names
        """
        issues = []

        for field in REQUIRED_FORM_FIELDS:
            if field not in form_data:
                issues.append(f"Missing form field: {field}")
            elif not form_data[field]:
                # Field exists but is None, empty string, or 0
                issues.append(f"Empty form field: {field}")

        return issues

    def _check_medical_note_sections(self, medical_note: MedicalNote) -> List[str]:
        """
        Check that all required medical note sections are present

        Args:
            medical_note: MedicalNote object

        Returns:
            List of missing section names
        """
        issues = []

        # Convert MedicalNote to dict for easier checking
        medical_note_dict = medical_note.model_dump()

        for section in REQUIRED_MEDICAL_NOTE_SECTIONS:
            if section not in medical_note_dict:
                issues.append(f"Medical note missing section: {section}")
            elif not medical_note_dict[section]:
                # Section exists but is None or empty
                issues.append(f"Medical note section empty: {section}")
            elif isinstance(medical_note_dict[section], dict):
                # For nested objects, check if they have any content
                if not any(medical_note_dict[section].values()):
                    issues.append(f"Medical note section incomplete: {section}")

        return issues

    def _check_cost_breakdown(self, medical_note: MedicalNote) -> List[str]:
        """
        Check that cost breakdown is complete and not all zeros

        Args:
            medical_note: MedicalNote object

        Returns:
            List of cost-related issues
        """
        issues = []

        try:
            cost_breakdown = medical_note.cost_breakdown

            # Check if total cost is zero or very low
            if cost_breakdown.total_estimated_cost <= 0:
                issues.append("Cost breakdown: Total estimated cost is zero or missing")
                return issues

            # Check if all cost components are zero (suspicious)
            cost_components = [
                cost_breakdown.room_charges,
                cost_breakdown.surgeon_fees,
                cost_breakdown.anesthetist_fees,
                cost_breakdown.ot_charges,
                cost_breakdown.investigations,
                cost_breakdown.medicines_consumables
            ]

            if all(cost == 0 for cost in cost_components):
                issues.append("Cost breakdown: All cost components are zero (only total provided)")

            # Check for negative costs (data entry error)
            if any(cost < 0 for cost in cost_components):
                issues.append("Cost breakdown: Contains negative values")

            # Verify total matches sum of components (with small tolerance for rounding)
            calculated_total = sum([
                cost_breakdown.room_charges,
                cost_breakdown.surgeon_fees,
                cost_breakdown.anesthetist_fees,
                cost_breakdown.ot_charges,
                cost_breakdown.icu_charges or 0,
                cost_breakdown.investigations,
                cost_breakdown.medicines_consumables,
                cost_breakdown.implants or 0,
                cost_breakdown.other_charges or 0
            ])

            # Allow 1% tolerance for rounding differences
            if abs(calculated_total - cost_breakdown.total_estimated_cost) > (cost_breakdown.total_estimated_cost * 0.01):
                issues.append(f"Cost breakdown: Sum of components (₹{calculated_total:,.0f}) doesn't match total (₹{cost_breakdown.total_estimated_cost:,.0f})")

        except Exception as e:
            issues.append(f"Cost breakdown: Unable to validate - {str(e)}")

        return issues

    def _calculate_score_impact(self, issues: List[str]) -> int:
        """
        Calculate score deduction based on number of issues

        Args:
            issues: List of identified issues

        Returns:
            Negative integer representing score deduction
        """
        return -1 * len(issues) * SCORE_DEDUCTION_PER_FIELD

    def get_summary(self, result: CompletenessResult) -> str:
        """
        Generate human-readable summary of completeness check

        Args:
            result: CompletenessResult object

        Returns:
            Plain-language summary string
        """
        if result.status == "pass":
            return "✓ All required information is complete"

        # Group issues by category
        form_issues = [i for i in result.issues if "form field" in i.lower()]
        medical_issues = [i for i in result.issues if "medical note" in i.lower()]
        cost_issues = [i for i in result.issues if "cost" in i.lower()]

        summary_parts = []

        if form_issues:
            summary_parts.append(f"Missing {len(form_issues)} form field(s)")
        if medical_issues:
            summary_parts.append(f"Missing {len(medical_issues)} medical note section(s)")
        if cost_issues:
            summary_parts.append(f"{len(cost_issues)} cost breakdown issue(s)")

        return f"✗ Incomplete: {', '.join(summary_parts)}"
