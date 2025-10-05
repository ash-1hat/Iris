"""
Interactive PDF Extraction Test Script
Allows you to choose which PDF to extract and displays all extracted details
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Use the manual (fixed) version of PDF extractor
from src.services.manual_pdf_extractor import PDFExtractor
from src.models.schemas import MedicalNote


def display_extracted_data(medical_note: MedicalNote, pdf_name: str):
    """
    Display all extracted data in a formatted way
    
    Args:
        medical_note: The extracted medical note object
        pdf_name: Name of the PDF file
    """
    print("\n" + "╔" + "=" * 98 + "╗")
    print("║" + f" EXTRACTED DATA FROM: {pdf_name}".ljust(98) + "║")
    print("╚" + "=" * 98 + "╝")
    
    # === PATIENT INFORMATION ===
    print("\n" + "─" * 100)
    print("👤 PATIENT INFORMATION")
    print("─" * 100)
    print(f"  Name:              {medical_note.patient_info.name}")
    print(f"  Age:               {medical_note.patient_info.age} years")
    print(f"  Gender:            {medical_note.patient_info.gender}")
    print(f"  Patient ID:        {medical_note.patient_info.patient_id or 'N/A'}")
    print(f"  Contact Number:    {medical_note.patient_info.contact_number or 'N/A'}")
    
    # === DIAGNOSIS ===
    print("\n" + "─" * 100)
    print("🏥 DIAGNOSIS")
    print("─" * 100)
    print(f"  Primary Diagnosis: {medical_note.diagnosis.primary_diagnosis}")
    print(f"  ICD-10 Code:       {medical_note.diagnosis.icd_10_code}")
    print(f"  Diagnosis Date:    {medical_note.diagnosis.diagnosis_date or 'N/A'}")
    if medical_note.diagnosis.secondary_diagnoses:
        print(f"  Secondary:         {', '.join(medical_note.diagnosis.secondary_diagnoses)}")
    
    # === CLINICAL HISTORY ===
    print("\n" + "─" * 100)
    print("📋 CLINICAL HISTORY")
    print("─" * 100)
    print(f"  Chief Complaints:")
    # Wrap long text
    complaints = medical_note.clinical_history.chief_complaints
    if len(complaints) > 80:
        words = complaints.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line + word) < 80:
                current_line += word + " "
            else:
                lines.append(current_line.strip())
                current_line = word + " "
        if current_line:
            lines.append(current_line.strip())
        for i, line in enumerate(lines):
            if i == 0:
                print(f"    {line}")
            else:
                print(f"    {line}")
    else:
        print(f"    {complaints}")
    
    print(f"\n  Duration:          {medical_note.clinical_history.duration_of_symptoms or 'N/A'}")
    
    if medical_note.clinical_history.comorbidities:
        print(f"  Comorbidities:     {', '.join(medical_note.clinical_history.comorbidities)}")
    else:
        print(f"  Comorbidities:     None")
    
    if medical_note.clinical_history.relevant_medical_history:
        print(f"  Medical History:   {medical_note.clinical_history.relevant_medical_history[:100]}...")
    
    # === DIAGNOSTIC TESTS ===
    print("\n" + "─" * 100)
    print(f"🔬 DIAGNOSTIC TESTS ({len(medical_note.diagnostic_tests)} tests performed)")
    print("─" * 100)
    if medical_note.diagnostic_tests:
        for i, test in enumerate(medical_note.diagnostic_tests, 1):
            print(f"  {i}. {test.test_name}")
            if test.date_performed:
                print(f"     Date:     {test.date_performed}")
            if test.key_findings:
                print(f"     Findings: {test.key_findings[:80]}{'...' if len(test.key_findings) > 80 else ''}")
            print()
    else:
        print("  No diagnostic tests recorded")
    
    # === PROPOSED TREATMENT ===
    print("\n" + "─" * 100)
    print("💉 PROPOSED TREATMENT")
    print("─" * 100)
    print(f"  Procedure:         {medical_note.proposed_treatment.procedure_name}")
    print(f"  Procedure Code:    {medical_note.proposed_treatment.procedure_code or 'N/A'}")
    print(f"  Anesthesia:        {medical_note.proposed_treatment.anesthesia_type or 'N/A'}")
    if medical_note.proposed_treatment.surgical_approach:
        approach_text = medical_note.proposed_treatment.surgical_approach
        if len(approach_text) > 80:
            print(f"  Surgical Approach: {approach_text[:80]}...")
        else:
            print(f"  Surgical Approach: {approach_text}")
    
    # === MEDICAL JUSTIFICATION ===
    print("\n" + "─" * 100)
    print("📝 MEDICAL JUSTIFICATION")
    print("─" * 100)
    print(f"  Why Hospitalization Required:")
    print(f"    {medical_note.medical_justification.why_hospitalization_required[:90]}...")
    print(f"\n  Why Treatment Necessary:")
    print(f"    {medical_note.medical_justification.why_treatment_necessary[:90]}...")
    
    # === HOSPITALIZATION DETAILS ===
    print("\n" + "─" * 100)
    print("🏨 HOSPITALIZATION DETAILS")
    print("─" * 100)
    
    # Hospitalization Type
    if hasattr(medical_note.hospitalization_details, 'hospitalization_type') and medical_note.hospitalization_details.hospitalization_type:
        hosp_type = medical_note.hospitalization_details.hospitalization_type
        emoji = "🚨" if hosp_type == "Emergency" else "📅"
        print(f"  Type:              {emoji} {hosp_type}")
    
    print(f"  Admission Date:    {medical_note.hospitalization_details.planned_admission_date}")
    print(f"  Expected Stay:     {medical_note.hospitalization_details.expected_length_of_stay} days")
    print(f"  ICU Required:      {'Yes' if medical_note.hospitalization_details.icu_required else 'No'}")
    if medical_note.hospitalization_details.icu_required and hasattr(medical_note.hospitalization_details, 'icu_duration'):
        if medical_note.hospitalization_details.icu_duration:
            print(f"  ICU Duration:      {medical_note.hospitalization_details.icu_duration} days")
    
    # === COST BREAKDOWN ===
    print("\n" + "─" * 100)
    print("💰 COST BREAKDOWN")
    print("─" * 100)
    costs = medical_note.cost_breakdown
    
    print(f"  Room Charges:                    ₹ {costs.room_charges:>12,.2f}")
    print(f"  Surgeon Fees:                    ₹ {costs.surgeon_fees:>12,.2f}")
    print(f"  Anesthetist Fees:                ₹ {costs.anesthetist_fees:>12,.2f}")
    print(f"  OT Charges:                      ₹ {costs.ot_charges:>12,.2f}")
    
    if costs.icu_charges and costs.icu_charges > 0:
        print(f"  ICU Charges:                     ₹ {costs.icu_charges:>12,.2f}")
    
    print(f"  Investigations/Diagnostics:      ₹ {costs.investigations:>12,.2f}")
    print(f"  Medicines + Consumables:         ₹ {costs.medicines_consumables:>12,.2f}")
    
    if hasattr(costs, 'implants') and costs.implants and costs.implants > 0:
        print(f"  Implants:                        ₹ {costs.implants:>12,.2f}")
    
    if costs.other_charges and costs.other_charges > 0:
        print(f"  Other Charges:                   ₹ {costs.other_charges:>12,.2f}")
    
    print(f"  " + "─" * 44)
    print(f"  TOTAL ESTIMATED COST:            ₹ {costs.total_estimated_cost:>12,.2f}")
    
    # === DOCTOR DETAILS ===
    print("\n" + "─" * 100)
    print("👨‍⚕️ TREATING DOCTOR DETAILS")
    print("─" * 100)
    print(f"  Name:              {medical_note.doctor_details.name}")
    print(f"  Qualification:     {medical_note.doctor_details.qualification or 'N/A'}")
    print(f"  Specialty:         {medical_note.doctor_details.specialty or 'N/A'}")
    print(f"  Registration No:   {medical_note.doctor_details.registration_number or 'N/A'}")
    
    # === HOSPITAL DETAILS ===
    print("\n" + "─" * 100)
    print("🏥 HOSPITAL DETAILS")
    print("─" * 100)
    print(f"  Hospital Name:     {medical_note.hospital_details.name}")
    print(f"  Address:           {medical_note.hospital_details.address or 'N/A'}")
    if medical_note.hospital_details.contact_number:
        print(f"  Contact:           {medical_note.hospital_details.contact_number}")
    
    print("\n" + "═" * 100)


def main():
    """
    Main function to run interactive PDF extraction
    """
    print("\n" + "╔" + "═" * 98 + "╗")
    print("║" + " " * 35 + "PDF EXTRACTOR TEST" + " " * 44 + "║")
    print("║" + " " * 25 + "Interactive Medical Note Extraction" + " " * 38 + "║")
    print("╚" + "═" * 98 + "╝")
    
    # Define PDF paths
    project_root = Path(__file__).parent.parent
    pdf_files = {
        "1": {
            "path": project_root / "medical_note_pdf Template.pdf",
            "name": "medical_note_pdf Template.pdf"
        },
        "2": {
            "path": project_root / "test2.pdf",
            "name": "test2.pdf"
        }
    }
    
    # Check which PDFs exist
    available_pdfs = {}
    for key, pdf_info in pdf_files.items():
        if pdf_info["path"].exists():
            available_pdfs[key] = pdf_info
        else:
            print(f"\n⚠️  Warning: {pdf_info['name']} not found at {pdf_info['path']}")
    
    if not available_pdfs:
        print("\n❌ Error: No PDF files found!")
        print(f"   Expected PDFs in: {project_root}")
        return False
    
    # Display menu
    print("\n" + "─" * 100)
    print("📄 AVAILABLE PDF FILES:")
    print("─" * 100)
    for key, pdf_info in available_pdfs.items():
        print(f"  [{key}] {pdf_info['name']}")
    print("  [Q] Quit")
    print("─" * 100)
    
    # Get user choice
    choice = input("\nSelect a PDF to extract (enter number or Q to quit): ").strip().upper()
    
    if choice == 'Q':
        print("\n👋 Exiting...")
        return True
    
    if choice not in available_pdfs:
        print(f"\n❌ Invalid choice: {choice}")
        return False
    
    # Extract the selected PDF
    selected_pdf = available_pdfs[choice]
    pdf_path = selected_pdf["path"]
    pdf_name = selected_pdf["name"]
    
    print(f"\n🔄 Extracting data from: {pdf_name}")
    print("   Please wait...")
    
    # Initialize extractor
    extractor = PDFExtractor(enable_llm_fallback=False)
    
    try:
        # Extract medical note
        medical_note = extractor.extract_from_pdf(str(pdf_path))
        
        print("\n✅ Extraction completed successfully!")
        
        # Display all extracted data
        display_extracted_data(medical_note, pdf_name)
        
        print("\n✅ Data extraction and display completed.")
        return True
        
    except Exception as e:
        print(f"\n❌ Extraction failed: {str(e)}")
        import traceback
        print("\nDetailed error:")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
