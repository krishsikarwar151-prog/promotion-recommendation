"""
Home / Overview Dashboard page.
Shows KPI summary cards, promotion rate donut, department bar, and model badge strip.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.ui_components import page_header, kpi_card, alert
from src.analytics import (
    compute_kpis, chart_dept_distribution, chart_dept_promotion_rate,
    chart_training_score_hist, chart_recruitment_channel, _base_layout
)


def render(df: pd.DataFrame, metrics: dict):
    page_header(
        "👔 PromotionAI — HR Intelligence Platform",
        "Enterprise-grade machine learning for fair, data-driven promotion decisions."
    )

    # ── Model badge strip ──────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:1.5rem;">
        <span style="background:#EFF6FF;border:1px solid #BFDBFE;color:#1E40AF;
                     padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600;">
            📁 {len(df):,} Employees
        </span>
        <span style="background:#F0FDF4;border:1px solid #BBF7D0;color:#166534;
                     padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600;">
            🤖 Random Forest + SMOTE
        </span>
        <span style="background:#FFF7ED;border:1px solid #FED7AA;color:#9A3412;
                     padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600;">
            🎯 ROC-AUC: {metrics.get('roc_auc',0)*100:.1f}%
        </span>
        <span style="background:#F5F3FF;border:1px solid #DDD6FE;color:#5B21B6;
                     padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600;">
            ⚡ Real-Time Inference
        </span>
        <span style="background:#FDF2F8;border:1px solid #FBCFE8;color:#9D174D;
                     padding:5px 14px;border-radius:999px;font-size:0.8rem;font-weight:600;">
            🔬 SHAP Explainability
        </span>
    </div>
    """, unsafe_allow_html=True)

    kpis = compute_kpis(df)

    # ── KPI cards row ──────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("Total Employees", f"{kpis['total_employees']:,}", "Historical dataset")
    with c2:
        kpi_card("Promoted", f"{kpis['promoted']:,}", "Actual historical labels")
    with c3:
        kpi_card("Promotion Rate", f"{kpis['promotion_rate']*100:.1f}%", "89:11 class imbalance")
    with c4:
        kpi_card("Avg Training Score", f"{kpis['avg_training']:.1f}", "Out of 100")
    with c5:
        kpi_card("KPI Met Rate", f"{kpis['kpi_met_pct']:.1f}%", "KPIs >80% threshold")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts row ─────────────────────────────────────────────────────────────
    ch1, ch2 = st.columns(2, gap="large")

    with ch1:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="content-card-title">🏢 Department Distribution</div>', unsafe_allow_html=True)
        st.plotly_chart(chart_dept_distribution(df), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with ch2:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="content-card-title">📈 Promotion Rate by Department</div>', unsafe_allow_html=True)
        fig = chart_dept_promotion_rate(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    ch3, ch4 = st.columns(2, gap="large")

    with ch3:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="content-card-title">📊 Training Score Distribution</div>', unsafe_allow_html=True)
        st.plotly_chart(chart_training_score_hist(df), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with ch4:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="content-card-title">📡 Recruitment Channel Mix</div>', unsafe_allow_html=True)
        st.plotly_chart(chart_recruitment_channel(df), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Quick-start guide ──────────────────────────────────────────────────────
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.markdown('<div class="content-card-title">🚀 Quick Start Guide</div>', unsafe_allow_html=True)
    cols = st.columns(5)
    steps = [
        ("⚡", "Individual Prediction", "Enter employee details and get an instant ML prediction with probability."),
        ("📁", "Bulk CSV Upload", "Upload a CSV of employees for batch scoring and download results."),
        ("🔍", "Explainable AI", "Understand WHY the model made its prediction using SHAP values."),
        ("📈", "Skill Gap Analysis", "Get a personalised 90-day development plan for any employee."),
        ("✅", "HR Review", "Record your final decision separately from the model's recommendation."),
    ]
    for col, (icon, title, desc) in zip(cols, steps):
        with col:
            st.markdown(f"""
            <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;
                        padding:1rem;text-align:center;height:100%;">
                <div style="font-size:1.8rem;">{icon}</div>
                <div style="font-weight:700;font-size:0.85rem;color:#0F172A;margin:6px 0 4px;">{title}</div>
                <div style="font-size:0.78rem;color:#64748B;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    alert(
        "⚠️ <strong>Important:</strong> All predictions are machine learning estimates based on historical patterns. "
        "They are intended as decision-support tools only. Final promotion decisions must be made by qualified HR personnel.",
        "warning"
    )
