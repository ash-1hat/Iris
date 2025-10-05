"""
Claim Storage Service
Saves pre-authorization validation results for later discharge validation
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import random


class ClaimStorageService:
    """
    Service to save and retrieve pre-authorization claims

    Saved claims can be loaded later during discharge validation
    to compare actual costs against pre-auth estimates
    """

    def __init__(self, storage_dir: str = None):
        """
        Initialize claim storage service

        Args:
            storage_dir: Directory to store claim JSON files
        """
        if storage_dir is None:
            # Default to data/stored_claims/ in project root
            project_root = Path(__file__).parent.parent.parent
            storage_dir = project_root / "data" / "stored_claims"

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def generate_claim_id(self) -> str:
        """
        Generate unique claim ID

        Format: CR-YYYYMMDD-XXXXX
        where XXXXX is 5-digit random number

        Returns:
            Claim ID string

        Example:
            "CR-20251005-12345"
        """
        date_str = datetime.now().strftime("%Y%m%d")
        random_num = random.randint(10000, 99999)
        claim_id = f"CR-{date_str}-{random_num}"

        # Ensure uniqueness - regenerate if file exists
        while (self.storage_dir / f"{claim_id}.json").exists():
            random_num = random.randint(10000, 99999)
            claim_id = f"CR-{date_str}-{random_num}"

        return claim_id

    def save_claim(
        self,
        validation_result,
        form_data: Dict,
        medical_note: Dict
    ) -> str:
        """
        Save pre-authorization validation result

        Args:
            validation_result: Complete validation result (Pydantic ValidationResult object or dict)
            form_data: Original form input data
            medical_note: Extracted medical note data

        Returns:
            Generated claim ID

        Example:
            claim_id = storage.save_claim(result, form_data, medical_note)
            # Returns: "CR-20251005-12345"
        """
        claim_id = self.generate_claim_id()

        # Handle Pydantic object or dict
        if hasattr(validation_result, 'final_score'):
            # It's a Pydantic ValidationResult object
            validation_score = validation_result.final_score
            readiness_status = validation_result.overall_status
        else:
            # It's a dict
            validation_score = validation_result.get("overall_score", 0)
            readiness_status = validation_result.get("readiness_status", "unknown")

        # Build claim record
        claim_record = {
            "claim_id": claim_id,
            "timestamp": datetime.now().isoformat(),
            "validation_score": validation_score,
            "readiness_status": readiness_status,

            # Patient information
            "patient_info": {
                "name": medical_note.get("patient_info", {}).get("name", "Unknown"),
                "age": medical_note.get("patient_info", {}).get("age"),
                "gender": medical_note.get("patient_info", {}).get("gender"),
                "contact": medical_note.get("patient_info", {}).get("contact_number"),
            },

            # Policy information
            "policy_info": {
                "insurer": form_data.get("insurer"),
                "policy_type": form_data.get("policy_type"),
                "policy_number": form_data.get("policy_number"),
                "sum_insured": form_data.get("sum_insured"),
                "policy_start_date": form_data.get("policy_start_date"),
            },

            # Procedure information
            "procedure_info": {
                "procedure_id": form_data.get("procedure_id"),
                "diagnosis": medical_note.get("diagnosis", {}).get("primary_diagnosis"),
                "icd_code": medical_note.get("diagnosis", {}).get("icd_10_code"),
                "planned_admission_date": form_data.get("planned_admission_date"),
                "expected_stay_days": medical_note.get("hospitalization_details", {}).get("expected_length_of_stay", 1),
                "room_type": medical_note.get("hospitalization_details", {}).get("hospitalization_type", "Unknown"),
            },

            # Hospital information
            "hospital_info": {
                "name": medical_note.get("hospital_details", {}).get("name"),
                "address": medical_note.get("hospital_details", {}).get("address"),
            },

            # Doctor information
            "doctor_info": {
                "name": medical_note.get("doctor_details", {}).get("name"),
                "qualification": medical_note.get("doctor_details", {}).get("qualification"),
                "registration_number": medical_note.get("doctor_details", {}).get("registration_number"),
            },

            # Expected costs (from pre-auth)
            "expected_costs": {
                "room_charges": medical_note.get("cost_breakdown", {}).get("room_charges", 0),
                "surgeon_fees": medical_note.get("cost_breakdown", {}).get("surgeon_fees", 0),
                "anesthetist_fees": medical_note.get("cost_breakdown", {}).get("anesthetist_fees", 0),
                "ot_charges": medical_note.get("cost_breakdown", {}).get("ot_charges", 0),
                "icu_charges": medical_note.get("cost_breakdown", {}).get("icu_charges", 0),
                "investigations": medical_note.get("cost_breakdown", {}).get("investigations", 0),
                "medicines_consumables": medical_note.get("cost_breakdown", {}).get("medicines_consumables", 0),
                "implants": medical_note.get("cost_breakdown", {}).get("implants", 0),
                "other_charges": medical_note.get("cost_breakdown", {}).get("other_charges", 0),
                "total_estimated_cost": medical_note.get("cost_breakdown", {}).get("total_estimated_cost", 0),
            },

            # Validation results summary
            "validation_summary": {
                "completeness_status": getattr(validation_result.agent_results.completeness, 'status', 'unknown') if hasattr(validation_result, 'agent_results') else 'unknown',
                "policy_status": getattr(validation_result.agent_results.policy, 'status', 'unknown') if hasattr(validation_result, 'agent_results') else 'unknown',
                "medical_review_status": getattr(validation_result.agent_results.medical, 'status', 'unknown') if hasattr(validation_result, 'agent_results') else 'unknown',
                "fwa_status": getattr(validation_result.agent_results.fwa, 'status', 'unknown') if hasattr(validation_result, 'agent_results') else 'unknown',
            },
        }

        # Save to JSON file
        file_path = self.storage_dir / f"{claim_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(claim_record, f, indent=2, ensure_ascii=False)

        return claim_id

    def load_claim(self, claim_id: str) -> Optional[Dict]:
        """
        Load saved claim by ID

        Args:
            claim_id: Claim ID to load

        Returns:
            Claim record dict if found, None otherwise

        Example:
            claim = storage.load_claim("CR-20251005-12345")
        """
        file_path = self.storage_dir / f"{claim_id}.json"

        if not file_path.exists():
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_all_claims(self) -> list:
        """
        List all saved claims

        Returns:
            List of claim IDs

        Example:
            claims = storage.list_all_claims()
            # Returns: ["CR-20251005-12345", "CR-20251006-67890"]
        """
        claim_files = self.storage_dir.glob("CR-*.json")
        claim_ids = [f.stem for f in claim_files]
        return sorted(claim_ids, reverse=True)  # Most recent first
