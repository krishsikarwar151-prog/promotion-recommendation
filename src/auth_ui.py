"""
PromotionAI — Firebase Authentication & Role-Based Access Control UI.

Provides:
  - Secure Firebase login & registration modal/portal
  - Quick-switch demo accounts (Admin vs HR)
  - Sidebar user status badge & logout button
  - Role verification helpers
"""

import streamlit as st
from src.config import ROLE_ADMIN, ROLE_HR
from src.database import (
    authenticate_user,
    register_user,
    get_firebase_status,
)


def render_login_portal():
    """Render the Firebase Authentication login/register portal."""
    status = get_firebase_status()

    st.markdown("""
    <div style="text-align: center; margin-top: 1.5rem; margin-bottom: 2rem;">
        <div style="font-size: 3rem; margin-bottom: 0.5rem;">👔</div>
        <h1 style="color: #0F172A; font-size: 2.1rem; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 0.3rem;">
            PromotionAI • HR Intelligence
        </h1>
        <p style="color: #64748B; font-size: 1rem; max-width: 500px; margin: 0 auto;">
            Enterprise Machine Learning Platform for Objective, Explainable & Fair Promotion Recommendations
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Firebase project connection badge
    st.markdown(f"""
    <div style="max-width: 540px; margin: 0 auto 1.5rem auto; background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 0.65rem 1rem; text-align: center; font-size: 0.82rem; color: #166534;">
        🔥 <strong>Firebase:</strong> Connected to <code>{status.get('project_id', 'promotion-a1dc4')}</code> &nbsp;|&nbsp; 🔐 <strong>Auth & Datastore:</strong> Live Active
    </div>
    """, unsafe_allow_html=True)

    col_center = st.columns([1, 2, 1])[1]

    with col_center:
        auth_tab1, auth_tab2, auth_tab3 = st.tabs(["🔐 Sign In", "⚡ Quick Demo Logins", "📝 Create Account"])

        # ── TAB 1: Email / Password Sign In ───────────────────────────────────
        with auth_tab1:
            st.markdown("<p style='font-size:0.88rem; color:#475569;'>Sign in with your corporate email credentials.</p>", unsafe_allow_html=True)
            with st.form("signin_form"):
                email = st.text_input("Corporate Email", placeholder="user@company.com", key="login_email")
                password = st.text_input("Password", type="password", key="login_pw")
                login_btn = st.form_submit_button("Sign In to PromotionAI", type="primary", use_container_width=True)

                if login_btn:
                    with st.spinner("Authenticating with Firebase..."):
                        success, user, msg = authenticate_user(email, password)
                        if success:
                            st.session_state['user'] = user
                            st.session_state['page'] = 'home'
                            st.success(f"Welcome back, {user['display_name']}!")
                            st.rerun()
                        else:
                            st.error(f"Authentication Failed: {msg}")

        # ── TAB 2: Quick Demo Logins (One-Click) ──────────────────────────────
        with auth_tab2:
            st.markdown("<p style='font-size:0.88rem; color:#475569;'>Test the system immediately with pre-configured role profiles:</p>", unsafe_allow_html=True)

            c_admin, c_hr = st.columns(2)
            with c_admin:
                st.markdown("""
                <div style="background:#FEF2F2; border:1px solid #FECACA; border-radius:8px; padding:0.8rem; margin-bottom:0.5rem; text-align:center;">
                    <div style="font-size:1.5rem;">👑</div>
                    <strong style="color:#991B1B; font-size:0.9rem;">Administrator</strong>
                    <div style="font-size:0.75rem; color:#7F1D1D; margin-top:2px;">Full CRUD & Deletion rights</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Log in as Admin", type="primary", use_container_width=True, key="btn_login_admin"):
                    success, user, _ = authenticate_user("admin@promotionai.internal", "Admin@2026!")
                    if success:
                        st.session_state['user'] = user
                        st.session_state['page'] = 'home'
                        st.rerun()

            with c_hr:
                st.markdown("""
                <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-radius:8px; padding:0.8rem; margin-bottom:0.5rem; text-align:center;">
                    <div style="font-size:1.5rem;">👔</div>
                    <strong style="color:#1E40AF; font-size:0.9rem;">HR Specialist</strong>
                    <div style="font-size:0.75rem; color:#1E3A8A; margin-top:2px;">Predictions & Reviews</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Log in as HR", use_container_width=True, key="btn_login_hr"):
                    success, user, _ = authenticate_user("hr@promotionai.internal", "HRManager@2026!")
                    if success:
                        st.session_state['user'] = user
                        st.session_state['page'] = 'home'
                        st.rerun()

        # ── TAB 3: Create Account ─────────────────────────────────────────────
        with auth_tab3:
            st.markdown("<p style='font-size:0.88rem; color:#475569;'>Register a new account in Cloud Firestore.</p>", unsafe_allow_html=True)
            with st.form("register_form"):
                reg_name = st.text_input("Full Name", placeholder="e.g. Alex Morgan")
                reg_email = st.text_input("Corporate Email", placeholder="e.g. alex@company.com")
                reg_pw = st.text_input("Create Password", type="password", placeholder="Min. 6 characters")
                reg_role = st.selectbox("Designated Role", [ROLE_HR, ROLE_ADMIN], index=0)

                reg_submit = st.form_submit_button("Create Account in Firebase", type="primary", use_container_width=True)

                if reg_submit:
                    with st.spinner("Registering user in Firebase..."):
                        ok, user, msg = register_user(reg_email, reg_pw, reg_role, reg_name)
                        if ok:
                            st.session_state['user'] = user
                            st.session_state['page'] = 'home'
                            st.success(f"Account registered! Logged in as {user['display_name']} ({user['role']}).")
                            st.rerun()
                        else:
                            st.error(msg)


def render_sidebar_user_badge(current_user: dict):
    """Render the current logged-in user profile, role badge, and logout button."""
    role = current_user.get("role", ROLE_HR)
    email = current_user.get("email", "")
    name = current_user.get("display_name", email.split("@")[0].title())
    is_admin = (role == ROLE_ADMIN)

    badge_bg = "#DC2626" if is_admin else "#2563EB"
    badge_label = "Admin 👑" if is_admin else "HR Specialist 👔"

    st.markdown(f"""
    <div style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 0.75rem 0.85rem; margin-bottom: 1rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="font-weight:700; color:#F8FAFC; font-size:0.88rem;">{name}</div>
            <span style="background:{badge_bg}; color:#FFFFFF; font-size:0.68rem; font-weight:700; padding:2px 7px; border-radius:10px;">
                {badge_label}
            </span>
        </div>
        <div style="font-size:0.73rem; color:#94A3B8; margin-top:2px; word-break:break-all;">{email}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚪 Sign Out", key="sidebar_logout_btn", use_container_width=True):
        st.session_state['user'] = None
        st.session_state['page'] = 'home'
        st.rerun()
