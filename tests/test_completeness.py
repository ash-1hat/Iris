"""
Unit tests for Completeness Checker Agent
Tests rule-based validation of required fields and document completeness
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.agents.completeness_checker import CompletenessChecker
from src.models.schemas import (
    MedicalNote, PatientInfo, DiagnosisInfo, ClinicalHistory,
    ProposedTreatment, MedicalJustification, HospitalizationDetails,
    CostBreakdown, DoctorDetails, HospitalDetails
)


class TestCompletenessChecker:
    """Test suite for CompletenessChecker agent"""

    def setup_method(self):
        """Setup test fixtures"""
        self.checker = CompletenessChecker()

        # Complete form data (happy path)
        self.complete_form_data = {
            'policy_number': 'POL123456',
            'policy_start_date': '2023-01-15',
            'sum_insured': 500000,
            'planned_admission_date': '2025-03-20',
            'hospital_name': 'Apollo Hospital',
            'insurer': 'Star Health',
            'policy_type': 'Comprehensive',
            'procedure_id': 'cataract_surgery'
        }

        # Complete medical note (happy path)
        self.complete_medical_note = MedicalNote(
            patient_info=PatientInfo(
                name="John Doe",
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
                chief_complaints="Gradual vision loss in right eye",
                duration_of_symptoms="6 months",
                relevant_medical_history="Diabetes controlled",
                comorbidities=["Type 2 Diabetes"]
            ),
            proposed_treatment=ProposedTreatment(
                procedure_name="Cataract Surgery - Phacoemulsification",
                procedure_type="elective"
            ),
            medical_justification=MedicalJustification(
                why_hospitalization_required="Surgical intervention requires sterile OT environment",
                why_treatment_necessary="Visual impairment affecting daily activities",
                how_treatment_addresses_diagnosis="Phacoemulsification will remove opaque lens",
                expected_outcomes="Improved vision to 6/12 or better"
            ),
            hospitalization_details=HospitalizationDetails(
                planned_admission_date="2025-03-20",
                expected_length_of_stay=1,
                icu_required=False
            ),
            cost_breakdown=CostBreakdown(
                room_charges=5000,
                surgeon_fees=25000,
                anesthetist_fees=5000,
                ot_charges=15000,
                investigations=3000,
                medicines_consumables=7000,
                total_estimated_cost=60000
            ),
            doctor_details=DoctorDetails(
                name="Dr. Sharma",
                qualification="MS Ophthalmology",
                registration_number="MCI12345"
            ),
            hospital_details=HospitalDetails(
                name="Apollo Hospital",
                location="Mumbai",
                type="private"
            )
        )

    def test_all_fields_complete(self):
        """Test 1: All fields present -> pass, score_impact=0"""
        result = self.checker.validate(self.complete_form_data, self.complete_medical_note)

        assert result.status == "pass"
        assert result.score_impact == 0
        assert len(result.issues) == 0

    def test_missing_form_fields(self):
        """Test 2: Missing 3 form fields -> fail, score_impact=-15"""
        incomplete_form = self.complete_form_data.copy()
        del incomplete_form['policy_number']
        del incomplete_form['sum_insured']
        del incomplete_form['hospital_name']

        result = self.checker.validate(incomplete_form, self.complete_medical_note)

        assert result.status == "fail"
        assert result.score_impact == -15  # 3 fields * -5 each
        assert len(result.issues) == 3
        assert any("policy_number" in issue for issue in result.issues)
        assert any("sum_insured" in issue for issue in result.issues)
        assert any("hospital_name" in issue for issue in result.issues)

    def test_empty_form_fields(self):
        """Test empty/None form field values"""
        incomplete_form = self.complete_form_data.copy()
        incomplete_form['policy_number'] = ""
        incomplete_form['sum_insured'] = 0

        result = self.checker.validate(incomplete_form, self.complete_medical_note)

        assert result.status == "fail"
        assert result.score_impact == -10  # 2 fields * -5 each
        assert len(result.issues) == 2
        assert any("policy_number" in issue.lower() for issue in result.issues)
        assert any("sum_insured" in issue.lower() for issue in result.issues)

    def test_missing_medical_note_sections(self):
        """Test 3: Empty medical note -> fail with all section issues"""
        # Create minimal medical note with missing sections
        minimal_note = MedicalNote(
            patient_info=PatientInfo(
                name="", age=0, gender="Male", contact_number=""
            ),
            diagnosis=DiagnosisInfo(
                primary_diagnosis="", icd_10_code="", diagnosis_date=""
            ),
            clinical_history=ClinicalHistory(
                chief_complaints=""
            ),
            proposed_treatment=ProposedTreatment(
                procedure_name="", procedure_type=""
            ),
            medical_justification=MedicalJustification(
                why_hospitalization_required="",
                why_treatment_necessary=""
            ),
            hospitalization_details=HospitalizationDetails(
                planned_admission_date="",
                expected_length_of_stay=0
            ),
            cost_breakdown=CostBreakdown(
                room_charges=0, surgeon_fees=0, anesthetist_fees=0,
                ot_charges=0, investigations=0, medicines_consumables=0,
                total_estimated_cost=0
            ),
            doctor_details=DoctorDetails(
                name="", qualification="", registration_number=""
            ),
            hospital_details=HospitalDetails(
                name="", location="", type=""
            )
        )

        result = self.checker.validate(self.complete_form_data, minimal_note)

        assert result.status == "fail"
        # Should have issues for empty sections + cost breakdown being 0
        assert len(result.issues) > 5
        assert result.score_impact < -20

    def test_missing_cost_breakdown(self):
        """Test 4: Cost breakdown total is zero -> fail, score_impact=-5"""
        note_with_zero_cost = MedicalNote(
            patient_info=self.complete_medical_note.patient_info,
            diagnosis=self.complete_medical_note.diagnosis,
            clinical_history=self.complete_medical_note.clinical_history,
            proposed_treatment=self.complete_medical_note.proposed_treatment,
            medical_justification=self.complete_medical_note.medical_justification,
            hospitalization_details=self.complete_medical_note.hospitalization_details,
            cost_breakdown=CostBreakdown(
                room_charges=0, surgeon_fees=0, anesthetist_fees=0,
                ot_charges=0, investigations=0, medicines_consumables=0,
                total_estimated_cost=0
            ),
            doctor_details=self.complete_medical_note.doctor_details,
            hospital_details=self.complete_medical_note.hospital_details
        )

        result = self.checker.validate(self.complete_form_data, note_with_zero_cost)

        assert result.status == "fail"
        assert any("cost" in issue.lower() for issue in result.issues)
        assert result.score_impact <= -5

    def test_partial_medical_note(self):
        """Test 5: Partial medical note -> fail with specific missing sections"""
        partial_note = MedicalNote(
            patient_info=self.complete_medical_note.patient_info,
            diagnosis=DiagnosisInfo(primary_diagnosis="", icd_10_code="", diagnosis_date=""),
            clinical_history=ClinicalHistory(chief_complaints=""),
            proposed_treatment=self.complete_medical_note.proposed_treatment,
            medical_justification=self.complete_medical_note.medical_justification,
            hospitalization_details=self.complete_medical_note.hospitalization_details,
            cost_breakdown=self.complete_medical_note.cost_breakdown,
            doctor_details=self.complete_medical_note.doctor_details,
            hospital_details=self.complete_medical_note.hospital_details
        )

        result = self.checker.validate(self.complete_form_data, partial_note)

        assert result.status == "fail"
        assert len(result.issues) > 0
        # Check that specific sections are mentioned in issues
        assert any("diagnosis" in issue.lower() for issue in result.issues)
        assert any("clinical_history" in issue.lower() for issue in result.issues)

    def test_cost_breakdown_all_components_zero(self):
        """Test cost breakdown with all components zero but non-zero total"""
        note_with_suspicious_cost = MedicalNote(
            patient_info=self.complete_medical_note.patient_info,
            diagnosis=self.complete_medical_note.diagnosis,
            clinical_history=self.complete_medical_note.clinical_history,
            proposed_treatment=self.complete_medical_note.proposed_treatment,
            medical_justification=self.complete_medical_note.medical_justification,
            hospitalization_details=self.complete_medical_note.hospitalization_details,
            cost_breakdown=CostBreakdown(
                room_charges=0, surgeon_fees=0, anesthetist_fees=0,
                ot_charges=0, investigations=0, medicines_consumables=0,
                total_estimated_cost=50000
            ),
            doctor_details=self.complete_medical_note.doctor_details,
            hospital_details=self.complete_medical_note.hospital_details
        )

        result = self.checker.validate(self.complete_form_data, note_with_suspicious_cost)

        assert result.status == "fail"
        assert any("all cost components are zero" in issue.lower() for issue in result.issues)

    def test_cost_breakdown_negative_values(self):
        """Test cost breakdown with negative values (data entry error)"""
        note_with_negative_cost = MedicalNote(
            patient_info=self.complete_medical_note.patient_info,
            diagnosis=self.complete_medical_note.diagnosis,
            clinical_history=self.complete_medical_note.clinical_history,
            proposed_treatment=self.complete_medical_note.proposed_treatment,
            medical_justification=self.complete_medical_note.medical_justification,
            hospitalization_details=self.complete_medical_note.hospitalization_details,
            cost_breakdown=CostBreakdown(
                room_charges=5000, surgeon_fees=-10000, anesthetist_fees=5000,
                ot_charges=15000, investigations=3000, medicines_consumables=7000,
                total_estimated_cost=25000
            ),
            doctor_details=self.complete_medical_note.doctor_details,
            hospital_details=self.complete_medical_note.hospital_details
        )

        result = self.checker.validate(self.complete_form_data, note_with_negative_cost)

        assert result.status == "fail"
        assert any("negative" in issue.lower() for issue in result.issues)

    def test_cost_breakdown_sum_mismatch(self):
        """Test cost breakdown where sum doesn't match total"""
        note_with_mismatch = MedicalNote(
            patient_info=self.complete_medical_note.patient_info,
            diagnosis=self.complete_medical_note.diagnosis,
            clinical_history=self.complete_medical_note.clinical_history,
            proposed_treatment=self.complete_medical_note.proposed_treatment,
            medical_justification=self.complete_medical_note.medical_justification,
            hospitalization_details=self.complete_medical_note.hospitalization_details,
            cost_breakdown=CostBreakdown(
                room_charges=5000, surgeon_fees=25000, anesthetist_fees=5000,
                ot_charges=15000, investigations=3000, medicines_consumables=7000,
                total_estimated_cost=100000  # Should be 60000
            ),
            doctor_details=self.complete_medical_note.doctor_details,
            hospital_details=self.complete_medical_note.hospital_details
        )

        result = self.checker.validate(self.complete_form_data, note_with_mismatch)

        assert result.status == "fail"
        assert any("doesn't match total" in issue.lower() for issue in result.issues)

    def test_cost_breakdown_within_tolerance(self):
        """Test cost breakdown with rounding difference within 1% tolerance"""
        note_with_rounding = MedicalNote(
            patient_info=self.complete_medical_note.patient_info,
            diagnosis=self.complete_medical_note.diagnosis,
            clinical_history=self.complete_medical_note.clinical_history,
            proposed_treatment=self.complete_medical_note.proposed_treatment,
            medical_justification=self.complete_medical_note.medical_justification,
            hospitalization_details=self.complete_medical_note.hospitalization_details,
            cost_breakdown=CostBreakdown(
                room_charges=5000, surgeon_fees=25000, anesthetist_fees=5000,
                ot_charges=15000, investigations=3000, medicines_consumables=7000,
                total_estimated_cost=60100  # 100 rupee difference (< 1%)
            ),
            doctor_details=self.complete_medical_note.doctor_details,
            hospital_details=self.complete_medical_note.hospital_details
        )

        result = self.checker.validate(self.complete_form_data, note_with_rounding)

        # Should pass - within tolerance
        assert result.status == "pass"
        assert result.score_impact == 0

    def test_get_summary_pass(self):
        """Test summary generation for passing result"""
        result = self.checker.validate(self.complete_form_data, self.complete_medical_note)
        summary = self.checker.get_summary(result)

        assert "complete" in summary.lower()
        assert result.status == "pass"

    def test_get_summary_fail(self):
        """Test summary generation for failing result"""
        incomplete_form = self.complete_form_data.copy()
        del incomplete_form['policy_number']

        result = self.checker.validate(incomplete_form, self.complete_medical_note)
        summary = self.checker.get_summary(result)

        assert "incomplete" in summary.lower() or "missing" in summary.lower()
        assert result.status == "fail"


def run_completeness_tests():
    """Run all completeness checker tests"""
    print("=" * 60)
    print("COMPLETENESS CHECKER TESTS")
    print("=" * 60)

    # Run pytest programmatically
    exit_code = pytest.main([__file__, "-v", "--tb=short"])

    print("\n" + "=" * 60)
    if exit_code == 0:
        print("✓ All Completeness Checker tests passed")
    else:
        print("✗ Some tests failed")
    print("=" * 60)

    return exit_code == 0


if __name__ == "__main__":
    import sys
    success = run_completeness_tests()
    sys.exit(0 if success else 1)
