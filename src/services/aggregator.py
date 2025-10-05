"""
Aggregator Service
Combines results from all 4 agents into final validation decision
"""

from typing import List
from src.models.schemas import (
    ValidationResult,
    AgentResults,
    CompletenessResult,
    PolicyValidationResult,
    MedicalReviewResult,
    FWADetectionResult
)


class Aggregator:
    """
    Aggregates results from all validation agents into a final decision

    Responsibilities:
    - Calculate final score (base 100 + sum of all agent score impacts)
    - Determine overall status using hierarchy (fail > warning > pass)
    - Collect all issues from all agents
    - Generate actionable recommendations
    - Determine approval likelihood
    """

    def __init__(self):
        """Initialize aggregator"""
        pass

    def aggregate(
        self,
        completeness: CompletenessResult,
        policy: PolicyValidationResult,
        medical: MedicalReviewResult,
        fwa: FWADetectionResult
    ) -> ValidationResult:
        """
        Aggregate all agent results into final validation result

        Args:
            completeness: Result from Completeness Checker
            policy: Result from Policy Validator
            medical: Result from Medical Reviewer
            fwa: Result from FWA Detector

        Returns:
            ValidationResult with final score, status, and recommendations

        Example:
            >>> aggregator = Aggregator()
            >>> result = aggregator.aggregate(comp, policy, medical, fwa)
            >>> print(result.final_score)  # 85
            >>> print(result.overall_status)  # "warning"
        """
        # 1. Calculate final score (base 100 + sum of all score impacts)
        final_score = self._calculate_final_score(completeness, policy, medical, fwa)

        # 2. Determine overall status (hierarchy: fail > warning > pass)
        overall_status = self._determine_overall_status(completeness, policy, medical, fwa)

        # 3. Collect all issues from all agents
        all_issues = self._collect_all_issues(completeness, policy, medical, fwa)

        # 4. Generate actionable recommendations
        recommendations = self._generate_recommendations(completeness, policy, medical, fwa)

        # 5. Determine approval likelihood
        approval_likelihood = self._determine_approval_likelihood(overall_status, final_score)

        # 6. Generate executive summary
        summary = self._generate_summary(overall_status, final_score, completeness, policy, medical, fwa)

        # 7. Package agent results
        agent_results = AgentResults(
            completeness=completeness,
            policy=policy,
            medical=medical,
            fwa=fwa
        )

        return ValidationResult(
            overall_status=overall_status,
            final_score=final_score,
            approval_likelihood=approval_likelihood,
            agent_results=agent_results,
            all_issues=all_issues,
            recommendations=recommendations,
            summary=summary
        )

    def _calculate_final_score(
        self,
        completeness: CompletenessResult,
        policy: PolicyValidationResult,
        medical: MedicalReviewResult,
        fwa: FWADetectionResult
    ) -> int:
        """
        Calculate final score (base 100 + sum of all impacts)

        Args:
            completeness, policy, medical, fwa: Agent results

        Returns:
            Final score (clamped to 0-100 range)
        """
        base_score = 100

        total_score = (
            base_score +
            completeness.score_impact +
            policy.score_impact +
            medical.score_impact +
            fwa.score_impact
        )

        # Clamp to 0-100 range
        return max(0, min(100, total_score))

    def _determine_overall_status(
        self,
        completeness: CompletenessResult,
        policy: PolicyValidationResult,
        medical: MedicalReviewResult,
        fwa: FWADetectionResult
    ) -> str:
        """
        Determine overall status using hierarchy (fail > warning > pass)

        Args:
            completeness, policy, medical, fwa: Agent results

        Returns:
            Status: "pass", "warning", or "fail"
        """
        statuses = [
            completeness.status,
            policy.status,
            medical.status,
            fwa.status
        ]

        # Hierarchy: fail > warning > pass
        if "fail" in statuses:
            return "fail"
        elif "warning" in statuses:
            return "warning"
        else:
            return "pass"

    def _collect_all_issues(
        self,
        completeness: CompletenessResult,
        policy: PolicyValidationResult,
        medical: MedicalReviewResult,
        fwa: FWADetectionResult
    ) -> List[str]:
        """
        Collect all issues from all agents into a single list

        Args:
            completeness, policy, medical, fwa: Agent results

        Returns:
            List of all issue descriptions
        """
        issues = []

        # Completeness issues
        issues.extend(completeness.issues)

        # Policy violations
        for violation in policy.violations:
            issues.append(f"[Policy] {violation.explanation}")

        # Medical concerns
        for concern in medical.concerns:
            issues.append(f"[Medical] {concern.description}")

        # FWA flags
        for flag in fwa.flags:
            issues.append(f"[FWA] {flag.detail}")

        return issues

    def _generate_recommendations(
        self,
        completeness: CompletenessResult,
        policy: PolicyValidationResult,
        medical: MedicalReviewResult,
        fwa: FWADetectionResult
    ) -> List[str]:
        """
        Generate prioritized, actionable recommendations

        Priority:
        1. Critical policy violations (blockers)
        2. Missing required information (completeness)
        3. Medical documentation improvements
        4. FWA concerns requiring justification

        Args:
            completeness, policy, medical, fwa: Agent results

        Returns:
            List of actionable recommendations
        """
        recommendations = []

        # 1. Critical policy violations (highest priority)
        critical_violations = [v for v in policy.violations if v.severity == "critical"]
        for violation in critical_violations:
            recommendations.append(f"🚫 CRITICAL: {violation.suggestion}")

        # 2. Missing required information
        if completeness.status == "fail":
            for issue in completeness.issues:
                recommendations.append(f"📋 Required: {issue}")

        # 3. Medical documentation improvements
        for concern in medical.concerns:
            # Map concern type to PDF section
            section_map = {
                "missing_evidence": "Clinical Findings & Diagnostic Tests",
                "insufficient_justification": "Medical Justification",
                "template_language": "Medical Justification",
                "treatment_mismatch": "Treatment & Diagnosis Sections"
            }
            section = section_map.get(concern.type, "Medical Documentation")
            recommendations.append(f"🏥 {section}: {concern.suggestion}")

        # 4. Policy warnings
        warning_violations = [v for v in policy.violations if v.severity == "warning"]
        for violation in warning_violations:
            recommendations.append(f"⚠️ Policy: {violation.suggestion}")

        # 5. Quality check concerns
        for flag in fwa.flags:
            # Map flag category to PDF section
            section_map = {
                "cost_inflation": "Cost Breakdown",
                "overtreatment": "Hospitalization Details",
                "unjustified_upgrade": "Cost Breakdown & Treatment Details"
            }
            section = section_map.get(flag.category, "Documentation")
            recommendations.append(f"🔍 {section}: {flag.insurer_action}")

        # If no recommendations but status is not pass, add generic one
        if not recommendations and (completeness.status != "pass" or
                                   policy.status != "pass" or
                                   medical.status != "pass" or
                                   fwa.status != "pass"):
            recommendations.append("Review all agent findings and address identified concerns")

        return recommendations

    def _determine_approval_likelihood(self, overall_status: str, final_score: int) -> str:
        """
        Determine approval likelihood based on status and score

        Logic:
        - fail status OR score < 50 → low
        - warning status AND score 50-79 → medium
        - warning status AND score >= 80 → high (minor issues only)
        - pass status → high

        Args:
            overall_status: Overall status
            final_score: Final score (0-100)

        Returns:
            Approval likelihood: "high", "medium", or "low"
        """
        if overall_status == "fail" or final_score < 50:
            return "low"
        elif overall_status == "warning":
            if final_score >= 80:
                return "high"  # Minor issues only
            else:
                return "medium"
        else:  # pass
            return "high"

    def _generate_summary(
        self,
        overall_status: str,
        final_score: int,
        completeness: CompletenessResult,
        policy: PolicyValidationResult,
        medical: MedicalReviewResult,
        fwa: FWADetectionResult
    ) -> str:
        """
        Generate executive summary of validation

        Args:
            overall_status: Overall status
            final_score: Final score
            completeness, policy, medical, fwa: Agent results

        Returns:
            Human-readable summary string
        """
        # Count issues by agent
        comp_issues = len(completeness.issues)
        policy_issues = len(policy.violations)
        medical_issues = len(medical.concerns)
        fwa_issues = len(fwa.flags)

        # Build summary
        if overall_status == "pass":
            summary = f"✅ Pre-authorization approved (Score: {final_score}/100). "
            summary += "All validation checks passed. Ready for submission."

        elif overall_status == "fail":
            summary = f"❌ Pre-authorization rejected (Score: {final_score}/100). "

            # Identify primary failure reasons
            failures = []
            if completeness.status == "fail":
                failures.append(f"incomplete documentation ({comp_issues} missing)")
            if policy.status == "fail":
                failures.append(f"policy violations ({policy_issues} critical)")
            if medical.status == "fail":
                failures.append(f"insufficient medical justification")
            if fwa.status == "fail":
                failures.append(f"high fraud risk ({fwa_issues} red flags)")

            summary += f"Critical issues: {', '.join(failures)}."

        else:  # warning
            summary = f"⚠️ Pre-authorization needs review (Score: {final_score}/100). "

            # Count total issues
            total_issues = comp_issues + policy_issues + medical_issues + fwa_issues
            summary += f"{total_issues} issues identified across agents. "

            # Highlight key concerns
            concerns = []
            if comp_issues > 0:
                concerns.append(f"{comp_issues} documentation gaps")
            if policy_issues > 0:
                concerns.append(f"{policy_issues} policy concerns")
            if medical_issues > 0:
                concerns.append(f"{medical_issues} medical review items")
            if fwa_issues > 0:
                concerns.append(f"{fwa_issues} FWA flags")

            summary += f"Issues: {', '.join(concerns)}."

        return summary
