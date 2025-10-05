"""
Iris - Health Insurance Claims Co-Pilot
Main Streamlit Application with Sidebar Navigation

Modules:
1. Pre-Authorization Validation
2. Discharge Bill Validation
"""

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Iris - Claims Co-Pilot",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
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
    </style>
""", unsafe_allow_html=True)

# Main header
st.markdown('<p class="main-header">🏥 Iris - Health Insurance Claims Co-Pilot</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Validate your insurance claims before submission</p>', unsafe_allow_html=True)

# Module selector in main area - PROMINENT
st.markdown("---")
st.markdown("# 🔄 SELECT MODULE")
st.info("**IMPORTANT:** Choose which type of validation you need")

main_module_choice = st.radio(
    "What do you want to validate?",
    ["📋 Pre-Authorization (Before Treatment)", "🏥 Discharge Validation (After Treatment)"],
    index=0,
    horizontal=True,
    key="main_module_selector",
    label_visibility="visible"
)

st.markdown("---")
st.markdown("---")

# Sidebar - Module selection (same choice)
with st.sidebar:
    st.header("🔄 Select Module")

    module_choice = st.radio(
        "Choose validation type:",
        ["📋 Pre-Authorization", "🏥 Discharge Validation"],
        index=0,
        help="Select which module you want to use"
    )

    st.markdown("---")

    st.header("ℹ️ About Iris")
    st.markdown("""
    **Iris** helps you validate your health insurance claims documentation before submission.

    ### What We Do:
    - ✓ Check documentation completeness
    - ✓ Validate policy compliance
    - ✓ Compare costs against estimates
    - ✓ Provide medical guidance

    ### What We DON'T Do:
    - ✗ Predict insurer approval
    - ✗ Calculate your payment amount
    - ✗ Make coverage decisions

    **Final decisions are made by your insurance company.**
    """)

    st.markdown("---")
    st.markdown("**Version:** 1.0.0")
    st.markdown("**Last Updated:** Oct 2025")

# Render selected module (use main area choice)
if main_module_choice == "📋 Pre-Authorization (Before Treatment)":
    from modules import preauth_module
    preauth_module.render()
else:
    from modules import discharge_module
    discharge_module.render()
