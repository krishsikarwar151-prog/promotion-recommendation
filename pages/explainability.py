"""
Explainable AI page — Global SHAP summary + individual employee SHAP exploration.
"""
import streamlit as st
import pandas as pd
import numpy as np
from typing import List

from src.ui_components import page_header, alert, section_title
from src.explainability import (
    get_shap_explainer, compute_shap_values,
    plot_individual_shap, plot_global_importance,
    build_plain_language_explanation
)
from src.preprocessing import preprocess_single
from src.predict import predict_single
from src.config import DEPARTMENTS, EDUCATIONS, RECRUITMENT_CHANNELS, REGIONS


def render(model, metrics: dict, feature_columns: List[str], df_raw: pd.DataFrame, X_test: pd.DataFrame):
    page_header(
        "🔍 Explainable AI — SHAP Analysis",
        "Understand how the model makes decisions, both globally and for individual employees."
    )

    alert(
        "⚠️ SHAP values describe the <strong>model's statistical reasoning</strong>, not causal relationships. "
        "A positive SHAP contribution means the feature pushed this prediction <em>toward promotion</em> "
        "relative to the model's average prediction — it does not imply causation.",
        "info"
    )

    tab_global, tab_individual = st.tabs(["🌐 Global Importance", "👤 Individual Explanation"])

    # ── Tab 1: Global ──────────────────────────────────────────────────────────
    with tab_global:
        st.markdown("### 📊 Global Feature Importance")
        st.write("Which features does the model rely on most across all 54,808 employees?")

        fig_gi = plot_global_importance(metrics, top_n=20)
        if fig_gi:
            st.plotly_chart(fig_gi, use_container_width=True)

        fi = metrics.get('feature_importances')
        if fi is not None:
            top_df = fi.reset_index()
            top_df.columns = ['Feature', 'Relative Importance']
            top_df['Relative Importance (%)'] = (top_df['Relative Importance'] * 100).round(2)
            top_df = top_df.drop('Relative Importance', axis=1)
            top_df.index = range(1, len(top_df) + 1)

            with st.expander("📋 Full Feature Importance Table", expanded=False):
                st.dataframe(top_df, use_container_width=True)

        # Interpretation guide
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="content-card-title">📖 How to Read This Chart</div>', unsafe_allow_html=True)
        st.markdown("""
        | Feature | Typical Impact |
        |---------|---------------|
        | `avg_training_score` | Strongest driver — higher scores correlate with promotion |
        | `previous_year_rating` | Consistent high ratings (4–5) signal promotion readiness |
        | `KPIs_met >80%` | Meeting KPIs is one of the most important binary signals |
        | `awards_won?` | Organizational recognition significantly boosts the score |
        | `length_of_service` | Moderate impact — very long tenure may slightly reduce probability |
        | `age`, `no_of_trainings` | Secondary signals with moderate importance |
        | Categorical features | Department, Region, Education — minor but measurable effects |
        """)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Tab 2: Individual ──────────────────────────────────────────────────────
    with tab_individual:
        st.markdown("### 👤 Explore Explanation for a Specific Employee")
        st.write("Select an employee from the dataset or enter custom values to see their individual SHAP explanation.")

        mode = st.radio("Input method:", ["Select from Dataset", "Enter Custom Employee"], horizontal=True)

        input_dict = None

        if mode == "Select from Dataset":
            idx = st.selectbox(
                "Select employee index (sample of 100):",
                options=df_raw.sample(100, random_state=1).index.tolist()
            )
            row = df_raw.loc[idx]
            input_dict = {
                'no_of_trainings':      int(row.get('no_of_trainings', 1)),
                'age':                  int(row.get('age', 30)),
                'previous_year_rating': float(row.get('previous_year_rating', 3.0)),
                'length_of_service':    int(row.get('length_of_service', 3)),
                'KPIs_met >80%':        int(row.get('KPIs_met >80%', 0)),
                'awards_won?':          int(row.get('awards_won?', 0)),
                'avg_training_score':   float(row.get('avg_training_score', 60)),
                'department':           str(row.get('department', 'Technology')),
                'region':               str(row.get('region', 'region_1')),
                'education':            str(row.get('education', "Bachelor's")),
                'gender':               str(row.get('gender', 'm')),
                'recruitment_channel':  str(row.get('recruitment_channel', 'sourcing')),
            }
            actual = int(row.get('is_promoted', -1)) if 'is_promoted' in row else -1
            st.info(f"Actual historical label: **{'Promoted ✅' if actual == 1 else 'Not Promoted ❌' if actual == 0 else 'Unknown'}**")

        else:
            with st.form("explain_custom_form"):
                cc1, cc2 = st.columns(2)
                with cc1:
                    e_dept   = st.selectbox("Department", DEPARTMENTS, key="ex_dept")
                    e_edu    = st.selectbox("Education", EDUCATIONS, key="ex_edu")
                    e_region = st.selectbox("Region", REGIONS, key="ex_region")
                    e_gender = st.selectbox("Gender", ["m", "f"], format_func=lambda x: "Male" if x=="m" else "Female", key="ex_gender")
                    e_rc     = st.selectbox("Recruitment Channel", RECRUITMENT_CHANNELS, key="ex_rc")
                    e_age    = st.number_input("Age", 18, 70, 30, key="ex_age")
                with cc2:
                    e_svc    = st.number_input("Length of Service (yrs)", 1, 40, 5, key="ex_svc")
                    e_train  = st.number_input("No. of Trainings", 1, 15, 2, key="ex_train")
                    e_rating = st.select_slider("Previous Year Rating", [1,2,3,4,5], value=3, key="ex_rating")
                    e_score  = st.slider("Avg Training Score", 39, 100, 65, key="ex_score")
                    e_kpi    = st.selectbox("KPIs Met >80%?", ["No","Yes"], key="ex_kpi")
                    e_award  = st.selectbox("Award Won?", ["No","Yes"], key="ex_award")
                custom_submitted = st.form_submit_button("Compute SHAP Explanation")

            if custom_submitted or 'custom_explain_dict' in st.session_state:
                if custom_submitted:
                    st.session_state['custom_explain_dict'] = {
                        'no_of_trainings':      int(e_train),
                        'age':                  int(e_age),
                        'previous_year_rating': float(e_rating),
                        'length_of_service':    int(e_svc),
                        'KPIs_met >80%':        1 if e_kpi == "Yes" else 0,
                        'awards_won?':          1 if e_award == "Yes" else 0,
                        'avg_training_score':   float(e_score),
                        'department':           e_dept,
                        'region':               e_region,
                        'education':            e_edu,
                        'gender':               e_gender,
                        'recruitment_channel':  e_rc,
                    }
                input_dict = st.session_state['custom_explain_dict']

        if input_dict is not None:
            pred, prob = predict_single(input_dict, model, feature_columns)
            X_single   = preprocess_single(input_dict, feature_columns)

            with st.spinner("Computing SHAP values…"):
                try:
                    explainer = get_shap_explainer(model, X_test)
                    shap_vals, base_val = compute_shap_values(explainer, X_single)
                    explanation = build_plain_language_explanation(
                        shap_vals, feature_columns, X_single, pred, prob
                    )

                    outcome_color = "#16A34A" if pred == 1 else "#DC2626"
                    st.markdown(f"""
                    <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;padding:1.2rem;margin-bottom:1rem;">
                        <span style="font-size:1.15rem;font-weight:800;color:{outcome_color};">
                            {'🎉 Promotion Recommended' if pred==1 else '❌ Not Recommended'}
                        </span>
                        &nbsp;&nbsp;
                        <span style="font-size:1rem;color:#475569;font-weight:600;">
                            Probability: <strong style="color:{outcome_color};">{prob*100:.1f}%</strong>
                        </span>
                        &nbsp;&nbsp;
                        <span style="font-size:0.88rem;color:#94A3B8;">
                            (base value: {base_val:.3f})
                        </span>
                    </div>
                    """, unsafe_allow_html=True)

                    st.plotly_chart(
                        plot_individual_shap(shap_vals, base_val, X_single, feature_columns, top_n=12),
                        use_container_width=True
                    )

                    pos_col, neg_col = st.columns(2)
                    with pos_col:
                        st.markdown("**✅ Factors pushing toward promotion:**")
                        for item in explanation['top_positive']:
                            st.markdown(f"- {item}")
                    with neg_col:
                        st.markdown("**❌ Factors reducing prediction:**")
                        for item in explanation['top_negative']:
                            st.markdown(f"- {item}")

                    alert(explanation['disclaimer'], "warning")

                except Exception as e:
                    alert(f"SHAP computation failed: {e}", "danger")
