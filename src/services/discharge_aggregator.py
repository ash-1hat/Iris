"""
Discharge Aggregator
Combines outputs from all 3 discharge validation agents

Agents:
- Agent 5: Bill Reconciliation
- Agent 6: Cost Escalation Analyzer
- Agent 8: Medical Guidance Generator
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class DischargeValidationResult:
    """Complete discharge validation result"""

    # Overall metrics
    overall_score: int
    completeness_status: str  # "complete" | "partial" | "incomplete"

    # Agent results
    bill_reconciliation: Dict
    cost_escalation: Dict
    medical_guidance: Dict

    # Aggregated outputs
    bill_comparison_summary: str
    variance_analysis: str
    document_checklist: Dict
    recommendations: list

    # Summary for patient
    patient_summary: str


class DischargeAggregator:
    """
    Aggregates results from all discharge validation agents

    Philosophy:
    - We document WHAT HAPPENED, not whether it's justified
    - We show variance analysis, NOT approval prediction
    - We provide medical guidance, NOT financial promises
    """

    def __init__(self):
        pass

    def aggregate(
        self,
        bill_reconciliation_result: Dict,
        cost_escalation_result: Dict,
        medical_guidance_result: Dict,
        has_discharge_summary: bool = True,
        has_final_bill: bool = True
    ) -> DischargeValidationResult:
        """
        Aggregate all agent results

        Args:
            bill_reconciliation_result: From Agent 5
            cost_escalation_result: From Agent 6
            medical_guidance_result: From Agent 8
            has_discharge_summary: Whether discharge summary PDF was provided
            has_final_bill: Whether final bill PDF was provided

        Returns:
            DischargeValidationResult with all aggregated data
        """

        # Calculate overall score
        overall_score = self._calculate_overall_score(
            bill_reconciliation_result,
            cost_escalation_result,
            medical_guidance_result,
            has_discharge_summary,
            has_final_bill
        )

        # Determine completeness status
        completeness_status = self._determine_completeness_status(
            overall_score,
            has_discharge_summary,
            has_final_bill
        )

        # Generate bill comparison summary
        bill_comparison_summary = self._generate_bill_comparison_summary(
            bill_reconciliation_result
        )

        # Generate variance analysis
        variance_analysis = self._generate_variance_analysis(
            bill_reconciliation_result,
            cost_escalation_result
        )

        # Generate document checklist
        document_checklist = self._generate_document_checklist(
            has_discharge_summary,
            has_final_bill,
            medical_guidance_result
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            bill_reconciliation_result,
            cost_escalation_result,
            medical_guidance_result,
            document_checklist
        )

        # Generate patient summary
        patient_summary = self._generate_patient_summary(
            overall_score,
            completeness_status,
            bill_reconciliation_result,
            cost_escalation_result,
            has_discharge_summary
        )

        return DischargeValidationResult(
            overall_score=overall_score,
            completeness_status=completeness_status,
            bill_reconciliation=bill_reconciliation_result,
            cost_escalation=cost_escalation_result,
            medical_guidance=medical_guidance_result,
            bill_comparison_summary=bill_comparison_summary,
            variance_analysis=variance_analysis,
            document_checklist=document_checklist,
            recommendations=recommendations,
            patient_summary=patient_summary
        )

    def _calculate_overall_score(
        self,
        bill_recon: Dict,
        cost_esc: Dict,
        med_guide: Dict,
        has_discharge: bool,
        has_bill: bool
    ) -> int:
        """
        Calculate overall completeness score

        Base: 100
        Deductions:
        - Missing discharge summary: -20
        - Missing final bill: -20
        - Bill reconciliation score impact: varies
        - Cost escalation score impact: varies
        - Medical guidance score impact: 0 (informational)
        """

        score = 100

        # Document completeness
        if not has_discharge:
            score -= 20
        if not has_bill:
            score -= 20

        # Agent score impacts
        score += bill_recon.get('score_impact', 0)
        score += cost_esc.get('score_impact', 0)
        score += med_guide.get('score_impact', 0)  # Always 0

        # Cap at 0-100
        return max(0, min(100, score))

    def _determine_completeness_status(
        self,
        score: int,
        has_discharge: bool,
        has_bill: bool
    ) -> str:
        """Determine overall completeness status"""

        if not has_discharge or not has_bill:
            return "incomplete"

        if score >= 80:
            return "complete"
        elif score >= 60:
            return "partial"
        else:
            return "incomplete"

    def _generate_bill_comparison_summary(self, bill_recon: Dict) -> str:
        """Generate bill comparison summary table"""

        total_var = bill_recon.get('total_variance', {})
        line_items = bill_recon.get('line_item_comparison', [])

        summary = f"Total Cost Comparison:\n"
        summary += f"  Expected: Rs.{total_var.get('expected', 0):,.2f}\n"
        summary += f"  Actual: Rs.{total_var.get('actual', 0):,.2f}\n"
        summary += f"  Variance: Rs.{total_var.get('difference', 0):+,.2f} ({total_var.get('percentage', 0):+.1f}%)\n\n"

        summary += "Line Item Breakdown:\n"
        for item in line_items:
            if item['difference'] != 0:
                summary += f"  - {item['display_name']}: Rs.{item['expected']:,.2f} to Rs.{item['actual']:,.2f} "
                summary += f"(Rs.{item['difference']:+,.2f})\n"

        return summary

    def _generate_variance_analysis(
        self,
        bill_recon: Dict,
        cost_esc: Dict
    ) -> str:
        """
        Generate variance analysis showing what happened

        IMPORTANT: Shows medical reasons, NOT whether justified
        """

        analysis = ""

        # Overall variance
        status = bill_recon.get('status', 'unknown')
        if status == 'acceptable':
            analysis += "Cost variance is within acceptable range (<=10%).\n\n"
        elif status == 'minor_variance':
            analysis += "Minor cost variance detected (10-25%).\n\n"
        else:
            analysis += "Significant cost variance detected (>25%).\n\n"

        # Medical reasons from discharge summary
        esc_status = cost_esc.get('status', 'unknown')
        explanations = cost_esc.get('variance_explanations', [])

        if esc_status == 'documented' and explanations:
            analysis += "Medical Reasons Documented in Discharge Summary:\n"
            for exp in explanations:
                if exp.get('documented'):
                    analysis += f"  - {exp.get('variance', '').replace('_', ' ').title()}: "
                    analysis += f"{exp.get('medical_reason', 'See discharge summary')}\n"
            analysis += "\n"
        elif esc_status == 'partially_documented':
            analysis += "Some variances have documented medical reasons. Review discharge summary for details.\n\n"
        elif esc_status == 'not_documented':
            analysis += "Cost variances found but medical reasons not clearly documented in discharge summary.\n\n"

        # Stay variance
        stay_var = bill_recon.get('stay_variance', {})
        if stay_var.get('is_extended'):
            analysis += f"Hospital stay extended by {stay_var.get('extra_days')} day(s). "
            analysis += "Check discharge summary for medical reason.\n"

        return analysis

    def _generate_document_checklist(
        self,
        has_discharge: bool,
        has_bill: bool,
        med_guide: Dict
    ) -> Dict:
        """Generate document checklist"""

        checklist = {
            "discharge_summary": {
                "present": has_discharge,
                "status": "Present" if has_discharge else "Missing"
            },
            "final_bill": {
                "present": has_bill,
                "status": "Present" if has_bill else "Missing"
            },
            "medications_documented": {
                "present": len(med_guide.get('medication_schedule', {}).get('detailed_schedule', [])) > 0,
                "count": len(med_guide.get('medication_schedule', {}).get('detailed_schedule', []))
            },
            "follow_up_documented": {
                "present": len(med_guide.get('follow_up_plan', {}).get('appointments', [])) > 0,
                "count": len(med_guide.get('follow_up_plan', {}).get('appointments', []))
            },
            "warning_signs_documented": {
                "present": len(med_guide.get('warning_signs', {}).get('signs', [])) > 0,
                "count": len(med_guide.get('warning_signs', {}).get('signs', []))
            }
        }

        return checklist

    def _generate_recommendations(
        self,
        bill_recon: Dict,
        cost_esc: Dict,
        med_guide: Dict,
        checklist: Dict
    ) -> list:
        """Generate actionable recommendations"""

        recommendations = []

        # Document completeness
        if not checklist['discharge_summary']['present']:
            recommendations.append("Obtain discharge summary from hospital")
        if not checklist['final_bill']['present']:
            recommendations.append("Obtain detailed final bill from hospital")

        # Variance issues
        if bill_recon.get('status') == 'significant_variance':
            if cost_esc.get('status') == 'not_documented':
                recommendations.append("Request hospital to document medical reasons for cost increase in discharge summary")

        # Medical guidance completeness
        if not checklist['medications_documented']['present']:
            recommendations.append("Ensure all discharge medications are documented")
        if not checklist['follow_up_documented']['present']:
            recommendations.append("Confirm follow-up appointment schedule with hospital")

        # If no issues
        if not recommendations:
            recommendations.append("Documentation appears complete. Submit to insurer for their review.")

        return recommendations

    def _generate_patient_summary(
        self,
        score: int,
        status: str,
        bill_recon: Dict,
        cost_esc: Dict,
        has_discharge: bool
    ) -> str:
        """
        Generate plain-language summary for patient

        CRITICAL: NO financial predictions or approval likelihood
        """

        summary = ""

        # Overall status
        if status == "complete":
            summary += "Your discharge documentation appears complete. "
        elif status == "partial":
            summary += "Your discharge documentation is mostly complete but has some gaps. "
        else:
            summary += "Your discharge documentation is incomplete. "

        # Cost variance
        total_var = bill_recon.get('total_variance', {})
        variance_pct = abs(total_var.get('percentage', 0))

        if variance_pct <= 10:
            summary += f"The final bill (Rs.{total_var.get('actual', 0):,.2f}) is close to the pre-authorization estimate (Rs.{total_var.get('expected', 0):,.2f}). "
        else:
            summary += f"The final bill (Rs.{total_var.get('actual', 0):,.2f}) differs from the pre-authorization estimate (Rs.{total_var.get('expected', 0):,.2f}) by Rs.{abs(total_var.get('difference', 0)):,.2f}. "

        # Medical reasons
        if has_discharge:
            esc_status = cost_esc.get('status', '')
            if esc_status == 'documented':
                summary += "Medical reasons for cost differences are documented in your discharge summary. "
            elif esc_status == 'partially_documented':
                summary += "Some medical reasons are documented in your discharge summary. "

        # What to do next
        summary += "\n\nNext Steps:\n"
        summary += "1. Review the bill comparison and variance analysis below\n"
        summary += "2. Check the medical guidance section for your recovery instructions\n"
        summary += "3. Submit all documents to your insurance company for their review\n"
        summary += "\nIMPORTANT: Your insurance company will make the final decision on coverage and payment. "
        summary += "This validation only checks documentation completeness."

        return summary


# Test function
def test_discharge_aggregator():
    """Test the discharge aggregator"""

    aggregator = DischargeAggregator()

    # Sample agent results
    bill_recon_result = {
        "status": "acceptable",
        "total_variance": {
            "expected": 68000,
            "actual": 69500,
            "difference": 1500,
            "percentage": 2.21
        },
        "line_item_comparison": [
            {
                "item": "room_charges",
                "display_name": "Room Charges",
                "expected": 3500,
                "actual": 7000,
                "difference": 3500,
                "percentage": 100.0,
                "severity": "significant"
            },
            {
                "item": "surgeon_fees",
                "display_name": "Surgeon Fees",
                "expected": 18000,
                "actual": 18000,
                "difference": 0,
                "percentage": 0.0,
                "severity": "acceptable"
            }
        ],
        "stay_variance": {
            "expected_days": 1,
            "actual_days": 2,
            "extra_days": 1,
            "is_extended": True
        },
        "score_impact": -6,
        "summary": "Final bill is within acceptable range..."
    }

    cost_esc_result = {
        "status": "documented",
        "variance_explanations": [
            {
                "variance": "room_charges",
                "amount": 3500,
                "documented": True,
                "medical_reason": "Extended stay due to post-op nausea and vomiting",
                "source": "complications"
            }
        ],
        "overall_finding": "All variances have documented medical reasons",
        "score_impact": 0,
        "summary": "All variances explained in discharge summary"
    }

    med_guide_result = {
        "status": "complete",
        "medication_schedule": {
            "summary": "3 medications",
            "detailed_schedule": [
                {"name": "Moxifloxacin", "dosage": "4x daily", "duration": "7 days"}
            ],
            "key_reminders": ["Wash hands before applying"]
        },
        "follow_up_plan": {
            "summary": "3 appointments",
            "appointments": [
                {"timing": "Day 1", "purpose": "Post-op check"}
            ]
        },
        "warning_signs": {
            "signs": ["Sudden vision loss", "Severe pain"]
        },
        "recovery_timeline": "Recovery takes 4-6 weeks",
        "score_impact": 0,
        "summary": "Complete guidance available"
    }

    print("="*80)
    print("TESTING DISCHARGE AGGREGATOR")
    print("="*80)

    result = aggregator.aggregate(
        bill_recon_result,
        cost_esc_result,
        med_guide_result,
        has_discharge_summary=True,
        has_final_bill=True
    )

    print(f"\n[OVERALL SCORE]: {result.overall_score}/100")
    print(f"[COMPLETENESS STATUS]: {result.completeness_status.upper()}")

    print("\n[BILL COMPARISON SUMMARY]")
    print(result.bill_comparison_summary)

    print("[VARIANCE ANALYSIS]")
    print(result.variance_analysis)

    print("[DOCUMENT CHECKLIST]")
    for doc, info in result.document_checklist.items():
        status = "[Y]" if info.get('present', False) else "[N]"
        count_info = f" ({info.get('count', 0)} items)" if 'count' in info else ""
        print(f"  {status} {doc.replace('_', ' ').title()}{count_info}")

    print("\n[RECOMMENDATIONS]")
    for i, rec in enumerate(result.recommendations, 1):
        print(f"  {i}. {rec}")

    print("\n[PATIENT SUMMARY]")
    print(result.patient_summary)

    print("\n" + "="*80)
    print("[OK] Test completed")
    print("="*80)


if __name__ == "__main__":
    test_discharge_aggregator()
