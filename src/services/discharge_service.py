"""
Discharge Service
Orchestrates the complete discharge validation flow

Components:
- PDF Extractors (final bill + discharge summary)
- Agent 5: Bill Reconciliation
- Agent 6: Cost Escalation Analyzer
- Agent 8: Medical Guidance Generator
- Aggregator
"""

import sys
from pathlib import Path
from typing import Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.discharge_pdf_extractor import extract_final_bill, extract_discharge_summary
from src.agents.bill_reconciliation import BillReconciliationAgent
from src.agents.cost_escalation_analyzer import CostEscalationAnalyzer
from src.agents.medical_guidance_generator import MedicalGuidanceGenerator
from src.services.discharge_aggregator import DischargeAggregator
from src.services.claim_storage import ClaimStorageService


class DischargeService:
    """
    Main service for discharge validation

    Orchestrates:
    1. Load pre-auth data (from claim ID or manual input)
    2. Extract PDFs (final bill + discharge summary)
    3. Run 3 agents
    4. Aggregate results
    5. Return complete validation result
    """

    def __init__(self, anthropic_api_key: Optional[str] = None):
        """Initialize service with all agents"""
        self.bill_recon_agent = BillReconciliationAgent()
        self.cost_esc_agent = CostEscalationAnalyzer(anthropic_api_key)
        self.med_guide_agent = MedicalGuidanceGenerator(anthropic_api_key)
        self.aggregator = DischargeAggregator()
        self.claim_storage = ClaimStorageService()

    def validate_discharge_with_claim_id(
        self,
        claim_id: str,
        final_bill_pdf_path: str,
        discharge_summary_pdf_path: str
    ) -> Dict:
        """
        Validate discharge using saved claim ID

        Args:
            claim_id: Claim reference ID from pre-auth (e.g., "CR-20251005-12345")
            final_bill_pdf_path: Path to final hospital bill PDF
            discharge_summary_pdf_path: Path to discharge summary PDF

        Returns:
            DischargeValidationResult as dict
        """

        # Load pre-auth claim data
        claim_data = self.claim_storage.load_claim(claim_id)

        if not claim_data:
            raise ValueError(f"Claim ID {claim_id} not found")

        # Extract expected costs from claim data
        expected_costs = claim_data.get('expected_costs', {})
        expected_stay_days = claim_data.get('procedure_info', {}).get('expected_stay_days', 1)

        # Extract PDFs
        final_bill = extract_final_bill(final_bill_pdf_path, use_llm_fallback=True)
        discharge_summary = extract_discharge_summary(discharge_summary_pdf_path, use_llm=True)

        # Run validation
        return self._run_validation(
            expected_costs,
            expected_stay_days,
            final_bill,
            discharge_summary
        )

    def validate_discharge_manual(
        self,
        expected_costs: Dict,
        expected_stay_days: int,
        final_bill_pdf_path: str,
        discharge_summary_pdf_path: str
    ) -> Dict:
        """
        Validate discharge with manual pre-auth input

        Args:
            expected_costs: Pre-auth cost breakdown
                {
                    "room_charges": 3500,
                    "surgeon_fees": 18000,
                    ...
                    "total_estimated_cost": 52000
                }
            expected_stay_days: Expected hospital stay
            final_bill_pdf_path: Path to final bill PDF
            discharge_summary_pdf_path: Path to discharge summary PDF

        Returns:
            DischargeValidationResult as dict
        """

        # Extract PDFs
        final_bill = extract_final_bill(final_bill_pdf_path, use_llm_fallback=True)
        discharge_summary = extract_discharge_summary(discharge_summary_pdf_path, use_llm=True)

        # Run validation
        return self._run_validation(
            expected_costs,
            expected_stay_days,
            final_bill,
            discharge_summary
        )

    def _run_validation(
        self,
        expected_costs: Dict,
        expected_stay_days: int,
        final_bill: Dict,
        discharge_summary: Dict
    ) -> Dict:
        """
        Run all agents and aggregate results

        Internal method called by both validation modes
        """

        # Get actual stay from discharge summary or bill
        actual_stay_days = discharge_summary.get('days_stayed', final_bill.get('total_days', 0))

        # Agent 5: Bill Reconciliation
        print("Running Agent 5: Bill Reconciliation...")
        bill_recon_result = self.bill_recon_agent.reconcile(
            expected_costs=expected_costs,
            actual_bill=final_bill,
            expected_stay_days=expected_stay_days,
            actual_stay_days=actual_stay_days
        )

        # Agent 6: Cost Escalation Analyzer
        print("Running Agent 6: Cost Escalation Analyzer...")
        cost_esc_result = self.cost_esc_agent.analyze(
            line_item_variances=bill_recon_result['line_item_comparison'],
            discharge_summary=discharge_summary,
            stay_variance=bill_recon_result['stay_variance']
        )

        # Agent 8: Medical Guidance Generator
        print("Running Agent 8: Medical Guidance Generator...")
        med_guide_result = self.med_guide_agent.generate(
            discharge_summary=discharge_summary,
            procedure_type="general"
        )

        # Aggregate results
        print("Aggregating results...")
        aggregated_result = self.aggregator.aggregate(
            bill_reconciliation_result=bill_recon_result,
            cost_escalation_result=cost_esc_result,
            medical_guidance_result=med_guide_result,
            has_discharge_summary=True,
            has_final_bill=True
        )

        # Convert to dict for easy serialization
        return {
            "overall_score": aggregated_result.overall_score,
            "completeness_status": aggregated_result.completeness_status,
            "bill_comparison_summary": aggregated_result.bill_comparison_summary,
            "variance_analysis": aggregated_result.variance_analysis,
            "document_checklist": aggregated_result.document_checklist,
            "recommendations": aggregated_result.recommendations,
            "patient_summary": aggregated_result.patient_summary,

            # Full agent results for detailed display
            "bill_reconciliation": aggregated_result.bill_reconciliation,
            "cost_escalation": aggregated_result.cost_escalation,
            "medical_guidance": aggregated_result.medical_guidance,

            # Add discharge summary and final bill for PDF generator access
            "discharge_summary": discharge_summary,
            "final_bill": final_bill
        }


