"""
Agent 6: Cost Escalation Analyzer (LLM)
Analyzes discharge summary to find medical reasons for cost variances

For each cost variance, checks:
- Is there a medical reason documented in discharge summary?
- What was the complication/issue?
- Was it documented contemporaneously?

Philosophy: We document "what happened", NOT "was it justified"
"""

from typing import Dict, List, Optional
import os
from anthropic import Anthropic


class CostEscalationAnalyzer:
    """
    LLM-powered analyzer to find medical reasons for cost variances

    Uses discharge summary to explain why costs differed from pre-auth estimate
    """

    def __init__(self, anthropic_api_key: Optional[str] = None):
        """Initialize with Anthropic API key"""
        if anthropic_api_key is None:
            anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')

        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.client = Anthropic(api_key=anthropic_api_key)
        self.model = "claude-sonnet-4-20250514"

    def analyze(
        self,
        line_item_variances: List[Dict],
        discharge_summary: Dict,
        stay_variance: Dict
    ) -> Dict:
        """
        Analyze cost variances using discharge summary

        Args:
            line_item_variances: From bill reconciliation agent
                [
                    {
                        "item": "room_charges",
                        "display_name": "Room Charges",
                        "expected": 3500,
                        "actual": 7000,
                        "difference": 3500,
                        "percentage": 100.0,
                        "severity": "significant"
                    },
                    ...
                ]

            discharge_summary: Extracted discharge summary data
                {
                    "complications": "Post-operative nausea and vomiting...",
                    "postop_course": "IMMEDIATE POST-OPERATIVE PERIOD...",
                    "medications": [...],
                    "days_stayed": 2,
                    ...
                }

            stay_variance: From bill reconciliation
                {
                    "expected_days": 1,
                    "actual_days": 2,
                    "extra_days": 1,
                    "is_extended": True
                }

        Returns:
            {
                "status": "documented" | "partially_documented" | "not_documented",
                "variance_explanations": [
                    {
                        "variance": "room_charges",
                        "amount": 3500,
                        "documented": True,
                        "medical_reason": "Extended stay due to post-op nausea...",
                        "source": "complications section",
                        "contemporaneous": True
                    },
                    ...
                ],
                "overall_finding": "...",
                "score_impact": -5,
                "summary": "..."
            }
        """

        # Filter only significant variances
        significant_variances = [
            v for v in line_item_variances
            if v['severity'] in ['significant', 'minor'] and abs(v['difference']) > 100
        ]

        if not significant_variances:
            return {
                "status": "no_significant_variance",
                "variance_explanations": [],
                "overall_finding": "No significant cost variances to analyze.",
                "score_impact": 0,
                "summary": "All costs are within expected range."
            }

        # Build LLM prompt
        prompt = self._build_prompt(significant_variances, discharge_summary, stay_variance)

        # Call LLM
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            analysis_text = response.content[0].text

            # Parse LLM response
            result = self._parse_llm_response(
                analysis_text,
                significant_variances,
                stay_variance
            )

            return result

        except Exception as e:
            return {
                "status": "error",
                "variance_explanations": [],
                "overall_finding": f"Error analyzing variances: {str(e)}",
                "score_impact": 0,
                "summary": "Could not complete variance analysis due to error."
            }

    def _build_prompt(
        self,
        variances: List[Dict],
        discharge_summary: Dict,
        stay_variance: Dict
    ) -> str:
        """Build LLM prompt for variance analysis"""

        # Extract key sections from discharge summary
        complications = discharge_summary.get('complications', 'Not documented')
        postop_course = discharge_summary.get('postop_course', 'Not documented')
        medications = discharge_summary.get('medications', [])
        discharge_condition = discharge_summary.get('discharge_condition', 'Not documented')

        # Build variance list
        variance_list = "\n".join([
            f"- {v['display_name']}: Expected Rs.{v['expected']:,.2f}, "
            f"Actual Rs.{v['actual']:,.2f}, "
            f"Difference: Rs.{v['difference']:+,.2f} ({v['percentage']:+.1f}%)"
            for v in variances
        ])

        # Stay variance
        stay_info = ""
        if stay_variance.get('is_extended'):
            stay_info = f"\nHospital stay was extended by {stay_variance['extra_days']} day(s) from planned {stay_variance['expected_days']} day(s)."

        prompt = f"""You are analyzing cost variances between pre-authorization estimate and actual discharge bill.

COST VARIANCES FOUND:
{variance_list}
{stay_info}

DISCHARGE SUMMARY SECTIONS:

COMPLICATIONS:
{complications}

POST-OPERATIVE COURSE:
{postop_course[:1000]}...

MEDICATIONS PRESCRIBED:
{len(medications)} medications prescribed

DISCHARGE CONDITION:
{discharge_condition[:500]}...

TASK:
For each cost variance, determine:
1. Is there a medical reason documented in the discharge summary?
2. What was the reason (complication, extended stay, additional treatment)?
3. Is it mentioned in complications, post-op course, or medications?

IMPORTANT RULES:
- Only state WHAT HAPPENED, not whether it was justified or will be approved
- Look for specific medical reasons (nausea, infection, observation needed, etc.)
- Extended hospital stay should have a reason in post-op course or complications
- Additional medications should be explained by complications or conditions
- Mark as "documented" if medical reason is explicitly stated
- Mark as "not documented" if no medical reason is found

OUTPUT FORMAT (return as plain text, one variance per line):

VARIANCE: <variance_name>
AMOUNT: <difference_amount>
DOCUMENTED: Yes/No
REASON: <medical reason from discharge summary, or "Not documented">
SOURCE: <which section: complications/postop_course/medications/not found>

---

Example:
VARIANCE: room_charges
AMOUNT: +3500
DOCUMENTED: Yes
REASON: Patient experienced post-operative nausea and vomiting. Kept under observation for 24 additional hours as precautionary measure.
SOURCE: complications, postop_course

Begin analysis:
"""

        return prompt

    def _parse_llm_response(
        self,
        response_text: str,
        variances: List[Dict],
        stay_variance: Dict
    ) -> Dict:
        """Parse LLM response into structured format"""

        explanations = []
        lines = response_text.strip().split('\n')

        current_variance = {}
        for line in lines:
            line = line.strip()

            if line.startswith('VARIANCE:'):
                # Save previous variance if exists
                if current_variance:
                    explanations.append(current_variance)
                # Start new variance
                current_variance = {
                    "variance": line.split(':', 1)[1].strip(),
                    "documented": False,
                    "medical_reason": "",
                    "source": "",
                    "amount": 0
                }

            elif line.startswith('AMOUNT:') and current_variance:
                amount_str = line.split(':', 1)[1].strip()
                # Extract number from string like "+3500" or "Rs.3500"
                import re
                match = re.search(r'[+-]?\d+', amount_str.replace(',', ''))
                if match:
                    current_variance["amount"] = float(match.group())

            elif line.startswith('DOCUMENTED:') and current_variance:
                doc_value = line.split(':', 1)[1].strip().lower()
                current_variance["documented"] = doc_value.startswith('y')

            elif line.startswith('REASON:') and current_variance:
                current_variance["medical_reason"] = line.split(':', 1)[1].strip()

            elif line.startswith('SOURCE:') and current_variance:
                current_variance["source"] = line.split(':', 1)[1].strip()

        # Add last variance
        if current_variance:
            explanations.append(current_variance)

        # Calculate overall status
        documented_count = sum(1 for e in explanations if e.get('documented', False))
        total_count = len(explanations)

        if total_count == 0:
            status = "no_significant_variance"
        elif documented_count == total_count:
            status = "documented"
        elif documented_count > 0:
            status = "partially_documented"
        else:
            status = "not_documented"

        # Calculate score impact
        score_impact = self._calculate_score_impact(status, documented_count, total_count)

        # Generate summary
        summary = self._generate_summary(status, documented_count, total_count, stay_variance)

        # Overall finding
        overall_finding = f"{documented_count} out of {total_count} significant cost variances have documented medical reasons in discharge summary."

        return {
            "status": status,
            "variance_explanations": explanations,
            "overall_finding": overall_finding,
            "score_impact": score_impact,
            "summary": summary
        }

    def _calculate_score_impact(self, status: str, documented: int, total: int) -> int:
        """
        Calculate score impact

        Deductions:
        - All documented: 0
        - Partially documented: -5
        - Not documented: -10
        """
        if status == "documented" or status == "no_significant_variance":
            return 0
        elif status == "partially_documented":
            return -5
        else:
            return -10

    def _generate_summary(
        self,
        status: str,
        documented: int,
        total: int,
        stay_variance: Dict
    ) -> str:
        """Generate human-readable summary"""

        if status == "no_significant_variance":
            return "No significant cost variances to analyze."

        if status == "documented":
            summary = f"All {total} significant cost variance(s) have documented medical reasons in discharge summary. "
        elif status == "partially_documented":
            summary = f"{documented} out of {total} cost variance(s) have documented medical reasons. "
        else:
            summary = f"Cost variances found but medical reasons not documented in discharge summary. "

        if stay_variance.get('is_extended'):
            summary += f"Extended hospital stay of {stay_variance['extra_days']} day(s) "
            if status == "documented":
                summary += "is explained in discharge summary."
            else:
                summary += "should be verified against discharge summary."

        return summary


