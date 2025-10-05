"""
Debug script to view raw text extracted from PDFs
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Use the manual (fixed) version of PDF extractor
from src.services.manual_pdf_extractor import PDFExtractor

def show_pdf_text(pdf_path: Path, section_name: str = None):
    """Show raw text from PDF"""
    extractor = PDFExtractor()
    
    print(f"\n{'='*100}")
    print(f"PDF: {pdf_path.name}")
    print(f"{'='*100}\n")
    
    # Extract raw text
    raw_text = extractor._extract_text_from_pdf(pdf_path)
    
    if section_name:
        # Show specific section
        if section_name.upper() == "COST":
            # Show cost section
            start_idx = raw_text.find("COST BREAKDOWN")
            if start_idx == -1:
                start_idx = raw_text.find("ESTIMATED COST")
            if start_idx != -1:
                end_idx = start_idx + 1500
                print(f"--- COST SECTION (characters {start_idx}-{end_idx}) ---")
                print(raw_text[start_idx:end_idx])
        elif section_name.upper() == "TESTS":
            # Show investigations section
            start_idx = raw_text.find("INVESTIGATIONS")
            if start_idx == -1:
                start_idx = raw_text.find("Investigations")
            if start_idx != -1:
                end_idx = start_idx + 1500
                print(f"--- INVESTIGATIONS SECTION (characters {start_idx}-{end_idx}) ---")
                print(raw_text[start_idx:end_idx])
    else:
        # Show full text
        print(raw_text)
    
    print(f"\n{'='*100}")
    print(f"Total length: {len(raw_text)} characters")
    print(f"{'='*100}\n")


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    
    # Check both PDFs
    pdf1 = project_root / "medical_note_pdf Template.pdf"
    pdf2 = project_root / "test2.pdf"
    
    print("\n" + "╔" + "="*98 + "╗")
    print("║" + " "*35 + "PDF TEXT DEBUG TOOL" + " "*44 + "║")
    print("╚" + "="*98 + "╝")
    
    print("\n[1] medical_note_pdf Template.pdf - Full Text")
    print("[2] medical_note_pdf Template.pdf - Cost Section")
    print("[3] medical_note_pdf Template.pdf - Tests Section")
    print("[4] test2.pdf - Full Text")
    print("[5] test2.pdf - Cost Section")
    print("[6] test2.pdf - Tests Section")
    
    choice = input("\nSelect option: ").strip()
    
    if choice == "1":
        show_pdf_text(pdf1)
    elif choice == "2":
        show_pdf_text(pdf1, "COST")
    elif choice == "3":
        show_pdf_text(pdf1, "TESTS")
    elif choice == "4":
        show_pdf_text(pdf2)
    elif choice == "5":
        show_pdf_text(pdf2, "COST")
    elif choice == "6":
        show_pdf_text(pdf2, "TESTS")
    else:
        print("Invalid choice")
