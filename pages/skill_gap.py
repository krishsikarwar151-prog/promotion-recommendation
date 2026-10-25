"""
Skill Gap Analysis page — standalone tool for HR to assess any employee.
"""
import streamlit as st
import pandas as pd

from src.ui_components import page_header, alert, section_title, kpi_card
from src.recommendations import analyse_skill_gaps, build_development_plan
from src.config import DEPARTMENTS, EDUCATIONS, RECRUITMENT_CHANNELS, REGIONS


def render():
    page_header(
        "📈 Skill Gap Analysis",
        "Identify development areas and generate a personalised 90-day action plan."
    )

    alert(
        "Recommendations are based on transparent, rule-based thresholds derived from the dataset. "
        "They are intended as <strong>HR decision-support</strong>, not automated decisions.",
        "info"
    )

    with st.form("skillgap_form"):
        section_title("Employee Information")
        cols = st.columns(3)

        with cols[0]:
            emp_name      = st.text_input("Employee Name", value="Priya Sharma")
            department    = st.selectbox("Department", DEPARTMENTS)
            education     = st.selectbox("Education", EDUCATIONS)

        with cols[1]:
            age               = st.number_input("Age", 18, 70, 30)
            length_of_service = st.number_input("Length of Service (Years)", 1, 40, 3)
            no_of_trainings   = st.number_input("Trainings Completed", 1, 15, 1)

        with cols[2]:
            previous_year_rating = st.select_slider("Previous Year Rating", [1,2,3,4,5], value=3)
            avg_training_score   = st.slider("Avg Training Score (0–100)", 39, 100, 60)
            kpis_met  = st.selectbox("KPIs Met >80%?", ["No", "Yes"])
            award_won = st.selectbox("Award Won?", ["No", "Yes"])

        submitted = st.form_submit_button("🔍 Analyse Skill Gaps", use_container_width=True)

    if not submitted:
        return

    employee = {
        'avg_training_score':   float(avg_training_score),
        'previous_year_rating': float(previous_year_rating),
        'KPIs_met >80%':        1 if kpis_met == "Yes" else 0,
        'awards_won?':          1 if award_won == "Yes" else 0,
        'length_of_service':    int(length_of_service),
        'no_of_trainings':      int(no_of_trainings),
        'age':                  int(age),
        'department':           department,
    }

    gaps     = analyse_skill_gaps(employee)
    dev_plan = build_development_plan(employee, gaps)

    st.markdown(f"### 📋 Analysis for **{emp_name}** — {department}")
    st.markdown("---")

    # ── Summary KPIs ──────────────────────────────────────────────────────────
    g_col1, g_col2, g_col3, g_col4 = st.columns(4)
    with g_col1:
        kpi_card("Gaps Found", str(len(gaps)), "Total development areas")
    with g_col2:
        high = sum(1 for g in gaps if g['priority'] == 'High')
        kpi_card("High Priority", str(high), "Immediate attention needed")
    with g_col3:
        kpi_card("Training Score", f"{int(avg_training_score)}/100",
                 "✅ On track" if avg_training_score >= 75 else "⚠️ Below benchmark (75)")
    with g_col4:
        kpi_card("Appraisal Rating", f"{previous_year_rating}/5",
                 "✅ Strong" if previous_year_rating >= 4 else "⚠️ Needs improvement")

    st.markdown("<br>", unsafe_allow_html=True)

    if not gaps:
        alert("✅ <strong>Excellent profile!</strong> No major gaps identified. "
              "This employee meets the key promotion benchmarks.", "success")
    else:
        st.markdown("### 🔍 Identified Skill Gaps")

        priority_icons = {'High': '🔴', 'Medium': '🟡', 'Low': '🟢'}
        for gap in gaps:
            icon = priority_icons[gap['priority']]
            with st.expander(
                f"{icon} {gap['name']}  —  Priority: {gap['priority']}",
                expanded=(gap['priority'] == 'High')
            ):
                st.markdown(gap['gap_description'])
                st.markdown("**📚 Recommended Development Resources:**")
                for idx, res in enumerate(gap['resources'], 1):
                    st.markdown(f"{idx}. {res}")

    # ── 90-Day Development Plan ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🗓️ 90-Day Development Plan")
    st.markdown(dev_plan['summary'])

    if dev_plan.get('timeline'):
        plan_data = pd.DataFrame(dev_plan['timeline'])
        plan_data.columns = ['Timeframe', 'Focus Area', 'Primary Action', 'Priority']

        # Color by priority
        def style_priority(val):
            if val == 'High':   return 'background-color: #FEE2E2; color: #991B1B; font-weight: bold'
            if val == 'Medium': return 'background-color: #FEF3C7; color: #92400E; font-weight: bold'
            return 'background-color: #DCFCE7; color: #166534; font-weight: bold'

        styled = plan_data.style.applymap(style_priority, subset=['Priority'])
        st.dataframe(styled, hide_index=True, use_container_width=True)

    st.info(f"📅 {dev_plan['next_review']}")

    # ── Progress tracker ──────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 Performance Benchmark Comparison")

    benchmarks = {
        'Training Score':      (float(avg_training_score), 75, 100),
        'Appraisal Rating':    (float(previous_year_rating) * 20, 80, 100),  # scale to %
        'KPI Achievement':     (100 if kpis_met == "Yes" else 0, 80, 100),
        'Awards Recognition':  (100 if award_won == "Yes" else 0, 0, 100),
        'Trainings Completed': (min(float(no_of_trainings) / 3.0 * 100, 100), 67, 100),
    }

    for metric_name, (val, benchmark_pct, _) in benchmarks.items():
        col_m, col_b = st.columns([3, 1])
        with col_m:
            color = "#16A34A" if val >= benchmark_pct else "#DC2626"
            st.write(f"**{metric_name}**")
            st.progress(min(int(val), 100) / 100)
        with col_b:
            st.markdown(f"""
            <div style="text-align:right; padding-top:0.5rem;">
                <span style="color:{color}; font-weight:700;">{val:.0f}%</span>
                <span style="color:#94A3B8; font-size:0.8rem;"> / benchmark {benchmark_pct}%</span>
            </div>
            """, unsafe_allow_html=True)
