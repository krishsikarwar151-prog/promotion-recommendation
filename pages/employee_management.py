"""
PromotionAI — Employee Records & CRUD Management Page.

Provides full Create, Read, Update, and Delete operations on Cloud Firestore:
  - Role-based Access Control (Admin vs HR permissions)
  - Strict input validation before writing to Firestore
  - Immutable audit logging for all changes
  - Pre-population from dataset
"""

import streamlit as st
import pandas as pd
import datetime

from src.ui_components import page_header, alert, kpi_card
from src.config import (
    DEPARTMENTS,
    EDUCATIONS,
    RECRUITMENT_CHANNELS,
    REGIONS,
    GENDERS,
    ROLE_ADMIN,
    ROLE_HR
)
from src.database import (
    list_employees,
    get_employee,
    create_employee,
    update_employee,
    delete_employee,
    seed_employees_from_dataframe,
    get_audit_logs,
    get_firebase_status
)


def render(df_raw: pd.DataFrame, current_user: dict):
    page_header(
        "👥 Cloud Firestore Employee Management",
        "Full CRUD operations, role-based access control, and audit logs stored in Cloud Firestore."
    )

    user_role = current_user.get("role", ROLE_HR)
    user_email = current_user.get("email", "hr@promotionai.internal")
    is_admin = (user_role == ROLE_ADMIN)

    # Status banner
    status = get_firebase_status()
    st.markdown(f"""
    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:0.65rem 1rem; margin-bottom:1.2rem; display:flex; justify-content:space-between; align-items:center;">
        <div>
            <span style="font-weight:700; color:#1E293B; font-size:0.85rem;">Storage Engine:</span>
            <span style="background:{'#DCFCE7' if status['is_live'] else '#EFF6FF'}; color:{'#166534' if status['is_live'] else '#1E40AF'}; padding:2px 8px; border-radius:12px; font-weight:700; font-size:0.75rem; margin-left:6px;">
                {status['mode']}
            </span>
        </div>
        <div style="font-size:0.78rem; color:#64748B;">
            Active User: <strong style="color:#0F172A;">{user_email}</strong> &nbsp;|&nbsp;
            Role: <span style="background:{'#FEE2E2' if is_admin else '#E0E7FF'}; color:{'#991B1B' if is_admin else '#3730A3'}; padding:2px 6px; border-radius:4px; font-weight:700;">{user_role}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs([
        "📋 Employee Directory",
        "➕ Add New Employee",
        "✏️ Edit Employee",
        "🗑️ Delete Employee (Admin)",
        "📜 Firestore Audit Logs"
    ])

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 1: Directory (Read)
    # ──────────────────────────────────────────────────────────────────────────
    with tabs[0]:
        st.subheader("Employee Records in Cloud Firestore")

        c1, c2, c3 = st.columns([2, 2, 2])
        with c1:
            dept_filter = st.selectbox("Filter Department", ["All"] + DEPARTMENTS, key="crud_dept_filter")
        with c2:
            search_query = st.text_input("Search by ID or Name", "", key="crud_search_query")
        with c3:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Refresh Directory", use_container_width=True):
                st.rerun()

        employees = list_employees(department=dept_filter, limit=200)

        if not employees:
            alert("No employee records found in Cloud Firestore. Click below to seed sample records from the dataset.", "info")
            if st.button("🌱 Seed 25 Sample Employees into Firestore", type="primary"):
                with st.spinner("Seeding records into Firestore..."):
                    seeded_count = seed_employees_from_dataframe(df_raw, limit=25, user=current_user)
                    st.success(f"Successfully seeded {seeded_count} employee records into Cloud Firestore!")
                    st.rerun()
        else:
            # Filter by search
            if search_query:
                q = search_query.strip().lower()
                employees = [
                    e for e in employees
                    if q in str(e.get("employee_id", "")).lower() or q in str(e.get("name", "")).lower()
                ]

            st.caption(f"Showing {len(employees)} employee records")
            emp_df = pd.DataFrame(employees)
            display_cols = [c for c in ["employee_id", "name", "department", "education", "age", "length_of_service", "previous_year_rating", "avg_training_score", "KPIs_met >80%"] if c in emp_df.columns]
            st.dataframe(emp_df[display_cols], use_container_width=True)

            # Quick inspect card
            sel_id = st.selectbox("Inspect Employee Details", [e.get("employee_id") for e in employees], key="inspect_emp_sel")
            if sel_id:
                emp_detail = get_employee(sel_id)
                if emp_detail:
                    with st.expander(f"🔍 Profile: Employee #{sel_id} ({emp_detail.get('name', 'N/A')})", expanded=True):
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.write(f"**Department:** {emp_detail.get('department')}")
                            st.write(f"**Education:** {emp_detail.get('education')}")
                            st.write(f"**Gender:** {emp_detail.get('gender')}")
                        with col_b:
                            st.write(f"**Age:** {emp_detail.get('age')}")
                            st.write(f"**Service:** {emp_detail.get('length_of_service')} yrs")
                            st.write(f"**Trainings:** {emp_detail.get('no_of_trainings')}")
                        with col_c:
                            st.write(f"**Rating (Prev Yr):** {emp_detail.get('previous_year_rating')}")
                            st.write(f"**KPIs >80%:** {'Yes' if emp_detail.get('KPIs_met >80%') else 'No'}")
                            st.write(f"**Avg Score:** {emp_detail.get('avg_training_score')}%")

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 2: Create Employee
    # ──────────────────────────────────────────────────────────────────────────
    with tabs[1]:
        st.subheader("Register New Employee in Firestore")
        st.markdown("All entries are validated against Firestore schema constraints before saving.")

        with st.form("create_employee_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                new_id = st.text_input("Employee ID*", placeholder="e.g. 90001")
                new_name = st.text_input("Full Name*", placeholder="e.g. Jane Doe")
                new_dept = st.selectbox("Department*", DEPARTMENTS)
                new_edu = st.selectbox("Education*", EDUCATIONS)
            with c2:
                new_gender = st.selectbox("Gender*", ["m", "f"], format_func=lambda x: "Male" if x == "m" else "Female")
                new_region = st.selectbox("Region*", REGIONS)
                new_channel = st.selectbox("Recruitment Channel*", RECRUITMENT_CHANNELS)
                new_age = st.number_input("Age*", min_value=18, max_value=70, value=30)
            with c3:
                new_service = st.number_input("Length of Service (years)*", min_value=1, max_value=40, value=4)
                new_trainings = st.number_input("Number of Trainings*", min_value=1, max_value=15, value=1)
                new_rating = st.slider("Previous Year Rating*", 1.0, 5.0, 3.0, 0.5)
                new_score = st.slider("Average Training Score*", 0.0, 100.0, 70.0, 1.0)
                new_kpi = st.checkbox("KPIs Met > 80%?", value=False)
                new_award = st.checkbox("Award Won Recently?", value=False)

            submitted = st.form_submit_button("💾 Save Employee to Firestore", type="primary", use_container_width=True)

            if submitted:
                payload = {
                    "employee_id": new_id.strip(),
                    "name": new_name.strip() or f"Employee {new_id}",
                    "department": new_dept,
                    "education": new_edu,
                    "gender": new_gender,
                    "region": new_region,
                    "recruitment_channel": new_channel,
                    "age": int(new_age),
                    "length_of_service": int(new_service),
                    "no_of_trainings": int(new_trainings),
                    "previous_year_rating": float(new_rating),
                    "avg_training_score": float(new_score),
                    "KPIs_met >80%": 1 if new_kpi else 0,
                    "awards_won?": 1 if new_award else 0
                }
                success, msg = create_employee(payload, user=current_user)
                if success:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 3: Edit Employee
    # ──────────────────────────────────────────────────────────────────────────
    with tabs[2]:
        st.subheader("Update Existing Employee Record")
        search_edit_id = st.text_input("Enter Employee ID to Edit", key="edit_search_id")

        if search_edit_id:
            emp = get_employee(search_edit_id)
            if not emp:
                alert(f"Employee with ID '{search_edit_id}' not found in Cloud Firestore.", "warning")
            else:
                st.info(f"Editing profile for: **{emp.get('name', search_edit_id)}**")
                with st.form("edit_emp_form"):
                    c1, c2 = st.columns(2)
                    with c1:
                        ed_name = st.text_input("Full Name", value=emp.get("name", ""))
                        ed_dept = st.selectbox("Department", DEPARTMENTS, index=DEPARTMENTS.index(emp.get("department")) if emp.get("department") in DEPARTMENTS else 0)
                        ed_edu = st.selectbox("Education", EDUCATIONS, index=EDUCATIONS.index(emp.get("education")) if emp.get("education") in EDUCATIONS else 0)
                        ed_trainings = st.number_input("No. of Trainings", min_value=1, max_value=15, value=int(emp.get("no_of_trainings", 1)))
                        ed_rating = st.slider("Previous Year Rating", 1.0, 5.0, float(emp.get("previous_year_rating", 3.0)), 0.5)
                    with c2:
                        ed_age = st.number_input("Age", min_value=18, max_value=70, value=int(emp.get("age", 30)))
                        ed_service = st.number_input("Length of Service", min_value=1, max_value=40, value=int(emp.get("length_of_service", 4)))
                        ed_score = st.slider("Avg Training Score", 0.0, 100.0, float(emp.get("avg_training_score", 60.0)), 1.0)
                        ed_kpi = st.checkbox("KPIs Met > 80%", value=bool(emp.get("KPIs_met >80%", 0)))
                        ed_award = st.checkbox("Award Won?", value=bool(emp.get("awards_won?", 0)))

                    update_btn = st.form_submit_button("🔄 Update Employee in Firestore", type="primary", use_container_width=True)
                    if update_btn:
                        update_payload = {
                            "name": ed_name,
                            "department": ed_dept,
                            "education": ed_edu,
                            "no_of_trainings": int(ed_trainings),
                            "previous_year_rating": float(ed_rating),
                            "age": int(ed_age),
                            "length_of_service": int(ed_service),
                            "avg_training_score": float(ed_score),
                            "KPIs_met >80%": 1 if ed_kpi else 0,
                            "awards_won?": 1 if ed_award else 0
                        }
                        ok, msg = update_employee(search_edit_id, update_payload, user=current_user)
                        if ok:
                            st.success(f"✅ {msg}")
                        else:
                            st.error(f"❌ {msg}")

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 4: Delete Employee (Admin only)
    # ──────────────────────────────────────────────────────────────────────────
    with tabs[3]:
        st.subheader("Delete Employee from Cloud Firestore")
        st.markdown("Permanently remove employee records and trigger Firestore audit logs.")

        if not is_admin:
            alert("🔒 Access Restricted: Deleting employee records requires Administrator privileges. Your current role is HR.", "warning")
        else:
            del_id = st.text_input("Enter Employee ID to Delete", key="delete_emp_id_input")
            if del_id:
                emp_to_del = get_employee(del_id)
                if not emp_to_del:
                    alert(f"Employee ID '{del_id}' does not exist in Firestore.", "info")
                else:
                    st.warning(f"⚠️ Are you sure you want to delete **{emp_to_del.get('name', del_id)}** ({emp_to_del.get('department')})?")
                    confirm_box = st.checkbox("I confirm that I want to permanently delete this employee record.")
                    if st.button("🗑️ Permanently Delete Record", type="primary", disabled=not confirm_box):
                        ok, msg = delete_employee(del_id, user=current_user)
                        if ok:
                            st.success(f"✅ {msg}")
                        else:
                            st.error(f"❌ {msg}")

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 5: Audit Trail
    # ──────────────────────────────────────────────────────────────────────────
    with tabs[4]:
        st.subheader("Firestore Audit Trail & Activity Logs")
        st.markdown("Immutable record of all database operations, administrative actions, and review decisions.")

        logs = get_audit_logs(limit=100)
        if not logs:
            st.info("No audit logs recorded yet.")
        else:
            logs_df = pd.DataFrame(logs)
            display_audit_cols = [c for c in ["timestamp", "action", "user_email", "user_role", "target_collection", "target_id", "details"] if c in logs_df.columns]
            st.dataframe(logs_df[display_audit_cols], use_container_width=True)
