"""
Test script for new PRE-AUTHORIZATION REQUEST template PDF extraction
Tests the updated PDF extractor against the new template format
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.pdf_extractor import PDFExtractor
from src.models.schemas import MedicalNote


def test_extraction_from_template_text():
    """
    Test extraction from the new template text format
    Uses the medical_note_template.txt as test data
    """
    print("\n" + "=" * 80)
    print("TEST: Extraction from New Template Text")
    print("=" * 80)
    
    # Read the template file
    template_path = Path(__file__).parent.parent / "medical_note_template.txt"
    
    if not template_path.exists():
        print(f"❌ Template file not found: {template_path}")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template_text = f.read()
    
    # Initialize extractor
    extractor = PDFExtractor(enable_llm_fallback=False)
    
    try:
        # Extract medical note
        print("\n📄 Extracting from template text...")
        medical_note = extractor.extract_from_text(template_text)
        
        print("\n✅ Extraction successful!")
        print("\n" + "-" * 80)
        print("EXTRACTED DATA:")
        print("-" * 80)
        
        # === PATIENT INFO ===
        print("\n👤 PATIENT INFORMATION:")
        print(f"   Name: {medical_note.patient_info.name}")
        print(f"   Age: {medical_note.patient_info.age} years")
        print(f"   Gender: {medical_note.patient_info.gender}")
        print(f"   Contact: {medical_note.patient_info.contact_number or 'N/A'}")
        print(f"   Patient ID: {medical_note.patient_info.patient_id or 'N/A'}")
        
        # Assertions
        assert "Rajesh Kumar" in medical_note.patient_info.name, "Patient name not extracted correctly"
        assert medical_note.patient_info.age == 68, f"Age incorrect: {medical_note.patient_info.age}"
        assert medical_note.patient_info.gender == "Male", f"Gender incorrect: {medical_note.patient_info.gender}"
        assert medical_note.patient_info.contact_number == "9876543210", f"Contact incorrect: {medical_note.patient_info.contact_number}"
        print("   ✓ Patient info validated")
        
        # === DIAGNOSIS ===
        print("\n🏥 DIAGNOSIS:")
        print(f"   Primary: {medical_note.diagnosis.primary_diagnosis}")
        print(f"   ICD-10: {medical_note.diagnosis.icd_10_code}")
        print(f"   Date: {medical_note.diagnosis.diagnosis_date or 'N/A'}")
        
        # Assertions
        assert "cataract" in medical_note.diagnosis.primary_diagnosis.lower(), "Diagnosis not extracted"
        assert medical_note.diagnosis.icd_10_code == "H25.9", f"ICD code incorrect: {medical_note.diagnosis.icd_10_code}"
        assert medical_note.diagnosis.diagnosis_date == "10/08/2024", f"Diagnosis date incorrect"
        print("   ✓ Diagnosis validated")
        
        # === CLINICAL HISTORY ===
        print("\n📋 CLINICAL HISTORY:")
        print(f"   Complaints: {medical_note.clinical_history.chief_complaints[:100]}...")
        print(f"   Duration: {medical_note.clinical_history.duration_of_symptoms or 'N/A'}")
        print(f"   Comorbidities: {medical_note.clinical_history.comorbidities or 'None'}")
        
        # Assertions
        assert "vision loss" in medical_note.clinical_history.chief_complaints.lower(), "Complaints not extracted"
        assert medical_note.clinical_history.duration_of_symptoms == "540 days", f"Duration incorrect"
        assert "Diabetes" in str(medical_note.clinical_history.comorbidities), "Diabetes not detected"
        assert "Hypertension" in str(medical_note.clinical_history.comorbidities), "Hypertension not detected"
        print("   ✓ Clinical history validated")
        
        # === DIAGNOSTIC TESTS ===
        print(f"\n🔬 DIAGNOSTIC TESTS ({len(medical_note.diagnostic_tests)} tests):")
        for i, test in enumerate(medical_note.diagnostic_tests[:5], 1):
            print(f"   {i}. {test.test_name}")
            if test.date_performed:
                print(f"      Date: {test.date_performed}")
            if test.key_findings:
                print(f"      Findings: {test.key_findings[:60]}...")
        
        # Assertions
        assert len(medical_note.diagnostic_tests) >= 3, f"Not enough tests extracted: {len(medical_note.diagnostic_tests)}"
        test_names = " ".join([t.test_name.lower() for t in medical_note.diagnostic_tests])
        assert "visual acuity" in test_names or "biomicroscopy" in test_names, "Key tests not extracted"
        print(f"   ✓ {len(medical_note.diagnostic_tests)} tests validated")
        
        # === PROPOSED TREATMENT ===
        print("\n💉 PROPOSED TREATMENT:")
        print(f"   Procedure: {medical_note.proposed_treatment.procedure_name}")
        print(f"   Code: {medical_note.proposed_treatment.procedure_code or 'N/A'}")
        print(f"   Anesthesia: {medical_note.proposed_treatment.anesthesia_type or 'N/A'}")
        
        # Assertions
        assert "phacoemulsification" in medical_note.proposed_treatment.procedure_name.lower(), "Procedure not extracted"
        assert medical_note.proposed_treatment.procedure_code == "08RJ3JZ", f"Procedure code incorrect"
        assert medical_note.proposed_treatment.anesthesia_type == "Local", f"Anesthesia incorrect: {medical_note.proposed_treatment.anesthesia_type}"
        print("   ✓ Treatment details validated")
        
        # === HOSPITALIZATION ===
        print("\n🏨 HOSPITALIZATION DETAILS:")
        print(f"   Admission Date: {medical_note.hospitalization_details.planned_admission_date}")
        print(f"   Expected Stay: {medical_note.hospitalization_details.expected_length_of_stay} days")
        print(f"   ICU Required: {medical_note.hospitalization_details.icu_required}")
        
        # Assertions
        assert medical_note.hospitalization_details.planned_admission_date == "05/10/2025", "Admission date incorrect"
        assert medical_note.hospitalization_details.expected_length_of_stay == 1, f"Length of stay incorrect"
        assert medical_note.hospitalization_details.icu_required == False, "ICU status incorrect"
        print("   ✓ Hospitalization details validated")
        
        # === COST BREAKDOWN ===
        print("\n💰 COST BREAKDOWN:")
        print(f"   Room Charges: ₹{medical_note.cost_breakdown.room_charges:,.0f}")
        print(f"   OT Charges: ₹{medical_note.cost_breakdown.ot_charges:,.0f}")
        print(f"   Surgeon Fees: ₹{medical_note.cost_breakdown.surgeon_fees:,.0f}")
        print(f"   Anesthetist Fees: ₹{medical_note.cost_breakdown.anesthetist_fees:,.0f}")
        print(f"   Investigations: ₹{medical_note.cost_breakdown.investigations:,.0f}")
        print(f"   Medicines + Consumables: ₹{medical_note.cost_breakdown.medicines_consumables:,.0f}")
        print(f"   Other: ₹{medical_note.cost_breakdown.other_charges:,.0f}")
        print(f"   ---")
        print(f"   TOTAL: ₹{medical_note.cost_breakdown.total_estimated_cost:,.0f}")
        
        # Assertions
        assert medical_note.cost_breakdown.room_charges == 3500, f"Room charges incorrect: {medical_note.cost_breakdown.room_charges}"
        assert medical_note.cost_breakdown.ot_charges == 12000, f"OT charges incorrect"
        assert medical_note.cost_breakdown.investigations == 2500, f"Investigation charges incorrect"
        assert medical_note.cost_breakdown.medicines_consumables == 15000, f"Medicines incorrect"
        assert medical_note.cost_breakdown.total_estimated_cost == 52000, f"Total incorrect: {medical_note.cost_breakdown.total_estimated_cost}"
        print("   ✓ All costs validated")
        
        # === DOCTOR DETAILS ===
        print("\n👨‍⚕️ DOCTOR DETAILS:")
        print(f"   Name: {medical_note.doctor_details.name}")
        print(f"   Qualification: {medical_note.doctor_details.qualification or 'N/A'}")
        print(f"   Registration: {medical_note.doctor_details.registration_number or 'N/A'}")
        
        # Assertions
        assert "Suresh Patel" in medical_note.doctor_details.name, f"Doctor name incorrect: {medical_note.doctor_details.name}"
        assert "MBBS" in (medical_note.doctor_details.qualification or ""), "Qualification not extracted"
        assert "KMC" in (medical_note.doctor_details.registration_number or ""), "Registration number not extracted"
        print("   ✓ Doctor details validated")
        
        # === HOSPITAL DETAILS ===
        print("\n🏥 HOSPITAL DETAILS:")
        print(f"   Name: {medical_note.hospital_details.name}")
        print(f"   Address: {medical_note.hospital_details.address or 'N/A'}")
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Extraction failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_extraction_from_pdf():
    """
    Test extraction from the actual PDF file
    """
    print("\n" + "=" * 80)
    print("TEST: Extraction from PDF File")
    print("=" * 80)
    
    # Check for PDF template
    pdf_path = Path(__file__).parent.parent / "medical_note_pdf Template.pdf"
    
    if not pdf_path.exists():
        print(f"⚠️  PDF template not found: {pdf_path}")
        print("   Skipping PDF test. Run text test only.")
        return None
    
    # Initialize extractor
    extractor = PDFExtractor(enable_llm_fallback=False)
    
    try:
        print(f"\n📄 Extracting from PDF: {pdf_path.name}")
        medical_note = extractor.extract_from_pdf(str(pdf_path))
        
        print("\n✅ PDF extraction successful!")
        print(f"\n   Patient: {medical_note.patient_info.name}, Age: {medical_note.patient_info.age}")
        print(f"   Diagnosis: {medical_note.diagnosis.primary_diagnosis}")
        print(f"   Procedure: {medical_note.proposed_treatment.procedure_name}")
        print(f"   Total Cost: ₹{medical_note.cost_breakdown.total_estimated_cost:,.0f}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ PDF extraction failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_extraction_confidence():
    """
    Test the confidence scoring of the extractor
    """
    print("\n" + "=" * 80)
    print("TEST: Extraction Confidence Scoring")
    print("=" * 80)
    
    template_path = Path(__file__).parent.parent / "medical_note_template.txt"
    
    if not template_path.exists():
        print(f"❌ Template file not found")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template_text = f.read()
    
    extractor = PDFExtractor(enable_llm_fallback=False)
    
    # Access internal method for confidence
    data, confidence = extractor._parse_with_rules(template_text)
    
    print(f"\n📊 Extraction Confidence: {confidence:.1%}")
    print(f"   Fields extracted: {int(confidence * 20)}/20 (approximate)")
    
    # Confidence should be reasonable (>60%)
    assert confidence > 0.6, f"Confidence too low: {confidence:.1%}"
    
    print(f"\n✅ Confidence score is acceptable")
    
    return True


def run_all_tests():
    """Run all test functions"""
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "NEW TEMPLATE PDF EXTRACTOR TEST SUITE" + " " * 24 + "║")
    print("╚" + "=" * 78 + "╝")
    
    results = {}
    
    # Test 1: Text extraction
    results['text_extraction'] = test_extraction_from_template_text()
    
    # Test 2: PDF extraction
    pdf_result = test_extraction_from_pdf()
    if pdf_result is not None:
        results['pdf_extraction'] = pdf_result
    
    # Test 3: Confidence scoring
    results['confidence_scoring'] = test_extraction_confidence()
    
    # Summary
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " " * 32 + "TEST SUMMARY" + " " * 33 + "║")
    print("╠" + "=" * 78 + "╣")
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"║  {test_name.replace('_', ' ').title():<50} {status:>25} ║")
    
    print("╚" + "=" * 78 + "╝")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! PDF extractor is working correctly with new template.")
    else:
        print("\n⚠️  SOME TESTS FAILED. Please review the errors above.")
    
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
