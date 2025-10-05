"""
Pre-Authorization Module
Handles pre-authorization validation UI and logic
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.preauth_service import PreAuthService
from utils.data_loader import list_available_procedures, list_available_policies
from services.claim_storage import ClaimStorageService


def get_policy_inputs():
    """Get policy and patient details from user"""
    st.subheader("📋 Policy & Patient Information")

    col1, col2 = st.columns(2)

    with col1:
        # Get available policies
        available_policies = list_available_policies()

        # Create display name: "Insurer - Policy Name"
        policy_display_options = {}
        for p in available_policies:
            display_name = f"{p['insurer']} - {p['policy_name']}"
            policy_display_options[display_name] = {
                'insurer': p['insurer'],
                'policy_type': p['policy_name']
            }

        # Sort options
        sorted_display_names = sorted(policy_display_options.keys())

        selected_policy_display = st.selectbox(
            "Insurance Policy",
            options=sorted_display_names,
            help="Select your insurance company and policy type"
        )

        # Extract insurer and policy type
        selected_policy = policy_display_options[selected_policy_display]
        insurer = selected_policy['insurer']
        policy_type = selected_policy['policy_type']

        policy_number = st.text_input(
            "Policy Number",
            placeholder="e.g., SH12345678",
            help="Your policy number"
        )

        sum_insured = st.number_input(
            "Sum Insured (Rs.)",
            min_value=100000,
            max_value=10000000,
            value=500000,
            step=100000,
            help="Your policy's sum insured amount"
        )

    with col2:
        policy_start_date = st.date_input(
            "Policy Start Date",
            value=datetime(2023, 1, 1),
            help="When did your policy start?"
        )

        planned_admission_date = st.date_input(
            "Planned Admission Date",
            value=datetime.now(),
            help="When is the hospitalization planned?"
        )

    # Procedure selection
    st.markdown("### 🏥 Procedure Information")

    procedures = list_available_procedures()
    procedure_options = {p['display_name']: p['procedure_id'] for p in procedures}

    selected_procedure_name = st.selectbox(
        "Select Procedure",
        options=list(procedure_options.keys()),
        help="Choose the procedure for pre-authorization"
    )

    procedure_id = procedure_options[selected_procedure_name]

    return {
        'insurer': insurer,
        'policy_type': policy_type,
        'policy_number': policy_number,
        'policy_start_date': policy_start_date.strftime('%Y-%m-%d'),
        'sum_insured': sum_insured,
        'planned_admission_date': planned_admission_date.strftime('%Y-%m-%d'),
        'procedure_id': procedure_id,
        'procedure_name': selected_procedure_name
    }


def display_validation_results(result):
    """Display validation results"""
    st.markdown("---")
    st.subheader("📊 Validation Results")

    # Overall metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Documentation Score",
            value=f"{result.final_score}/100",
            delta=f"{result.final_score - 100} from baseline"
        )

    with col2:
        status_emoji = {"pass": "✓", "warning": "⚠", "fail": "✗"}
        status_text = {"pass": "Complete", "warning": "Needs Review", "fail": "Incomplete"}
        st.metric(
            label="Status",
            value=f"{status_emoji.get(result.overall_status, '?')} {status_text.get(result.overall_status, 'Unknown')}"
        )

    with col3:
        likelihood_emoji = {"high": "🟢", "medium": "🟡", "low": "🔴"}
        st.metric(
            label="Readiness",
            value=f"{likelihood_emoji.get(result.approval_likelihood, '?')} {result.approval_likelihood.title()}"
        )

    # Summary
    st.markdown("### 📝 Summary")
    status_class = f"status-{result.overall_status}"
    st.markdown(f'<div class="{status_class}">{result.summary}</div>', unsafe_allow_html=True)

    # Agent-wise results (collapsed display)
    st.markdown("### 🔍 Section-wise Analysis")

    agents = {
        "📋 Documentation Completeness": result.agent_results.completeness,
        "📜 Policy Compliance": result.agent_results.policy,
        "🏥 Medical Review": result.agent_results.medical,
        "🔍 Quality Check": result.agent_results.fwa
    }

    for agent_name, agent_result in agents.items():
        with st.expander(f"{agent_name} - {agent_result.status.upper()}", expanded=(agent_result.status != "pass")):
            status_colors = {"pass": "green", "warning": "orange", "fail": "red"}
            st.markdown(f"**Status:** :{status_colors.get(agent_result.status, 'gray')}[{agent_result.status.upper()}]")
            st.markdown(f"**Score Impact:** {agent_result.score_impact}")

            if hasattr(agent_result, 'issues') and agent_result.issues:
                st.markdown("**Issues Found:**")
                for i, issue in enumerate(agent_result.issues, 1):
                    st.markdown(f"{i}. {issue}")

            if hasattr(agent_result, 'violations') and agent_result.violations:
                st.markdown("**Policy Violations:**")
                for i, violation in enumerate(agent_result.violations, 1):
                    severity_color = "red" if violation.severity == "critical" else "orange"
                    st.markdown(f"{i}. :{severity_color}[**{violation.severity.upper()}**] {violation.explanation}")
                    st.markdown(f"   💡 *Recommendation:* {violation.suggestion}")

            if hasattr(agent_result, 'concerns') and agent_result.concerns:
                st.markdown("**Medical Concerns:**")
                for i, concern in enumerate(agent_result.concerns, 1):
                    st.markdown(f"{i}. **{concern.type}:** {concern.description}")
                    st.markdown(f"   💡 *Recommendation:* {concern.suggestion}")

            if hasattr(agent_result, 'flags') and agent_result.flags:
                st.markdown("**Quality Flags:**")
                for i, flag in enumerate(agent_result.flags, 1):
                    st.markdown(f"{i}. **{flag.category}:** {flag.detail}")
                    st.markdown(f"   📌 *Evidence:* {flag.evidence}")

    # Recommendations
    if result.recommendations:
        st.markdown("### ✅ Action Items to Address")
        st.info("Please address the following items to improve your documentation:")

        for i, recommendation in enumerate(result.recommendations, 1):
            st.markdown(f"{i}. {recommendation}")


def render():
    """Main render function for pre-auth module"""

    st.markdown("## Pre-Authorization Validation")
    st.markdown("Validate your pre-authorization documentation before submitting to your insurer.")

    # Initialize session state
    if 'preauth_validation_result' not in st.session_state:
        st.session_state.preauth_validation_result = None

    # Main form
    with st.form("preauth_form"):
        # Get policy inputs
        form_data = get_policy_inputs()

        # PDF upload
        st.markdown("---")
        st.subheader("📄 Medical Note Upload")

        uploaded_file = st.file_uploader(
            "Upload Pre-Authorization Medical Note (PDF)",
            type=['pdf'],
            help="Upload the medical note PDF from your doctor"
        )

        # Submit button
        st.markdown("---")
        submitted = st.form_submit_button(
            "🔍 Validate Documentation",
            type="primary",
            use_container_width=True
        )

    # Process validation
    if submitted:
        if not uploaded_file:
            st.error("Please upload a medical note PDF to proceed.")
            return

        if not form_data['policy_number']:
            st.error("Please enter a policy number.")
            return

        # Show progress
        with st.spinner("Processing your documentation..."):
            try:
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    tmp_file_path = tmp_file.name

                # Initialize service
                service = PreAuthService(enable_llm_fallback=False)

                # Run validation - returns (result, medical_note)
                result, medical_note = service.validate_preauth_from_pdf(
                    pdf_path=tmp_file_path,
                    insurer=form_data['insurer'],
                    policy_type=form_data['policy_type'],
                    procedure_id=form_data['procedure_id'],
                    form_data=form_data
                )

                # Store result
                st.session_state.preauth_validation_result = result
                st.session_state.preauth_form_data = form_data
                st.session_state.preauth_medical_note = medical_note

                # Clean up
                Path(tmp_file_path).unlink()

                st.success("Validation completed successfully!")

            except Exception as e:
                st.error(f"Error during validation: {str(e)}")
                import traceback
                with st.expander("View error details"):
                    st.code(traceback.format_exc())
                return

    # Display results
    if st.session_state.preauth_validation_result:
        display_validation_results(st.session_state.preauth_validation_result)

        # Save data option
        st.markdown("---")
        st.subheader("💾 Save Data for Discharge Validation")

        st.info("""
        **Save this pre-authorization data** for discharge validation later:
        - You'll get a **Reference ID**
        - Use this ID after treatment completes for faster discharge bill validation
        - We'll compare final bill against this pre-auth estimate

        *This is optional - you can validate discharge later without saving.*
        """)

        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("💾 Save for Discharge Validation", type="primary", use_container_width=True):
                try:
                    storage = ClaimStorageService()
                    claim_id = storage.save_claim(
                        validation_result=st.session_state.preauth_validation_result,
                        form_data=st.session_state.preauth_form_data,
                        medical_note=st.session_state.preauth_medical_note
                    )

                    st.session_state.preauth_saved_claim_id = claim_id
                    st.success("Data saved successfully!")
                    st.balloons()

                except Exception as e:
                    st.error(f"Error saving data: {str(e)}")

        # Show reference ID if saved
        if 'preauth_saved_claim_id' in st.session_state and st.session_state.preauth_saved_claim_id:
            st.markdown("---")
            st.success("### Data Saved Successfully!")

            claim_id = st.session_state.preauth_saved_claim_id
            st.markdown(f"""
            ### 📋 Your Reference ID:
            ## `{claim_id}`

            **IMPORTANT:** Write this down or take a screenshot.

            You will need this ID after treatment is complete for discharge bill validation.
            """)

            # Copy-friendly text input
            st.text_input(
                "Reference ID (you can copy this):",
                value=claim_id,
                disabled=True,
                key="preauth_claim_id_display"
            )
