"""
FWA Detector Agent
Hybrid fraud/waste/abuse detection using rules + LLM
"""

import json
from typing import Dict, List, Optional
from src.models.schemas import FWADetectionResult, FWAFlag, MedicalNote
from src.utils.llm_client import call_llm_with_retry


# LLM Prompt template for FWA pattern detection
PROMPT_TEMPLATE = """You are a quality assurance specialist for health insurance claims in India.

YOUR TASK: Review the CLAIM DATA (medical note and costs) for potential fraud/waste/abuse. Focus ONLY on the claim itself, not on the reference data.

=== CLAIM DATA (Review this) ===
Diagnosis: {diagnosis}
Treatment: {treatment}
Total Cost: ₹{total_cost:,}
Cost Breakdown:
{cost_breakdown}
Hospital Stay: {stay_duration} days
Overnight Stay Mentioned: {overnight_mentioned}

=== REFERENCE DATA (Guidelines only - Do NOT audit or flag errors in this data) ===
Typical Cost Range: ₹{typical_min:,} - ₹{typical_max:,}
Typical Hospital Stay: {typical_stay_min}-{typical_stay_max} days

DETAILED COST ANALYSIS (from medical guidelines):
{cost_analysis}

FRAUD/WASTE/ABUSE PATTERNS (from medical guidelines):
{fwa_patterns}

=== CRITICAL ASSESSMENT RULES ===

**WHAT TO FOCUS ON:**
- Review the CLAIM DATA (diagnosis, treatment, costs, hospital stay) for red flags
- Compare claim costs against reference ranges provided above
- Look for patterns from FWA_PATTERNS section that match the claim

**WHAT TO IGNORE:**
- DO NOT flag or comment on errors, inconsistencies, or data quality issues in the REFERENCE DATA (medical guidelines)
- If reference data shows unusual values (e.g., "24-72 days" for a day surgery), IGNORE IT - this is a data error in our reference files, not a claim issue
- Your job is to review the CLAIM, not audit our internal medical reference database

**COST FLAGGING RULES - BE STRICT:**
1. **Assess each cost component INDEPENDENTLY** - Do NOT say "combined with other costs" or link multiple items together
2. **Only flag if cost EXCEEDS the maximum** of the stated range:
   - ₹24,500 surgeon fee with range ₹20,000-45,000 → DO NOT FLAG (it's within range, not even "upper end")
   - ₹18,000 room charges with range ₹7,000-20,000 → DO NOT FLAG (within range)
   - ₹46,000 surgeon fee with range ₹20,000-45,000 → FLAG (exceeds maximum)
3. **Only flag costs >2x typical maximum** without clear medical justification
4. **"Upper end" is NOT a red flag** - Costs anywhere within the range are acceptable
5. **1-day admission for day surgery is NORMAL** (includes prep, surgery, recovery) - Only flag if >1 day AND no medical reason documented

**OUTPUT RULES:**
- Be FAIR, FLEXIBLE, and REASONABLE - Pre-authorization stage should be lenient
- Focus ONLY on clear, unjustifiable deviations that insurers would question
- Each flag should stand alone (don't link flags together with "combined with...")
- Return EMPTY flags array if no major red flags found

Return ONLY a valid JSON object with this exact structure:
{{
  "risk_level": "low" | "medium" | "high",
  "flags": [
    {{
      "category": "cost_inflation" | "overtreatment" | "unjustified_upgrade",
      "detail": "specific concern about THE CLAIM",
      "evidence": "what in THE CLAIM triggered this",
      "insurer_action": "likely response"
    }}
  ]
}}

IMPORTANT: Return ONLY the JSON object, no other text."""


