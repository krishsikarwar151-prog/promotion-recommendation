"""
Fairness & Bias Audit page.
Compares historical promotion rates and performance metrics across demographic/organisational groups.

IMPORTANT DISCLAIMER:
- Sensitive attributes (gender, department, region) are used ONLY for auditing purposes.
- No promotion decisions should be based on these attributes.
- Small sample size warnings are shown for groups with < 100 employees.
- This analysis shows statistical associations, not causes.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.ui_components import page_header, alert, section_title
from src.analytics import compute_fairness_metrics, chart_fairness_bar, _base_layout


def render(df: pd.DataFrame):
    page_header(
        "⚖️ Fairness & Bias Audit",
        "Examine historical promotion disparities across employee groups — for HR review and awareness only."
    )

    alert(
        "⚠️ <strong>Disclaimer:</strong> This module analyses statistical associations in historical data "
        "and is intended for <strong>awareness and review</strong> only. Observed disparities may reflect "
        "systemic factors, sample selection, or historical biases — not causal discrimination. "
        "Small sample sizes are flagged. Do <strong>NOT</strong> use these statistics as grounds for or against individual promotion decisions.",
        "warning"
    )

    # ── Group selector ─────────────────────────────────────────────────────────
    group_options = {
        'Department':           'department',
        'Gender':               'gender',
        'Education Level':      'education',
        'Recruitment Channel':  'recruitment_channel',
    }
    selected_label = st.selectbox("Compare promotion outcomes by:", list(group_options.keys()))
    group_col = group_options[selected_label]

    # ── Compute fairness table ─────────────────────────────────────────────────
    fairness_df = compute_fairness_metrics(df, group_col)

    if fairness_df.empty:
        alert("Not enough data for this comparison.", "warning")
        return

    # Flag small samples
    small_flag = fairness_df['Small Sample'].any()
    if small_flag:
        alert(
            "⚠️ Some groups have fewer than 100 employees. Statistics for these groups "
            "are less reliable and should be interpreted with caution.",
            "warning"
        )

    # ── Summary table ──────────────────────────────────────────────────────────
    section_title(f"📋 Group Comparison: {selected_label}")

    display_df = fairness_df.drop(columns=['Small Sample']).copy()
    st.dataframe(display_df, hide_index=True, use_container_width=True)

    # ── Promotion rate bar chart ───────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="content-card-title">📊 Historical Promotion Rate by Group</div>', unsafe_allow_html=True)
        fig = chart_fairness_bar(fairness_df, 'Promotion Rate (%)')
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="content-card-title">📈 Avg Training Score by Group</div>', unsafe_allow_html=True)
        fig2 = chart_fairness_bar(fairness_df, 'Avg Training Score')
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    col3, col4 = st.columns(2, gap="large")

    with col3:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="content-card-title">⭐ Avg Performance Rating by Group</div>', unsafe_allow_html=True)
        fig3 = chart_fairness_bar(fairness_df, 'Avg Rating')
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="content-card-title">🎯 KPI Met Rate by Group (%)</div>', unsafe_allow_html=True)
        fig4 = chart_fairness_bar(fairness_df, 'KPI Met Rate (%)')
        st.plotly_chart(fig4, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Disparity analysis ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📐 Disparity Analysis")

    promo_rates = fairness_df[['Group', 'Promotion Rate (%)']].copy()
    promo_rates['Promotion Rate (%)'] = pd.to_numeric(promo_rates['Promotion Rate (%)'], errors='coerce')
    max_rate = promo_rates['Promotion Rate (%)'].max()
    min_rate = promo_rates['Promotion Rate (%)'].min()
    max_group = promo_rates.loc[promo_rates['Promotion Rate (%)'].idxmax(), 'Group']
    min_group = promo_rates.loc[promo_rates['Promotion Rate (%)'].idxmin(), 'Group']
    disparity = max_rate - min_rate

    d_col1, d_col2, d_col3 = st.columns(3)
    with d_col1:
        st.metric("Highest Promotion Rate", f"{max_rate:.1f}%", f"Group: {max_group}")
    with d_col2:
        st.metric("Lowest Promotion Rate", f"{min_rate:.1f}%", f"Group: {min_group}")
    with d_col3:
        st.metric("Absolute Disparity", f"{disparity:.1f}pp",
                  "pp = percentage points")

    if disparity > 5:
        alert(
            f"A {disparity:.1f} percentage-point gap in promotion rates between <strong>{max_group}</strong> "
            f"and <strong>{min_group}</strong> warrants further investigation. "
            "This may reflect genuine performance differences, historical bias, or sample characteristics.",
            "warning"
        )
    else:
        alert(
            f"The promotion rate disparity of {disparity:.1f} percentage points across groups is relatively low. "
            "Continue monitoring as the dataset grows.",
            "success"
        )

    # ── Gender deep-dive ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔍 Gender Analysis (Historical Data)")

    gender_df = df.groupby('gender').agg(
        Count=('is_promoted', 'count'),
        Promoted=('is_promoted', 'sum'),
        Avg_Training=('avg_training_score', 'mean'),
        Avg_Rating=('previous_year_rating', 'mean'),
        KPI_Rate=('KPIs_met >80%', 'mean'),
    ).reset_index()
    gender_df['Promotion Rate (%)'] = (gender_df['Promoted'] / gender_df['Count'] * 100).round(2)
    gender_df['gender'] = gender_df['gender'].map({'m': 'Male', 'f': 'Female'})

    st.dataframe(gender_df.rename(columns={
        'gender': 'Gender', 'Count': 'Employees', 'Promoted': 'Promoted (historical)',
        'Avg_Training': 'Avg Training Score', 'Avg_Rating': 'Avg Rating',
        'KPI_Rate': 'KPI Met Rate'
    }), hide_index=True, use_container_width=True)

    alert(
        "Gender is included in the dataset and model features. "
        "Model gender importance is < 3% (Gini weight). "
        "HR should review if the observed promotion rate gap is explained by performance differences "
        "or warrants a deeper equity audit.",
        "info"
    )

    # ── Report download ────────────────────────────────────────────────────────
    report_data = fairness_df.drop(columns=['Small Sample'])
    st.download_button(
        "📥 Download Fairness Report CSV",
        data=report_data.to_csv(index=False).encode('utf-8'),
        file_name=f"fairness_report_{group_col}.csv",
        mime="text/csv"
    )
