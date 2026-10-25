"""
Individual Employee Prediction page with full SHAP explanation inline.
"""
import streamlit as st
import pandas as pd
import numpy as np
from typing import List

from src.ui_components import page_header, alert, section_title, kpi_card
from src.config import DEPARTMENTS, EDUCATIONS, RECRUITMENT_CHANNELS, REGIONS
from src.predict import predict_single
from src.preprocessing import preprocess_single
from src.explainability import (
    get_shap_explainer, compute_shap_values,
    plot_individual_shap, build_plain_language_explanation,
    plot_global_importance
)
from src.recommendations import analyse_skill_gaps, build_development_plan
from src.database import log_prediction_history


def render(model, metrics, feature_columns: List[str], df_raw: pd.DataFrame, X_test: pd.DataFrame):
    page_header(
        "⚡ Individual Promotion Prediction",
        "Enter employee details to generate an ML-powered promotion recommendation with SHAP explanation."
    )

    # ── Input form ────────────────────────────────────────────────────────────
    with st.form("prediction_form", clear_on_submit=False):
        c_left, c_right = st.columns(2, gap="large")

        with c_left:
            section_title("1. Employee Details")
            emp_name = st.text_input("Employee Name", value="Rahul Sharma", placeholder="Full name")
            emp_id   = st.text_input("Employee ID (optional)", value="", placeholder="e.g. EMP-001")

            department = st.selectbox("Department", options=DEPARTMENTS,
                                      index=DEPARTMENTS.index("Technology"))
            education  = st.selectbox("Education Level", options=EDUCATIONS, index=0)
            region     = st.selectbox("Region", options=REGIONS, index=0)

            gc, rc = st.columns(2)
            with gc:
                gender = st.selectbox("Gender", options=["m", "f"],
                                      format_func=lambda x: "Male" if x == "m" else "Female")
            with rc:
                recruitment_channel = st.selectbox("Recruitment Channel",
                                                   options=RECRUITMENT_CHANNELS)
            age = st.number_input("Age (Years)", min_value=18, max_value=70, value=29, step=1)

        with c_right:
            section_title("2. Performance & Track Record")
            sc, tc = st.columns(2)
            with sc:
                length_of_service = st.number_input("Length of Service (Years)",
                                                     min_value=1, max_value=40, value=4, step=1)
            with tc:
                no_of_trainings = st.number_input("Trainings Completed",
                                                  min_value=1, max_value=15, value=1, step=1)

            previous_year_rating = st.select_slider(
                "Previous Year Rating (1=Low, 5=High)", options=[1, 2, 3, 4, 5], value=4
            )
            avg_training_score = st.slider(
                "Average Training Score (0–100)", min_value=39, max_value=100, value=76
            )

            k_col, a_col = st.columns(2)
            with k_col:
                kpis_met = st.selectbox("KPIs Met >80%?", options=["No", "Yes"], index=1)
            with a_col:
                award_won = st.selectbox("Award Won?", options=["No", "Yes"], index=0)

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("🚀 Predict Promotion & Explain", use_container_width=True)

    # ── Build input dict ───────────────────────────────────────────────────────
    if submitted:
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
            'recruitment_channel':   recruitment_channel,
        }
        prediction, probability = predict_single(input_dict, model, feature_columns)

        log_prediction_history(
            employee_id=emp_id.strip() or "N/A",
            features=input_dict,
            prediction=prediction,
            probability=probability,
            user=st.session_state.get('user')
        )

        st.session_state['last_prediction'] = {
            'input_dict':   input_dict,
            'prediction':   prediction,
            'probability':  probability,
            'emp_name':     emp_name.strip() or "Employee",
            'emp_id':       emp_id.strip() or "N/A",
            'department':   department,
        }

    # ── Display results ────────────────────────────────────────────────────────
    if 'last_prediction' not in st.session_state:
        alert("Fill in the form above and click <strong>Predict Promotion & Explain</strong> to see results.", "info")
        return

    res = st.session_state['last_prediction']
    prediction  = res['prediction']
    probability = res['probability']
    input_dict  = res['input_dict']
    emp_name    = res['emp_name']
    emp_id      = res['emp_id']

    st.markdown("---")

    # ── Prediction result card ─────────────────────────────────────────────────
    r1, r2 = st.columns([1.3, 1], gap="large")

    with r1:
        if prediction == 1:
            st.markdown(f"""
            <div class="result-promoted">
                <div class="result-label" style="color:#16A34A;">🎉 PROMOTION RECOMMENDED</div>
                <p style="color:#15803D;font-size:1rem;margin:0.5rem 0;">
                    <strong>{emp_name}</strong> matches the profile of promoted employees across key benchmarks.
                </p>
                <div class="result-prob">Probability: <strong style="color:#16A34A;">{probability*100:.1f}%</strong></div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="result-not-promoted">
                <div class="result-label" style="color:#DC2626;">❌ NOT RECOMMENDED</div>
                <p style="color:#991B1B;font-size:1rem;margin:0.5rem 0;">
                    <strong>{emp_name}</strong> is currently below the promotion benchmark in this appraisal cycle.
                </p>
                <div class="result-prob">Probability: <strong style="color:#DC2626;">{probability*100:.1f}%</strong></div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.write(f"**Likelihood Index:** `{probability*100:.1f}%` — Decision Threshold: `50.0%`")
        st.progress(min(max(probability, 0.0), 1.0))

    with r2:
        section_title("Candidate Profile Summary")
        summary_df = pd.DataFrame({
            "Field": ["Name", "ID", "Department", "Education", "Region", "Gender", "Age",
                      "Service", "Trainings", "Rating", "Training Score", "KPIs Met", "Award Won"],
            "Value": [
                emp_name, emp_id, input_dict['department'], input_dict['education'],
                input_dict['region'],
                "Male" if input_dict['gender'] == 'm' else "Female",
                f"{input_dict['age']} yrs",
                f"{input_dict['length_of_service']} yrs",
                str(input_dict['no_of_trainings']),
                f"{input_dict['previous_year_rating']}/5",
                f"{int(input_dict['avg_training_score'])}/100",
                "Yes" if input_dict['KPIs_met >80%'] else "No",
                "Yes" if input_dict['awards_won?'] else "No",
            ]
        })
        st.dataframe(summary_df, hide_index=True, use_container_width=True)

    # ── SHAP Explanation ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔍 Why This Prediction? (SHAP Explanation)")
    alert(
        "These feature contributions describe the <strong>model's statistical reasoning</strong>, "
        "not causal relationships. They do not guarantee a promotion outcome.",
        "info"
    )

    with st.spinner("Computing SHAP values…"):
        try:
            explainer  = get_shap_explainer(model, X_test)
            X_single   = preprocess_single(input_dict, feature_columns)
            shap_vals, base_val = compute_shap_values(explainer, X_single)
            explanation = build_plain_language_explanation(
                shap_vals, feature_columns, X_single, prediction, probability
            )

            # Plain-language summary
            st.markdown(f"**{explanation['outcome_summary']}**")

            e_col1, e_col2 = st.columns(2, gap="large")

            with e_col1:
                st.markdown("#### ✅ Factors Supporting Promotion")
                if explanation['top_positive']:
                    for item in explanation['top_positive']:
                        st.markdown(f"- {item}")
                else:
                    st.markdown("_No strong positive factors detected._")

            with e_col2:
                st.markdown("#### ❌ Factors Reducing Score")
                if explanation['top_negative']:
                    for item in explanation['top_negative']:
                        st.markdown(f"- {item}")
                else:
                    st.markdown("_No strong negative factors detected._")

            # SHAP waterfall bar chart
            st.plotly_chart(
                plot_individual_shap(shap_vals, base_val, X_single, feature_columns),
                use_container_width=True
            )

            st.markdown(f"""
            <div class="alert-warning">{explanation['disclaimer']}</div>
            """, unsafe_allow_html=True)

        except Exception as e:
            alert(f"SHAP computation unavailable: {e}. Showing global importance instead.", "warning")
            fig_gi = plot_global_importance(metrics)
            if fig_gi:
                st.plotly_chart(fig_gi, use_container_width=True)

    # ── Global feature importance ──────────────────────────────────────────────
    with st.expander("📊 Global Feature Importance (across all employees)", expanded=False):
        fig_gi = plot_global_importance(metrics)
        if fig_gi:
            st.plotly_chart(fig_gi, use_container_width=True)
            st.caption(
                "Global importance shows which features the model relies on most across all predictions. "
                "Individual SHAP values above show how these features influenced THIS specific employee's prediction."
            )

    # ── Skill Gap & Development Plan ──────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📈 Skill Gap Analysis & 90-Day Development Plan")

    gaps = analyse_skill_gaps(input_dict)
    dev_plan = build_development_plan(input_dict, gaps)

    if not gaps:
        alert("✅ No major skill gaps identified. This employee meets key promotion benchmarks.", "success")
    else:
        for gap in gaps:
            badge_color = {'High': '#FEE2E2', 'Medium': '#FEF3C7', 'Low': '#DCFCE7'}[gap['priority']]
            text_color  = {'High': '#991B1B', 'Medium': '#92400E', 'Low': '#166534'}[gap['priority']]
            with st.expander(f"{'🔴' if gap['priority']=='High' else '🟡' if gap['priority']=='Medium' else '🟢'} {gap['name']} — Priority: {gap['priority']}", expanded=(gap['priority']=='High')):
                st.markdown(gap['gap_description'])
                st.markdown("**Recommended actions:**")
                for r in gap['resources']:
                    st.markdown(f"- {r}")

    st.markdown(f"**Development Plan Summary:** {dev_plan['summary']}")

    if dev_plan.get('timeline'):
        plan_df = pd.DataFrame(dev_plan['timeline'])
        st.dataframe(plan_df.rename(columns={
            'window': 'Timeframe', 'area': 'Focus Area',
            'action': 'Recommended Action', 'priority': 'Priority'
        }), hide_index=True, use_container_width=True)

    st.info(dev_plan['next_review'])

    # ── PDF Download ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📄 Download Assessment Report")
    if st.button("Generate PDF Report"):
        from src.reports import generate_employee_pdf
        try:
            shap_expl = build_plain_language_explanation(
                shap_vals, feature_columns, X_single, prediction, probability
            ) if 'shap_vals' in dir() else {'top_positive': [], 'top_negative': [], 'disclaimer': ''}
        except Exception:
            shap_expl = {'top_positive': [], 'top_negative': [], 'disclaimer': ''}

        emp_data = {**input_dict, 'name': emp_name, 'employee_id': emp_id}
        pdf_bytes = generate_employee_pdf(emp_data, prediction, probability, shap_expl, gaps, dev_plan)
        ext = 'pdf' if pdf_bytes[:4] == b'%PDF' else 'txt'
        st.download_button(
            label="📥 Download Report",
            data=pdf_bytes,
            file_name=f"promotion_report_{emp_name.replace(' ','_')}.{ext}",
            mime='application/pdf' if ext == 'pdf' else 'text/plain'
        )
