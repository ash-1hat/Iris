"""
Phase 1 Integration Tests
Tests data loaders, models, and PDF extraction
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    try:
        from src.models.schemas import (
            MedicalNote, PatientInfo, PreAuthRequest, ValidationResult
        )
        from src.utils.data_loader import (
            load_procedure_registry, load_policy_data, load_procedure_data,
            get_procedure_by_id, get_procedure_by_synonym
        )
        from src.utils.llm_client import get_llm_client, validate_api_key
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_procedure_registry():
    """Test procedure registry loading"""
    print("\nTesting procedure registry...")
    try:
        from src.utils.data_loader import load_procedure_registry, get_procedure_by_id

        registry = load_procedure_registry()
        print(f"✓ Loaded {len(registry)} procedures from registry")

        # Test getting specific procedure
        cataract = get_procedure_by_id("cataract_surgery")
        if cataract:
            print(f"✓ Found procedure: {cataract.user_display_name}")
            print(f"  - Medical file: {cataract.medical_data_file}")
            print(f"  - Synonyms: {', '.join(cataract.common_synonyms[:3])}")
        else:
            print("✗ Could not find cataract_surgery")
            return False

        return True
    except Exception as e:
        print(f"✗ Registry test failed: {e}")
        return False


def test_procedure_data_loading():
    """Test medical procedure data loading"""
    print("\nTesting procedure data loading...")
    try:
        from src.utils.data_loader import load_procedure_data

        # Test loading cataract data
        cataract_data = load_procedure_data("cataract_surgery")
        print(f"✓ Loaded cataract procedure data")
        print(f"  - Category: {cataract_data.metadata.get('category')}")

        # Check cost analysis structure
        if 'cost_analysis' in cataract_data.model_dump():
            cost_data = cataract_data.cost_analysis
            if 'india_tier1_cities' in cost_data:
                overall_range = cost_data['india_tier1_cities'].get('overall_range', {})
                print(f"  - Cost range: ₹{overall_range.get('minimum'):,} - ₹{overall_range.get('maximum'):,}")
            else:
                print("  ⚠ Cost analysis structure different than expected")

        # Check if FWA patterns exist
        if 'fraud_waste_abuse_patterns' in cataract_data.model_dump():
            print(f"  - Has FWA detection patterns: ✓")
        else:
            print(f"  - FWA patterns missing (OK for smaller procedures)")

        return True
    except Exception as e:
        print(f"✗ Procedure data loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_policy_data_loading():
    """Test policy data loading"""
    print("\nTesting policy data loading...")
    try:
        from src.utils.data_loader import load_policy_data, get_waiting_period_for_procedure

        # Test Star Health Comprehensive
        policy = load_policy_data("Star Health", "Comprehensive")
        print(f"✓ Loaded policy: {policy.policy_name}")
        print(f"  - Insurer: {policy.insurer}")
        print(f"  - Initial waiting period: {policy.waiting_periods.get('initial_days')} days")

        # Test waiting period lookup
        cataract_waiting = get_waiting_period_for_procedure(policy, "cataract_surgery")
        if cataract_waiting:
            print(f"  - Cataract waiting period: {cataract_waiting} months")
        else:
            print(f"  ⚠ Could not find cataract waiting period")

        # Check coverage structure
        if '500000' in policy.coverage_by_sum_insured:
            coverage_500k = policy.coverage_by_sum_insured['500000']
            room_rent = coverage_500k.get('room_rent_max_per_day')
            print(f"  - Room rent limit (5L SI): ₹{room_rent}/day")

        return True
    except Exception as e:
        print(f"✗ Policy data loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_synonym_matching():
    """Test procedure matching by synonyms"""
    print("\nTesting synonym matching...")
    try:
        from src.utils.data_loader import get_procedure_by_synonym

        test_cases = [
            ("Cataract Surgery", "cataract_surgery"),
            ("phaco", "cataract_surgery"),
            ("TKR", "total_knee_replacement"),
            ("Lap appy", "appendectomy"),
        ]

        all_passed = True
        for user_input, expected_id in test_cases:
            result = get_procedure_by_synonym(user_input)
            if result and result.procedure_id == expected_id:
                print(f"✓ '{user_input}' → {result.user_display_name}")
            else:
                print(f"✗ '{user_input}' failed to match")
                all_passed = False

        return all_passed
    except Exception as e:
        print(f"✗ Synonym matching failed: {e}")
        return False


def test_pydantic_models():
    """Test Pydantic model validation"""
    print("\nTesting Pydantic models...")
    try:
        from src.models.schemas import PatientInfo, DiagnosisInfo, MedicalNote

        # Test PatientInfo
        patient = PatientInfo(
            name="Test Patient",
            age=65,
            gender="Male",
            contact_number="9876543210"
        )
        print(f"✓ PatientInfo model works")

        # Test DiagnosisInfo
        diagnosis = DiagnosisInfo(
            primary_diagnosis="Senile Cataract",
            icd_10_code="H25.9",
            diagnosis_date="2024-01-15"
        )
        print(f"✓ DiagnosisInfo model works")

        return True
    except Exception as e:
        print(f"✗ Pydantic model test failed: {e}")
        return False


def test_llm_client():
    """Test LLM client setup (without making actual API call)"""
    print("\nTesting LLM client setup...")
    try:
        from src.utils.llm_client import validate_api_key

        has_api_key = validate_api_key()
        if has_api_key:
            print("✓ ANTHROPIC_API_KEY is set and valid")
        else:
            print("⚠ ANTHROPIC_API_KEY not set (required for PDF extraction and agents)")
            print("  Set it in .env file to use LLM features")

        return True  # Don't fail if API key not set, just warn
    except Exception as e:
        print(f"✗ LLM client test failed: {e}")
        return False


def test_data_consistency():
    """Test consistency between registry and actual files"""
    print("\nTesting data consistency...")
    try:
        from src.utils.data_loader import load_procedure_registry
        from pathlib import Path

        registry = load_procedure_registry()
        medical_data_dir = Path("medical_data")

        all_consistent = True
        for entry in registry:
            medical_file = medical_data_dir / entry.medical_data_file
            if not medical_file.exists():
                print(f"✗ Missing file: {entry.medical_data_file}")
                all_consistent = False

        if all_consistent:
            print(f"✓ All {len(registry)} medical data files exist")

        return all_consistent
    except Exception as e:
        print(f"✗ Consistency test failed: {e}")
        return False


def run_all_tests():
    """Run all Phase 1 tests"""
    print("=" * 60)
    print("PHASE 1 VALIDATION TESTS")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("Procedure Registry", test_procedure_registry),
        ("Procedure Data Loading", test_procedure_data_loading),
        ("Policy Data Loading", test_policy_data_loading),
        ("Synonym Matching", test_synonym_matching),
        ("Pydantic Models", test_pydantic_models),
        ("LLM Client Setup", test_llm_client),
        ("Data Consistency", test_data_consistency),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n✗ {name} crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:10} {name}")

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("🎉 Phase 1 COMPLETE - Ready for Phase 2!")
    elif passed_count >= total_count - 1:
        print("⚠️  Phase 1 MOSTLY COMPLETE - Review warnings before Phase 2")
    else:
        print("❌ Phase 1 INCOMPLETE - Fix errors before proceeding")

    print("=" * 60)

    return passed_count == total_count


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
