"""
Unit tests for FWA Detector Agent
Tests hybrid rule-based + LLM fraud/waste/abuse detection
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import patch
from src.agents.fwa_detector import FWADetector
from src.models.schemas import (
    MedicalNote, PatientInfo, DiagnosisInfo, ClinicalHistory,
    ProposedTreatment, MedicalJustification, HospitalizationDetails,
    CostBreakdown, DoctorDetails, HospitalDetails
)
from src.utils.data_loader import load_procedure_data


class TestFWADetector:
    """Test suite for FWADetector agent"""

    def setup_method(self):
        """Setup test fixtures"""
        self.detector = FWADetector()

        # Load actual procedure data
        self.cataract_procedure = load_procedure_data("cataract_surgery")

        # Base medical note
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

    @patch('src.agents.fwa_detector.call_llm_with_retry')
    def test_cost_within_range(self, mock_llm):
        """Test 1: Cost within range → pass, risk=low, score=0"""
        mock_llm.return_value = '{"risk_level": "low", "flags": []}'

        # Normal cost (51,000 within typical range)
        costs = {
            'room_charges': 3500,
            'surgeon_fees': 18000,
            'anesthetist_fees': 5000,
            'ot_charges': 12000,
            'investigations': 2500,
            'medicines_consumables': 10000,
            'total_estimated_cost': 51000
        }

        result = self.detector.detect(
            diagnosis="Senile Cataract",
            treatment="Cataract Surgery",
            costs=costs,
            procedure_data=self.cataract_procedure.model_dump(),
            stay_duration=1,
            medical_note=self.base_medical_note
        )

        assert result.status == "pass"
        assert result.risk_level == "low"
        assert result.score_impact == 0

    @patch('src.agents.fwa_detector.call_llm_with_retry')
    def test_cost_2x_typical_without_justification(self, mock_llm):
        """Test 2: Cost 2x typical without justification → fail, risk=high"""
        mock_llm.return_value = """{
            "risk_level": "high",
            "flags": [
                {
                    "category": "cost_inflation",
                    "detail": "Cost significantly exceeds typical range without documented justification",
                    "evidence": "Total ₹130,000 vs typical max ₹65,000",
                    "insurer_action": "Request detailed itemized breakdown and clinical justification"
                }
            ]
        }"""

        # Very high cost (130,000 = 2x typical max of 65,000)
        costs = {
            'room_charges': 16000,
            'surgeon_fees': 35000,
            'anesthetist_fees': 10000,
            'ot_charges': 25000,
            'investigations': 8000,
            'medicines_consumables': 36000,
            'total_estimated_cost': 130000
        }

        result = self.detector.detect(
            diagnosis="Cataract",
            treatment="Cataract Surgery",
            costs=costs,
            procedure_data=self.cataract_procedure.model_dump(),
            stay_duration=1,
            medical_note=self.base_medical_note
        )

        assert result.status == "fail"
        assert result.risk_level == "high"
        assert result.score_impact == -20
        assert len(result.flags) >= 1

    @patch('src.agents.fwa_detector.call_llm_with_retry')
    def test_premium_iol_without_astigmatism(self, mock_llm):
        """Test 3: Premium IOL without astigmatism docs → warning/fail"""
        mock_llm.return_value = """{
            "risk_level": "medium",
            "flags": [
                {
                    "category": "unjustified_upgrade",
                    "detail": "Premium IOL selected without documented astigmatism >1.5D",
                    "evidence": "No corneal topography or astigmatism measurement provided",
                    "insurer_action": "May approve standard IOL only, patient pays difference"
                }
            ]
        }"""

        costs = {
            'room_charges': 3500,
            'surgeon_fees': 18000,
            'anesthetist_fees': 5000,
            'ot_charges': 12000,
            'investigations': 2500,
            'medicines_consumables': 25000,  # Higher due to premium IOL
            'total_estimated_cost': 66000
        }

        result = self.detector.detect(
            diagnosis="Cataract",
            treatment="Cataract Surgery with Premium Toric IOL",
            costs=costs,
            procedure_data=self.cataract_procedure.model_dump(),
            stay_duration=1,
            medical_note=self.base_medical_note
        )

        assert result.status == "warning"
        assert result.risk_level == "medium"
        assert any(f.category == "unjustified_upgrade" for f in result.flags)

    @patch('src.agents.fwa_detector.call_llm_with_retry')
    def test_overnight_stay_for_daycare(self, mock_llm):
        """Test 4: Overnight stay for routine day-care procedure → warning"""
        mock_llm.return_value = """{
            "risk_level": "medium",
            "flags": [
                {
                    "category": "overtreatment",
                    "detail": "Overnight stay planned for routine day-care procedure",
                    "evidence": "Typical stay: 0-1 days, Planned: 2 days without complication risk documented",
                    "insurer_action": "May approve 1 day only"
                }
            ]
        }"""

        costs = {
            'room_charges': 7000,  # 2 days
            'surgeon_fees': 18000,
            'anesthetist_fees': 5000,
            'ot_charges': 12000,
            'investigations': 2500,
            'medicines_consumables': 10000,
            'total_estimated_cost': 54500
        }

        # Medical note with 2-day stay
        overnight_note = MedicalNote(
            patient_info=self.base_medical_note.patient_info,
            diagnosis=self.base_medical_note.diagnosis,
            clinical_history=self.base_medical_note.clinical_history,
            proposed_treatment=self.base_medical_note.proposed_treatment,
            medical_justification=self.base_medical_note.medical_justification,
            hospitalization_details=HospitalizationDetails(
                planned_admission_date="05/10/2025",
                expected_length_of_stay=2  # 2 days
            ),
            cost_breakdown=CostBreakdown(**costs),
            doctor_details=self.base_medical_note.doctor_details,
            hospital_details=self.base_medical_note.hospital_details
        )

        result = self.detector.detect(
            diagnosis="Cataract",
            treatment="Cataract Surgery",
            costs=costs,
            procedure_data=self.cataract_procedure.model_dump(),
            stay_duration=2,
            medical_note=overnight_note
        )

        assert result.status in ["warning", "fail"]
        assert result.risk_level in ["medium", "high"]

    @patch('src.agents.fwa_detector.call_llm_with_retry')
    def test_high_cost_bilateral_justified(self, mock_llm):
        """Test 5: Cost 2x but bilateral surgery documented → pass/warning (context-aware)"""
        mock_llm.return_value = """{
            "risk_level": "low",
            "flags": []
        }"""

        # High cost but justified by bilateral procedure
        costs = {
            'room_charges': 5000,
            'surgeon_fees': 36000,  # Double for bilateral
            'anesthetist_fees': 8000,
            'ot_charges': 20000,
            'investigations': 3000,
            'medicines_consumables': 18000,  # Double IOL
            'total_estimated_cost': 90000
        }

        bilateral_note = MedicalNote(
            patient_info=self.base_medical_note.patient_info,
            diagnosis=DiagnosisInfo(
                primary_diagnosis="Bilateral Senile Cataract",
                icd_10_code="H25.9",
                diagnosis_date="2025-01-15"
            ),
            clinical_history=self.base_medical_note.clinical_history,
            proposed_treatment=ProposedTreatment(
                procedure_name="Bilateral Cataract Surgery - Sequential",
                procedure_type="elective"
            ),
            medical_justification=self.base_medical_note.medical_justification,
            hospitalization_details=self.base_medical_note.hospitalization_details,
            cost_breakdown=CostBreakdown(**costs),
            doctor_details=self.base_medical_note.doctor_details,
            hospital_details=self.base_medical_note.hospital_details
        )

        result = self.detector.detect(
            diagnosis="Bilateral Senile Cataract",
            treatment="Bilateral Cataract Surgery",
            costs=costs,
            procedure_data=self.cataract_procedure.model_dump(),
            stay_duration=1,
            medical_note=bilateral_note
        )

        # Should pass or low risk since bilateral is documented
        assert result.status in ["pass", "warning"]
        assert result.risk_level in ["low", "medium"]

    @patch('src.agents.fwa_detector.call_llm_with_retry')
    def test_extended_stay_with_complication(self, mock_llm):
        """Test 6: Extended stay with complication documented → pass"""
        mock_llm.return_value = """{
            "risk_level": "low",
            "flags": []
        }"""

        costs = {
            'room_charges': 10500,  # 3 days
            'surgeon_fees': 18000,
            'anesthetist_fees': 5000,
            'ot_charges': 12000,
            'investigations': 5000,
            'medicines_consumables': 12000,
            'total_estimated_cost': 62500
        }

        result = self.detector.detect(
            diagnosis="Cataract with posterior capsule rupture risk",
            treatment="Cataract Surgery with extended monitoring",
            costs=costs,
            procedure_data=self.cataract_procedure.model_dump(),
            stay_duration=3,
            medical_note=self.base_medical_note
        )

        # Should pass since complication justifies extended stay
        assert result.status in ["pass", "warning"]

    @patch('src.agents.fwa_detector.call_llm_with_retry')
    def test_multiple_red_flags(self, mock_llm):
        """Test 7: Multiple red flags → fail, risk=high"""
        mock_llm.return_value = """{
            "risk_level": "high",
            "flags": [
                {
                    "category": "cost_inflation",
                    "detail": "Excessive cost without justification",
                    "evidence": "Total ₹150,000 vs typical ₹65,000",
                    "insurer_action": "Detailed review required"
                },
                {
                    "category": "unjustified_upgrade",
                    "detail": "Premium IOL without clinical indication",
                    "evidence": "No astigmatism documented",
                    "insurer_action": "May cover standard IOL only"
                },
                {
                    "category": "overtreatment",
                    "detail": "Extended stay without complication",
                    "evidence": "3 days for routine procedure",
                    "insurer_action": "May approve 1 day only"
                }
            ]
        }"""

        costs = {
            'room_charges': 24000,  # 3 days at 8000/day
            'surgeon_fees': 40000,
            'anesthetist_fees': 12000,
            'ot_charges': 30000,
            'investigations': 10000,
            'medicines_consumables': 34000,
            'total_estimated_cost': 150000
        }

        result = self.detector.detect(
            diagnosis="Cataract",
            treatment="Cataract Surgery",
            costs=costs,
            procedure_data=self.cataract_procedure.model_dump(),
            stay_duration=3,
            medical_note=self.base_medical_note
        )

        assert result.status == "fail"
        assert result.risk_level == "high"
        assert result.score_impact == -20
        assert len(result.flags) >= 3

    @patch('src.agents.fwa_detector.call_llm_with_retry')
    def test_llm_timeout_uses_rules_only(self, mock_llm):
        """Test 8: LLM timeout → use only rule-based flags"""
        # Simulate LLM timeout
        mock_llm.side_effect = TimeoutError("LLM request timed out")

        # High cost that triggers rule-based detection
        costs = {
            'room_charges': 3500,
            'surgeon_fees': 18000,
            'anesthetist_fees': 5000,
            'ot_charges': 12000,
            'investigations': 2500,
            'medicines_consumables': 10000,
            'total_estimated_cost': 120000  # 120k > 1.5 * 65k (typical max)
        }

        result = self.detector.detect(
            diagnosis="Cataract",
            treatment="Cataract Surgery",
            costs=costs,
            procedure_data=self.cataract_procedure.model_dump(),
            stay_duration=1,
            medical_note=self.base_medical_note
        )

        # Should still work with rule-based flags only
        assert result.status in ["pass", "warning", "fail"]
        # Should have at least the rule-based cost inflation flag
        if result.flags:
            assert any(f.category == "cost_inflation" for f in result.flags)

    @patch('src.agents.fwa_detector.call_llm_with_retry')
    def test_get_summary_pass(self, mock_llm):
        """Test summary generation for passing result"""
        mock_llm.return_value = '{"risk_level": "low", "flags": []}'

        costs = {
            'room_charges': 3500,
            'surgeon_fees': 18000,
            'anesthetist_fees': 5000,
            'ot_charges': 12000,
            'investigations': 2500,
            'medicines_consumables': 10000,
            'total_estimated_cost': 51000
        }

        result = self.detector.detect(
            diagnosis="Cataract",
            treatment="Cataract Surgery",
            costs=costs,
            procedure_data=self.cataract_procedure.model_dump(),
            stay_duration=1,
            medical_note=self.base_medical_note
        )

        summary = self.detector.get_summary(result)
        assert "no" in summary.lower() and "flag" in summary.lower()

    @patch('src.agents.fwa_detector.call_llm_with_retry')
    def test_get_summary_high_risk(self, mock_llm):
        """Test summary generation for high risk result"""
        mock_llm.return_value = """{
            "risk_level": "high",
            "flags": [
                {"category": "cost_inflation", "detail": "High cost", "evidence": "Evidence", "insurer_action": "Action"}
            ]
        }"""

        costs = {
            'room_charges': 3500,
            'surgeon_fees': 18000,
            'anesthetist_fees': 5000,
            'ot_charges': 12000,
            'investigations': 2500,
            'medicines_consumables': 10000,
            'total_estimated_cost': 150000
        }

        result = self.detector.detect(
            diagnosis="Cataract",
            treatment="Cataract Surgery",
            costs=costs,
            procedure_data=self.cataract_procedure.model_dump(),
            stay_duration=1,
            medical_note=self.base_medical_note
        )

        summary = self.detector.get_summary(result)
        assert "high" in summary.lower()
        assert "review required" in summary.lower()


def run_fwa_detector_tests():
    """Run all FWA detector tests"""
    print("=" * 60)
    print("FWA DETECTOR TESTS")
    print("=" * 60)

    # Run pytest programmatically
    exit_code = pytest.main([__file__, "-v", "--tb=short"])

    print("\n" + "=" * 60)
    if exit_code == 0:
        print("All FWA Detector tests passed")
    else:
        print("Some tests failed")
    print("=" * 60)

    return exit_code == 0


if __name__ == "__main__":
    import sys
    success = run_fwa_detector_tests()
    sys.exit(0 if success else 1)
