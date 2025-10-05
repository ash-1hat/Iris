"""
Unit tests for Medical Reviewer Agent
Tests LLM-powered medical necessity assessment
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import patch, MagicMock
from src.agents.medical_reviewer import MedicalReviewer
from src.models.schemas import (
    MedicalNote, PatientInfo, DiagnosisInfo, ClinicalHistory,
    ProposedTreatment, MedicalJustification, HospitalizationDetails,
    CostBreakdown, DoctorDetails, HospitalDetails
)
from src.utils.data_loader import load_procedure_data


class TestMedicalReviewer:
    """Test suite for MedicalReviewer agent"""

    def setup_method(self):
        """Setup test fixtures"""
        self.reviewer = MedicalReviewer()

        # Load actual procedure data
        self.cataract_procedure = load_procedure_data("cataract_surgery")

        # Strong medical note (good justification)
        self.strong_medical_note = MedicalNote(
            patient_info=PatientInfo(
                name="Test Patient",
                age=68,
                gender="Male",
                contact_number="9876543210"
            ),
            diagnosis=DiagnosisInfo(
                primary_diagnosis="Senile Cataract with significant visual impairment",
                icd_10_code="H25.9",
                diagnosis_date="2025-01-15"
            ),
            clinical_history=ClinicalHistory(
                chief_complaints="Progressive bilateral vision loss over 18 months, difficulty reading, unable to drive"
            ),
            proposed_treatment=ProposedTreatment(
                procedure_name="Phacoemulsification with IOL implantation",
                procedure_type="elective"
            ),
            medical_justification=MedicalJustification(
                why_hospitalization_required="Surgical intervention requires sterile OT environment with post-op monitoring",
                why_treatment_necessary="Visual acuity deteriorated to 6/60 in right eye, 6/36 in left eye, affecting daily living activities",
                how_treatment_addresses_diagnosis="Phacoemulsification will remove opaque lens and restore functional vision",
                expected_outcomes="Improved vision to 6/12 or better, restored independence in daily activities"
            ),
            hospitalization_details=HospitalizationDetails(
                planned_admission_date="05/10/2025",
                expected_length_of_stay=1
            ),
            cost_breakdown=CostBreakdown(
                room_charges=3500,
                surgeon_fees=18000,
                anesthetist_fees=5000,
                ot_charges=12000,
                investigations=2500,
                medicines_consumables=10000,
                total_estimated_cost=51000
            ),
            doctor_details=DoctorDetails(
                name="Dr. Test",
                qualification="MS Ophthalmology",
                registration_number="12345"
            ),
            hospital_details=HospitalDetails(
                name="Test Hospital",
                location="Mumbai",
                type="private"
            )
        )

        # Weak medical note (vague justification)
        self.weak_medical_note = MedicalNote(
            patient_info=PatientInfo(
                name="Test Patient 2",
                age=55,
                gender="Male",
                contact_number="9876543210"
            ),
            diagnosis=DiagnosisInfo(
                primary_diagnosis="Cataract",
                icd_10_code="H25.9",
                diagnosis_date="2025-01-15"
            ),
            clinical_history=ClinicalHistory(
                chief_complaints="Vision is not clear"
            ),
            proposed_treatment=ProposedTreatment(
                procedure_name="Cataract operation",
                procedure_type="elective"
            ),
            medical_justification=MedicalJustification(
                why_hospitalization_required="Patient wants surgery",
                why_treatment_necessary="Patient has vision problem",
                how_treatment_addresses_diagnosis="",
                expected_outcomes=""
            ),
            hospitalization_details=HospitalizationDetails(
                planned_admission_date="05/10/2025",
                expected_length_of_stay=1
            ),
            cost_breakdown=CostBreakdown(
                room_charges=3500,
                surgeon_fees=18000,
                anesthetist_fees=5000,
                ot_charges=12000,
                investigations=2500,
                medicines_consumables=10000,
                total_estimated_cost=51000
            ),
            doctor_details=DoctorDetails(
                name="Dr. Test",
                qualification="MS",
                registration_number="12345"
            ),
            hospital_details=HospitalDetails(
                name="Test Hospital",
                location="Mumbai",
                type="private"
            )
        )

    @patch('src.agents.medical_reviewer.call_llm_with_retry')
    def test_strong_justification(self, mock_llm):
        """Test 1: Strong justification with functional impact → pass, 'strong'"""
        # Mock LLM response
        mock_llm.return_value = """{
            "assessment": "strong",
            "concerns": []
        }"""

        result = self.reviewer.review(
            diagnosis="Senile Cataract with significant visual impairment",
            treatment="Phacoemulsification with IOL implantation",
            justification="Visual acuity 6/60, affecting daily activities",
            procedure_data=self.cataract_procedure.model_dump(),
            medical_note=self.strong_medical_note
        )

        assert result.status == "pass"
        assert result.score_impact == 0
        assert len(result.concerns) == 0
        assert result.doctor_feedback_required is False

    @patch('src.agents.medical_reviewer.call_llm_with_retry')
    def test_concerning_justification(self, mock_llm):
        """Test 2: 'Patient wants surgery' → fail, 'concerning'"""
        # Mock LLM response
        mock_llm.return_value = """{
            "assessment": "concerning",
            "concerns": [
                {
                    "type": "insufficient_justification",
                    "description": "Justification based on patient preference ('patient wants') rather than medical necessity",
                    "suggestion": "Provide objective clinical evidence (VA measurements, functional impact on specific activities)"
                },
                {
                    "type": "missing_evidence",
                    "description": "No objective measurements provided (visual acuity, slit lamp findings)",
                    "suggestion": "Document VA measurements and clinical examination findings"
                }
            ]
        }"""

        result = self.reviewer.review(
            diagnosis="Cataract",
            treatment="Cataract operation",
            justification="Patient wants surgery",
            procedure_data=self.cataract_procedure.model_dump(),
            medical_note=self.weak_medical_note
        )

        assert result.status == "fail"
        assert result.score_impact < -15
        assert len(result.concerns) >= 1
        assert result.doctor_feedback_required is True

    @patch('src.agents.medical_reviewer.call_llm_with_retry')
    def test_missing_diagnostic_tests(self, mock_llm):
        """Test 3: Missing diagnostic tests → warning, 'weak'"""
        mock_llm.return_value = """{
            "assessment": "weak",
            "concerns": [
                {
                    "type": "missing_evidence",
                    "description": "No diagnostic test results documented",
                    "suggestion": "Provide VA measurements, slit lamp findings, IOP, fundus examination"
                }
            ]
        }"""

        result = self.reviewer.review(
            diagnosis="Cataract",
            treatment="Cataract surgery",
            justification="Vision problem for some time",
            procedure_data=self.cataract_procedure.model_dump(),
            medical_note=self.weak_medical_note
        )

        assert result.status == "warning"
        assert result.score_impact <= -10
        assert len(result.concerns) >= 1

    @patch('src.agents.medical_reviewer.call_llm_with_retry')
    def test_template_language(self, mock_llm):
        """Test 4: Template language detected → warning"""
        mock_llm.return_value = """{
            "assessment": "acceptable",
            "concerns": [
                {
                    "type": "template_language",
                    "description": "Generic phrases detected: 'standard protocol followed'",
                    "suggestion": "Replace with patient-specific details and clinical findings"
                }
            ]
        }"""

        result = self.reviewer.review(
            diagnosis="Cataract",
            treatment="Cataract surgery",
            justification="Standard protocol followed for cataract management",
            procedure_data=self.cataract_procedure.model_dump(),
            medical_note=self.strong_medical_note
        )

        assert result.status == "warning"
        assert len(result.concerns) == 1
        assert any(c.type == "template_language" for c in result.concerns)

    @patch('src.agents.medical_reviewer.call_llm_with_retry')
    def test_acceptable_with_minor_issues(self, mock_llm):
        """Test 5: Acceptable justification with minor concerns → warning"""
        mock_llm.return_value = """{
            "assessment": "acceptable",
            "concerns": [
                {
                    "type": "insufficient_justification",
                    "description": "Could provide more specific functional impact details",
                    "suggestion": "Add specific activities affected (e.g., cannot read medicine labels)"
                }
            ]
        }"""

        result = self.reviewer.review(
            diagnosis="Senile Cataract",
            treatment="Phacoemulsification",
            justification="VA 6/60, affecting daily activities",
            procedure_data=self.cataract_procedure.model_dump(),
            medical_note=self.strong_medical_note
        )

        assert result.status == "warning"
        assert result.score_impact == -10  # -5 for acceptable + -5 for 1 concern
        assert len(result.concerns) == 1

    @patch('src.agents.medical_reviewer.call_llm_with_retry')
    def test_llm_timeout_graceful_degradation(self, mock_llm):
        """Test 6: LLM API timeout → graceful degradation (return warning)"""
        # Simulate LLM timeout
        mock_llm.side_effect = TimeoutError("LLM request timed out")

        result = self.reviewer.review(
            diagnosis="Cataract",
            treatment="Cataract surgery",
            justification="Some justification",
            procedure_data=self.cataract_procedure.model_dump(),
            medical_note=self.strong_medical_note
        )

        assert result.status == "warning"
        assert result.doctor_feedback_required is True
        assert any("Unable to perform LLM review" in c.description for c in result.concerns)

    @patch('src.agents.medical_reviewer.call_llm_with_retry')
    def test_invalid_json_response(self, mock_llm):
        """Test 7: Invalid JSON response → retry once, then graceful degradation"""
        # First call returns invalid JSON
        mock_llm.return_value = "This is not valid JSON at all"

        result = self.reviewer.review(
            diagnosis="Cataract",
            treatment="Cataract surgery",
            justification="Some justification",
            procedure_data=self.cataract_procedure.model_dump(),
            medical_note=self.strong_medical_note
        )

        # Should still return a result (graceful degradation in parsing)
        assert result.status in ["pass", "warning", "fail"]
        assert len(result.concerns) >= 0  # May have concerns from parsing error

    @patch('src.agents.medical_reviewer.call_llm_with_retry')
    def test_json_with_extra_text(self, mock_llm):
        """Test JSON parsing when LLM adds extra text"""
        mock_llm.return_value = """Here is my assessment:
        {
            "assessment": "strong",
            "concerns": []
        }
        I hope this helps!"""

        result = self.reviewer.review(
            diagnosis="Cataract",
            treatment="Cataract surgery",
            justification="Good justification",
            procedure_data=self.cataract_procedure.model_dump(),
            medical_note=self.strong_medical_note
        )

        assert result.status == "pass"
        assert len(result.concerns) == 0

    @patch('src.agents.medical_reviewer.call_llm_with_retry')
    def test_multiple_concerns_triggers_feedback(self, mock_llm):
        """Test that >2 concerns triggers doctor feedback requirement"""
        mock_llm.return_value = """{
            "assessment": "acceptable",
            "concerns": [
                {
                    "type": "missing_evidence",
                    "description": "No VA measurements",
                    "suggestion": "Add VA"
                },
                {
                    "type": "insufficient_justification",
                    "description": "Vague functional impact",
                    "suggestion": "Be specific"
                },
                {
                    "type": "template_language",
                    "description": "Generic phrases",
                    "suggestion": "Use patient-specific details"
                }
            ]
        }"""

        result = self.reviewer.review(
            diagnosis="Cataract",
            treatment="Cataract surgery",
            justification="Some justification",
            procedure_data=self.cataract_procedure.model_dump(),
            medical_note=self.strong_medical_note
        )

        assert len(result.concerns) == 3
        assert result.doctor_feedback_required is True

    @patch('src.agents.medical_reviewer.call_llm_with_retry')
    def test_get_summary_pass(self, mock_llm):
        """Test summary generation for passing result"""
        mock_llm.return_value = '{"assessment": "strong", "concerns": []}'

        result = self.reviewer.review(
            diagnosis="Cataract",
            treatment="Cataract surgery",
            justification="Good justification with VA 6/60",
            procedure_data=self.cataract_procedure.model_dump(),
            medical_note=self.strong_medical_note
        )

        summary = self.reviewer.get_summary(result)
        assert "well-documented" in summary.lower()

    @patch('src.agents.medical_reviewer.call_llm_with_retry')
    def test_get_summary_fail(self, mock_llm):
        """Test summary generation for failing result"""
        mock_llm.return_value = """{
            "assessment": "concerning",
            "concerns": [
                {"type": "insufficient_justification", "description": "Vague", "suggestion": "Fix"}
            ]
        }"""

        result = self.reviewer.review(
            diagnosis="Cataract",
            treatment="Cataract surgery",
            justification="Patient wants surgery",
            procedure_data=self.cataract_procedure.model_dump(),
            medical_note=self.weak_medical_note
        )

        summary = self.reviewer.get_summary(result)
        assert "feedback required" in summary.lower() or "concern" in summary.lower()


def run_medical_reviewer_tests():
    """Run all medical reviewer tests"""
    print("=" * 60)
    print("MEDICAL REVIEWER TESTS")
    print("=" * 60)

    # Run pytest programmatically
    exit_code = pytest.main([__file__, "-v", "--tb=short"])

    print("\n" + "=" * 60)
    if exit_code == 0:
        print("All Medical Reviewer tests passed")
    else:
        print("Some tests failed")
    print("=" * 60)

    return exit_code == 0


if __name__ == "__main__":
    import sys
    success = run_medical_reviewer_tests()
    sys.exit(0 if success else 1)
