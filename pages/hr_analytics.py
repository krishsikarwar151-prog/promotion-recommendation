"""
HR Analytics Dashboard page.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from src.ui_components import page_header, alert, section_title, kpi_card
from src.analytics import (
    compute_kpis, chart_dept_distribution, chart_dept_promotion_rate,
    chart_rating_dist, chart_training_score_hist, chart_age_service,
    chart_training_score_by_promotion, chart_recruitment_channel,
    chart_education_dist, _base_layout
)


def render(df: pd.DataFrame):
    page_header(
        "📊 HR Analytics Dashboard",
        "Interactive workforce analytics based on historical HR data (54,808 employees)."
    )

    # ── Filters ────────────────────────────────────────────────────────────────
    with st.expander("🔽 Filters", expanded=False):
        f1, f2, f3 = st.columns(3)
        with f1:
            dept_filter = st.multiselect(
                "Department", options=sorted(df['department'].unique()),
                default=[]
            )
        with f2:
            edu_filter = st.multiselect(
                "Education", options=sorted(df['education'].dropna().unique()),
                default=[]
            )
        with f3:
            promoted_filter = st.selectbox(
                "Promotion Status (historical)", ["All", "Promoted", "Not Promoted"]
            )

    filtered = df.copy()
    if dept_filter:
        filtered = filtered[filtered['department'].isin(dept_filter)]
    if edu_filter:
        filtered = filtered[filtered['education'].isin(edu_filter)]
    if promoted_filter == "Promoted":
        filtered = filtered[filtered['is_promoted'] == 1]
    elif promoted_filter == "Not Promoted":
        filtered = filtered[filtered['is_promoted'] == 0]

    if len(filtered) == 0:
        alert("No data matches the current filters. Please adjust them.", "warning")
        return

    # ── KPI Strip ──────────────────────────────────────────────────────────────
    kpis = compute_kpis(filtered)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: kpi_card("Employees", f"{kpis['total_employees']:,}", "In selection")
    with c2: kpi_card("Promoted", f"{kpis['promoted']:,}" if kpis['promoted'] else "N/A", "Historical")
    with c3: kpi_card("Promo Rate", f"{kpis['promotion_rate']*100:.1f}%" if kpis['promotion_rate'] else "N/A", "Actual labels")
    with c4: kpi_card("Avg Training", f"{kpis['avg_training']:.1f}" if kpis['avg_training'] else "N/A", "Score /100")
    with c5: kpi_card("Avg Rating", f"{kpis['avg_rating']:.2f}" if kpis['avg_rating'] else "N/A", "Score /5")
    with c6: kpi_card("KPI Met %", f"{kpis['kpi_met_pct']:.1f}%" if kpis['kpi_met_pct'] else "N/A", ">80% threshold")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts ─────────────────────────────────────────────────────────────────
    row1_c1, row1_c2 = st.columns(2, gap="large")
    with row1_c1:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.plotly_chart(chart_dept_distribution(filtered), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with row1_c2:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        fig = chart_dept_promotion_rate(filtered)
        if fig: st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    row2_c1, row2_c2 = st.columns(2, gap="large")
    with row2_c1:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.plotly_chart(chart_training_score_hist(filtered), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with row2_c2:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.plotly_chart(chart_rating_dist(filtered), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    row3_c1, row3_c2 = st.columns(2, gap="large")
    with row3_c1:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.plotly_chart(chart_age_service(filtered), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with row3_c2:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        fig_ts = chart_training_score_by_promotion(filtered)
        if fig_ts: st.plotly_chart(fig_ts, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    row4_c1, row4_c2 = st.columns(2, gap="large")
    with row4_c1:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.plotly_chart(chart_recruitment_channel(filtered), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with row4_c2:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.plotly_chart(chart_education_dist(filtered), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Raw data table ─────────────────────────────────────────────────────────
    with st.expander("📋 View Raw Data Table", expanded=False):
        st.dataframe(filtered, use_container_width=True, height=350)
        st.download_button(
            "📥 Download Filtered Data",
            data=filtered.to_csv(index=False).encode('utf-8'),
            file_name="filtered_employees.csv",
            mime="text/csv"
        )
