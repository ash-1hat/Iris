"""
Phase 3 Integration Tests
End-to-end testing of the full pre-authorization validation pipeline
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import patch
from src.services.preauth_service import PreAuthService
from src.models.schemas import (
    MedicalNote, PatientInfo, DiagnosisInfo, ClinicalHistory,
    ProposedTreatment, MedicalJustification, HospitalizationDetails,
    CostBreakdown, DoctorDetails, HospitalDetails, PolicyData, ProcedureData
)
from src.utils.data_loader import load_policy_data, load_procedure_data


class TestPhase3Integration:
    """Integration tests for full pre-authorization pipeline"""

    def setup_method(self):
        """Setup test fixtures"""
        self.service = PreAuthService()

        # Load real procedure and policy data
        self.cataract_procedure = load_procedure_data("cataract_surgery")
        self.star_comprehensive = load_policy_data("Star Health", "Comprehensive")

        # Base form data
        # Note: Cataract has 24-month waiting period, so policy must be >24 months old
        self.base_form_data = {
            'insurer': 'Star Health',
            'policy_type': 'Comprehensive',
            'policy_number': 'SH12345678',
            'policy_start_date': '2023-01-01',  # >24 months before admission
            'sum_insured': 500000,
            'previous_claims_total': 0,
            'procedure_id': 'cataract_surgery',
            'hospital_name': 'Apollo Hospital',
            'planned_admission_date': '2025-05-10',
            'patient_age_at_policy_start': 63
        }

    @patch('src.agents.medical_reviewer.call_llm_with_retry')
    @patch('src.agents.fwa_detector.call_llm_with_retry')
    def test_perfect_case_all_agents_pass(self, fwa_mock, medical_mock):
        """Test 1: Perfect case - all agents pass, high score, high approval"""
        # Mock LLM responses
        medical_mock.return_value = '{"assessment": "strong", "concerns": []}'
        fwa_mock.return_value = '{"risk_level": "low", "flags": []}'

        # Create perfect medical note
        medical_note = MedicalNote(
            patient_info=PatientInfo(
                name="Test Patient",
                age=65,
                gender="Male",
                patient_id="P12345",
                contact_number="9876543210"
            ),
            diagnosis=DiagnosisInfo(
                primary_diagnosis="Senile Cataract",
                icd_10_code="H25.9",
                diagnosis_date="2025-01-15",
                secondary_diagnoses=[]
            ),
            clinical_history=ClinicalHistory(
                chief_complaints="Progressive vision loss in right eye",
                duration_of_symptoms="6 months",
                relevant_medical_history="Diabetes controlled on medication",
                comorbidities=["Diabetes Type 2"]
            ),
            diagnostic_tests=[
                {"test_name": "Visual Acuity Test", "date_performed": "2025-01-15", "key_findings": "6/60 right eye"},
                {"test_name": "Slit Lamp Examination", "date_performed": "2025-01-15", "key_findings": "Dense nuclear sclerosis"}
            ],
            proposed_treatment=ProposedTreatment(
                procedure_name="Cataract Surgery - Phacoemulsification",
                procedure_code="CPT-66984",
                surgical_approach="Phacoemulsification",
                anesthesia_type="Local"
            ),
            medical_justification=MedicalJustification(
                why_hospitalization_required="Surgical intervention required for vision restoration",
                why_treatment_necessary="Patient has significant vision impairment affecting daily activities like reading and driving",
                how_treatment_addresses_diagnosis="Phacoemulsification will remove cataract and restore vision",
                expected_outcomes="Vision improvement to 6/12 or better"
            ),
            hospitalization_details=HospitalizationDetails(
                planned_admission_date="2025-05-10",
                expected_length_of_stay=1,
                icu_required=False
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
                name="Dr. Kumar",
                qualification="MS Ophthalmology",
                specialty="Ophthalmology",
                registration_number="MCI123456",
                email="dr.kumar@example.com",
                phone="9999999999"
            ),
            hospital_details=HospitalDetails(
                name="Apollo Hospital",
                address="Mumbai",
                registration_number="HOSP123",
                contact_number="9999999998"
            )
        )

        # Run validation
        result = self.service.validate_preauth(
            medical_note=medical_note,
            policy_data=self.star_comprehensive,
            procedure_data=self.cataract_procedure,
            form_data=self.base_form_data
        )

        # Assertions
        assert result.overall_status == "pass"
        assert result.final_score >= 90
        assert result.approval_likelihood == "high"
        assert "approved" in result.summary.lower() or "passed" in result.summary.lower()

    @patch('src.agents.medical_reviewer.call_llm_with_retry')
    @patch('src.agents.fwa_detector.call_llm_with_retry')
    def test_minor_issues_warning_status(self, fwa_mock, medical_mock):
        """Test 2: Minor issues - warnings from multiple agents, medium score"""
        # Mock LLM responses with minor concerns
        medical_mock.return_value = """{
            "assessment": "acceptable",
            "concerns": [{
                "type": "insufficient_justification",
                "description": "Could provide more specific functional impact details",
                "suggestion": "Add specific affected activities"
            }]
        }"""
        fwa_mock.return_value = '{"risk_level": "low", "flags": []}'

        # Medical note with some missing optional fields
        medical_note = MedicalNote(
            patient_info=PatientInfo(
                name="Test Patient",
                age=65,
                gender="Male",
                contact_number="9876543210"  # Missing patient_id
            ),
            diagnosis=DiagnosisInfo(
                primary_diagnosis="Senile Cataract",
                icd_10_code="H25.9"
                # Missing diagnosis_date
            ),
            clinical_history=ClinicalHistory(
                chief_complaints="Vision loss"
                # Missing duration_of_symptoms
            ),
            diagnostic_tests=[
                {"test_name": "Visual Acuity Test", "key_findings": "6/60"}
            ],
            proposed_treatment=ProposedTreatment(
                procedure_name="Cataract Surgery",
                anesthesia_type="Local"
            ),
            medical_justification=MedicalJustification(
                why_hospitalization_required="Surgery needed",
                why_treatment_necessary="Patient has vision problems"
            ),
            hospitalization_details=HospitalizationDetails(
                planned_admission_date="2025-05-10",
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
                name="Dr. Kumar",
                qualification="MS",
                registration_number="MCI123456"
            ),
            hospital_details=HospitalDetails(
                name="Apollo Hospital"
            )
        )

        # Run validation
        result = self.service.validate_preauth(
            medical_note=medical_note,
            policy_data=self.star_comprehensive,
            procedure_data=self.cataract_procedure,
            form_data=self.base_form_data
        )

        # Assertions
        assert result.overall_status == "warning"
        assert 70 <= result.final_score <= 90
        assert result.approval_likelihood in ["medium", "high"]
        assert len(result.all_issues) > 0
        assert len(result.recommendations) > 0

    @patch('src.agents.medical_reviewer.call_llm_with_retry')
    @patch('src.agents.fwa_detector.call_llm_with_retry')
    def test_critical_failure_policy_violation(self, fwa_mock, medical_mock):
        """Test 3: Critical failure - policy violation (waiting period), low score"""
        # Mock LLM responses
        medical_mock.return_value = '{"assessment": "acceptable", "concerns": []}'
        fwa_mock.return_value = '{"risk_level": "low", "flags": []}'

        # Policy start date recent (violates 24-month cataract waiting period)
        form_data = self.base_form_data.copy()
        form_data['policy_start_date'] = '2024-04-01'  # Only ~13 months before admission (needs 24)
        form_data['planned_admission_date'] = '2025-05-10'
        form_data['patient_age_at_policy_start'] = 65

        medical_note = MedicalNote(
            patient_info=PatientInfo(
                name="Test Patient",
                age=65,
                gender="Male",
                contact_number="9876543210"
            ),
            diagnosis=DiagnosisInfo(
                primary_diagnosis="Senile Cataract",
                icd_10_code="H25.9",
                diagnosis_date="2025-01-15"  # Diagnosed BEFORE policy start
            ),
            clinical_history=ClinicalHistory(
                chief_complaints="Vision loss"
            ),
            proposed_treatment=ProposedTreatment(
                procedure_name="Cataract Surgery",
                anesthesia_type="Local"
            ),
            medical_justification=MedicalJustification(
                why_hospitalization_required="Surgical intervention required",
                why_treatment_necessary="Vision impairment"
            ),
            hospitalization_details=HospitalizationDetails(
                planned_admission_date="2025-05-10",
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
                name="Dr. Kumar",
                qualification="MS",
                registration_number="MCI123456"
            ),
            hospital_details=HospitalDetails(
                name="Apollo Hospital"
            )
        )

        # Run validation
        result = self.service.validate_preauth(
            medical_note=medical_note,
            policy_data=self.star_comprehensive,
            procedure_data=self.cataract_procedure,
            form_data=form_data
        )

        # Assertions
        assert result.overall_status == "fail"
        assert result.final_score < 85  # 100 - 20 (policy) - some from medical warnings
        assert result.approval_likelihood == "low"
        assert any("waiting period" in issue.lower() for issue in result.all_issues)

    @patch('src.agents.medical_reviewer.call_llm_with_retry')
    @patch('src.agents.fwa_detector.call_llm_with_retry')
    def test_multiple_issues_combined(self, fwa_mock, medical_mock):
        """Test 4: Multiple issues across all agents - combines correctly"""
        # Mock LLM responses with issues
        medical_mock.return_value = """{
            "assessment": "weak",
            "concerns": [
                {
                    "type": "template_language",
                    "description": "Generic justification language detected",
                    "suggestion": "Provide patient-specific details"
                },
                {
                    "type": "insufficient_justification",
                    "description": "Missing functional impact documentation",
                    "suggestion": "Document specific affected activities"
                }
            ]
        }"""
        fwa_mock.return_value = """{
            "risk_level": "medium",
            "flags": [{
                "category": "cost_inflation",
                "detail": "Cost slightly above typical range",
                "evidence": "₹75,000 vs typical ₹65,000",
                "insurer_action": "Request itemized breakdown"
            }]
        }"""

        # Medical note with issues
        medical_note = MedicalNote(
            patient_info=PatientInfo(
                name="Test Patient",
                age=65,
                gender="Male"
                # Missing contact_number (optional but recommended)
            ),
            diagnosis=DiagnosisInfo(
                primary_diagnosis="Cataract",  # Less specific
                icd_10_code="H25.9"
            ),
            clinical_history=ClinicalHistory(
                chief_complaints="Vision problems"
            ),
            proposed_treatment=ProposedTreatment(
                procedure_name="Cataract Surgery"
                # Missing surgical_approach
            ),
            medical_justification=MedicalJustification(
                why_hospitalization_required="Patient needs surgery",
                why_treatment_necessary="Patient wants better vision"  # Patient preference, not medical necessity
            ),
            hospitalization_details=HospitalizationDetails(
                planned_admission_date="2025-05-10",
                expected_length_of_stay=1
            ),
            cost_breakdown=CostBreakdown(
                room_charges=8000,
                surgeon_fees=25000,
                anesthetist_fees=8000,
                ot_charges=15000,
                investigations=4000,
                medicines_consumables=15000,
                total_estimated_cost=75000  # Higher than typical
            ),
            doctor_details=DoctorDetails(
                name="Dr. Kumar",
                registration_number="MCI123456"
            ),
            hospital_details=HospitalDetails(
                name="Apollo Hospital"
            )
        )

        # Run validation
        result = self.service.validate_preauth(
            medical_note=medical_note,
            policy_data=self.star_comprehensive,
            procedure_data=self.cataract_procedure,
            form_data=self.base_form_data
        )

        # Assertions
        assert result.overall_status in ["warning", "fail"]
        assert result.final_score < 80
        assert len(result.all_issues) >= 3  # Issues from multiple agents
        assert len(result.recommendations) > 0
        assert any("[Medical]" in issue for issue in result.all_issues)
        assert any("[FWA]" in issue for issue in result.all_issues)

    @patch('src.agents.medical_reviewer.call_llm_with_retry')
    @patch('src.agents.fwa_detector.call_llm_with_retry')
    def test_llm_failure_graceful_degradation(self, fwa_mock, medical_mock):
        """Test 5: LLM timeout - graceful degradation, still returns result"""
        # Simulate LLM failures
        medical_mock.side_effect = TimeoutError("LLM request timed out")
        fwa_mock.side_effect = TimeoutError("LLM request timed out")

        medical_note = MedicalNote(
            patient_info=PatientInfo(
                name="Test Patient",
                age=65,
                gender="Male",
                contact_number="9876543210"
            ),
            diagnosis=DiagnosisInfo(
                primary_diagnosis="Senile Cataract",
                icd_10_code="H25.9",
                diagnosis_date="2025-01-15"
            ),
            clinical_history=ClinicalHistory(
                chief_complaints="Vision loss"
            ),
            proposed_treatment=ProposedTreatment(
                procedure_name="Cataract Surgery",
                anesthesia_type="Local"
            ),
            medical_justification=MedicalJustification(
                why_hospitalization_required="Surgical intervention required",
                why_treatment_necessary="Vision impairment"
            ),
            hospitalization_details=HospitalizationDetails(
                planned_admission_date="2025-05-10",
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
                name="Dr. Kumar",
                qualification="MS",
                registration_number="MCI123456"
            ),
            hospital_details=HospitalDetails(
                name="Apollo Hospital"
            )
        )

        # Run validation - should not crash
        result = self.service.validate_preauth(
            medical_note=medical_note,
            policy_data=self.star_comprehensive,
            procedure_data=self.cataract_procedure,
            form_data=self.base_form_data
        )

        # Assertions - should still return a valid result
        assert result is not None
        assert result.overall_status in ["pass", "warning", "fail"]
        assert 0 <= result.final_score <= 100
        assert result.approval_likelihood in ["high", "medium", "low"]
        # Should have used rule-based detection for FWA and graceful degradation for medical


def run_integration_tests():
    """Run all integration tests"""
    print("=" * 60)
    print("PHASE 3 INTEGRATION TESTS")
    print("=" * 60)

    # Run pytest programmatically
    exit_code = pytest.main([__file__, "-v", "--tb=short"])

    print("\n" + "=" * 60)
    if exit_code == 0:
        print("✅ All integration tests passed")
    else:
        print("❌ Some tests failed")
    print("=" * 60)

    return exit_code == 0


if __name__ == "__main__":
    import sys
    success = run_integration_tests()
    sys.exit(0 if success else 1)