# Test function
def test_cost_escalation_analyzer():
    """Test the cost escalation analyzer"""

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Check for API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("[ERROR] ANTHROPIC_API_KEY not set. Skipping LLM test.")
        return

    agent = CostEscalationAnalyzer()

    # Sample variances from bill reconciliation
    variances = [
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
            "item": "medicines",
            "display_name": "Medicines",
            "expected": 12000,
            "actual": 17000,
            "difference": 5000,
            "percentage": 41.7,
            "severity": "significant"
        }
    ]

    # Sample discharge summary
    discharge_summary = {
        "complications": "Post-operative nausea and vomiting (PONV) on evening of surgery day (05/10/2025). Managed successfully with IV antiemetic (Ondansetron 4mg). No recurrence after initial treatment. This necessitated extended hospital stay of one additional day for observation.",
        "postop_course": "IMMEDIATE POST-OPERATIVE PERIOD (Day 0 - 05/10/2025): Patient shifted to recovery room. Vital signs stable. Patient developed nausea and two episodes of vomiting at 8:00 PM (12 hours post-surgery). Administered Ondansetron 4mg IV with good response. Patient kept under observation overnight as precautionary measure. POST-OPERATIVE DAY 1 (06/10/2025): Morning review: Patient comfortable, nausea completely resolved. Decision made to observe for additional 24 hours to ensure no recurrence.",
        "medications": [
            {"name": "Moxifloxacin 0.5% Eye Drops", "dosage": "4 times daily", "duration": "7 days"},
            {"name": "Ondansetron 4mg IV", "dosage": "Single dose", "duration": "As needed"}
        ],
        "days_stayed": 2
    }

    stay_variance = {
        "expected_days": 1,
        "actual_days": 2,
        "extra_days": 1,
        "is_extended": True
    }

    print("="*80)
    print("TESTING COST ESCALATION ANALYZER (LLM)")
    print("="*80)

    result = agent.analyze(variances, discharge_summary, stay_variance)

    print("\n[STATUS]:", result['status'].upper())
    print("[SCORE IMPACT]:", result['score_impact'])

    print("\n[OVERALL FINDING]")
    print(result['overall_finding'])

    print("\n[VARIANCE EXPLANATIONS]")
    for i, explanation in enumerate(result['variance_explanations'], 1):
        print(f"\n{i}. {explanation.get('variance', 'Unknown').replace('_', ' ').title()}")
        print(f"   Amount: Rs.{abs(explanation.get('amount', 0)):,.2f}")
        print(f"   Documented: {'Yes' if explanation.get('documented') else 'No'}")
        print(f"   Reason: {explanation.get('medical_reason', 'Not found')}")
        print(f"   Source: {explanation.get('source', 'N/A')}")

    print("\n[SUMMARY]")
    print(result['summary'])

    print("\n" + "="*80)
    print("[OK] Test completed")
    print("="*80)


if __name__ == "__main__":
    test_cost_escalation_analyzer()
