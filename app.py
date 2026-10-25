"""
PromotionAI — Employee Promotion Recommendation System
Main application entry point with Firebase Authentication & Cloud Firestore.

Routing is handled via st.session_state['page'].
Role-based access control (Admin & HR) protects routes and operations.
"""
import warnings
warnings.filterwarnings("ignore")

import os
import sys

# Ensure the project root is on the path when running from any directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import streamlit as st

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="PromotionAI • HR Intelligence Platform",
    page_icon="👔",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "PromotionAI — ML-powered Employee Promotion Recommendation System with Cloud Firestore"}
)

from src.ui_components import inject_css, footer
from src.database import init_db, get_firebase_status
from src.auth_ui import render_login_portal, render_sidebar_user_badge
from src.config import CSV_FILE, MODEL_PATH, MODEL_LEGACY_PATH, ROLE_ADMIN, ROLE_HR
from src.train_model import load_or_train_model

import pandas as pd

# ── Initialise Database (Cloud Firestore) ──────────────────────────────────────
firebase_status = init_db()

# ── Inject global CSS ─────────────────────────────────────────────────────────
inject_css()

# ── User Authentication Gate ──────────────────────────────────────────────────
if 'user' not in st.session_state or st.session_state['user'] is None:
    render_login_portal()
    footer()
    st.stop()

current_user = st.session_state['user']
user_role = current_user.get("role", ROLE_HR)
is_admin = (user_role == ROLE_ADMIN)

# ── Cache: data & model ───────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data():
    df = pd.read_csv(CSV_FILE)
    df['education'] = df['education'].fillna("Bachelor's")
    df['previous_year_rating'] = df['previous_year_rating'].fillna(
        df['previous_year_rating'].median()
    )
    return df


@st.cache_resource(show_spinner=False)
def get_model_and_split(_df):
    return load_or_train_model(_df)


df_raw = load_data()
model, metrics, feature_columns, X_test, y_test = get_model_and_split(df_raw)

# Share globally via session state for pages
st.session_state['model']           = model
st.session_state['metrics']         = metrics
st.session_state['feature_columns'] = feature_columns
st.session_state['df_raw']          = df_raw
st.session_state['X_test']          = X_test
st.session_state['y_test']          = y_test

# ── Navigation (Full suite + Firestore Records CRUD) ─────────────────────────
PAGES = {
    "🏠 Home Dashboard":             "home",
    "👥 Cloud Firestore Records":    "employees",
    "⚡ Individual Prediction":      "predict",
    "📁 Bulk CSV Prediction":        "bulk",
    "🔍 Explainable AI (SHAP)":      "explain",
    "📈 Skill Gap Analysis":          "skillgap",
    "📊 HR Analytics":               "analytics",
    "🤖 Model Performance":          "model_perf",
    "⚖️ Fairness Audit":             "fairness",
    "✅ HR Review Workflow":          "review",
    "📄 Review History & Reports":   "history",
}

if 'page' not in st.session_state or st.session_state['page'] not in PAGES.values():
    st.session_state['page'] = 'home'

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding-bottom: 1.2rem;">
        <div style="font-size:2rem;">👔</div>
        <div style="font-size:1.05rem; font-weight:800; color:#F1F5F9; letter-spacing:-0.3px;">PromotionAI</div>
        <div style="font-size:0.73rem; color:#94A3B8; margin-top:2px;">HR Intelligence Platform</div>
    </div>
    """, unsafe_allow_html=True)

    # User Profile & Logout
    render_sidebar_user_badge(current_user)

    st.markdown("<p style='font-size:0.7rem; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:0.5rem;'>Platform Navigation</p>", unsafe_allow_html=True)

    for label, key in PAGES.items():
        if st.button(label, key=f"nav_{key}", use_container_width=True):
            st.session_state['page'] = key
            st.rerun()

    st.markdown("---")
    status_color = "#10B981" if firebase_status['is_live'] else "#3B82F6"
    st.markdown(f"""
    <div style="font-size:0.72rem; color:#475569; padding: 0 0.5rem;">
        <strong style="color:#94A3B8;">Storage:</strong> <span style="color:{status_color}; font-weight:600;">{firebase_status['mode']}</span><br>
        <strong style="color:#94A3B8;">Dataset:</strong> {len(df_raw):,} employees<br>
        <strong style="color:#94A3B8;">Model:</strong> Random Forest (SMOTE)<br>
        <strong style="color:#94A3B8;">ROC-AUC:</strong> {metrics.get('roc_auc', 0):.3f}<br>
        <strong style="color:#94A3B8;">F1 Score:</strong> {metrics.get('f1', 0):.3f}
    </div>
    """, unsafe_allow_html=True)

# ── Page routing ──────────────────────────────────────────────────────────────
page = st.session_state['page']

if page == 'home':
    from pages.home import render
    render(df_raw, metrics)

elif page == 'employees':
    from pages.employee_management import render
    render(df_raw, current_user)

elif page == 'predict':
    from pages.prediction import render
    render(model, metrics, feature_columns, df_raw, X_test)

elif page == 'bulk':
    from pages.bulk_prediction import render
    render(model, feature_columns)

elif page == 'explain':
    from pages.explainability import render
    render(model, metrics, feature_columns, df_raw, X_test)

elif page == 'skillgap':
    from pages.skill_gap import render
    render()

elif page == 'analytics':
    from pages.hr_analytics import render
    render(df_raw)

elif page == 'model_perf':
    from pages.model_performance import render
    render(df_raw, metrics)

elif page == 'fairness':
    from pages.fairness_audit import render
    render(df_raw)

elif page == 'review':
    from pages.hr_review import render
    render(model, feature_columns, current_user)

elif page == 'history':
    from pages.review_history import render
    render(current_user)

footer()
