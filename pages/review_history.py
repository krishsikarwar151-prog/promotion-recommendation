"""
Review History & Reports page.
Shows all saved HR review records, allows search/filter, deletion, and PDF/CSV download.
"""
import streamlit as st
import pandas as pd

from src.ui_components import page_header, alert, section_title, kpi_card
from src.database import get_all_reviews, delete_review, get_review_stats


def render(current_user: dict = None):
    page_header(
        "📄 Review History & Reports",
        "Browse, filter, and export all completed HR review records stored in Cloud Firestore."
    )

    user_role = (current_user or {}).get("role", "HR")
    is_admin = (user_role == "Admin")

    # ── Stats strip ────────────────────────────────────────────────────────────
    stats = get_review_stats()
    total = stats.get('total', 0)
    breakdown = stats.get('breakdown', {})

    if total == 0:
        alert(
            "No HR reviews recorded yet in Cloud Firestore. Use the <strong>HR Review Workflow</strong> page to record decisions.",
            "info"
        )
        return

    approved = breakdown.get('Approve Promotion', breakdown.get('Approve', 0))
    rejected = breakdown.get('Reject Promotion', breakdown.get('Reject', 0))
    on_hold  = breakdown.get('Hold for Further Review', breakdown.get('Hold', 0))

    s1, s2, s3, s4 = st.columns(4)
    with s1: kpi_card("Total Reviews",    str(total),    "All time in Firestore")
    with s2: kpi_card("Approved",         str(approved), "Promotion approved")
    with s3: kpi_card("Rejected",         str(rejected), "No promotion")
    with s4: kpi_card("On Hold",          str(on_hold),  "Pending decision")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Load & display records ─────────────────────────────────────────────────
    reviews = get_all_reviews()
    df = pd.DataFrame(reviews)

    if df.empty:
        alert("No review records found.", "info")
        return

    # Filter controls
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        dept_filter = st.multiselect(
            "Filter by Department",
            options=sorted(df['department'].dropna().unique()),
            default=[]
        )
    with col_f2:
        decision_filter = st.multiselect(
            "Filter by HR Decision",
            options=sorted(df['hr_decision'].dropna().unique()),
            default=[]
        )
    with col_f3:
        search_name = st.text_input("Search by Employee Name", placeholder="Type name...")

    filtered = df.copy()
    if dept_filter:
        filtered = filtered[filtered['department'].isin(dept_filter)]
    if decision_filter:
        filtered = filtered[filtered['hr_decision'].isin(decision_filter)]
    if search_name:
        filtered = filtered[filtered['employee_name'].str.contains(search_name, case=False, na=False)]

    st.markdown(f"**{len(filtered):,}** records shown")

    # Display columns
    display_cols = [
        'id', 'employee_id', 'employee_name', 'department',
        'prediction', 'probability', 'hr_decision',
        'reviewer_name', 'review_date', 'status'
    ]
    display_cols = [c for c in display_cols if c in filtered.columns]

    display_df = filtered[display_cols].copy()
    if 'probability' in display_df.columns:
        display_df['probability'] = display_df['probability'].apply(
            lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A"
        )
    if 'prediction' in display_df.columns:
        display_df['prediction'] = display_df['prediction'].map(
            {1: '✅ Promoted', 0: '❌ Not Promoted'}
        )

    st.dataframe(display_df, hide_index=True, use_container_width=True, height=380)

    # ── Download ───────────────────────────────────────────────────────────────
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            "📥 Download All Reviews from Firestore (CSV)",
            data=filtered.to_csv(index=False).encode('utf-8'),
            file_name="firestore_hr_review_history.csv",
            mime="text/csv"
        )

    # ── Delete a review ────────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("🗑️ Delete a Review Record (Admin Only)", expanded=False):
        if not is_admin:
            alert("🔒 Access Restricted: Deleting reviews requires Administrator privileges. Your active role is HR.", "warning")
        else:
            alert("Deleting a review permanently removes it from Cloud Firestore. Use only for data corrections.", "warning")
            record_options = filtered['id'].tolist() if 'id' in filtered.columns else []
            if record_options:
                del_id = st.selectbox("Select Review / Employee ID to delete:", options=record_options)
                if st.button("Delete Selected Review from Firestore", type="primary"):
                    ok, msg = delete_review(del_id, user=current_user)
                    if ok:
                        st.success(f"Review '{del_id}' deleted from Firestore.")
                        st.rerun()
                    else:
                        st.error(msg)
            else:
                st.info("No records available to delete.")

    # ── Detail view ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔍 View Full Review Details")
    selected_id = st.selectbox(
        "Select a Review ID:",
        options=filtered['id'].tolist() if 'id' in filtered.columns else []
    )

    if selected_id:
        row = filtered[filtered['id'] == selected_id].iloc[0]
        detail_dict = {
            'Employee ID':          row.get('employee_id', 'N/A'),
            'Employee Name':        row.get('employee_name', 'N/A'),
            'Department':           row.get('department', 'N/A'),
            'Model Prediction':     '✅ Promoted' if row.get('prediction') == 1 else '❌ Not Promoted',
            'Model Probability':    f"{row.get('probability',0)*100:.1f}%",
            'HR Decision':          row.get('hr_decision', 'N/A'),
            'Decision Reason':      row.get('decision_reason', 'N/A'),
            'Development Actions':  row.get('development_actions', '—'),
            'Reviewed By':          row.get('reviewer_name', 'N/A'),
            'Review Date':          row.get('review_date', 'N/A'),
            'Status':               row.get('status', 'N/A'),
        }
        detail_df = pd.DataFrame(detail_dict.items(), columns=['Field', 'Value'])
        st.dataframe(detail_df, hide_index=True, use_container_width=True)
