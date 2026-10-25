"""
Explainability module: SHAP-based individual and global explanations.

Supports TreeExplainer (RandomForest, XGBoost, GBM) and falls back to
permutation importance for linear models.

IMPORTANT: Feature contributions describe the MODEL'S reasoning,
not causal relationships or guaranteed promotion outcomes.
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from typing import List, Optional, Tuple

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px


# ──────────────────────────────────────────────────────────────────────────────
# SHAP helpers
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_shap_explainer(_model, _X_background: pd.DataFrame):
    """
    Build and cache a SHAP explainer.
    Uses TreeExplainer for tree-based models, LinearExplainer otherwise.
    Background dataset is a stratified sample of ≤200 rows for speed.
    """
    import shap
    background = _X_background.sample(
        n=min(200, len(_X_background)), random_state=42
    )
    try:
        explainer = shap.TreeExplainer(_model, background)
    except Exception:
        try:
            explainer = shap.LinearExplainer(_model, background)
        except Exception:
            explainer = shap.KernelExplainer(_model.predict_proba, background)
    return explainer


def compute_shap_values(explainer, X_single: pd.DataFrame):
    """
    Compute SHAP values for a single row.
    Returns (shap_values_positive_class, base_value).
    """
    import shap
    sv = explainer(X_single)

    # Handle both old-style (list) and new-style Explanation objects
    if hasattr(sv, 'values'):
        vals = sv.values
        base = sv.base_values
        if vals.ndim == 3:        # multi-class: take class-1 slice
            vals = vals[:, :, 1]
            base = base[:, 1] if base.ndim == 2 else base
        shap_row = vals[0]
        base_val = float(base[0]) if hasattr(base, '__len__') else float(base)
    else:
        # Old shap list API
        sv_class1 = sv[1] if isinstance(sv, list) else sv
        shap_row = sv_class1[0]
        base_val = float(explainer.expected_value[1]) if isinstance(
            explainer.expected_value, (list, np.ndarray)) else float(explainer.expected_value)

    return shap_row, base_val


# ──────────────────────────────────────────────────────────────────────────────
# Individual explanation waterfall chart
# ──────────────────────────────────────────────────────────────────────────────

def plot_individual_shap(
    shap_values: np.ndarray,
    base_value: float,
    X_single: pd.DataFrame,
    feature_columns: List[str],
    top_n: int = 10
) -> go.Figure:
    """
    Draw a horizontal waterfall bar chart showing the top-N features
    that pushed the prediction toward (+) or away from (−) promotion.
    """
    shap_df = pd.DataFrame({
        'feature': feature_columns,
        'shap_value': shap_values,
        'input_value': X_single.iloc[0].values
    })
    shap_df['abs_shap'] = shap_df['shap_value'].abs()
    shap_df = shap_df.nlargest(top_n, 'abs_shap').sort_values('shap_value')

    colors = ['#DC2626' if v < 0 else '#16A34A' for v in shap_df['shap_value']]
    labels = [
        f"{row['feature']} = {row['input_value']:.2g}  ({'+' if row['shap_value']>0 else ''}{row['shap_value']:.3f})"
        for _, row in shap_df.iterrows()
    ]

    fig = go.Figure(go.Bar(
        x=shap_df['shap_value'].values,
        y=labels,
        orientation='h',
        marker_color=colors,
        text=[f"{'+' if v>0 else ''}{v:.3f}" for v in shap_df['shap_value']],
        textposition='outside',
        hovertemplate='Feature: %{y}<br>SHAP: %{x:.4f}<extra></extra>'
    ))

    fig.update_layout(
        title=dict(text=f"Individual SHAP Contributions (base = {base_value:.3f})", font=dict(size=14)),
        xaxis_title="SHAP value  →  pushes toward Promotion",
        yaxis_title="",
        height=max(320, top_n * 36),
        margin=dict(l=20, r=60, t=40, b=20),
        paper_bgcolor='#FFFFFF',
        plot_bgcolor='#F8FAFC',
        xaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='#94A3B8'),
        font=dict(family="Inter, sans-serif", size=12),
    )
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# Global feature importance chart
# ──────────────────────────────────────────────────────────────────────────────

def plot_global_importance(metrics: dict, top_n: int = 15) -> Optional[go.Figure]:
    """
    Bar chart of global feature importances from the model's feature_importances_ attribute.
    Returns None if no importances are available.
    """
    fi = metrics.get('feature_importances')
    if fi is None:
        return None

    top = fi.head(top_n).reset_index()
    top.columns = ['Feature', 'Importance']
    top = top.sort_values('Importance', ascending=True)

    fig = px.bar(
        top, x='Importance', y='Feature', orientation='h',
        color='Importance',
        color_continuous_scale=['#93C5FD', '#1D4ED8'],
        text=top['Importance'].apply(lambda x: f"{x*100:.1f}%"),
        title=f"Global Feature Importance — Top {top_n} Drivers"
    )
    fig.update_coloraxes(showscale=False)
    fig.update_traces(textposition='outside')
    fig.update_layout(
        height=max(300, top_n * 28),
        margin=dict(l=10, r=60, t=50, b=10),
        paper_bgcolor='#FFFFFF',
        plot_bgcolor='#F8FAFC',
        xaxis=dict(title="Relative Importance (Gini)", showgrid=True, gridcolor='#E2E8F0'),
        font=dict(family="Inter, sans-serif", size=12),
    )
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# Human-readable explanation text
# ──────────────────────────────────────────────────────────────────────────────

def build_plain_language_explanation(
    shap_values: np.ndarray,
    feature_columns: List[str],
    X_single: pd.DataFrame,
    prediction: int,
    probability: float,
    top_n: int = 5
) -> dict:
    """
    Produce a human-readable explanation dict:
      {
        'outcome_summary': str,
        'top_positive': List[str],   # features pushing TOWARD promotion
        'top_negative': List[str],   # features pushing AWAY from promotion
        'disclaimer': str,
      }
    """
    shap_df = pd.DataFrame({
        'feature': feature_columns,
        'shap_value': shap_values,
        'input_value': X_single.iloc[0].values
    }).sort_values('shap_value', ascending=False)

    positives = shap_df[shap_df['shap_value'] > 0].head(top_n)
    negatives = shap_df[shap_df['shap_value'] < 0].tail(top_n)

    def fmt_row(row):
        return f"**{row['feature']}** = `{row['input_value']:.2g}` (impact: {'+' if row['shap_value']>0 else ''}{row['shap_value']:.3f})"

    outcome = "🎉 **Recommended for Promotion**" if prediction == 1 else "❌ **Not Recommended for Promotion**"

    return {
        'outcome_summary': f"{outcome} — Model confidence: **{probability*100:.1f}%**",
        'top_positive': [fmt_row(r) for _, r in positives.iterrows()],
        'top_negative': [fmt_row(r) for _, r in negatives.iterrows()],
        'disclaimer': (
            "⚠️ These feature contributions describe the **model's statistical reasoning**, "
            "not causal relationships. A high SHAP value for a feature means the model weighted "
            "that input heavily — it does not guarantee that changing the feature will change the outcome, "
            "nor does the model prediction constitute an official promotion decision."
        )
    }
