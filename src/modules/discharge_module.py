"""
Discharge Validation Module
Handles discharge bill validation UI and logic
"""

import streamlit as st
import sys
from pathlib import Path
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.discharge_service import DischargeService
from services.claim_storage import ClaimStorageService


def display_discharge_results(result):
    """Display discharge validation results"""

    st.markdown("---")
    st.subheader("📊 Discharge Validation Results")

    # Overall metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Completeness Score",
            value=f"{result['overall_score']}/100"
        )

    with col2:
        status_map = {"complete": "✓ Ready", "partial": "⚠ Partial", "incomplete": "✗ Incomplete"}
        st.metric(
            label="Status",
            value=status_map.get(result['completeness_status'], "Unknown")
        )

    with col3:
        bill_recon = result['bill_reconciliation']
        variance_pct = bill_recon['total_variance']['percentage']
        st.metric(
            label="Cost Variance",
            value=f"{variance_pct:+.1f}%"
        )

    # Patient summary
    st.markdown("### 📝 Summary for Patient")
    st.info(result['patient_summary'])

    # Bill comparison
    st.markdown("### 💰 Bill Comparison")
    with st.expander("View Bill Comparison", expanded=True):
        st.text(result['bill_comparison_summary'])

    # Variance analysis
    st.markdown("### 🔍 Variance Analysis")
    with st.expander("View Variance Analysis", expanded=True):
        st.text(result['variance_analysis'])

    # Medical guidance - Simplified summary view
    st.markdown("### 💊 Your Recovery Instructions")

    med_guide = result['medical_guidance']

    # Summary information
    st.info(f"""
    **📋 Summary:**
    - {med_guide['medication_schedule']['summary']}
    - {med_guide['follow_up_plan']['summary']}
    - {len(med_guide['activity_guidelines']['dos'])} recommended activities, {len(med_guide['activity_guidelines']['donts'])} activities to avoid
    - {len(med_guide['warning_signs']['signs'])} warning signs to watch for
    """)

    # Download PDF button (prominent placement)
    from src.utils.recovery_pdf_generator import generate_recovery_pdf

    pdf_bytes = generate_recovery_pdf(med_guide, result)

    st.download_button(
        label="📄 Download Complete Recovery Guide (PDF)",
        data=pdf_bytes,
        file_name=f"recovery_instructions_{result.get('discharge_summary', {}).get('patient_info', {}).get('name', 'patient').replace(' ', '_')}.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True
    )

    st.caption("💡 Download the PDF for a complete, printable recovery guide with detailed medication schedules, follow-up appointments, do's and don'ts, and warning signs.")

    # Recovery timeline (keep this visible)
    st.markdown("### 🕐 Recovery Timeline")
    st.info(med_guide['recovery_timeline'])

    # Recommendations
    if result['recommendations']:
        st.markdown("### ✅ Recommendations")
        for i, rec in enumerate(result['recommendations'], 1):
            st.markdown(f"{i}. {rec}")

    # Legal disclaimer
    st.markdown("---")
    st.warning("""
    **IMPORTANT DISCLAIMER**

    This validation checks documentation completeness and compares costs against planned estimates.

    **We do NOT:**
    - Predict whether your insurer will approve the claim
    - Calculate what you will pay
    - Determine if costs are "justified"
    - Make any guarantees about claim outcome

    **Your insurance company makes all final decisions about coverage and payment.**

    For questions about your claim status or coverage, contact your insurance company directly.
    """)


