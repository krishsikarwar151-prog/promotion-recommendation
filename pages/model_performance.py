"""
Model Performance page — evaluation metrics, ROC, PR curves, confusion matrix,
and optional multi-model comparison.
"""
import streamlit as st
import pandas as pd

from src.ui_components import page_header, alert, section_title, kpi_card
from src.analytics import (
    chart_roc_curve, chart_pr_curve, chart_confusion_matrix
)
from src.explainability import plot_global_importance


def render(df_raw: pd.DataFrame, metrics: dict):
    page_header(
        "🤖 Model Performance",
        "Evaluation metrics computed on the stratified 20% holdout test set (10,962 employees)."
    )

    alert(
        "All metrics below are computed on the <strong>held-out test set</strong> (unseen during training). "
        "The class imbalance (91% not promoted) makes accuracy a misleading primary metric — "
        "use <strong>F1, Recall, and ROC-AUC</strong> for a fair assessment.",
        "info"
    )

    # ── Primary metrics ────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1: kpi_card("Accuracy",   f"{metrics['accuracy']*100:.2f}%",  "Overall correct predictions")
    with m2: kpi_card("Precision",  f"{metrics['precision']*100:.2f}%", "Of predicted promos, truly promoted")
    with m3: kpi_card("Recall",     f"{metrics['recall']*100:.2f}%",    "Of actual promos, correctly caught")
    with m4: kpi_card("F1 Score",   f"{metrics['f1']*100:.2f}%",        "Harmonic mean of P & R")
    with m5: kpi_card("ROC-AUC",    f"{metrics.get('roc_auc',0)*100:.2f}%", "Discrimination ability")

    pr_auc = metrics.get('pr_auc')
    if pr_auc:
        pa_col, _ = st.columns([1, 4])
        with pa_col:
            kpi_card("PR-AUC", f"{pr_auc*100:.2f}%", "For imbalanced classes")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts row ─────────────────────────────────────────────────────────────
    ch1, ch2 = st.columns(2, gap="large")
    with ch1:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.plotly_chart(chart_confusion_matrix(metrics), use_container_width=True)
        cm = metrics['confusion_matrix']
        st.caption(
            f"TN={cm[0][0]:,}  FP={cm[0][1]:,}  FN={cm[1][0]:,}  TP={cm[1][1]:,} | "
            f"Test set: {cm.sum():,} employees"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with ch2:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.plotly_chart(chart_roc_curve(metrics), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if pr_auc:
        ch3, _ = st.columns([1, 1], gap="large")
        with ch3:
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            st.plotly_chart(chart_pr_curve(metrics), use_container_width=True)
            st.caption("PR-AUC is more informative than ROC-AUC for highly imbalanced datasets.")
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Feature importance ─────────────────────────────────────────────────────
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    fig_gi = plot_global_importance(metrics, top_n=20)
    if fig_gi:
        st.plotly_chart(fig_gi, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Multi-model comparison ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔬 Multi-Model Comparison")
    st.write(
        "Compare Logistic Regression, Random Forest, Gradient Boosting, and XGBoost "
        "trained on the same split. This trains fresh models and may take 1–3 minutes."
    )

    if st.button("🚀 Train & Compare All Models"):
        with st.spinner("Training and evaluating all models on the full dataset…"):
            try:
                from src.train_model import train_all_models
                results = train_all_models(df_raw)
                rows = []
                for name, res in results.items():
                    m = res['metrics']
                    rows.append({
                        'Model': name,
                        'Accuracy (%)':  round(m['accuracy']*100, 2),
                        'Precision (%)': round(m['precision']*100, 2),
                        'Recall (%)':    round(m['recall']*100, 2),
                        'F1 (%)':        round(m['f1']*100, 2),
                        'ROC-AUC (%)':   round(m.get('roc_auc',0)*100, 2),
                        'PR-AUC (%)':    round(m.get('pr_auc',0)*100, 2),
                    })
                comp_df = pd.DataFrame(rows).set_index('Model')

                # Highlight best in each column
                st.success("✅ Model comparison complete!")
                st.dataframe(
                    comp_df.style.highlight_max(axis=0, color='#DCFCE7'),
                    use_container_width=True
                )
                alert(
                    "Green cells = best score in that column. "
                    "For imbalanced datasets, prioritise <strong>F1</strong> and <strong>ROC-AUC</strong> over Accuracy.",
                    "info"
                )

                # ROC overlay
                import plotly.graph_objects as go
                palette = ['#2563EB', '#16A34A', '#DC2626', '#D97706']
                fig_roc = go.Figure()
                for (name, res), color in zip(results.items(), palette):
                    m = res['metrics']
                    fig_roc.add_trace(go.Scatter(
                        x=m['fpr'], y=m['tpr'], mode='lines',
                        name=f"{name} (AUC={m.get('roc_auc',0):.3f})",
                        line=dict(width=2.5, color=color)
                    ))
                fig_roc.add_trace(go.Scatter(x=[0,1], y=[0,1], mode='lines',
                                              name='Random', line=dict(dash='dash', color='#94A3B8')))
                fig_roc.update_layout(
                    title='ROC Curves — All Models',
                    xaxis_title='False Positive Rate',
                    yaxis_title='True Positive Rate',
                    height=380,
                    paper_bgcolor='#FFFFFF', plot_bgcolor='#F8FAFC',
                    font=dict(family="Inter, sans-serif")
                )
                st.plotly_chart(fig_roc, use_container_width=True)

            except Exception as e:
                alert(f"Model comparison failed: {e}", "danger")

    # ── Model architecture docs ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📖 Model Architecture & Training Details")
    with st.expander("View Technical Details", expanded=False):
        st.markdown("""
        | Component | Detail |
        |-----------|--------|
        | **Algorithm** | Random Forest Classifier (scikit-learn) |
        | **Estimators** | 100 decision trees |
        | **Max Depth** | 10 (prevents overfitting) |
        | **Min Samples Leaf** | 2 |
        | **Class Imbalance** | SMOTE (1:1 oversampling in training fold only) |
        | **Train / Test Split** | 80% / 20%, stratified by target |
        | **Encoding** | One-hot with `drop_first=True` (53 features total) |
        | **Missing Values** | education → `Bachelor's` (mode); rating → 3.0 (corporate median) |
        | **Feature Importance** | Gini impurity averaged over 100 trees |
        | **Explainability** | SHAP TreeExplainer |
        | **Saved Artifact** | `models/model_rf.joblib` (joblib format) |

        **Why SMOTE over class-weight adjustment?**
        The 89:11 class ratio is severe enough that class-weight alone produces a high-recall
        but low-precision model. SMOTE synthesises new minority examples by interpolating
        along k-NN vectors, providing better calibrated decision boundaries.

        **Why Random Forest over XGBoost?**
        Random Forest with max_depth=10 provides near-equivalent AUC with superior
        interpretability via SHAP TreeExplainer, and trains in ~30s vs ~2min for a tuned XGBoost.
        XGBoost is available in the Model Comparison section for benchmarking.
        """)
