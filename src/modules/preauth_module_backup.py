"""
Iris - Pre-Authorization Documentation Validator
Streamlit frontend for validating pre-authorization documentation
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.preauth_service import PreAuthService
from src.utils.data_loader import list_available_procedures, list_available_policies
from src.services.claim_storage import ClaimStorageService


# Page configuration
st.set_page_config(
    page_title="Iris - Pre-Auth Validator",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .status-pass {
        background-color: #d4edda;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        border-left: 5px solid #28a745;
    }
    .status-warning {
        background-color: #fff3cd;
        color: #856404;
        padding: 10px;
        border-radius: 5px;
        border-left: 5px solid #ffc107;
    }
    .status-fail {
        background-color: #f8d7da;
        color: #721c24;
        padding: 10px;
        border-radius: 5px;
        border-left: 5px solid #dc3545;
    }
    .issue-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 4px solid #6c757d;
    }
    </style>
""", unsafe_allow_html=True)


def display_header():
    """Display application header"""
    st.markdown('<p class="main-header">🏥 Iris - Pre-Authorization Validator</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Validate your pre-authorization documentation before submission</p>', unsafe_allow_html=True)
    st.markdown("---")


def get_policy_inputs():
    """Get policy and patient details from user"""
    st.subheader("📋 Policy & Patient Information")

    col1, col2 = st.columns(2)

    with col1:
        # Get available policies and create combined dropdown options
        available_policies = list_available_policies()

        # Create display name: "Insurer - Policy Name"
        policy_display_options = {}
        for p in available_policies:
            display_name = f"{p['insurer']} - {p['policy_name']}"
            policy_display_options[display_name] = {
                'insurer': p['insurer'],
                'policy_type': p['policy_name']
            }

        # Sort options alphabetically
        sorted_display_names = sorted(policy_display_options.keys())

        selected_policy_display = st.selectbox(
            "Insurance Policy",
            options=sorted_display_names,
            help="Select your insurance company and policy type"
        )

        # Extract insurer and policy type from selection
        selected_policy = policy_display_options[selected_policy_display]
        insurer = selected_policy['insurer']
        policy_type = selected_policy['policy_type']

        policy_number = st.text_input(
            "Policy Number",
            placeholder="e.g., SH12345678",
            help="Your policy number"
        )

        sum_insured = st.number_input(
            "Sum Insured (₹)",
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
    """Display validation results in a user-friendly format"""
    st.markdown("---")
    st.subheader("📊 Validation Results")

    # Overall score and status
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Documentation Score",
            value=f"{result.final_score}/100",
            delta=f"{result.final_score - 100} from baseline"
        )

    with col2:
        status_emoji = {
            "pass": "✅",
            "warning": "⚠️",
            "fail": "❌"
        }
        status_text = {
            "pass": "Complete",
            "warning": "Needs Review",
            "fail": "Incomplete"
        }
        st.metric(
            label="Status",
            value=f"{status_emoji.get(result.overall_status, '❓')} {status_text.get(result.overall_status, 'Unknown')}"
        )

    with col3:
        likelihood_emoji = {
            "high": "🟢",
            "medium": "🟡",
            "low": "🔴"
        }
        st.metric(
            label="Readiness",
            value=f"{likelihood_emoji.get(result.approval_likelihood, '❓')} {result.approval_likelihood.title()}"
        )

    # Summary message
    st.markdown("### 📝 Summary")

    status_class = f"status-{result.overall_status}"
    st.markdown(f'<div class="{status_class}">{result.summary}</div>', unsafe_allow_html=True)

    # Agent-wise results
    st.markdown("### 🔍 Section-wise Analysis")

    agents = {
        "📋 Documentation Completeness": result.agent_results.completeness,
        "📜 Policy Compliance": result.agent_results.policy,
        "🏥 Medical Review": result.agent_results.medical,
        "🔍 Quality Check": result.agent_results.fwa
    }

    for agent_name, agent_result in agents.items():
        with st.expander(f"{agent_name} - {agent_result.status.upper()}", expanded=(agent_result.status != "pass")):
            # Status indicator
            status_colors = {"pass": "green", "warning": "orange", "fail": "red"}
            st.markdown(f"**Status:** :{status_colors.get(agent_result.status, 'gray')}[{agent_result.status.upper()}]")
            st.markdown(f"**Score Impact:** {agent_result.score_impact}")

            # Display specific issues
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

    # Action items
    if result.recommendations:
        st.markdown("### ✅ Action Items to Address")
        st.info("Please address the following items to improve your documentation:")

        for i, recommendation in enumerate(result.recommendations, 1):
            st.markdown(f"{i}. {recommendation}")

    # All issues consolidated
    if result.all_issues:
        with st.expander(f"📋 All Issues ({len(result.all_issues)} total)", expanded=False):
            for i, issue in enumerate(result.all_issues, 1):
                st.markdown(f"{i}. {issue}")


