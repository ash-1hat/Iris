"""
Pydantic models for ClaimReady API
Defines data contracts for validation requests and responses
"""

from datetime import date, datetime
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, EmailStr


# ============================================================================
# MEDICAL NOTE EXTRACTION
# ============================================================================

class PatientInfo(BaseModel):
    """Section A: Patient Information"""
    name: str
    age: int
    gender: Literal["Male", "Female", "Other"]
    patient_id: Optional[str] = None
    contact_number: Optional[str] = None


class DiagnosisInfo(BaseModel):
    """Section B: Diagnosis"""
    primary_diagnosis: str
    icd_10_code: str
    diagnosis_date: Optional[str] = None
    secondary_diagnoses: Optional[List[str]] = None


class ClinicalHistory(BaseModel):
    """Section C: Clinical History"""
    chief_complaints: str
    duration_of_symptoms: Optional[str] = None
    relevant_medical_history: Optional[str] = None
    comorbidities: Optional[List[str]] = None


class DiagnosticTest(BaseModel):
    """Single diagnostic test entry"""
    test_name: str
    date_performed: Optional[str] = None
    key_findings: Optional[str] = None


class ProposedTreatment(BaseModel):
    """Section E: Proposed Treatment"""
    procedure_name: str
    procedure_code: Optional[str] = None
    surgical_approach: Optional[str] = None
    anesthesia_type: Optional[Literal["General", "Spinal", "Local", "Regional"]] = None


class MedicalJustification(BaseModel):
    """Section F: Medical Justification"""
    why_hospitalization_required: str
    why_treatment_necessary: str
    how_treatment_addresses_diagnosis: Optional[str] = None
    expected_outcomes: Optional[str] = None


class HospitalizationDetails(BaseModel):
    """Section G: Hospitalization Details"""
    planned_admission_date: str
    expected_length_of_stay: int  # days
    icu_required: bool = False
    icu_duration: Optional[int] = None  # days
    hospitalization_type: Optional[Literal["Emergency", "Planned"]] = None


class CostBreakdown(BaseModel):
    """Section H: Cost Breakdown"""
    room_charges: float
    surgeon_fees: float
    anesthetist_fees: float
    ot_charges: float
    icu_charges: Optional[float] = 0.0
    investigations: float
    medicines_consumables: float
    implants: Optional[float] = 0.0
    other_charges: Optional[float] = 0.0
    total_estimated_cost: float


class DoctorDetails(BaseModel):
    """Section I: Doctor Details"""
    name: str
    qualification: Optional[str] = None
    specialty: Optional[str] = None
    registration_number: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class HospitalDetails(BaseModel):
    """Section J: Hospital Details"""
    name: str
    address: Optional[str] = None
    registration_number: Optional[str] = None
    contact_number: Optional[str] = None


class MedicalNote(BaseModel):
    """Complete extracted medical note from PDF"""
    patient_info: PatientInfo
    diagnosis: DiagnosisInfo
    clinical_history: ClinicalHistory
    diagnostic_tests: Optional[List[DiagnosticTest]] = []
    proposed_treatment: ProposedTreatment
    medical_justification: MedicalJustification
    hospitalization_details: HospitalizationDetails
    cost_breakdown: CostBreakdown
    doctor_details: DoctorDetails
    hospital_details: HospitalDetails


# ============================================================================
# PRE-AUTH REQUEST
# ============================================================================

class PreAuthRequest(BaseModel):
    """Pre-authorization validation request"""
    # Policy Information
    insurer: str = Field(..., description="Insurance company name")
    policy_type: str = Field(..., description="Policy product name")
    policy_number: str = Field(..., description="Policy number")
    policy_start_date: str = Field(..., description="Policy start date (YYYY-MM-DD)")
    sum_insured: int = Field(..., description="Total sum insured in INR")
    previous_claims_total: Optional[int] = Field(0, description="Total previous claims in current policy year")

    # Procedure Information
    procedure_id: str = Field(..., description="Procedure identifier from registry")
    hospital_name: str = Field(..., description="Name of hospital")
    planned_admission_date: str = Field(..., description="Planned admission date (YYYY-MM-DD)")

    # Medical Note (extracted from PDF)
    medical_note: MedicalNote = Field(..., description="Extracted medical note data")

    # Optional metadata
    patient_age_at_policy_start: Optional[int] = None


