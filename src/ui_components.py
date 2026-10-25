"""
Shared Streamlit UI utilities: CSS injection, KPI cards, alert boxes.
"""
import streamlit as st


GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
    background-color: #F1F5F9 !important;
    color: #1E293B !important;
}

/* ── Sidebar ────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #0F172A 0%, #1E3A5F 100%) !important;
    border-right: none !important;
}
[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
[data-testid="stSidebar"] .block-container {
    padding-top: 1.5rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}
[data-testid="stSidebarNav"] { display: none !important; }

/* Nav item styling */
.nav-section {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #64748B !important;
    padding: 1rem 0 0.4rem 0;
}
.nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 9px 14px;
    border-radius: 8px;
    font-size: 0.88rem;
    font-weight: 500;
    cursor: pointer;
    margin-bottom: 2px;
    transition: background 0.15s;
    color: #CBD5E1 !important;
}
.nav-item:hover { background: rgba(255,255,255,0.08); }
.nav-item.active {
    background: rgba(59,130,246,0.25) !important;
    color: #93C5FD !important;
    font-weight: 700;
}

/* ── Main content ───────────────────────────────────────────────────── */
.main .block-container {
    max-width: 1200px;
    padding-top: 1.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}

/* ── Page header ────────────────────────────────────────────────────── */
.page-header {
    margin-bottom: 1.5rem;
}
.page-title {
    font-size: 1.9rem;
    font-weight: 800;
    color: #0F172A;
    letter-spacing: -0.4px;
    margin-bottom: 0.2rem;
}
.page-subtitle {
    font-size: 0.92rem;
    color: #64748B;
}

/* ── KPI Card ───────────────────────────────────────────────────────── */
.kpi-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    transition: box-shadow 0.2s;
}
.kpi-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
.kpi-label {
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #64748B;
    margin-bottom: 0.4rem;
}
.kpi-value {
    font-size: 2rem;
    font-weight: 800;
    color: #0F172A;
    line-height: 1.1;
}
.kpi-sub {
    font-size: 0.8rem;
    color: #94A3B8;
    margin-top: 0.3rem;
}

/* ── Content Card ───────────────────────────────────────────────────── */
.content-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    padding: 1.5rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.content-card-title {
    font-size: 1rem;
    font-weight: 700;
    color: #0F172A;
    margin-bottom: 0.3rem;
}
.content-card-desc {
    font-size: 0.83rem;
    color: #64748B;
    margin-bottom: 1rem;
}

/* ── Section title ──────────────────────────────────────────────────── */
.section-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #0F172A;
    margin-bottom: 0.8rem;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid #E2E8F0;
}

/* ── Result cards ───────────────────────────────────────────────────── */
.result-promoted {
    background: linear-gradient(135deg, #F0FDF4, #DCFCE7);
    border: 1.5px solid #86EFAC;
    border-radius: 14px;
    padding: 1.5rem 1.75rem;
    text-align: center;
}
.result-not-promoted {
    background: linear-gradient(135deg, #FEF2F2, #FEE2E2);
    border: 1.5px solid #FECACA;
    border-radius: 14px;
    padding: 1.5rem 1.75rem;
    text-align: center;
}
.result-label {
    font-size: 1.5rem;
    font-weight: 800;
    margin-bottom: 0.4rem;
}
.result-prob {
    font-size: 1.05rem;
    font-weight: 600;
    background: #FFFFFF;
    display: inline-block;
    padding: 4px 16px;
    border-radius: 999px;
    border: 1px solid #E2E8F0;
    margin-top: 0.5rem;
}

/* ── Alert boxes ────────────────────────────────────────────────────── */
.alert-info {
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    border-left: 4px solid #2563EB;
    border-radius: 8px;
    padding: 0.85rem 1.1rem;
    font-size: 0.88rem;
    color: #1E40AF;
    margin: 0.75rem 0;
}
.alert-warning {
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    border-left: 4px solid #D97706;
    border-radius: 8px;
    padding: 0.85rem 1.1rem;
    font-size: 0.88rem;
    color: #92400E;
    margin: 0.75rem 0;
}
.alert-success {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-left: 4px solid #16A34A;
    border-radius: 8px;
    padding: 0.85rem 1.1rem;
    font-size: 0.88rem;
    color: #166534;
    margin: 0.75rem 0;
}
.alert-danger {
    background: #FEF2F2;
    border: 1px solid #FECACA;
    border-left: 4px solid #DC2626;
    border-radius: 8px;
    padding: 0.85rem 1.1rem;
    font-size: 0.88rem;
    color: #991B1B;
    margin: 0.75rem 0;
}

/* ── Gap / Priority badges ──────────────────────────────────────────── */
.badge-high   { background:#FEE2E2; color:#991B1B; border-radius:999px; padding:2px 12px; font-size:0.78rem; font-weight:700; }
.badge-medium { background:#FEF3C7; color:#92400E; border-radius:999px; padding:2px 12px; font-size:0.78rem; font-weight:700; }
.badge-low    { background:#DCFCE7; color:#166534; border-radius:999px; padding:2px 12px; font-size:0.78rem; font-weight:700; }

/* ── Form styling ───────────────────────────────────────────────────── */
[data-testid="stForm"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 14px !important;
    padding: 1.75rem !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
}

/* ── Buttons ────────────────────────────────────────────────────────── */
.stButton > button, [data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #2563EB, #1D4ED8) !important;
    color: #FFFFFF !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    border-radius: 9px !important;
    padding: 0.65rem 1.5rem !important;
    border: none !important;
    box-shadow: 0 2px 8px rgba(37,99,235,0.25) !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #1D4ED8, #1E40AF) !important;
    box-shadow: 0 4px 12px rgba(37,99,235,0.35) !important;
    transform: translateY(-1px) !important;
}

/* ── Metrics ────────────────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 1rem !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

/* Footer */
.footer {
    text-align: center;
    color: #94A3B8;
    font-size: 0.78rem;
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid #E2E8F0;
}
</style>
"""


def inject_css():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    st.markdown(f"""
    <div class="page-header">
        <div class="page-title">{title}</div>
        {"<div class='page-subtitle'>" + subtitle + "</div>" if subtitle else ""}
    </div>
    """, unsafe_allow_html=True)


def kpi_card(label: str, value: str, sub: str = ""):
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {"<div class='kpi-sub'>" + sub + "</div>" if sub else ""}
    </div>
    """, unsafe_allow_html=True)


def alert(msg: str, kind: str = "info"):
    """kind: 'info' | 'warning' | 'success' | 'danger'"""
    st.markdown(f'<div class="alert-{kind}">{msg}</div>', unsafe_allow_html=True)


def section_title(text: str):
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


def footer():
    st.markdown("""
    <div class="footer">
        PromotionAI &nbsp;•&nbsp; AI-powered HR analytics system &nbsp;•&nbsp;
        Predictions are estimates and do not constitute official promotion decisions.
    </div>
    """, unsafe_allow_html=True)
