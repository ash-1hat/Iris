"""
Agent 5: Bill Reconciliation
Rule-based comparison of pre-authorization estimates vs actual discharge bill

Compares:
- Total cost variance (expected vs actual)
- Line-item comparison (room, surgeon, OT, medicines, etc.)
- Stay duration (expected vs actual days)
- Severity classification (acceptable/minor/significant)
"""

from typing import Dict, List, Optional
from datetime import datetime


class BillReconciliationAgent:
    """
    Compares pre-authorization estimates with actual discharge bill

    Philosophy:
    - We document variances, we do NOT judge if justified
    - We calculate differences objectively
    - We classify severity based on percentage thresholds
    - We do NOT predict if insurer will approve
    """

    def __init__(self):
        # Variance thresholds for severity classification
        self.ACCEPTABLE_THRESHOLD = 0.10  # ≤10% variance = acceptable
        self.MINOR_THRESHOLD = 0.25       # ≤25% variance = minor
        # >25% = significant

    def reconcile(
        self,
        expected_costs: Dict,
        actual_bill: Dict,
        expected_stay_days: int,
        actual_stay_days: int
    ) -> Dict:
        """
        Main reconciliation function

        Args:
            expected_costs: Pre-auth cost breakdown
                {
                    "room_charges": 3500,
                    "surgeon_fees": 18000,
                    "ot_charges": 12000,
                    "medicines": 15000,
                    "total_estimated_cost": 52000
                }

            actual_bill: Discharge bill breakdown (from extractor)
                {
                    "itemized_costs": {
                        "room_charges": 7000,
                        "surgeon_fees": 18000,
                        ...
                    },
                    "total_bill_amount": 79500,
                    "net_payable_amount": 80975,
                    ...
                }

            expected_stay_days: From pre-auth (e.g., 1)
            actual_stay_days: From discharge bill (e.g., 2)

        Returns:
            {
                "status": "acceptable" | "minor_variance" | "significant_variance",
                "total_variance": {
                    "expected": 52000,
                    "actual": 79500,
                    "difference": 27500,
                    "percentage": 52.88
                },
                "line_item_comparison": [
                    {
                        "item": "room_charges",
                        "expected": 3500,
                        "actual": 7000,
                        "difference": 3500,
                        "percentage": 100.0,
                        "severity": "significant"
                    },
                    ...
                ],
                "stay_variance": {
                    "expected_days": 1,
                    "actual_days": 2,
                    "extra_days": 1
                },
                "score_impact": -20,  # Based on severity
                "summary": "..."
            }
        """

        # Extract actual itemized costs from bill
        actual_itemized = actual_bill.get('itemized_costs', {})
        actual_total = actual_bill.get('total_bill_amount', 0)

        # Get expected total
        expected_total = expected_costs.get('total_estimated_cost', 0)

        # Calculate total variance
        total_variance = self._calculate_total_variance(expected_total, actual_total)

        # Line-by-line comparison
        line_item_comparison = self._compare_line_items(expected_costs, actual_itemized)

        # Stay variance
        stay_variance = self._calculate_stay_variance(expected_stay_days, actual_stay_days)

        # Determine overall severity
        overall_severity = self._determine_severity(total_variance['percentage'])

        # Calculate score impact
        score_impact = self._calculate_score_impact(overall_severity, line_item_comparison)

        # Generate summary
        summary = self._generate_summary(
            total_variance,
            stay_variance,
            overall_severity,
            len([item for item in line_item_comparison if item['difference'] != 0])
        )

        return {
            "status": overall_severity,
            "total_variance": total_variance,
            "line_item_comparison": line_item_comparison,
            "stay_variance": stay_variance,
            "score_impact": score_impact,
            "summary": summary
        }

    def _calculate_total_variance(self, expected: float, actual: float) -> Dict:
        """Calculate total cost variance"""
        difference = actual - expected

        if expected > 0:
            percentage = (difference / expected) * 100
        else:
            percentage = 0.0

        return {
            "expected": expected,
            "actual": actual,
            "difference": difference,
            "percentage": round(percentage, 2)
        }

    def _compare_line_items(self, expected: Dict, actual: Dict) -> List[Dict]:
        """
        Compare each cost line item

        Maps both expected and actual to standard categories:
        - room_charges
        - nursing_charges
        - surgeon_fees
        - anesthetist_fees
        - ot_charges
        - ot_consumables
        - medicines
        - implants
        - investigations
        - other_charges
        """

        # Standard line item categories
        categories = [
            "room_charges",
            "nursing_charges",
            "surgeon_fees",
            "anesthetist_fees",
            "ot_charges",
            "ot_consumables",
            "medicines",
            "medicines_consumables",  # Alternative name
            "implants",
            "investigations",
            "other_charges"
        ]

        comparison = []

        # Track which categories we've seen
        seen_categories = set()

        for category in categories:
            expected_amount = expected.get(category, 0)
            actual_amount = actual.get(category, 0)

            # Handle alternative naming (medicines vs medicines_consumables)
            if category == "medicines_consumables" and "medicines" in seen_categories:
                continue
            if category == "medicines" and actual_amount == 0:
                actual_amount = actual.get("medicines_consumables", 0)

            # Skip if both are zero
            if expected_amount == 0 and actual_amount == 0:
                continue

            difference = actual_amount - expected_amount

            if expected_amount > 0:
                percentage = (abs(difference) / expected_amount) * 100
            else:
                percentage = 0.0 if actual_amount == 0 else 999.9  # New item not in pre-auth

            # Determine severity for this line item
            if abs(percentage) <= self.ACCEPTABLE_THRESHOLD * 100:
                severity = "acceptable"
            elif abs(percentage) <= self.MINOR_THRESHOLD * 100:
                severity = "minor"
            else:
                severity = "significant"

            comparison.append({
                "item": category,
                "display_name": category.replace('_', ' ').title(),
                "expected": expected_amount,
                "actual": actual_amount,
                "difference": difference,
                "percentage": round(percentage, 2),
                "severity": severity
            })

            seen_categories.add(category)

        return comparison

    def _calculate_stay_variance(self, expected_days: int, actual_days: int) -> Dict:
        """Calculate hospital stay variance"""
        extra_days = actual_days - expected_days

        return {
            "expected_days": expected_days,
            "actual_days": actual_days,
            "extra_days": extra_days,
            "is_extended": extra_days > 0
        }

    def _determine_severity(self, variance_percentage: float) -> str:
        """
        Classify overall variance severity

        Thresholds:
        - ≤10%: acceptable
        - ≤25%: minor_variance
        - >25%: significant_variance
        """
        abs_percentage = abs(variance_percentage)

        if abs_percentage <= self.ACCEPTABLE_THRESHOLD * 100:
            return "acceptable"
        elif abs_percentage <= self.MINOR_THRESHOLD * 100:
            return "minor_variance"
        else:
            return "significant_variance"

    def _calculate_score_impact(self, severity: str, line_items: List[Dict]) -> int:
        """
        Calculate score impact based on variance severity

        Deductions:
        - Acceptable: 0
        - Minor variance: -5
        - Significant variance: -15
        - Additional -2 for each line item with significant variance
        """
        base_impact = {
            "acceptable": 0,
            "minor_variance": -5,
            "significant_variance": -15
        }

        impact = base_impact.get(severity, 0)

        # Additional deduction for significant line item variances (max 2-3 items)
        significant_items = [item for item in line_items if item['severity'] == 'significant']
        impact += min(len(significant_items), 3) * -2  # Only penalize first 3

        # Cap at -20 (reduced from -40)
        return max(impact, -20)

    def _generate_summary(
        self,
        total_variance: Dict,
        stay_variance: Dict,
        severity: str,
        items_with_variance: int
    ) -> str:
        """Generate human-readable summary"""

        expected = total_variance['expected']
        actual = total_variance['actual']
        diff = total_variance['difference']
        pct = total_variance['percentage']

        # Base summary
        if severity == "acceptable":
            summary = f"Final bill (Rs.{actual:,.2f}) is within acceptable range of pre-auth estimate (Rs.{expected:,.2f}). "
        elif severity == "minor_variance":
            summary = f"Final bill (Rs.{actual:,.2f}) has minor variance of Rs.{abs(diff):,.2f} ({abs(pct):.1f}%) from pre-auth estimate (Rs.{expected:,.2f}). "
        else:
            summary = f"Final bill (Rs.{actual:,.2f}) has significant variance of Rs.{abs(diff):,.2f} ({abs(pct):.1f}%) from pre-auth estimate (Rs.{expected:,.2f}). "

        # Add stay variance info
        if stay_variance['is_extended']:
            summary += f"Hospital stay extended by {stay_variance['extra_days']} day(s) from planned {stay_variance['expected_days']} day(s). "

        # Add line items info
        if items_with_variance > 0:
            summary += f"{items_with_variance} line item(s) show cost variance. "

        summary += "Check discharge summary for medical reasons explaining variances."

        return summary


