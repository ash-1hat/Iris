"""
Unit tests for Policy Validator Agent
Tests structured lookup validation against policy rules
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from datetime import datetime, timedelta
from src.agents.policy_validator import PolicyValidator
from src.models.schemas import (
    MedicalNote, PatientInfo, DiagnosisInfo, ClinicalHistory,
    ProposedTreatment, MedicalJustification, HospitalizationDetails,
    CostBreakdown, DoctorDetails, HospitalDetails
)
from src.utils.data_loader import load_policy_data


class TestPolicyValidator:
    """Test suite for PolicyValidator agent"""

    def setup_method(self):
        """Setup test fixtures"""
        self.validator = PolicyValidator()

        # Load actual policy data
        self.star_policy = load_policy_data("Star Health", "Comprehensive")

        # Base form data
        self.base_form_data = {
            'policy_number': 'STAR/COMP/2021/123456',
            'sum_insured': 500000,
            'previous_claims_amount': 0,
            'insurer': 'Star Health',
            'policy_type': 'Comprehensive',
            'procedure_id': 'cataract_surgery',
            'hospital_name': 'Apollo Hospital',
        }

        # Base medical note with cost breakdown
        self.base_medical_note = MedicalNote(
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
                procedure_type="elective"
            ),
            medical_justification=MedicalJustification(
                why_hospitalization_required="Surgical intervention required",
                why_treatment_necessary="Vision impairment"
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

    def test_all_checks_pass(self):
        """Test 1: All policy checks pass - cataract surgery 25 months after policy start"""
        # Policy started 25 months ago (waiting period: 24 months for cataract)
        policy_start = datetime.now() - timedelta(days=25 * 30)
        admission_date = datetime.now() + timedelta(days=7)

        form_data = self.base_form_data.copy()
        form_data['policy_start_date'] = policy_start.strftime('%d/%m/%Y')
        form_data['planned_admission_date'] = admission_date.strftime('%d/%m/%Y')

        result = self.validator.validate(
            self.star_policy,
            'cataract_surgery',
            form_data,
            self.base_medical_note
        )

        assert result.status == "pass"
        assert result.score_impact == 0
        assert len(result.violations) == 0

    def test_waiting_period_not_met(self):
        """Test 2: Cataract surgery 12 months after policy start - FAIL (waiting period 24 months)"""
        # Policy started 12 months ago
        policy_start = datetime.now() - timedelta(days=12 * 30)
        admission_date = datetime.now() + timedelta(days=7)

        form_data = self.base_form_data.copy()
        form_data['policy_start_date'] = policy_start.strftime('%d/%m/%Y')
        form_data['planned_admission_date'] = admission_date.strftime('%d/%m/%Y')

        result = self.validator.validate(
            self.star_policy,
            'cataract_surgery',
            form_data,
            self.base_medical_note
        )

        assert result.status == "fail"
        assert result.score_impact == -20  # Critical violation
        assert any(v.rule == 'procedure_waiting_period' for v in result.violations)
        assert any(v.severity == 'critical' for v in result.violations)

    def test_admission_before_policy_start(self):
        """Test 3: Admission date before policy start - FAIL (critical)"""
        # Policy starts in future
        policy_start = datetime.now() + timedelta(days=30)
        admission_date = datetime.now() + timedelta(days=7)

        form_data = self.base_form_data.copy()
        form_data['policy_start_date'] = policy_start.strftime('%d/%m/%Y')
        form_data['planned_admission_date'] = admission_date.strftime('%d/%m/%Y')

        result = self.validator.validate(
            self.star_policy,
            'cataract_surgery',
            form_data,
            self.base_medical_note
        )

        assert result.status == "fail"
        assert any(v.rule == 'policy_active' for v in result.violations)
        assert any(v.severity == 'critical' for v in result.violations)

    def test_cost_exceeds_sum_insured(self):
        """Test 4: Total cost > sum insured - WARNING"""
        policy_start = datetime.now() - timedelta(days=36 * 30)
        admission_date = datetime.now() + timedelta(days=7)

        form_data = self.base_form_data.copy()
        form_data['policy_start_date'] = policy_start.strftime('%d/%m/%Y')
        form_data['planned_admission_date'] = admission_date.strftime('%d/%m/%Y')
        form_data['sum_insured'] = 40000  # Less than total cost of 51,000

        result = self.validator.validate(
            self.star_policy,
            'cataract_surgery',
            form_data,
            self.base_medical_note
        )

        assert result.status == "warning"
        assert result.score_impact == -10  # Warning violation
        assert any(v.rule == 'sum_insured' for v in result.violations)
        assert any(v.severity == 'warning' for v in result.violations)

    def test_cost_exceeds_available_si_after_claims(self):
        """Test 5: Total cost > (sum insured - previous claims) - WARNING"""
        policy_start = datetime.now() - timedelta(days=36 * 30)
        admission_date = datetime.now() + timedelta(days=7)

        form_data = self.base_form_data.copy()
        form_data['policy_start_date'] = policy_start.strftime('%d/%m/%Y')
        form_data['planned_admission_date'] = admission_date.strftime('%d/%m/%Y')
        form_data['sum_insured'] = 500000
        form_data['previous_claims_amount'] = 460000  # Available: 40,000, Cost: 51,000

        result = self.validator.validate(
            self.star_policy,
            'cataract_surgery',
            form_data,
            self.base_medical_note
        )

        assert result.status == "warning"
        assert any(v.rule == 'sum_insured' for v in result.violations)
        assert any("previous claims" in v.explanation.lower() for v in result.violations if v.rule == 'sum_insured')

    def test_room_rent_exceeds_limit(self):
        """Test 6: Room rent exceeds policy limit - WARNING"""
        policy_start = datetime.now() - timedelta(days=36 * 30)
        admission_date = datetime.now() + timedelta(days=7)

        form_data = self.base_form_data.copy()
        form_data['policy_start_date'] = policy_start.strftime('%d/%m/%Y')
        form_data['planned_admission_date'] = admission_date.strftime('%d/%m/%Y')

        # Create medical note with high room charges
        # For 500k SI, Star Health limit is 5000/day
        high_room_note = MedicalNote(
            patient_info=self.base_medical_note.patient_info,
            diagnosis=self.base_medical_note.diagnosis,
            clinical_history=self.base_medical_note.clinical_history,
            proposed_treatment=self.base_medical_note.proposed_treatment,
            medical_justification=self.base_medical_note.medical_justification,
            hospitalization_details=HospitalizationDetails(
                planned_admission_date="05/10/2025",
                expected_length_of_stay=1
            ),
            cost_breakdown=CostBreakdown(
                room_charges=8000,  # 8000/day exceeds 5000/day limit
                surgeon_fees=18000,
                anesthetist_fees=5000,
                ot_charges=12000,
                investigations=2500,
                medicines_consumables=10000,
                total_estimated_cost=55500
            ),
            doctor_details=self.base_medical_note.doctor_details,
            hospital_details=self.base_medical_note.hospital_details
        )

        result = self.validator.validate(
            self.star_policy,
            'cataract_surgery',
            form_data,
            high_room_note
        )

        assert result.status == "warning"
        assert any(v.rule == 'room_rent_limit' for v in result.violations)
        assert any("proportionate deduction" in v.suggestion.lower() for v in result.violations)

    def test_excluded_procedure(self):
        """Test 7: Excluded procedure - PASS (procedure not in exclusions)"""
        policy_start = datetime.now() - timedelta(days=36 * 30)
        admission_date = datetime.now() + timedelta(days=7)

        form_data = self.base_form_data.copy()
        form_data['policy_start_date'] = policy_start.strftime('%d/%m/%Y')
        form_data['planned_admission_date'] = admission_date.strftime('%d/%m/%Y')

        # Note: The actual exclusions in policy are descriptive phrases,
        # not procedure_ids. So most medical procedures will pass this check.
        # This test verifies the exclusion check doesn't throw errors
        result = self.validator.validate(
            self.star_policy,
            'cataract_surgery',  # Valid procedure
            form_data,
            self.base_medical_note
        )

        # Should pass (not excluded)
        assert result.status == "pass"

    def test_initial_waiting_period_not_met(self):
        """Test 8: Initial 30-day waiting period not met - FAIL (critical)"""
        # Policy started 20 days ago (initial waiting: 30 days)
        policy_start = datetime.now() - timedelta(days=20)
        admission_date = datetime.now() + timedelta(days=2)

        form_data = self.base_form_data.copy()
        form_data['policy_start_date'] = policy_start.strftime('%d/%m/%Y')
        form_data['planned_admission_date'] = admission_date.strftime('%d/%m/%Y')

        result = self.validator.validate(
            self.star_policy,
            'appendectomy',  # Emergency procedure, but still subject to initial waiting
            form_data,
            self.base_medical_note
        )

        assert result.status == "fail"
        assert any(v.rule == 'initial_waiting_period' for v in result.violations)
        assert any(v.severity == 'critical' for v in result.violations)

    def test_multiple_violations(self):
        """Test 9: Multiple violations - correct cumulative score"""
        # Policy started 20 days ago
        policy_start = datetime.now() - timedelta(days=20)
        admission_date = datetime.now() + timedelta(days=2)

        form_data = self.base_form_data.copy()
        form_data['policy_start_date'] = policy_start.strftime('%d/%m/%Y')
        form_data['planned_admission_date'] = admission_date.strftime('%d/%m/%Y')
        form_data['sum_insured'] = 40000  # Cost exceeds SI

        result = self.validator.validate(
            self.star_policy,
            'cataract_surgery',
            form_data,
            self.base_medical_note
        )

        assert result.status == "fail"
        # Should have violations for: initial waiting period (critical -20),
        # procedure waiting period (critical -20), sum insured (warning -10)
        assert len(result.violations) >= 2
        assert result.score_impact <= -30

    def test_barely_meets_waiting_period(self):
        """Test 10: Waiting period barely met (exactly 24 months) - PASS"""
        # Policy started exactly 24 months ago (using exact month arithmetic)
        admission_date = datetime.now()
        # Calculate 24 months back properly
        policy_start = admission_date.replace(year=admission_date.year - 2)  # 24 months = 2 years

        form_data = self.base_form_data.copy()
        form_data['policy_start_date'] = policy_start.strftime('%d/%m/%Y')
        form_data['planned_admission_date'] = admission_date.strftime('%d/%m/%Y')

        result = self.validator.validate(
            self.star_policy,
            'cataract_surgery',
            form_data,
            self.base_medical_note
        )

        # Should pass (24 months is the exact requirement)
        assert result.status == "pass"
        assert result.score_impact == 0

    def test_date_format_yyyy_mm_dd(self):
        """Test date parsing with YYYY-MM-DD format"""
        policy_start = datetime.now() - timedelta(days=36 * 30)
        admission_date = datetime.now() + timedelta(days=7)

        form_data = self.base_form_data.copy()
        form_data['policy_start_date'] = policy_start.strftime('%Y-%m-%d')  # YYYY-MM-DD
        form_data['planned_admission_date'] = admission_date.strftime('%Y-%m-%d')

        result = self.validator.validate(
            self.star_policy,
            'cataract_surgery',
            form_data,
            self.base_medical_note
        )

        assert result.status == "pass"
        assert result.score_impact == 0

    def test_get_summary_pass(self):
        """Test summary generation for passing result"""
        policy_start = datetime.now() - timedelta(days=36 * 30)
        admission_date = datetime.now() + timedelta(days=7)

        form_data = self.base_form_data.copy()
        form_data['policy_start_date'] = policy_start.strftime('%d/%m/%Y')
        form_data['planned_admission_date'] = admission_date.strftime('%d/%m/%Y')

        result = self.validator.validate(
            self.star_policy,
            'cataract_surgery',
            form_data,
            self.base_medical_note
        )

        summary = self.validator.get_summary(result)
        assert "requirements met" in summary.lower()

    def test_get_summary_fail(self):
        """Test summary generation for failing result"""
        policy_start = datetime.now() - timedelta(days=12 * 30)
        admission_date = datetime.now() + timedelta(days=7)

        form_data = self.base_form_data.copy()
        form_data['policy_start_date'] = policy_start.strftime('%d/%m/%Y')
        form_data['planned_admission_date'] = admission_date.strftime('%d/%m/%Y')

        result = self.validator.validate(
            self.star_policy,
            'cataract_surgery',
            form_data,
            self.base_medical_note
        )

        summary = self.validator.get_summary(result)
        assert "critical" in summary.lower()


def run_policy_validator_tests():
    """Run all policy validator tests"""
    print("=" * 60)
    print("POLICY VALIDATOR TESTS")
    print("=" * 60)

    # Run pytest programmatically
    exit_code = pytest.main([__file__, "-v", "--tb=short"])

    print("\n" + "=" * 60)
    if exit_code == 0:
        print("All Policy Validator tests passed")
    else:
        print("Some tests failed")
    print("=" * 60)

    return exit_code == 0


if __name__ == "__main__":
    import sys
    success = run_policy_validator_tests()
    sys.exit(0 if success else 1)