def render():
    """Main render function for discharge module"""

    st.markdown("## Discharge Bill Validation")
    st.markdown("Validate your discharge documentation and compare actual costs against pre-authorization estimates.")

    # Initialize session state
    if 'discharge_validation_result' not in st.session_state:
        st.session_state.discharge_validation_result = None

    # Option 1: With Reference ID
    st.subheader("📋 Do you have a Reference ID from Pre-Authorization?")

    has_claim_id = st.radio(
        "Select validation mode:",
        ["Yes - I have a Reference ID", "No - I'll enter costs manually"],
        horizontal=True
    )

    # Main form
    with st.form("discharge_form"):

        if has_claim_id == "Yes - I have a Reference ID":
            st.markdown("### Enter your Reference ID")

            claim_id = st.text_input(
                "Reference ID",
                placeholder="e.g., CR-20251005-12345",
                help="The Reference ID you received after pre-authorization validation"
            )

            # Load saved data to show summary
            if claim_id:
                try:
                    storage = ClaimStorageService()
                    claim_data = storage.load_claim(claim_id)

                    if claim_data:
                        st.success("Reference ID found! Your pre-authorization data has been loaded.")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Patient", claim_data.get('patient_info', {}).get('name', 'N/A'))
                        with col2:
                            st.metric("Procedure", claim_data.get('procedure_info', {}).get('procedure_id', 'N/A'))
                        with col3:
                            expected_total = claim_data.get('expected_costs', {}).get('total_estimated_cost', 0)
                            st.metric("Expected Cost", f"Rs.{expected_total:,.2f}")
                    else:
                        st.warning("Reference ID not found. Please check and try again.")
                except Exception as e:
                    st.error(f"Error loading data: {str(e)}")

        else:
            st.markdown("### Enter Pre-Authorization Costs Manually")

            st.info("If you don't have a Reference ID, enter the costs from your pre-authorization approval letter.")

            col1, col2 = st.columns(2)

            with col1:
                room_charges = st.number_input("Room Charges (Rs.)", min_value=0, value=3500)
                surgeon_fees = st.number_input("Surgeon Fees (Rs.)", min_value=0, value=18000)
                ot_charges = st.number_input("OT Charges (Rs.)", min_value=0, value=12000)
                medicines = st.number_input("Medicines (Rs.)", min_value=0, value=12000)

            with col2:
                anesthetist_fees = st.number_input("Anesthetist Fees (Rs.)", min_value=0, value=5000)
                implants = st.number_input("Implants (Rs.)", min_value=0, value=15000)
                investigations = st.number_input("Investigations (Rs.)", min_value=0, value=2000)
                other_charges = st.number_input("Other Charges (Rs.)", min_value=0, value=500)

            total_estimated = (room_charges + surgeon_fees + ot_charges + medicines +
                             anesthetist_fees + implants + investigations + other_charges)

            st.metric("Total Estimated Cost", f"Rs.{total_estimated:,.2f}")

            expected_stay = st.number_input("Expected Hospital Stay (days)", min_value=1, value=1)

        # Upload PDFs
        st.markdown("---")
        st.subheader("📄 Upload Discharge Documents")

        col1, col2 = st.columns(2)

        with col1:
            final_bill_pdf = st.file_uploader(
                "Final Hospital Bill (PDF)",
                type=['pdf'],
                help="Upload the detailed final bill from hospital"
            )

        with col2:
            discharge_summary_pdf = st.file_uploader(
                "Discharge Summary (PDF)",
                type=['pdf'],
                help="Upload the discharge summary from doctor"
            )

        # Submit button
        st.markdown("---")
        submitted = st.form_submit_button(
            "🔍 Validate Discharge Documents",
            type="primary",
            use_container_width=True
        )

    # Process validation
    if submitted:
        if not final_bill_pdf or not discharge_summary_pdf:
            st.error("Please upload both final bill and discharge summary PDFs.")
            return

        # Show progress
        with st.spinner("Validating discharge documents..."):
            try:
                # Save PDFs temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_bill:
                    tmp_bill.write(final_bill_pdf.read())
                    bill_path = tmp_bill.name

                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_discharge:
                    tmp_discharge.write(discharge_summary_pdf.read())
                    discharge_path = tmp_discharge.name

                # Initialize service
                service = DischargeService()

                # Validate based on mode
                if has_claim_id == "Yes - I have a Reference ID":
                    if not claim_id:
                        st.error("Please enter a Reference ID.")
                        return

                    result = service.validate_discharge_with_claim_id(
                        claim_id=claim_id,
                        final_bill_pdf_path=bill_path,
                        discharge_summary_pdf_path=discharge_path
                    )
                else:
                    # Manual mode
                    expected_costs = {
                        "room_charges": room_charges,
                        "surgeon_fees": surgeon_fees,
                        "anesthetist_fees": anesthetist_fees,
                        "ot_charges": ot_charges,
                        "medicines": medicines,
                        "implants": implants,
                        "investigations": investigations,
                        "other_charges": other_charges,
                        "total_estimated_cost": total_estimated
                    }

                    result = service.validate_discharge_manual(
                        expected_costs=expected_costs,
                        expected_stay_days=expected_stay,
                        final_bill_pdf_path=bill_path,
                        discharge_summary_pdf_path=discharge_path
                    )

                # Store result
                st.session_state.discharge_validation_result = result

                # Clean up
                Path(bill_path).unlink()
                Path(discharge_path).unlink()

                st.success("Validation completed successfully!")

            except Exception as e:
                st.error(f"Error during validation: {str(e)}")
                import traceback
                with st.expander("View error details"):
                    st.code(traceback.format_exc())
                return

    # Display results
    if st.session_state.discharge_validation_result:
        display_discharge_results(st.session_state.discharge_validation_result)