# ============================================================================
# AGENT RESULTS
# ============================================================================

class CompletenessResult(BaseModel):
    """Result from Completeness Checker Agent"""
    status: Literal["pass", "fail"]
    issues: List[str] = []
    score_impact: int = Field(..., description="Score deduction (negative value)")


class PolicyViolation(BaseModel):
    """Single policy violation"""
    rule: str = Field(..., description="Rule name that was violated")
    severity: Literal["critical", "warning"]
    explanation: str = Field(..., description="What went wrong")
    suggestion: str = Field(..., description="How to fix it")


class PolicyValidationResult(BaseModel):
    """Result from Policy Validator Agent"""
    status: Literal["pass", "warning", "fail"]
    violations: List[PolicyViolation] = []
    score_impact: int


class MedicalConcern(BaseModel):
    """Single medical review concern"""
    type: str = Field(..., description="Type of concern (e.g., treatment_mismatch)")
    description: str = Field(..., description="Detailed description of the issue")
    suggestion: str = Field(..., description="What needs to be added/clarified")


class MedicalReviewResult(BaseModel):
    """Result from Medical Review Agent"""
    status: Literal["pass", "warning", "fail"]
    concerns: List[MedicalConcern] = []
    score_impact: int
    doctor_feedback_required: bool = False


class FWAFlag(BaseModel):
    """Single fraud/waste/abuse flag"""
    category: str = Field(..., description="Category of FWA (e.g., cost_inflation)")
    detail: str = Field(..., description="Specific issue detail")
    evidence: str = Field(..., description="What triggered this flag")
    insurer_action: str = Field(..., description="Likely insurer response")


class FWADetectionResult(BaseModel):
    """Result from FWA Detector Agent"""
    status: Literal["pass", "warning", "fail"]
    risk_level: Literal["low", "medium", "high"]
    flags: List[FWAFlag] = []
    score_impact: int


# ============================================================================
# AGGREGATED RESPONSE
# ============================================================================

class AgentResults(BaseModel):
    """Container for all individual agent results"""
    completeness: CompletenessResult
    policy: PolicyValidationResult
    medical: MedicalReviewResult
    fwa: FWADetectionResult


class ValidationResult(BaseModel):
    """Complete pre-authorization validation result"""
    overall_status: Literal["pass", "warning", "fail"]
    final_score: int = Field(..., ge=0, le=100, description="Final score (0-100)")
    approval_likelihood: Literal["high", "medium", "low"]

    # Individual agent results
    agent_results: AgentResults

    # Aggregated issues and recommendations
    all_issues: List[str] = Field(default_factory=list, description="All issues from all agents")
    recommendations: List[str] = Field(default_factory=list, description="Prioritized action items")

    # Summary
    summary: str = Field(..., description="Executive summary of validation")

    # Metadata
    validated_at: datetime = Field(default_factory=datetime.now)


# ============================================================================
# DATA MODELS FOR LOADED DATA
# ============================================================================

class ProcedureData(BaseModel):
    """Loaded procedure data from medical_data/*.json"""
    procedure_id: str
    metadata: Dict
    hospitalization: Dict
    cost_analysis: Dict
    medical_necessity: Dict
    required_diagnostics: Optional[Dict] = None
    fraud_waste_abuse_patterns: Optional[Dict] = None
    contextual_notes_for_llm: Optional[Dict] = None


class PolicyData(BaseModel):
    """Loaded policy data from policy_data/*.json"""
    policy_id: str
    insurer: str
    policy_name: str
    waiting_periods: Dict
    exclusions: List[str]
    coverage_by_sum_insured: Dict


class ProcedureRegistryEntry(BaseModel):
    """Single entry from procedure registry"""
    procedure_id: str
    user_display_name: str
    common_synonyms: List[str]
    icd_10_codes: List[str]
    medical_data_file: str
    policy_waiting_period_key: Optional[str] = None
    policy_exclusion_keywords: Optional[List[str]] = []
    alternative_keys: Optional[List[str]] = []
    notes: Optional[str] = None