# Test function
def test_discharge_service():
    """Test the complete discharge service"""

    from dotenv import load_dotenv
    load_dotenv()

    service = DischargeService()

    # Test paths (using our test PDFs)
    project_root = Path(__file__).parent.parent.parent
    bill_pdf = project_root / "final_bill_template.pdf"
    discharge_pdf = project_root / "discharge_summary.pdf"

    # Expected costs (from pre-auth)
    expected_costs = {
        "room_charges": 3500,
        "nursing_charges": 0,
        "surgeon_fees": 18000,
        "anesthetist_fees": 5000,
        "ot_charges": 12000,
        "medicines": 12000,
        "implants": 15000,
        "investigations": 2000,
        "other_charges": 500,
        "total_estimated_cost": 68000
    }

    expected_stay = 1

    print("="*80)
    print("TESTING DISCHARGE SERVICE (FULL FLOW)")
    print("="*80)

    print("\nValidating discharge with manual pre-auth input...")
    print(f"  Bill PDF: {bill_pdf.name}")
    print(f"  Discharge PDF: {discharge_pdf.name}")
    print(f"  Expected Total: Rs.{expected_costs['total_estimated_cost']:,.2f}")
    print(f"  Expected Stay: {expected_stay} day(s)")
    print()

    result = service.validate_discharge_manual(
        expected_costs=expected_costs,
        expected_stay_days=expected_stay,
        final_bill_pdf_path=str(bill_pdf),
        discharge_summary_pdf_path=str(discharge_pdf)
    )

    print("\n" + "="*80)
    print("VALIDATION COMPLETE")
    print("="*80)

    print(f"\n[OVERALL SCORE]: {result['overall_score']}/100")
    print(f"[STATUS]: {result['completeness_status'].upper()}")

    print("\n[BILL COMPARISON]")
    print(result['bill_comparison_summary'])

    print("[VARIANCE ANALYSIS]")
    print(result['variance_analysis'])

    print("[RECOMMENDATIONS]")
    for i, rec in enumerate(result['recommendations'], 1):
        print(f"  {i}. {rec}")

    print("\n[MEDICAL GUIDANCE SUMMARY]")
    med_guide = result['medical_guidance']
    print(f"  Medications: {med_guide['medication_schedule']['summary']}")
    print(f"  Follow-up: {med_guide['follow_up_plan']['summary']}")
    print(f"  Activity Guidelines: {med_guide['activity_guidelines']['summary']}")
    print(f"  Warning Signs: {len(med_guide['warning_signs']['signs'])} items")

    print("\n[PATIENT SUMMARY]")
    print(result['patient_summary'])

    print("\n" + "="*80)
    print("[OK] Full discharge flow test completed")
    print("="*80)


if __name__ == "__main__":
    test_discharge_service()
