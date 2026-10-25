"""
HR Review Workflow page.
Allows HR users to:
  - Predict an employee's promotion likelihood
  - Record their final HR decision (Approve / Reject / Hold)
  - Enter reason and development actions
  - Persist the review to SQLite
"""
import streamlit as st
import pandas as pd
from typing import List

from src.ui_components import page_header, alert, section_title
from src.config import DEPARTMENTS, EDUCATIONS, RECRUITMENT_CHANNELS, REGIONS
from src.predict import predict_single
from src.database import save_review, get_review
from src.preprocessing import preprocess_single
from src.explainability import (
    get_shap_explainer, compute_shap_values,
    plot_individual_shap, build_plain_language_explanation
)


def render(model, feature_columns: List[str], current_user: dict = None):
    page_header(
        "✅ HR Review Workflow",
        "Record your official HR decision separately from the model's recommendation into Cloud Firestore."
    )

    alert(
        "The model's prediction is a <strong>decision-support tool</strong>. "
        "Your HR decision is recorded independently and is the authoritative outcome.",
        "info"
    )

    # ── Employee input ─────────────────────────────────────────────────────────
    with st.form("hr_review_form"):
        section_title("Employee & Review Details")

        row1_c1, row1_c2, row1_c3 = st.columns(3)
        with row1_c1:
            emp_id   = st.text_input("Employee ID *", placeholder="e.g. EMP-1234")
            emp_name = st.text_input("Employee Name *", value="")
            department = st.selectbox("Department", DEPARTMENTS)

        with row1_c2:
            education   = st.selectbox("Education", EDUCATIONS)
            region      = st.selectbox("Region", REGIONS, index=0)
            gender      = st.selectbox("Gender", ["m", "f"],
                                       format_func=lambda x: "Male" if x == "m" else "Female")
            rec_channel = st.selectbox("Recruitment Channel", RECRUITMENT_CHANNELS)

        with row1_c3:
            age               = st.number_input("Age", 18, 70, 30)
            length_of_service = st.number_input("Length of Service (Yrs)", 1, 40, 3)
            no_of_trainings   = st.number_input("Trainings Completed", 1, 15, 1)
            previous_year_rating = st.select_slider("Previous Year Rating", [1,2,3,4,5], value=3)
            avg_training_score   = st.slider("Avg Training Score", 39, 100, 65)
            kpis_met  = st.selectbox("KPIs Met >80%?", ["No", "Yes"])
            award_won = st.selectbox("Award Won?", ["No", "Yes"])

        section_title("HR Decision")

        hr_col1, hr_col2, hr_col3 = st.columns(3)
        with hr_col1:
            hr_decision = st.selectbox(
                "HR Final Decision *",
                options=["Approve Promotion", "Reject Promotion", "Hold for Further Review"],
            )
        with hr_col2:
            default_reviewer = (current_user or {}).get("display_name") or (current_user or {}).get("email") or ""
            reviewer_name = st.text_input("Reviewer Name *", value=default_reviewer, placeholder="Your name / HR ID")
        with hr_col3:
            st.markdown("<br>", unsafe_allow_html=True)

        decision_reason = st.text_area(
            "Reason / Justification *",
            placeholder="Briefly explain your decision (e.g. 'Candidate shows strong leadership but KPIs slightly below target').",
            height=90
        )
        dev_actions = st.text_area(
            "Development Actions (optional)",
            placeholder="List any agreed training, mentorship, or targets.",
            height=70
        )

        submitted = st.form_submit_button("💾 Save HR Review & Get Model Prediction", use_container_width=True)

    if not submitted:
        # Check if existing review for this employee
        return

    # ── Validate required fields ───────────────────────────────────────────────
    errors = []
    if not emp_id.strip():     errors.append("Employee ID is required.")
    if not emp_name.strip():   errors.append("Employee Name is required.")
    if not reviewer_name.strip(): errors.append("Reviewer Name is required.")
    if not decision_reason.strip(): errors.append("Decision Reason is required.")

    if errors:
        for e in errors:
            alert(e, "danger")
        return

    # ── Run model prediction ───────────────────────────────────────────────────
    input_dict = {
        'no_of_trainings':       int(no_of_trainings),
        'age':                   int(age),
        'previous_year_rating':  float(previous_year_rating),
        'length_of_service':     int(length_of_service),
        'KPIs_met >80%':         1 if kpis_met == "Yes" else 0,
        'awards_won?':           1 if award_won == "Yes" else 0,
        'avg_training_score':    float(avg_training_score),
        'department':            department,
        'region':                region,
        'education':             education,
        'gender':                gender,
        'recruitment_channel':   rec_channel,
    }

    prediction, probability = predict_single(input_dict, model, feature_columns)

    user_email = (current_user or {}).get("email", "hr@promotionai.internal")
    user_role = (current_user or {}).get("role", "HR")
    review_id = save_review(
        employee_id=emp_id.strip(),
        employee_name=emp_name.strip(),
        department=department,
        prediction=prediction,
        probability=probability,
        hr_decision=hr_decision,
        decision_reason=decision_reason.strip(),
        development_actions=dev_actions.strip(),
        reviewer_name=reviewer_name.strip(),
        reviewer_email=user_email,
        reviewer_role=user_role
    )

    st.success(f"✅ HR Review saved to Cloud Firestore! (Record ID: {review_id})")

    # ── Show model prediction vs HR decision ───────────────────────────────────
    st.markdown("---")
    st.markdown("### 📋 Review Summary")

    rc1, rc2 = st.columns(2, gap="large")

    with rc1:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="content-card-title">🤖 Model Recommendation</div>', unsafe_allow_html=True)
        pred_color = "#16A34A" if prediction == 1 else "#DC2626"
        pred_label = "PROMOTION RECOMMENDED" if prediction == 1 else "NOT RECOMMENDED"
        st.markdown(f"""
        <div style="text-align:center; padding: 1rem 0;">
            <div style="font-size:1.2rem;font-weight:800;color:{pred_color};">{pred_label}</div>
            <div style="font-size:1.5rem;font-weight:700;color:{pred_color};margin-top:0.5rem;">{probability*100:.1f}%</div>
            <div style="font-size:0.8rem;color:#94A3B8;">Model estimated probability</div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(min(max(probability, 0.0), 1.0))
        st.caption("This is a statistical estimate — not the official decision.")
        st.markdown('</div>', unsafe_allow_html=True)

    with rc2:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="content-card-title">✅ Your HR Decision</div>', unsafe_allow_html=True)
        decision_color = {
            "Approve Promotion": "#16A34A",
            "Reject Promotion": "#DC2626",
            "Hold for Further Review": "#D97706"
        }.get(hr_decision, "#64748B")
        st.markdown(f"""
        <div style="text-align:center; padding: 1rem 0;">
            <div style="font-size:1.2rem;font-weight:800;color:{decision_color};">{hr_decision.upper()}</div>
            <div style="font-size:0.9rem;color:#475569;margin-top:0.5rem;font-style:italic;">"{decision_reason}"</div>
            <div style="font-size:0.8rem;color:#94A3B8;margin-top:0.4rem;">Reviewed by: {reviewer_name}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Model vs HR alignment note
    model_suggests_promote = prediction == 1
    hr_approves = "Approve" in hr_decision
    if model_suggests_promote and hr_approves:
        alert("✅ Model and HR decision are aligned — both recommend promotion.", "success")
    elif not model_suggests_promote and not hr_approves:
        alert("✅ Model and HR decision are aligned — both indicate no promotion at this time.", "success")
    elif model_suggests_promote and not hr_approves:
        alert(
            "⚠️ <strong>Override noted:</strong> The model recommended promotion but HR has rejected/held. "
            "Ensure the justification is documented for audit purposes.",
            "warning"
        )
    else:
        alert(
            "⚠️ <strong>Override noted:</strong> The model did not recommend promotion but HR has approved. "
            "Ensure the justification is documented for audit purposes.",
            "warning"
        )

    # ── SHAP mini-explanation ──────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("🔍 View Model Explanation (SHAP)", expanded=False):
        X_test = st.session_state.get('X_test')
        if X_test is not None:
            with st.spinner("Computing SHAP…"):
                try:
                    explainer = get_shap_explainer(model, X_test)
                    X_single  = preprocess_single(input_dict, feature_columns)
                    shap_vals, base_val = compute_shap_values(explainer, X_single)
                    fig = plot_individual_shap(shap_vals, base_val, X_single, feature_columns, top_n=8)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    alert(f"SHAP unavailable: {e}", "warning")
        else:
            alert("SHAP background data not loaded. Restart the app.", "warning")
