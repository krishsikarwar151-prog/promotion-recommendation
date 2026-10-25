"""
Bulk CSV Prediction page.
"""
import io
import streamlit as st
import pandas as pd
from typing import List

from src.ui_components import page_header, alert, section_title
from src.predict import predict_batch
from src.reports import generate_bulk_csv


REQUIRED_COLUMNS = [
    'no_of_trainings', 'age', 'previous_year_rating', 'length_of_service',
    'KPIs_met >80%', 'awards_won?', 'avg_training_score',
    'department', 'region', 'education', 'gender', 'recruitment_channel'
]

SAMPLE_TEMPLATE = pd.DataFrame([{
    'employee_id': 'EMP-001',
    'no_of_trainings': 2,
    'age': 32,
    'previous_year_rating': 4.0,
    'length_of_service': 5,
    'KPIs_met >80%': 1,
    'awards_won?': 0,
    'avg_training_score': 74,
    'department': 'Technology',
    'region': 'region_7',
    'education': "Bachelor's",
    'gender': 'm',
    'recruitment_channel': 'sourcing',
}])


def render(model, feature_columns: List[str]):
    page_header(
        "📁 Bulk CSV Prediction",
        "Upload a workforce CSV to score multiple employees simultaneously."
    )

    col_up, col_dl = st.columns([3, 1], gap="large")

    with col_up:
        uploaded = st.file_uploader(
            "Upload employee records CSV", type=["csv"],
            help="Must contain the required columns listed below."
        )
    with col_dl:
        st.markdown("<br>", unsafe_allow_html=True)
        template_csv = SAMPLE_TEMPLATE.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Template CSV",
            data=template_csv,
            file_name="employee_template.csv",
            mime="text/csv"
        )

    # Required columns info
    with st.expander("📋 Required CSV Columns", expanded=False):
        st.markdown("Your CSV must contain the following columns:")
        st.code(", ".join(REQUIRED_COLUMNS))
        st.markdown("""
        - `KPIs_met >80%` and `awards_won?`: integer 0 or 1
        - `gender`: `m` or `f`
        - `previous_year_rating`: 1.0 – 5.0 (or blank for new employees)
        - `education`: `Bachelor's`, `Master's & above`, or `Below Secondary`
        """)

    batch_df = None

    if uploaded is not None:
        try:
            batch_df = pd.read_csv(uploaded)
            st.success(f"✅ Loaded **{uploaded.name}** — {len(batch_df):,} rows, {len(batch_df.columns)} columns")
        except Exception as e:
            alert(f"Error reading file: {e}", "danger")
            return
    else:
        if st.button("⚡ Use 20 Sample Employees from Dataset"):
            df_raw = st.session_state.get('df_raw')
            if df_raw is not None:
                batch_df = df_raw.sample(20, random_state=99).copy()
                st.session_state['sample_batch_df'] = batch_df

    if 'sample_batch_df' in st.session_state and batch_df is None:
        batch_df = st.session_state['sample_batch_df']

    if batch_df is None:
        alert("Upload a CSV file or click <strong>Use Sample Employees</strong> to get started.", "info")
        return

    # ── Preview ────────────────────────────────────────────────────────────────
    section_title("📋 Uploaded Records Preview")
    st.dataframe(batch_df.head(10), hide_index=True, use_container_width=True)

    if st.button("🚀 Run Batch Prediction", use_container_width=True):
        with st.spinner("Processing records through Random Forest model…"):
            try:
                result_df, warnings_list = predict_batch(batch_df, model, feature_columns)

                for w in warnings_list:
                    alert(w, "warning")

                promoted_n = int((result_df['Promotion_Prediction'] == 1).sum())
                total_n    = len(result_df)

                st.success(f"✅ Batch prediction complete — {total_n:,} employees processed")

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Evaluated", f"{total_n:,}")
                m2.metric("Promoted", f"{promoted_n:,}")
                m3.metric("Not Promoted", f"{total_n - promoted_n:,}")
                m4.metric("Promotion Rate", f"{promoted_n/total_n*100:.1f}%")

                st.markdown("<br>", unsafe_allow_html=True)
                section_title("📊 Batch Results")

                # Colour-code the prediction column
                display_df = result_df.copy()
                display_df['Promotion_Probability'] = display_df['Promotion_Probability'].apply(
                    lambda x: f"{x*100:.1f}%"
                )

                st.dataframe(
                    display_df.sort_values('Promotion_Probability', ascending=False),
                    hide_index=True,
                    use_container_width=True,
                    height=400
                )

                csv_bytes = generate_bulk_csv(result_df)
                st.download_button(
                    label="📥 Download Results CSV",
                    data=csv_bytes,
                    file_name="batch_promotion_predictions.csv",
                    mime="text/csv"
                )

                st.session_state['batch_results'] = result_df

            except ValueError as ve:
                alert(str(ve), "danger")
            except Exception as e:
                alert(f"Unexpected error during batch prediction: {e}", "danger")
