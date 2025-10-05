"""
Agent 8: Medical Guidance Generator (LLM)
Extracts and formats patient care instructions from discharge summary

Generates plain-language guidance for:
- Medication schedule
- Follow-up appointments
- Activity restrictions (DO's and DON'Ts)
- Warning signs requiring immediate attention
- Recovery timeline and expectations
"""

from typing import Dict, List, Optional
import os
from anthropic import Anthropic


class MedicalGuidanceGenerator:
    """
    LLM-powered generator for patient-friendly medical guidance

    Extracts from discharge summary and formats into actionable instructions
    """

    def __init__(self, anthropic_api_key: Optional[str] = None):
        """Initialize with Anthropic API key"""
        if anthropic_api_key is None:
            anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')

        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.client = Anthropic(api_key=anthropic_api_key)
        self.model = "claude-sonnet-4-20250514"

    def generate(
        self,
        discharge_summary: Dict,
        procedure_type: str = "general"
    ) -> Dict:
        """
        Generate medical guidance from discharge summary

        Args:
            discharge_summary: Extracted discharge summary
                {
                    "medications": [
                        {
                            "name": "Moxifloxacin 0.5% Eye Drops",
                            "dosage": "1 drop 4 times daily",
                            "duration": "7 days",
                            "purpose": "Antibiotic prophylaxis"
                        },
                        ...
                    ],
                    "follow_up_schedule": [
                        {
                            "timing": "Day 1 Post-Discharge",
                            "purpose": "Post-op check-up"
                        },
                        ...
                    ],
                    "activity_restrictions": {
                        "dos": ["Wear protective shield...", ...],
                        "donts": ["Do NOT rub eye...", ...]
                    },
                    "warning_signs": ["Sudden vision loss", ...],
                    "discharge_condition": "...",
                    "complications": "..."
                }

            procedure_type: Type of procedure (for context)

        Returns:
            {
                "status": "complete" | "partial" | "incomplete",
                "medication_schedule": {
                    "summary": "You need to take 6 medications",
                    "detailed_schedule": [...],
                    "key_reminders": [...]
                },
                "follow_up_plan": {
                    "summary": "3 follow-up appointments scheduled",
                    "appointments": [...],
                    "what_to_bring": [...]
                },
                "activity_guidelines": {
                    "summary": "Important activities to do and avoid",
                    "dos": [...],
                    "donts": [...],
                    "duration": "..."
                },
                "warning_signs": {
                    "summary": "Call doctor immediately if you notice:",
                    "signs": [...]
                },
                "recovery_timeline": "...",
                "score_impact": 0,  # Always 0 - informational only
                "summary": "..."
            }
        """

        try:
            # Extract medication schedule
            medication_schedule = self._format_medication_schedule(
                discharge_summary.get('medications', [])
            )

            # Extract follow-up plan
            follow_up_plan = self._format_follow_up_plan(
                discharge_summary.get('follow_up_schedule', [])
            )

            # Extract activity guidelines
            activity_guidelines = self._format_activity_guidelines(
                discharge_summary.get('activity_restrictions', {})
            )

            # Extract warning signs
            warning_signs = self._format_warning_signs(
                discharge_summary.get('warning_signs', [])
            )

            # Generate recovery timeline using LLM
            recovery_timeline = self._generate_recovery_timeline(
                discharge_summary,
                procedure_type
            )

            # Determine completeness
            status = self._determine_completeness(
                medication_schedule,
                follow_up_plan,
                activity_guidelines,
                warning_signs
            )

            # Generate summary
            summary = self._generate_summary(
                status,
                len(discharge_summary.get('medications', [])),
                len(discharge_summary.get('follow_up_schedule', [])),
                len(discharge_summary.get('warning_signs', []))
            )

            return {
                "status": status,
                "medication_schedule": medication_schedule,
                "follow_up_plan": follow_up_plan,
                "activity_guidelines": activity_guidelines,
                "warning_signs": warning_signs,
                "recovery_timeline": recovery_timeline,
                "score_impact": 0,  # Informational only
                "summary": summary
            }

        except Exception as e:
            return {
                "status": "error",
                "medication_schedule": {},
                "follow_up_plan": {},
                "activity_guidelines": {},
                "warning_signs": {},
                "recovery_timeline": "",
                "score_impact": 0,
                "summary": f"Error generating medical guidance: {str(e)}"
            }

    def _format_medication_schedule(self, medications: List[Dict]) -> Dict:
        """Format medication schedule into patient-friendly format"""

        if not medications:
            return {
                "summary": "No medications prescribed",
                "detailed_schedule": [],
                "key_reminders": []
            }

        summary = f"You need to take {len(medications)} medication(s)"

        detailed_schedule = []
        for med in medications:
            med_info = {
                "name": med.get('name', 'Unknown medication'),
                "dosage": med.get('dosage', 'As prescribed'),
                "duration": med.get('duration', 'As directed'),
                "purpose": med.get('purpose', 'As directed by doctor'),
                "patient_instruction": self._format_medication_instruction(med)
            }
            detailed_schedule.append(med_info)

        # Key reminders
        key_reminders = [
            "Take medications exactly as prescribed",
            "Wash hands before applying eye drops" if any('eye' in m.get('name', '').lower() for m in medications) else "Take with food if stomach upset occurs",
            "Do not stop medications without consulting your doctor",
            "Set reminders to avoid missing doses"
        ]

        return {
            "summary": summary,
            "detailed_schedule": detailed_schedule,
            "key_reminders": key_reminders
        }

    def _format_medication_instruction(self, medication: Dict) -> str:
        """Format single medication into patient instruction"""
        name = medication.get('name', 'Unknown')
        dosage = medication.get('dosage', 'As prescribed')
        duration = medication.get('duration', 'As directed')

        return f"Take {name} - {dosage} for {duration}"

    def _format_follow_up_plan(self, appointments: List[Dict]) -> Dict:
        """Format follow-up appointments"""

        if not appointments:
            return {
                "summary": "No follow-up appointments documented",
                "appointments": [],
                "what_to_bring": []
            }

        summary = f"{len(appointments)} follow-up appointment(s) scheduled"

        formatted_appointments = []
        for appt in appointments:
            formatted_appointments.append({
                "timing": appt.get('timing', 'TBD'),
                "purpose": appt.get('purpose', 'General check-up'),
                "important": "Day 1" in appt.get('timing', '') or "Tomorrow" in appt.get('timing', '')
            })

        what_to_bring = [
            "This discharge summary",
            "All medications you are taking",
            "Insurance card and ID",
            "List of any questions or concerns"
        ]

        return {
            "summary": summary,
            "appointments": formatted_appointments,
            "what_to_bring": what_to_bring
        }

    def _format_activity_guidelines(self, restrictions: Dict) -> Dict:
        """Format activity restrictions"""

        dos = restrictions.get('dos', [])
        donts = restrictions.get('donts', [])

        if not dos and not donts:
            return {
                "summary": "No specific activity restrictions documented",
                "dos": [],
                "donts": [],
                "duration": "Follow doctor's advice"
            }

        summary = f"{len(dos)} recommended activities, {len(donts)} activities to avoid"

        # Determine duration from donts text
        duration = "Follow for at least 2-4 weeks"
        for dont in donts:
            if 'week' in dont.lower():
                duration = "As specified in restrictions"
                break

        return {
            "summary": summary,
            "dos": dos,
            "donts": donts,
            "duration": duration
        }

    def _format_warning_signs(self, signs: List) -> Dict:
        """Format warning signs"""

        if not signs:
            return {
                "summary": "No specific warning signs documented",
                "signs": []
            }

        summary = "Call your doctor immediately if you notice:"

        return {
            "summary": summary,
            "signs": signs
        }

    def _generate_recovery_timeline(self, discharge_summary: Dict, procedure_type: str) -> str:
        """Use LLM to generate recovery timeline based on discharge info"""

        discharge_condition = discharge_summary.get('discharge_condition', '')
        complications = discharge_summary.get('complications', '')
        days_stayed = discharge_summary.get('days_stayed', 0)

        if not discharge_condition:
            return "Recovery timeline not available. Follow your doctor's guidance."

        # Build prompt
        prompt = f"""Based on this discharge information, generate a brief patient-friendly recovery timeline (2-3 sentences).

DISCHARGE CONDITION:
{discharge_condition[:500]}

COMPLICATIONS (if any):
{complications[:300] if complications else 'None documented'}

DAYS HOSPITALIZED: {days_stayed}

Generate a simple timeline telling the patient:
1. What to expect in the first week
2. When they should feel better
3. When they can return to normal activities

Keep it encouraging and realistic. Use plain language. 2-3 sentences maximum.

Example: "You should notice improvement in vision over the next 1-2 weeks. Most patients feel comfortable returning to light activities within a week. Full recovery typically takes 4-6 weeks."
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                temperature=0.5,  # Slightly higher for natural language
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            timeline = response.content[0].text.strip()
            return timeline

        except Exception as e:
            return "Recovery timeline: Follow your doctor's guidance for activity resumption."

    def _determine_completeness(
        self,
        medication_schedule: Dict,
        follow_up_plan: Dict,
        activity_guidelines: Dict,
        warning_signs: Dict
    ) -> str:
        """Determine if guidance is complete, partial, or incomplete"""

        has_medications = len(medication_schedule.get('detailed_schedule', [])) > 0
        has_follow_up = len(follow_up_plan.get('appointments', [])) > 0
        has_activities = len(activity_guidelines.get('dos', [])) > 0 or len(activity_guidelines.get('donts', [])) > 0
        has_warnings = len(warning_signs.get('signs', [])) > 0

        complete_sections = sum([has_medications, has_follow_up, has_activities, has_warnings])

        if complete_sections == 4:
            return "complete"
        elif complete_sections >= 2:
            return "partial"
        else:
            return "incomplete"

    def _generate_summary(
        self,
        status: str,
        med_count: int,
        appt_count: int,
        warning_count: int
    ) -> str:
        """Generate summary of medical guidance"""

        if status == "complete":
            return f"Complete discharge guidance extracted: {med_count} medication(s), {appt_count} follow-up appointment(s), {warning_count} warning sign(s) documented."
        elif status == "partial":
            return f"Partial discharge guidance available: {med_count} medication(s), {appt_count} follow-up appointment(s). Some sections may be incomplete."
        else:
            return "Limited discharge guidance available. Please consult your discharge summary document for complete instructions."


# Test function
def test_medical_guidance_generator():
    """Test the medical guidance generator"""

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Check for API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("[ERROR] ANTHROPIC_API_KEY not set. Skipping LLM test.")
        return

    agent = MedicalGuidanceGenerator()

    # Sample discharge summary (from our extraction)
    discharge_summary = {
        "medications": [
            {
                "name": "Moxifloxacin 0.5% Eye Drops",
                "dosage": "1 drop in right eye, 4 times daily",
                "duration": "7 days",
                "purpose": "Antibiotic prophylaxis"
            },
            {
                "name": "Prednisolone Acetate 1% Eye Drops",
                "dosage": "1 drop in right eye, 4 times daily, tapering",
                "duration": "4 weeks with gradual tapering",
                "purpose": "Control post-operative inflammation"
            },
            {
                "name": "Carboxymethylcellulose 0.5% Eye Drops",
                "dosage": "As needed, up to 6 times daily",
                "duration": "As required",
                "purpose": "Lubrication"
            }
        ],
        "follow_up_schedule": [
            {
                "timing": "Day 1 Post-Discharge (Tomorrow)",
                "purpose": "Post-operative check-up, Eye examination and pressure check"
            },
            {
                "timing": "Day 7 Post-Surgery",
                "purpose": "Detailed eye examination, Visual acuity assessment"
            },
            {
                "timing": "Week 4 Post-Surgery",
                "purpose": "Final post-operative assessment"
            }
        ],
        "activity_restrictions": {
            "dos": [
                "Wear the protective eye shield while sleeping for 1 week",
                "Use sunglasses when outdoors",
                "Take medications as prescribed",
                "Wash hands before instilling eye drops"
            ],
            "donts": [
                "Do NOT rub, press, or touch the operated eye",
                "Do NOT splash water directly into the eye while bathing",
                "Do NOT swim or go for water sports for 4 weeks",
                "Do NOT lift heavy weights (>5 kg) for 2 weeks"
            ]
        },
        "warning_signs": [
            "Sudden decrease or loss of vision",
            "Severe eye pain not relieved by prescribed medications",
            "Increasing redness of the eye",
            "Yellow or green discharge from the eye"
        ],
        "discharge_condition": "Patient discharged in stable condition with significantly improved vision in operated right eye. Visual Acuity at Discharge: Right Eye (operated): 6/18 (improving, expected to reach 6/6 with refractive correction after 4-6 weeks)",
        "complications": "Post-operative nausea and vomiting (PONV) managed successfully",
        "days_stayed": 2
    }

    print("="*80)
    print("TESTING MEDICAL GUIDANCE GENERATOR (LLM)")
    print("="*80)

    result = agent.generate(discharge_summary, procedure_type="cataract_surgery")

    print("\n[STATUS]:", result['status'].upper())
    print("[SCORE IMPACT]:", result['score_impact'])

    print("\n[MEDICATION SCHEDULE]")
    print(f"Summary: {result['medication_schedule']['summary']}")
    print("\nDetailed Schedule:")
    for i, med in enumerate(result['medication_schedule']['detailed_schedule'], 1):
        print(f"  {i}. {med['patient_instruction']}")
        print(f"     Purpose: {med['purpose']}")

    print("\n[FOLLOW-UP PLAN]")
    print(f"Summary: {result['follow_up_plan']['summary']}")
    print("\nAppointments:")
    for i, appt in enumerate(result['follow_up_plan']['appointments'], 1):
        priority = " [IMPORTANT]" if appt.get('important') else ""
        print(f"  {i}. {appt['timing']}{priority}")
        print(f"     {appt['purpose']}")

    print("\n[ACTIVITY GUIDELINES]")
    print(f"Summary: {result['activity_guidelines']['summary']}")
    print(f"\nDO's ({len(result['activity_guidelines']['dos'])} items):")
    for i, do in enumerate(result['activity_guidelines']['dos'][:3], 1):
        print(f"  {i}. {do}")
    print(f"\nDON'Ts ({len(result['activity_guidelines']['donts'])} items):")
    for i, dont in enumerate(result['activity_guidelines']['donts'][:3], 1):
        print(f"  {i}. {dont}")

    print("\n[WARNING SIGNS]")
    print(result['warning_signs']['summary'])
    for i, sign in enumerate(result['warning_signs']['signs'][:4], 1):
        print(f"  {i}. {sign}")

    print("\n[RECOVERY TIMELINE]")
    print(result['recovery_timeline'])

    print("\n[SUMMARY]")
    print(result['summary'])

    print("\n" + "="*80)
    print("[OK] Test completed")
    print("="*80)


if __name__ == "__main__":
    test_medical_guidance_generator()
