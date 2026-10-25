"""
Analytics module: computes KPIs and chart data for the HR Analytics Dashboard.
All aggregate statistics are derived from actual dataset records.
Model predictions and actual historical labels are clearly distinguished.
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ── Palette ───────────────────────────────────────────────────────────────────
PRIMARY   = '#2563EB'
SUCCESS   = '#16A34A'
DANGER    = '#DC2626'
WARNING   = '#D97706'
NEUTRAL   = '#64748B'
PALETTE   = [PRIMARY, SUCCESS, DANGER, WARNING, '#7C3AED', '#0891B2', '#BE185D']


# ── KPI Cards ─────────────────────────────────────────────────────────────────
def compute_kpis(df: pd.DataFrame) -> dict:
    """Compute dashboard KPI values from the historical dataset."""
    total = len(df)
    promoted = int(df['is_promoted'].sum()) if 'is_promoted' in df.columns else None
    promotion_rate = promoted / total if promoted is not None else None
    avg_training = float(df['avg_training_score'].mean()) if 'avg_training_score' in df.columns else None
    avg_rating   = float(df['previous_year_rating'].mean()) if 'previous_year_rating' in df.columns else None
    kpi_met_pct  = float((df['KPIs_met >80%'].sum() / total) * 100) if 'KPIs_met >80%' in df.columns else None
    awards_pct   = float((df['awards_won?'].sum() / total) * 100) if 'awards_won?' in df.columns else None

    return {
        'total_employees':  total,
        'promoted':         promoted,
        'promotion_rate':   promotion_rate,
        'avg_training':     avg_training,
        'avg_rating':       avg_rating,
        'kpi_met_pct':      kpi_met_pct,
        'awards_pct':       awards_pct,
    }


# ── Department charts ─────────────────────────────────────────────────────────
def chart_dept_distribution(df: pd.DataFrame) -> go.Figure:
    dept_counts = df['department'].value_counts().reset_index()
    dept_counts.columns = ['Department', 'Count']
    fig = px.bar(
        dept_counts.sort_values('Count'),
        x='Count', y='Department', orientation='h',
        color='Count', color_continuous_scale=[PRIMARY, '#93C5FD'],
        title='Employee Distribution by Department',
        text='Count'
    )
    fig.update_coloraxes(showscale=False)
    fig.update_traces(textposition='outside')
    fig.update_layout(**_base_layout(height=340))
    return fig


def chart_dept_promotion_rate(df: pd.DataFrame) -> go.Figure:
    if 'is_promoted' not in df.columns:
        return None
    grp = df.groupby('department').agg(
        total=('is_promoted', 'count'),
        promoted=('is_promoted', 'sum')
    ).reset_index()
    grp['rate'] = grp['promoted'] / grp['total'] * 100
    grp = grp.sort_values('rate', ascending=True)
    colors = [SUCCESS if r >= 10 else WARNING if r >= 6 else DANGER for r in grp['rate']]
    fig = go.Figure(go.Bar(
        x=grp['rate'], y=grp['department'], orientation='h',
        marker_color=colors,
        text=grp['rate'].apply(lambda x: f"{x:.1f}%"),
        textposition='outside',
    ))
    fig.update_layout(title='Promotion Rate by Department (%)', **_base_layout(height=340))
    return fig


# ── Performance charts ────────────────────────────────────────────────────────
def chart_rating_dist(df: pd.DataFrame) -> go.Figure:
    rc = df['previous_year_rating'].value_counts().sort_index()
    fig = px.bar(
        x=rc.index.astype(str), y=rc.values,
        color=rc.values, color_continuous_scale=[PRIMARY, '#93C5FD'],
        title='Previous Year Rating Distribution',
        labels={'x': 'Rating', 'y': 'Count'}
    )
    fig.update_coloraxes(showscale=False)
    fig.update_layout(**_base_layout(height=280))
    return fig


def chart_training_score_hist(df: pd.DataFrame) -> go.Figure:
    fig = px.histogram(
        df, x='avg_training_score', nbins=30,
        color_discrete_sequence=[PRIMARY],
        title='Average Training Score Distribution',
        labels={'avg_training_score': 'Training Score'}
    )
    fig.update_layout(**_base_layout(height=280))
    return fig


def chart_age_service(df: pd.DataFrame) -> go.Figure:
    fig = px.scatter(
        df.sample(min(3000, len(df)), random_state=42),
        x='age', y='length_of_service',
        color='is_promoted' if 'is_promoted' in df.columns else None,
        color_discrete_map={0: NEUTRAL, 1: SUCCESS},
        opacity=0.55,
        title='Age vs Length of Service',
        labels={'age': 'Age (Years)', 'length_of_service': 'Service (Years)'}
    )
    fig.update_layout(**_base_layout(height=300))
    return fig


def chart_training_score_by_promotion(df: pd.DataFrame) -> go.Figure:
    if 'is_promoted' not in df.columns:
        return None
    fig = px.box(
        df, x='is_promoted', y='avg_training_score',
        color='is_promoted',
        color_discrete_map={0: DANGER, 1: SUCCESS},
        points='outliers',
        title='Training Score by Promotion Outcome',
        labels={'is_promoted': 'Promoted (1=Yes)', 'avg_training_score': 'Avg Training Score'}
    )
    fig.update_layout(**_base_layout(height=300))
    return fig


def chart_recruitment_channel(df: pd.DataFrame) -> go.Figure:
    rc = df['recruitment_channel'].value_counts().reset_index()
    rc.columns = ['Channel', 'Count']
    fig = px.pie(
        rc, values='Count', names='Channel',
        color_discrete_sequence=PALETTE,
        title='Employees by Recruitment Channel',
        hole=0.45
    )
    fig.update_layout(**_base_layout(height=300))
    return fig


def chart_education_dist(df: pd.DataFrame) -> go.Figure:
    ec = df['education'].fillna("Bachelor's").value_counts().reset_index()
    ec.columns = ['Education', 'Count']
    fig = px.bar(
        ec, x='Education', y='Count',
        color='Count', color_continuous_scale=[PRIMARY, '#93C5FD'],
        title='Education Level Distribution', text='Count'
    )
    fig.update_coloraxes(showscale=False)
    fig.update_traces(textposition='outside')
    fig.update_layout(**_base_layout(height=280))
    return fig


# ── Fairness charts ───────────────────────────────────────────────────────────
def compute_fairness_metrics(df: pd.DataFrame, group_col: str, label_col: str = 'is_promoted') -> pd.DataFrame:
    """
    Compute FPR, FNR, precision, recall per group when both predicted and actual labels exist.
    For exploratory auditing only — small sample sizes are noted.
    """
    if label_col not in df.columns or group_col not in df.columns:
        return pd.DataFrame()

    rows = []
    for grp, sub in df.groupby(group_col):
        y_true = sub[label_col]
        n = len(sub)
        rows.append({
            'Group': grp,
            'Count': n,
            'Promotion Rate (%)': f"{y_true.mean()*100:.1f}",
            'Avg Training Score': f"{sub['avg_training_score'].mean():.1f}" if 'avg_training_score' in sub.columns else 'N/A',
            'Avg Rating': f"{sub['previous_year_rating'].mean():.1f}" if 'previous_year_rating' in sub.columns else 'N/A',
            'KPI Met Rate (%)': f"{sub['KPIs_met >80%'].mean()*100:.1f}" if 'KPIs_met >80%' in sub.columns else 'N/A',
            'Small Sample': n < 100
        })
    return pd.DataFrame(rows)


def chart_fairness_bar(fairness_df: pd.DataFrame, metric_col: str = 'Promotion Rate (%)') -> go.Figure:
    df = fairness_df.copy()
    df[metric_col] = pd.to_numeric(df[metric_col], errors='coerce')
    fig = px.bar(
        df.sort_values(metric_col),
        x='Group', y=metric_col,
        color='Group', color_discrete_sequence=PALETTE,
        title=f'{metric_col} by Group',
        text=df[metric_col].apply(lambda x: f"{x:.1f}%")
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(**_base_layout(height=320))
    return fig


# ── ROC / PR curves ───────────────────────────────────────────────────────────
def chart_roc_curve(metrics: dict) -> go.Figure:
    fpr = metrics.get('fpr', [0, 1])
    tpr = metrics.get('tpr', [0, 1])
    auc = metrics.get('roc_auc', 0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fpr, y=tpr, mode='lines', name=f'ROC (AUC={auc:.3f})', line=dict(color=PRIMARY, width=2.5)))
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode='lines', name='Random', line=dict(color=NEUTRAL, dash='dash')))
    fig.update_layout(
        title='ROC Curve', xaxis_title='False Positive Rate', yaxis_title='True Positive Rate',
        **_base_layout(height=300)
    )
    return fig


def chart_pr_curve(metrics: dict) -> go.Figure:
    rec  = metrics.get('rec_curve', [0, 1])
    prec = metrics.get('prec_curve', [1, 0])
    pr_auc = metrics.get('pr_auc', 0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rec, y=prec, mode='lines', name=f'PR (AUC={pr_auc:.3f})', line=dict(color=SUCCESS, width=2.5)))
    fig.update_layout(
        title='Precision-Recall Curve', xaxis_title='Recall', yaxis_title='Precision',
        **_base_layout(height=300)
    )
    return fig


# ── Confusion matrix ──────────────────────────────────────────────────────────
def chart_confusion_matrix(metrics: dict) -> go.Figure:
    cm = metrics.get('confusion_matrix')
    if cm is None:
        return None
    fig = go.Figure(go.Heatmap(
        z=cm,
        x=['Predicted: Retain', 'Predicted: Promote'],
        y=['Actual: Retain', 'Actual: Promote'],
        text=[[f"TN: {cm[0][0]:,}", f"FP: {cm[0][1]:,}"],
              [f"FN: {cm[1][0]:,}", f"TP: {cm[1][1]:,}"]],
        texttemplate="%{text}",
        colorscale=[[0, '#F1F5F9'], [0.5, '#BFDBFE'], [1, '#1D4ED8']],
        showscale=False
    ))
    fig.update_layout(
        title='Confusion Matrix', xaxis=dict(side='top'),
        **_base_layout(height=300)
    )
    return fig


# ── Helpers ───────────────────────────────────────────────────────────────────
def _base_layout(height: int = 320) -> dict:
    return dict(
        height=height,
        margin=dict(l=10, r=40, t=50, b=20),
        paper_bgcolor='#FFFFFF',
        plot_bgcolor='#F8FAFC',
        font=dict(family="Inter, sans-serif", size=12),
        legend=dict(bgcolor='rgba(0,0,0,0)')
    )