# Test function
def test_bill_reconciliation():
    """Test the bill reconciliation agent"""

    agent = BillReconciliationAgent()

    # Test Case 1: Pre-auth vs actual from our templates
    expected_costs = {
        "room_charges": 3500,
        "surgeon_fees": 18000,
        "anesthetist_fees": 5000,
        "ot_charges": 12000,
        "medicines": 12000,
        "implants": 15000,
        "investigations": 2000,
        "other_charges": 500,
        "total_estimated_cost": 68000
    }

    actual_bill = {
        "itemized_costs": {
            "room_charges": 7000,
            "nursing_charges": 1000,
            "surgeon_fees": 18000,
            "anesthetist_fees": 0,
            "ot_charges": 12000,
            "ot_consumables": 0,
            "medicines": 450,
            "implants": 0,
            "investigations": 0,
            "other_charges": 0
        },
        "total_bill_amount": 69500,
        "net_payable_amount": 72975
    }

    expected_stay = 1
    actual_stay = 2

    print("="*80)
    print("TESTING BILL RECONCILIATION AGENT")
    print("="*80)

    result = agent.reconcile(expected_costs, actual_bill, expected_stay, actual_stay)

    print("\n[STATUS]:", result['status'].upper())
    print("[SCORE IMPACT]:", result['score_impact'])

    print("\n[TOTAL VARIANCE]")
    tv = result['total_variance']
    print(f"  Expected: Rs.{tv['expected']:,.2f}")
    print(f"  Actual: Rs.{tv['actual']:,.2f}")
    print(f"  Difference: Rs.{tv['difference']:,.2f} ({tv['percentage']:+.2f}%)")

    print("\n[STAY VARIANCE]")
    sv = result['stay_variance']
    print(f"  Expected: {sv['expected_days']} days")
    print(f"  Actual: {sv['actual_days']} days")
    print(f"  Extra: {sv['extra_days']} day(s)")

    print("\n[LINE ITEM COMPARISON]")
    print(f"{'Item':<25} {'Expected':>12} {'Actual':>12} {'Difference':>12} {'%':>8} {'Severity':>12}")
    print("-"*80)

    for item in result['line_item_comparison']:
        print(f"{item['display_name']:<25} "
              f"Rs.{item['expected']:>10,.2f} "
              f"Rs.{item['actual']:>10,.2f} "
              f"Rs.{item['difference']:>10,.2f} "
              f"{item['percentage']:>7.1f}% "
              f"{item['severity']:>12}")

    print("\n[SUMMARY]")
    print(result['summary'])

    print("\n" + "="*80)
    print("[OK] Test completed")
    print("="*80)


if __name__ == "__main__":
    test_bill_reconciliation()
