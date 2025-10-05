"""
Unit tests for PDF Extractor
Tests extraction from both PDF files and text content
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.services.pdf_extractor import PDFExtractor
from src.models.schemas import MedicalNote


class TestPDFExtractor:
    """Test suite for PDF extractor"""

    def setup_method(self):
        """Setup test fixtures"""
        self.extractor = PDFExtractor()
        self.project_root = Path(__file__).parent.parent

    def test_extract_from_test_case_1_pdf(self):
        """Test extraction from Test-Case-1.pdf"""
        pdf_path = self.project_root / "Test-Case-1.pdf"

        if not pdf_path.exists():
            pytest.skip(f"Test PDF not found: {pdf_path}")

        # Extract medical note
        medical_note = self.extractor.extract_from_pdf(str(pdf_path))

        # Assertions - verify key fields are extracted
        assert medical_note is not None
        assert isinstance(medical_note, MedicalNote)

        # Patient info
        assert medical_note.patient_info.name is not None
        assert medical_note.patient_info.age > 0
        assert medical_note.patient_info.gender in ["Male", "Female", "Other"]

        # Diagnosis
        assert medical_note.diagnosis.primary_diagnosis is not None
        assert medical_note.diagnosis.icd_10_code is not None

        # Treatment
        assert medical_note.proposed_treatment.procedure_name is not None

        # Costs
        assert medical_note.cost_breakdown.total_estimated_cost > 0

        # Hospital details
        assert medical_note.hospital_details.name is not None

        # Doctor details
        assert medical_note.doctor_details.name is not None

        print("\n✅ Successfully extracted from Test-Case-1.pdf")
        print(f"   Patient: {medical_note.patient_info.name}, Age: {medical_note.patient_info.age}")
        print(f"   Diagnosis: {medical_note.diagnosis.primary_diagnosis}")
        print(f"   Procedure: {medical_note.proposed_treatment.procedure_name}")
        print(f"   Total Cost: ₹{medical_note.cost_breakdown.total_estimated_cost:,.0f}")

    def test_extract_from_text_ideal_case(self):
        """Test extraction from text (Test Case 1 from Test_Medical_Notes.md)"""
        # Simplified text version of Test Case 1
        text_content = """
        PATIENT DETAILS
        Patient Name: Rajesh Kumar
        Gender: Male
        Age: 68 Years
        Date of Birth: 15/03/1957
        Contact Number: 9876543210
        Address: 45, MG Road, Bengaluru - 560001
        TPA Card ID: SH123456789
        Policy Number: STAR/COMP/2021/123456
        Policy Start Date: 01/01/2022

        TREATING DOCTOR INFORMATION
        Doctor Name: Dr. Suresh Patel
        Contact Number: 9845123456
        Qualification: MBBS, MS (Ophthalmology), DNB
        Registration Number: KMC/12345/2005

        ILLNESS/DISEASE DETAILS
        Nature of Illness: Patient presents with progressive bilateral vision loss over past 18 months.
        Reports difficulty reading newspapers, recognizing faces at 2-3 meters distance.
        Visual acuity has deteriorated significantly affecting daily activities.

        Duration of Present Ailment: 540 Days
        Date of First Consultation: 10/08/2024
        Provisional Diagnosis: Age-related cataract, both eyes
        ICD-10 Code: H25.9

        RELEVANT CLINICAL FINDINGS
        Right eye: Visual acuity 6/60
        Left eye: Visual acuity 6/36
        Slit lamp: Grade 3+ nuclear sclerosis in both eyes
        IOP: Right 14 mmHg, Left 15 mmHg

        PAST MEDICAL HISTORY
        Diabetes Type 2 - Since 01/06/2015
        Hypertension - Since 15/03/2018

        INVESTIGATIONS
        1. Visual acuity testing (10/08/2024): Right 6/60, Left 6/36
        2. Slit lamp biomicroscopy (10/08/2024): Grade 3+ nuclear sclerosis
        3. Biometry for IOL (15/09/2024): Right eye 23.45mm
        4. Blood tests (20/09/2024): HbA1c 6.8%, FBS 118 mg/dL

        SURGICAL DETAILS
        Surgery: Phacoemulsification with foldable IOL implantation (Right eye)
        ICD-10 PCS Code: 08RJ3JZ
        Anesthesia: Peribulbar (Local)
        Other Details: Small incision phacoemulsification. Foldable IOL (+21.5D)

        HOSPITALIZATION DETAILS
        Date of Admission: 05/10/2025
        Expected Stay: 1 Day
        ICU Required: No
        Room Type: Single Private AC

        ESTIMATED COST BREAKDOWN
        Room Rent: ₹3,500
        Investigation: ₹2,500
        OT Charges: ₹12,000
        Surgeon Fees: ₹18,000
        Medicines + IOL: ₹15,000
        Other: ₹1,000
        TOTAL: ₹52,000

        HOSPITAL DETAILS
        Hospital Name: Apollo Hospital
        Address: Bengaluru
        Contact: 080-12345678
        """

        # Extract medical note
        medical_note = self.extractor.extract_from_text(text_content)

        # Assertions
        assert medical_note is not None
        assert "Rajesh Kumar" in medical_note.patient_info.name
        assert medical_note.patient_info.age == 68
        assert medical_note.patient_info.gender == "Male"
        assert medical_note.diagnosis.icd_10_code == "H25.9"
        assert "cataract" in medical_note.diagnosis.primary_diagnosis.lower()
        assert medical_note.cost_breakdown.total_estimated_cost == 52000

        print("\n✅ Successfully extracted from text content")
        print(f"   Patient: {medical_note.patient_info.name}")
        print(f"   Diagnosis: {medical_note.diagnosis.primary_diagnosis}")

    def test_missing_pdf_file_raises_error(self):
        """Test that missing PDF file raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            self.extractor.extract_from_pdf("nonexistent.pdf")

    def test_empty_text_raises_error(self):
        """Test that empty text raises ValueError"""
        with pytest.raises(ValueError, match="Failed to create MedicalNote"):
            self.extractor.extract_from_text("")


def run_pdf_extractor_tests():
    """Run all PDF extractor tests"""
    print("=" * 60)
    print("PDF EXTRACTOR TESTS")
    print("=" * 60)

    # Run pytest programmatically
    exit_code = pytest.main([__file__, "-v", "--tb=short", "-s"])

    print("\n" + "=" * 60)
    if exit_code == 0:
        print("All PDF Extractor tests passed")
    else:
        print("Some tests failed")
    print("=" * 60)

    return exit_code == 0


if __name__ == "__main__":
    import sys
    success = run_pdf_extractor_tests()
    sys.exit(0 if success else 1)
