"""
Data loading utilities for ClaimReady
Handles loading and caching of policy, procedure, and registry data
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from functools import lru_cache

from src.models.schemas import ProcedureData, PolicyData, ProcedureRegistryEntry


# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent


# ============================================================================
# PROCEDURE REGISTRY
# ============================================================================

@lru_cache(maxsize=1)
def load_procedure_registry() -> List[ProcedureRegistryEntry]:
    """
    Load procedure registry from data/procedure_registry.json
    Cached to avoid repeated file reads

    Returns:
        List of ProcedureRegistryEntry objects
    """
    registry_path = PROJECT_ROOT / "data" / "procedure_registry.json"

    if not registry_path.exists():
        raise FileNotFoundError(f"Procedure registry not found at {registry_path}")

    with open(registry_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [ProcedureRegistryEntry(**entry) for entry in data["procedures"]]


def get_procedure_by_id(procedure_id: str) -> Optional[ProcedureRegistryEntry]:
    """
    Get procedure registry entry by procedure_id

    Args:
        procedure_id: Procedure identifier (e.g., "cataract_surgery")

    Returns:
        ProcedureRegistryEntry or None if not found
    """
    registry = load_procedure_registry()

    for entry in registry:
        if entry.procedure_id == procedure_id:
            return entry

    return None


def get_procedure_by_synonym(user_input: str) -> Optional[ProcedureRegistryEntry]:
    """
    Match procedure by user input using common_synonyms
    Case-insensitive matching

    Args:
        user_input: User's procedure name input

    Returns:
        ProcedureRegistryEntry or None if no match found
    """
    registry = load_procedure_registry()
    user_input_lower = user_input.lower()

    for entry in registry:
        # Check exact match with display name
        if entry.user_display_name.lower() == user_input_lower:
            return entry

        # Check synonyms
        for synonym in entry.common_synonyms:
            if synonym.lower() == user_input_lower:
                return entry

    return None


# ============================================================================
# MEDICAL PROCEDURE DATA
# ============================================================================

@lru_cache(maxsize=20)
def load_procedure_data(procedure_id: str) -> ProcedureData:
    """
    Load detailed medical procedure data from medical_data/*.json

    Args:
        procedure_id: Procedure identifier (e.g., "cataract_surgery")

    Returns:
        ProcedureData object

    Raises:
        FileNotFoundError: If medical data file doesn't exist
        KeyError: If procedure_id not in registry
    """
    # Get the filename from registry
    registry_entry = get_procedure_by_id(procedure_id)
    if not registry_entry:
        raise KeyError(f"Procedure '{procedure_id}' not found in registry")

    medical_data_path = PROJECT_ROOT / "medical_data" / registry_entry.medical_data_file

    if not medical_data_path.exists():
        raise FileNotFoundError(f"Medical data file not found: {medical_data_path}")

    with open(medical_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Add procedure_id to the data
    data["procedure_id"] = procedure_id

    return ProcedureData(**data)


# ============================================================================
# POLICY DATA
# ============================================================================

def _normalize_policy_filename(insurer: str, policy_type: str) -> str:
    """
    Normalize insurer and policy type to match filenames

    Args:
        insurer: e.g., "Star Health", "HDFC ERGO", "Bajaj Allianz"
        policy_type: e.g., "Comprehensive", "Family Optima", "Healthcare"

    Returns:
        Normalized filename (e.g., "star_comprehensive.json")
    """
    # Map insurer names to file prefixes
    insurer_map = {
        "star health": "star",
        "star health and allied insurance": "star",
        "hdfc ergo": "hdfcergo",
        "hdfc ergo general insurance": "hdfcergo",
        "bajaj allianz": "bajaj",
        "bajaj allianz general insurance": "bajaj"
    }

    # Map policy types to file suffixes
    policy_map = {
        "comprehensive": "comprehensive",
        "comprehensive insurance policy": "comprehensive",
        "star comprehensive insurance policy": "comprehensive",
        "family optima": "familyoptima",
        "family health optima": "familyoptima",
        "family health optima insurance plan": "familyoptima",
        "healthcare": "healthcare",
        "my health care plan": "healthcare",
        "my health care plan-1": "healthcare",
        "my:optima secure": "myoptima",
        "optima secure": "myoptima"
    }

    insurer_key = insurer.lower().strip()
    policy_key = policy_type.lower().strip()

    insurer_prefix = insurer_map.get(insurer_key, insurer_key.replace(" ", ""))
    policy_suffix = policy_map.get(policy_key, policy_key.replace(" ", ""))

    return f"{insurer_prefix}_{policy_suffix}.json"


@lru_cache(maxsize=10)
def load_policy_data(insurer: str, policy_type: str) -> PolicyData:
    """
    Load policy data from policy_data/*.json

    Args:
        insurer: Insurance company name
        policy_type: Policy product name

    Returns:
        PolicyData object

    Raises:
        FileNotFoundError: If policy file doesn't exist
    """
    filename = _normalize_policy_filename(insurer, policy_type)
    policy_path = PROJECT_ROOT / "policy_data" / filename

    if not policy_path.exists():
        # Try to find similar filenames
        policy_dir = PROJECT_ROOT / "policy_data"
        available = [f.name for f in policy_dir.glob("*.json")] if policy_dir.exists() else []
        raise FileNotFoundError(
            f"Policy file not found: {filename}\n"
            f"Available policies: {', '.join(available)}"
        )

    with open(policy_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return PolicyData(**data)


def get_waiting_period_for_procedure(
    policy_data: PolicyData,
    procedure_id: str
) -> Optional[int]:
    """
    Get waiting period (in months) for a procedure from policy data
    Handles alternative keys and nested structure

    Args:
        policy_data: Loaded policy data
        procedure_id: Procedure identifier

    Returns:
        Waiting period in months, or None if no specific waiting period
    """
    # Get procedure registry entry for alternative keys
    registry_entry = get_procedure_by_id(procedure_id)
    if not registry_entry:
        return None

    # Get the waiting period key to look for
    primary_key = registry_entry.policy_waiting_period_key
    alternative_keys = registry_entry.alternative_keys or []

    # Check in specific_conditions (nested structure)
    if "specific_conditions" in policy_data.waiting_periods:
        conditions = policy_data.waiting_periods["specific_conditions"]

        # Try primary key first
        if primary_key and primary_key in conditions:
            return conditions[primary_key]

        # Try alternative keys
        for alt_key in alternative_keys:
            if alt_key in conditions:
                return conditions[alt_key]

    return None


def check_procedure_excluded(
    policy_data: PolicyData,
    procedure_id: str,
    diagnosis: str = ""
) -> bool:
    """
    Check if procedure is excluded by policy
    Uses exclusion keywords from procedure registry

    Args:
        policy_data: Loaded policy data
        procedure_id: Procedure identifier
        diagnosis: Optional diagnosis text for context

    Returns:
        True if procedure is excluded, False otherwise
    """
    registry_entry = get_procedure_by_id(procedure_id)
    if not registry_entry:
        return False

    exclusion_keywords = registry_entry.policy_exclusion_keywords or []

    # Check if any exclusion keyword appears in policy exclusions
    diagnosis_lower = diagnosis.lower()

    for exclusion in policy_data.exclusions:
        exclusion_lower = exclusion.lower()

        for keyword in exclusion_keywords:
            keyword_lower = keyword.lower()

            # Check if keyword in policy exclusion OR in diagnosis
            if keyword_lower in exclusion_lower:
                # If keyword found in exclusions, check diagnosis context
                if diagnosis_lower and keyword_lower in diagnosis_lower:
                    return True
                # If keyword is generic (like "cosmetic"), consider excluded
                elif keyword_lower in ["cosmetic", "experimental", "unproven"]:
                    return True

    return False


def get_room_rent_limit(policy_data: PolicyData, sum_insured: int) -> Optional[float]:
    """
    Get room rent limit per day for given sum insured

    Args:
        policy_data: Loaded policy data
        sum_insured: Sum insured amount

    Returns:
        Room rent limit per day in INR, or None if not found
    """
    sum_insured_str = str(sum_insured)

    if sum_insured_str in policy_data.coverage_by_sum_insured:
        coverage = policy_data.coverage_by_sum_insured[sum_insured_str]
        return coverage.get("room_rent_max_per_day")

    return None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def list_available_procedures() -> List[Dict[str, str]]:
    """
    List all available procedures with display names
    Useful for UI dropdowns

    Returns:
        List of dicts with procedure_id, display_name, synonyms
    """
    registry = load_procedure_registry()

    return [
        {
            "procedure_id": entry.procedure_id,
            "display_name": entry.user_display_name,
            "synonyms": ", ".join(entry.common_synonyms[:3])  # First 3 synonyms
        }
        for entry in registry
    ]


def list_available_policies() -> List[Dict[str, str]]:
    """
    List all available policies by scanning policy_data/ directory

    Returns:
        List of dicts with insurer, policy_type, filename
    """
    policy_dir = PROJECT_ROOT / "policy_data"

    if not policy_dir.exists():
        return []

    policies = []
    for policy_file in policy_dir.glob("*.json"):
        try:
            with open(policy_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            policies.append({
                "insurer": data.get("insurer", "Unknown"),
                "policy_name": data.get("policy_name", "Unknown"),
                "filename": policy_file.name
            })
        except Exception:
            continue

    return policies
