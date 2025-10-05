"""
Policy Validator Agent
Structured lookup validation against policy rules
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from src.models.schemas import PolicyValidationResult, MedicalNote
from src.utils.data_loader import (
    load_policy_data,
    get_waiting_period_for_procedure,
    get_room_rent_limit
)


class PolicyValidator:
    """
    Validates pre-authorization request against policy rules

    Checks:
    - Policy is active on admission date
    - Initial waiting period (30 days)
    - Procedure-specific waiting period (from policy JSON)
    - Procedure not excluded (from policy JSON)
    - Sum insured adequacy (total cost vs available SI)
    - Room rent sub-limits (from policy JSON)
    """

    def __init__(self):
        """Initialize policy validator"""
        pass

    def validate(
        self,
        policy_data,  # PolicyData or Dict
        procedure_id: str,
        form_data: Dict,
        medical_note: MedicalNote
    ) -> PolicyValidationResult:
        """
        Validate pre-authorization request against policy rules

        Args:
            policy_data: Policy data object from load_policy_data() (PolicyData or dict)
            procedure_id: Procedure identifier (e.g., "cataract_surgery")
            form_data: Form data with policy info and admission date
            medical_note: Medical note with cost breakdown

        Returns:
            PolicyValidationResult with status, violations, and score impact

        Example:
            >>> validator = PolicyValidator()
            >>> result = validator.validate(policy, "cataract_surgery", form, note)
            >>> print(result.status)  # "pass", "warning", or "fail"
        """
        violations = []

        # 1. Check policy is active on admission date
        policy_active_violations = self._check_policy_active(
            form_data.get('policy_start_date'),
            form_data.get('planned_admission_date')
        )
        violations.extend(policy_active_violations)

        # 2. Check initial waiting period (30 days)
        initial_waiting_violations = self._check_initial_waiting_period(
            policy_data,
            form_data.get('policy_start_date'),
            form_data.get('planned_admission_date')
        )
        violations.extend(initial_waiting_violations)

        # 3. Check procedure-specific waiting period
        procedure_waiting_violations = self._check_procedure_waiting_period(
            policy_data,
            procedure_id,
            form_data.get('policy_start_date'),
            form_data.get('planned_admission_date')
        )
        violations.extend(procedure_waiting_violations)

        # 4. Check procedure not excluded
        exclusion_violations = self._check_exclusions(
            policy_data,
            procedure_id
        )
        violations.extend(exclusion_violations)

        # 5. Check sum insured adequacy
        si_violations = self._check_sum_insured_adequacy(
            form_data.get('sum_insured', 0),
            form_data.get('previous_claims_amount', 0),
            medical_note.cost_breakdown.total_estimated_cost
        )
        violations.extend(si_violations)

        # 6. Check room rent sub-limits
        room_rent_violations = self._check_room_rent_limits(
            policy_data,
            form_data.get('sum_insured', 0),
            medical_note.cost_breakdown.room_charges,
            medical_note.hospitalization_details.expected_length_of_stay
        )
        violations.extend(room_rent_violations)

        # Calculate score impact
        score_impact = self._calculate_score_impact(violations)

        # Determine status
        has_critical = any(v['severity'] == 'critical' for v in violations)
        status = 'fail' if has_critical else ('warning' if violations else 'pass')

        return PolicyValidationResult(
            status=status,
            violations=violations,
            score_impact=score_impact
        )

    def _check_policy_active(
        self,
        policy_start_date: str,
        planned_admission_date: str
    ) -> List[Dict]:
        """
        Check if policy is active on planned admission date

        Args:
            policy_start_date: Policy start date (DD/MM/YYYY or YYYY-MM-DD)
            planned_admission_date: Planned admission date (DD/MM/YYYY or YYYY-MM-DD)

        Returns:
            List of violation dictionaries
        """
        violations = []

        try:
            # Parse dates (support both DD/MM/YYYY and YYYY-MM-DD formats)
            policy_start = self._parse_date(policy_start_date)
            admission_date = self._parse_date(planned_admission_date)

            if admission_date < policy_start:
                violations.append({
                    'rule': 'policy_active',
                    'severity': 'critical',
                    'explanation': f'Admission date ({planned_admission_date}) is before policy start date ({policy_start_date})',
                    'suggestion': 'Policy must be active on admission date. This claim will be rejected.'
                })

        except Exception as e:
            violations.append({
                'rule': 'policy_active',
                'severity': 'critical',
                'explanation': f'Unable to validate policy dates: {str(e)}',
                'suggestion': 'Verify date formats are correct'
            })

        return violations

    def _check_initial_waiting_period(
        self,
        policy_data,  # PolicyData or Dict
        policy_start_date: str,
        planned_admission_date: str
    ) -> List[Dict]:
        """
        Check if initial waiting period (typically 30 days) is met

        Args:
            policy_data: Policy data object or dict
            policy_start_date: Policy start date
            planned_admission_date: Planned admission date

        Returns:
            List of violation dictionaries
        """
        violations = []

        try:
            # Handle both PolicyData object and dict
            if isinstance(policy_data, dict):
                waiting_periods = policy_data.get('waiting_periods', {})
            else:
                waiting_periods = policy_data.waiting_periods

            initial_waiting_days = waiting_periods.get('initial_days', 30) if isinstance(waiting_periods, dict) else 30

            policy_start = self._parse_date(policy_start_date)
            admission_date = self._parse_date(planned_admission_date)

            days_elapsed = (admission_date - policy_start).days

            if days_elapsed < initial_waiting_days:
                shortfall_days = initial_waiting_days - days_elapsed
                violations.append({
                    'rule': 'initial_waiting_period',
                    'severity': 'critical',
                    'explanation': f'Initial waiting period not met. Required: {initial_waiting_days} days, Elapsed: {days_elapsed} days (Shortfall: {shortfall_days} days)',
                    'suggestion': f'Wait {shortfall_days} more days before admission. This claim will be rejected.'
                })

        except Exception as e:
            violations.append({
                'rule': 'initial_waiting_period',
                'severity': 'critical',
                'explanation': f'Unable to validate initial waiting period: {str(e)}',
                'suggestion': 'Verify date formats and policy data'
            })

        return violations

    def _check_procedure_waiting_period(
        self,
        policy_data,  # PolicyData or Dict
        procedure_id: str,
        policy_start_date: str,
        planned_admission_date: str
    ) -> List[Dict]:
        """
        Check if procedure-specific waiting period is met

        Args:
            policy_data: Policy data object or dict
            procedure_id: Procedure identifier
            policy_start_date: Policy start date
            planned_admission_date: Planned admission date

        Returns:
            List of violation dictionaries
        """
        violations = []

        try:
            # get_waiting_period_for_procedure expects PolicyData object
            # If dict, need to pass it correctly or convert
            if isinstance(policy_data, dict):
                # Call utility with dict (it will handle it)
                from src.models.schemas import PolicyData
                temp_policy = PolicyData(**policy_data)
                waiting_period_months = get_waiting_period_for_procedure(temp_policy, procedure_id)
            else:
                waiting_period_months = get_waiting_period_for_procedure(policy_data, procedure_id)

            if waiting_period_months is None or waiting_period_months == 0:
                # No specific waiting period for this procedure
                return violations

            policy_start = self._parse_date(policy_start_date)
            admission_date = self._parse_date(planned_admission_date)

            months_elapsed = self._calculate_months_between(policy_start, admission_date)

            if months_elapsed < waiting_period_months:
                shortfall_months = waiting_period_months - months_elapsed
                violations.append({
                    'rule': 'procedure_waiting_period',
                    'severity': 'critical',
                    'explanation': f'Procedure-specific waiting period not met. Required: {waiting_period_months} months, Elapsed: {months_elapsed} months (Shortfall: {shortfall_months} months)',
                    'suggestion': f'Wait {shortfall_months} more months before admission. This claim will be rejected.'
                })

        except Exception as e:
            violations.append({
                'rule': 'procedure_waiting_period',
                'severity': 'warning',
                'explanation': f'Unable to validate procedure waiting period: {str(e)}',
                'suggestion': 'Verify procedure ID and policy data'
            })

        return violations

    def _check_exclusions(
        self,
        policy_data,  # PolicyData or Dict
        procedure_id: str
    ) -> List[Dict]:
        """
        Check if procedure is excluded under the policy

        Args:
            policy_data: Policy data object or dict
            procedure_id: Procedure identifier

        Returns:
            List of violation dictionaries
        """
        violations = []

        try:
            # Handle both PolicyData object and dict
            if isinstance(policy_data, dict):
                exclusions = policy_data.get('exclusions', [])
            else:
                exclusions = policy_data.exclusions
            if isinstance(exclusions, dict):
                exclusions = exclusions.get('permanent', [])

            # Check if procedure_id is in exclusions list
            if procedure_id in exclusions:
                violations.append({
                    'rule': 'exclusions',
                    'severity': 'critical',
                    'explanation': f'Procedure "{procedure_id}" is permanently excluded under this policy',
                    'suggestion': 'This claim will be rejected. Procedure is not covered.'
                })

        except Exception as e:
            violations.append({
                'rule': 'exclusions',
                'severity': 'warning',
                'explanation': f'Unable to validate exclusions: {str(e)}',
                'suggestion': 'Verify policy exclusions list'
            })

        return violations

    def _check_sum_insured_adequacy(
        self,
        sum_insured: int,
        previous_claims_amount: int,
        total_estimated_cost: float
    ) -> List[Dict]:
        """
        Check if sum insured is adequate for the claim

        Args:
            sum_insured: Total sum insured
            previous_claims_amount: Amount already claimed in policy period
            total_estimated_cost: Total estimated cost for this claim

        Returns:
            List of violation dictionaries
        """
        violations = []

        available_si = sum_insured - previous_claims_amount

        if total_estimated_cost > sum_insured:
            violations.append({
                'rule': 'sum_insured',
                'severity': 'warning',
                'explanation': f'Total cost (₹{total_estimated_cost:,.0f}) exceeds sum insured (₹{sum_insured:,.0f})',
                'suggestion': f'Patient will bear ₹{total_estimated_cost - sum_insured:,.0f} out-of-pocket. Consider reducing costs.'
            })
        elif total_estimated_cost > available_si:
            violations.append({
                'rule': 'sum_insured',
                'severity': 'warning',
                'explanation': f'Total cost (₹{total_estimated_cost:,.0f}) exceeds available sum insured (₹{available_si:,.0f}) after previous claims (₹{previous_claims_amount:,.0f})',
                'suggestion': f'Patient will bear ₹{total_estimated_cost - available_si:,.0f} out-of-pocket. Consider reducing costs.'
            })

        return violations

    def _check_room_rent_limits(
        self,
        policy_data,  # PolicyData or Dict
        sum_insured: int,
        room_charges: float,
        stay_duration: int
    ) -> List[Dict]:
        """
        Check if room rent exceeds policy sub-limits

        Args:
            policy_data: Policy data object or dict
            sum_insured: Sum insured amount
            room_charges: Total room charges for stay
            stay_duration: Expected length of stay in days

        Returns:
            List of violation dictionaries
        """
        violations = []

        try:
            # get_room_rent_limit expects PolicyData object
            # If we have a dict, we need to handle it differently
            if isinstance(policy_data, dict):
                coverage_by_si = policy_data.get('coverage_by_sum_insured', {})
                sum_insured_str = str(sum_insured)
                coverage = coverage_by_si.get(sum_insured_str, {})
                room_rent_limit = coverage.get("room_rent_max_per_day")
            else:
                room_rent_limit = get_room_rent_limit(policy_data, sum_insured)

            if room_rent_limit is None:
                # No room rent limit for this SI tier
                return violations

            if stay_duration <= 0:
                # Cannot validate if stay duration is invalid
                return violations

            room_rent_per_day = room_charges / stay_duration

            if room_rent_per_day > room_rent_limit:
                excess_percentage = ((room_rent_per_day / room_rent_limit) - 1) * 100
                violations.append({
                    'rule': 'room_rent_limit',
                    'severity': 'warning',
                    'explanation': f'Room rent (₹{room_rent_per_day:,.0f}/day) exceeds policy limit (₹{room_rent_limit:,.0f}/day) by {excess_percentage:.0f}%',
                    'suggestion': 'Proportionate deduction will apply to multiple line items (surgery, ICU, etc.). Consider downgrading room category.'
                })

        except Exception as e:
            violations.append({
                'rule': 'room_rent_limit',
                'severity': 'warning',
                'explanation': f'Unable to validate room rent limit: {str(e)}',
                'suggestion': 'Verify room charges and stay duration'
            })

        return violations

    def _calculate_score_impact(self, violations: List[Dict]) -> int:
        """
        Calculate score deduction based on violations

        Args:
            violations: List of violation dictionaries

        Returns:
            Negative integer representing score deduction
        """
        score = 0

        for violation in violations:
            if violation['severity'] == 'critical':
                score -= 20
            elif violation['severity'] == 'warning':
                score -= 10

        return score

    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse date string in DD/MM/YYYY or YYYY-MM-DD format

        Args:
            date_str: Date string

        Returns:
            datetime object
        """
        # Try DD/MM/YYYY format first
        for fmt in ['%d/%m/%Y', '%Y-%m-%d']:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        raise ValueError(f"Unable to parse date: {date_str}. Expected DD/MM/YYYY or YYYY-MM-DD")

    def _calculate_months_between(self, start_date: datetime, end_date: datetime) -> int:
        """
        Calculate number of months between two dates

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Number of complete months
        """
        months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)

        # Check if we've completed the month (day of month comparison)
        if end_date.day < start_date.day:
            months -= 1

        return months

    def get_summary(self, result: PolicyValidationResult) -> str:
        """
        Generate human-readable summary of policy validation

        Args:
            result: PolicyValidationResult object

        Returns:
            Plain-language summary string
        """
        if result.status == "pass":
            return "✓ All policy requirements met"

        # Group violations by severity
        critical = [v for v in result.violations if v.severity == 'critical']
        warnings = [v for v in result.violations if v.severity == 'warning']

        summary_parts = []

        if critical:
            summary_parts.append(f"{len(critical)} critical violation(s)")
        if warnings:
            summary_parts.append(f"{len(warnings)} warning(s)")

        return f"✗ Policy issues: {', '.join(summary_parts)}"