class FWADetector:
    """
    Hybrid FWA detection agent using rules + LLM

    Detects:
    - Cost inflation (rule-based: >150% typical max)
    - Duration outliers (rule-based: >typical + 2 days)
    - Pattern-based fraud (LLM: using fraud_waste_abuse_patterns from procedure JSON)
    """

    def __init__(self):
        """Initialize FWA detector"""
        pass

    def detect(
        self,
        diagnosis: str,
        treatment: str,
        costs: Dict,
        procedure_data: Dict,
        stay_duration: int,
        medical_note: MedicalNote
    ) -> FWADetectionResult:
        """
        Detect fraud/waste/abuse red flags

        Args:
            diagnosis: Primary diagnosis
            treatment: Proposed treatment
            costs: Cost breakdown dictionary
            procedure_data: Procedure data with typical costs and FWA patterns
            stay_duration: Expected length of stay
            medical_note: Complete medical note for context

        Returns:
            FWADetectionResult with risk level, flags, and score impact

        Example:
            >>> detector = FWADetector()
            >>> result = detector.detect(diagnosis, treatment, costs, procedure_data, stay, note)
            >>> print(result.risk_level)  # "low", "medium", "high"
        """
        flags = []

        # 1. Rule-based: Check cost outliers
        cost_flags = self._check_cost_outliers(costs, procedure_data)
        flags.extend(cost_flags)

        # 2. Rule-based: Check duration outliers
        duration_flags = self._check_duration_outliers(stay_duration, procedure_data)
        flags.extend(duration_flags)

        # 3. LLM-based: Pattern detection
        llm_risk_level = None
        try:
            llm_flags, llm_risk_level = self._llm_pattern_detection(
                diagnosis,
                treatment,
                costs,
                procedure_data,
                stay_duration,
                medical_note
            )
            flags.extend(llm_flags)
        except Exception as e:
            # Graceful degradation - continue with rule-based flags only
            pass

        # Determine overall risk level (prioritize LLM assessment if available)
        risk_level = llm_risk_level if llm_risk_level else self._determine_risk_level(flags)

        # Calculate score impact
        score_impact = self._calculate_score_impact(flags, risk_level)

        # Determine status
        status = "fail" if risk_level == "high" else ("warning" if risk_level == "medium" else "pass")

        return FWADetectionResult(
            status=status,
            risk_level=risk_level,
            flags=flags,
            score_impact=score_impact
        )

    def _check_cost_outliers(self, costs: Dict, procedure_data: Dict) -> List[FWAFlag]:
        """
        Rule-based cost outlier detection (>150% of typical max)

        Args:
            costs: Cost breakdown
            procedure_data: Procedure data with typical costs

        Returns:
            List of FWAFlag objects
        """
        flags = []

        try:
            # Get total cost
            total_cost = costs.get('total_estimated_cost', 0)

            # Get typical cost range
            cost_analysis = procedure_data.get('cost_analysis', {})
            tier1_data = cost_analysis.get('india_tier1_cities', {})
            overall_range = tier1_data.get('overall_range', {})
            typical_max = overall_range.get('maximum', 0)

            if typical_max == 0:
                return flags

            # Check if cost exceeds 150% of typical max
            threshold = typical_max * 1.5
            if total_cost > threshold:
                excess_percentage = int(((total_cost / typical_max) - 1) * 100)
                flags.append(FWAFlag(
                    category="cost_inflation",
                    detail=f"Total cost ₹{total_cost:,.0f} is {excess_percentage}% above typical maximum",
                    evidence=f"Typical max: ₹{typical_max:,.0f}, Actual: ₹{total_cost:,.0f}",
                    insurer_action="Will request itemized justification for cost components"
                ))

        except Exception as e:
            # Silently skip if data structure issues
            pass

        return flags

    def _check_duration_outliers(self, stay_duration: int, procedure_data: Dict) -> List[FWAFlag]:
        """
        Rule-based duration outlier detection (>typical max + 2 days)

        Note: 1-day admission is considered normal for day surgery (includes prep and recovery)

        Args:
            stay_duration: Expected length of stay
            procedure_data: Procedure data with typical duration

        Returns:
            List of FWAFlag objects
        """
        flags = []

        try:
            # Get typical hospital stay range
            hospitalization = procedure_data.get('hospitalization_details', {})
            typical_stay = hospitalization.get('typical_hospital_stay', {})
            typical_max = typical_stay.get('maximum', 0)

            # Skip check if typical is 0 (day surgery) and actual is 1 day
            # 1-day admission for day surgery is normal (prep + surgery + recovery)
            if typical_max == 0 and stay_duration <= 1:
                return flags

            if typical_max == 0:
                return flags

            # Check if duration exceeds typical max + 2 days
            threshold = typical_max + 2
            if stay_duration > threshold:
                excess_days = stay_duration - typical_max
                flags.append(FWAFlag(
                    category="overtreatment",
                    detail=f"Hospital stay ({stay_duration} days) exceeds typical maximum by {excess_days} days",
                    evidence=f"Typical max: {typical_max} days, Planned: {stay_duration} days",
                    insurer_action="Will request clinical justification for extended stay"
                ))

        except Exception as e:
            # Silently skip if data structure issues
            pass

        return flags

    def _llm_pattern_detection(
        self,
        diagnosis: str,
        treatment: str,
        costs: Dict,
        procedure_data: Dict,
        stay_duration: int,
        medical_note: MedicalNote
    ) -> tuple:
        """
        LLM-based FWA pattern detection

        Args:
            diagnosis: Primary diagnosis
            treatment: Proposed treatment
            costs: Cost breakdown
            procedure_data: Procedure data
            stay_duration: Expected length of stay
            medical_note: Medical note

        Returns:
            Tuple of (List[FWAFlag], risk_level)
        """
        # Construct prompt
        prompt = self._construct_fwa_prompt(
            diagnosis,
            treatment,
            costs,
            procedure_data,
            stay_duration,
            medical_note
        )
        
        # Print prompt for debugging
        print("\n" + "="*80)
        print("PROMPT SENT TO AGENT-4 (FWA DETECTOR)")
        print("="*80)
        print(prompt)
        print("="*80 + "\n")

        # Call LLM
        response = call_llm_with_retry(
            prompt=prompt,
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            temperature=0.3,
            max_retries=2
        )

        # Parse response
        flags, risk_level = self._parse_fwa_response(response)

        return flags, risk_level

    def _construct_fwa_prompt(
        self,
        diagnosis: str,
        treatment: str,
        costs: Dict,
        procedure_data: Dict,
        stay_duration: int,
        medical_note: MedicalNote
    ) -> str:
        """
        Construct LLM prompt for FWA detection

        Args:
            diagnosis: Primary diagnosis
            treatment: Proposed treatment
            costs: Cost breakdown
            procedure_data: Procedure data
            stay_duration: Expected length of stay
            medical_note: Medical note for context

        Returns:
            Formatted prompt string
        """
        # Get complete cost analysis and FWA patterns
        cost_analysis = procedure_data.get('cost_analysis', {})
        fwa_patterns = procedure_data.get('fraud_waste_abuse_patterns', {})
        
        # Format cost analysis as JSON
        cost_analysis_text = json.dumps(cost_analysis, indent=2) if cost_analysis else "No cost analysis data available."
        
        # Format FWA patterns as JSON
        fwa_text = json.dumps(fwa_patterns, indent=2) if fwa_patterns else "No specific FWA patterns defined."
        
        # Extract typical ranges for backward compatibility in prompt
        tier1_data = cost_analysis.get('india_tier1_cities', {})
        overall_range = tier1_data.get('overall_range', {})
        typical_min = overall_range.get('minimum', 0)
        typical_max = overall_range.get('maximum', 0)
        
        # Get typical stay from hospitalization (fixed key)
        hospitalization = procedure_data.get('hospitalization', {})
        typical_duration = hospitalization.get('typical_duration', {})
        typical_stay_unit = typical_duration.get('unit', 'days')
        typical_stay_min = typical_duration.get('minimum', 0)
        typical_stay_max = typical_duration.get('maximum', 0)

        # Check if overnight stay is mentioned
        overnight_keywords = ["overnight", "over night", "over-night", "will stay overnight", "staying overnight"]
        overnight_mentioned = False

        # Check in justification fields
        justification_text = (
            str(medical_note.medical_justification.why_hospitalization_required or '') + ' ' +
            str(medical_note.medical_justification.why_treatment_necessary or '')
        ).lower()

        for keyword in overnight_keywords:
            if keyword in justification_text:
                overnight_mentioned = True
                break

        # Format cost breakdown
        total_cost = costs.get('total_estimated_cost', 0)
        cost_breakdown_text = f"""
- Room Charges: ₹{costs.get('room_charges', 0):,.0f}
- Surgeon Fees: ₹{costs.get('surgeon_fees', 0):,.0f}
- Anesthetist Fees: ₹{costs.get('anesthetist_fees', 0):,.0f}
- OT Charges: ₹{costs.get('ot_charges', 0):,.0f}
- ICU Charges: ₹{costs.get('icu_charges', 0):,.0f}
- Investigations: ₹{costs.get('investigations', 0):,.0f}
- Medicines/Consumables/Implants: ₹{costs.get('medicines_consumables', 0):,.0f}
- Other: ₹{costs.get('other_charges', 0):,.0f}
        """.strip()

        return PROMPT_TEMPLATE.format(
            diagnosis=diagnosis,
            treatment=treatment,
            total_cost=total_cost,
            cost_breakdown=cost_breakdown_text,
            stay_duration=stay_duration,
            overnight_mentioned="Yes" if overnight_mentioned else "No",
            typical_min=typical_min,
            typical_max=typical_max,
            typical_stay_min=typical_stay_min,
            typical_stay_max=typical_stay_max,
            cost_analysis=cost_analysis_text,
            fwa_patterns=fwa_text
        )

    def _parse_fwa_response(self, response: str) -> tuple:
        """
        Parse LLM JSON response for FWA flags and risk level

        Args:
            response: LLM response string

        Returns:
            Tuple of (List[FWAFlag], risk_level)
        """
        try:
            # Extract JSON from response
            response = response.strip()
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                return [], None

            json_str = response[start_idx:end_idx]
            data = json.loads(json_str)

            flags_data = data.get('flags', [])
            risk_level = data.get('risk_level', None)

            # Convert to FWAFlag objects
            flags = [
                FWAFlag(
                    category=f.get('category', 'cost_inflation'),
                    detail=f.get('detail', 'No detail provided'),
                    evidence=f.get('evidence', 'No evidence provided'),
                    insurer_action=f.get('insurer_action', 'Manual review required')
                )
                for f in flags_data
            ]

            return flags, risk_level

        except json.JSONDecodeError:
            return [], None

    def _determine_risk_level(self, flags: List[FWAFlag]) -> str:
        """
        Determine overall risk level based on flags

        Args:
            flags: List of FWAFlag objects

        Returns:
            Risk level: "low", "medium", "high"
        """
        if len(flags) == 0:
            return "low"
        elif len(flags) == 1:
            # Single flag - check if it's cost inflation or overtreatment
            if flags[0].category in ["cost_inflation", "overtreatment"]:
                return "medium"
            else:
                return "low"
        elif len(flags) >= 3:
            return "high"
        else:  # 2 flags
            return "medium"

    def _calculate_score_impact(self, flags: List[FWAFlag], risk_level: str) -> int:
        """
        Calculate score deduction based on flags and risk level

        Args:
            flags: List of FWAFlag objects
            risk_level: Overall risk level

        Returns:
            Negative integer representing score deduction
        """
        if risk_level == "high":
            return -20
        elif risk_level == "medium":
            return -10
        else:
            return 0

    def get_summary(self, result: FWADetectionResult) -> str:
        """
        Generate human-readable summary of FWA detection

        Args:
            result: FWADetectionResult object

        Returns:
            Plain-language summary string
        """
        if result.status == "pass":
            return "✓ No FWA red flags detected"

        flag_summary = f"{len(result.flags)} red flag(s)" if result.flags else "potential issues"

        if result.risk_level == "high":
            return f"✗ High FWA risk: {flag_summary}. Detailed review required."
        elif result.risk_level == "medium":
            return f"⚠ Medium FWA risk: {flag_summary}. Additional documentation needed."
        else:
            return f"⚠ Low FWA risk: {flag_summary}."