def main():
    """Main application flow"""
    display_header()

    # Initialize session state
    if 'validation_result' not in st.session_state:
        st.session_state.validation_result = None

    # Sidebar for instructions
    with st.sidebar:
        st.header("ℹ️ How to Use")
        st.markdown("""
        1. **Enter Policy Details**
           - Select your insurer and policy
           - Enter policy number and dates

        2. **Select Procedure**
           - Choose the procedure requiring pre-authorization

        3. **Upload Medical Note**
           - Upload the pre-authorization medical note PDF
           - Template format recommended

        4. **Review Results**
           - Check documentation completeness
           - Address identified issues
           - Download report (coming soon)

        ---

        **Note:** This tool validates documentation completeness only.
        It does not make approval/rejection decisions.
        """)

        st.markdown("---")
        st.markdown("**Version:** 1.0.0")
        st.markdown("**Last Updated:** Oct 2025")

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

    # Process validation when form is submitted
    if submitted:
        if not uploaded_file:
            st.error("❌ Please upload a medical note PDF to proceed.")
            return

        if not form_data['policy_number']:
            st.error("❌ Please enter a policy number.")
            return

        # Show progress
        with st.spinner("🔄 Processing your documentation..."):
            try:
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    tmp_file_path = tmp_file.name

                # Initialize service
                service = PreAuthService(enable_llm_fallback=False)

                # Run validation
                result = service.validate_preauth_from_pdf(
                    pdf_path=tmp_file_path,
                    insurer=form_data['insurer'],
                    policy_type=form_data['policy_type'],
                    procedure_id=form_data['procedure_id'],
                    form_data=form_data
                )

                # Store result and form data in session state
                st.session_state.validation_result = result
                st.session_state.form_data = form_data
                st.session_state.medical_note = result.get('medical_note', {})

                # Clean up temp file
                Path(tmp_file_path).unlink()

                st.success("✅ Validation completed successfully!")

            except Exception as e:
                st.error(f"❌ Error during validation: {str(e)}")
                import traceback
                with st.expander("View error details"):
                    st.code(traceback.format_exc())
                return

    # Display results if available
    if st.session_state.validation_result:
        display_validation_results(st.session_state.validation_result)

        # Save claim option
        st.markdown("---")
        st.subheader("💾 Save Claim for Discharge Tracking")

        st.info("""
        **Save this claim** to track it through discharge:
        - You'll get a **Claim Reference ID**
        - Use this ID later for faster discharge bill validation
        - We'll compare final bill against this pre-auth estimate

        *This is optional - you can validate discharge later without saving.*
        """)

        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("💾 Save Claim", type="primary", use_container_width=True):
                try:
                    storage = ClaimStorageService()
                    claim_id = storage.save_claim(
                        validation_result=st.session_state.validation_result,
                        form_data=st.session_state.form_data,
                        medical_note=st.session_state.medical_note
                    )

                    st.session_state.saved_claim_id = claim_id
                    st.success(f"✅ Claim saved successfully!")
                    st.balloons()

                except Exception as e:
                    st.error(f"❌ Error saving claim: {str(e)}")

        # Show claim ID if just saved
        if 'saved_claim_id' in st.session_state and st.session_state.saved_claim_id:
            st.markdown("---")
            st.success("### ✅ Claim Saved Successfully!")

            claim_id = st.session_state.saved_claim_id
            st.markdown(f"""
            ### 📋 Your Claim Reference ID:
            ## `{claim_id}`

            **IMPORTANT:** Write this down or take a screenshot.

            You will need this ID after treatment is complete for discharge bill validation.
            """)

            # Option to copy to clipboard (via text input)
            st.text_input(
                "Claim ID (you can copy this):",
                value=claim_id,
                disabled=True,
                key="claim_id_display"
            )


if __name__ == "__main__":
    main()
