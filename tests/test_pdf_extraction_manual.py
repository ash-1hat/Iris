"""
Manual PDF Extraction Test
Tests PDF text extraction (without LLM) to verify PDF reading works
Run this to validate PDF extraction is working before adding API credits
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.pdf_extractor import PDFExtractor


def test_pdf_text_extraction():
    """Test PDF text extraction without LLM"""
    print("=" * 60)
    print("PDF TEXT EXTRACTION TEST (No LLM)")
    print("=" * 60)

    extractor = PDFExtractor()
    project_root = Path(__file__).parent.parent
    pdf_path = project_root / "Test-Case-1.pdf"

    if not pdf_path.exists():
        print(f"\n❌ PDF file not found: {pdf_path}")
        return False

    print(f"\n📄 Reading PDF: {pdf_path.name}")

    try:
        # Extract text only (no LLM)
        pdf_text = extractor._extract_text_from_pdf(pdf_path)

        print(f"\n✅ Successfully extracted text from PDF")
        print(f"   Total characters: {len(pdf_text):,}")
        print(f"   Total lines: {len(pdf_text.splitlines()):,}")

        # Show first 1000 characters
        print(f"\n📝 First 1000 characters of extracted text:")
        print("-" * 60)
        print(pdf_text[:1000])
        print("-" * 60)

        # Check for key medical terms
        key_terms = [
            "patient", "diagnosis", "treatment", "hospital",
            "doctor", "cost", "admission", "procedure"
        ]

        print(f"\n🔍 Checking for key medical terms:")
        found_terms = []
        for term in key_terms:
            if term.lower() in pdf_text.lower():
                found_terms.append(term)
                print(f"   ✓ Found: '{term}'")
            else:
                print(f"   ✗ Missing: '{term}'")

        if len(found_terms) >= 4:
            print(f"\n✅ PDF contains medical information ({len(found_terms)}/{len(key_terms)} key terms found)")
            print(f"\n💡 PDF text extraction is working!")
            print(f"   Once you add API credits, the LLM will parse this into structured data.")
            return True
        else:
            print(f"\n⚠️  Only {len(found_terms)}/{len(key_terms)} key terms found")
            print(f"   This may not be a medical pre-authorization document")
            return False

    except Exception as e:
        print(f"\n❌ Error extracting text: {str(e)}")
        return False


def show_test_instructions():
    """Show instructions for full testing"""
    print("\n" + "=" * 60)
    print("NEXT STEPS TO TEST PDF EXTRACTOR WITH LLM")
    print("=" * 60)

    print("""
1. ADD API CREDITS:
   - Go to https://console.anthropic.com/
   - Navigate to Plans & Billing
   - Add credits to your account

2. RUN FULL TEST:
   python tests/test_pdf_extractor.py

3. EXPECTED OUTPUT:
   ✅ Extract patient info (name, age, gender)
   ✅ Extract diagnosis (condition, ICD-10 code)
   ✅ Extract treatment plan (procedure, costs)
   ✅ Extract hospital/doctor details
   ✅ Create structured MedicalNote object

4. IF TESTS PASS:
   - PDF extractor is ready
   - Can integrate with PreAuthService
   - Can build Streamlit frontend
    """)


if __name__ == "__main__":
    success = test_pdf_text_extraction()
    show_test_instructions()
    sys.exit(0 if success else 1)
