"""
Preprocessing pipeline for the Employee Promotion Prediction System.

All transformations here MUST be identical between training and inference.
The pipeline:
  1. Fills missing values (education → "Bachelor's", previous_year_rating → median)
  2. One-hot encodes categoricals with drop_first=True (matching training schema)
  3. Aligns result DataFrame to the saved feature_columns list
"""
import pandas as pd
import numpy as np
from typing import List


def fill_missing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fill known missing columns using the same strategy used during training.

    - education: mode = "Bachelor's"
    - previous_year_rating: median 3.0 (new employees without prior rating)
    """
    df = df.copy()
    if 'education' in df.columns:
        df['education'] = df['education'].fillna("Bachelor's")
    if 'previous_year_rating' in df.columns:
        df['previous_year_rating'] = df['previous_year_rating'].fillna(3.0)
    return df


def encode_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """
    One-hot encode categorical columns with drop_first=True,
    matching the encoding used during model training.
    """
    cat_cols = [c for c in ['department', 'region', 'education', 'gender', 'recruitment_channel']
                if c in df.columns]
    df = pd.get_dummies(df, columns=cat_cols, drop_first=True)
    return df


def align_to_schema(df: pd.DataFrame, feature_columns: List[str]) -> pd.DataFrame:
    """
    Ensure the DataFrame has exactly the columns expected by the model.
    Missing columns are added as 0; extra columns are dropped.
    """
    for col in feature_columns:
        if col not in df.columns:
            df[col] = 0
    return df[feature_columns]


def preprocess_single(input_dict: dict, feature_columns: List[str]) -> pd.DataFrame:
    """
    Full preprocessing for a single employee record provided as a plain dict.
    The dict should use raw column names (e.g. 'department', 'gender').

    Returns a single-row DataFrame aligned to feature_columns.
    """
    df = pd.DataFrame([input_dict])
    df = fill_missing(df)
    df = encode_categoricals(df)
    df = align_to_schema(df, feature_columns)
    return df


def preprocess_batch(df: pd.DataFrame, feature_columns: List[str]) -> pd.DataFrame:
    """
    Full preprocessing for a batch DataFrame.

    Returns the DataFrame aligned to feature_columns (ready for model.predict).
    """
    df = fill_missing(df)
    df = encode_categoricals(df)
    df = align_to_schema(df, feature_columns)
    return df


def validate_batch_csv(df: pd.DataFrame) -> dict:
    """
    Validate an uploaded CSV file for required columns and value ranges.

    Returns a dict:
      {
        'valid': bool,
        'errors': List[str],
        'warnings': List[str],
        'cleaned_df': pd.DataFrame | None
      }
    """
    REQUIRED_COLUMNS = [
        'no_of_trainings', 'age', 'previous_year_rating',
        'length_of_service', 'KPIs_met >80%', 'awards_won?',
        'avg_training_score', 'department', 'region',
        'education', 'gender', 'recruitment_channel'
    ]
    errors = []
    warnings_list = []
    cleaned = df.copy()

    # Check required columns
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {', '.join(missing_cols)}")
        return {'valid': False, 'errors': errors, 'warnings': warnings_list, 'cleaned_df': None}

    # Check numeric ranges
    if 'age' in cleaned.columns:
        bad_age = (cleaned['age'] < 18) | (cleaned['age'] > 70)
        if bad_age.any():
            warnings_list.append(f"{bad_age.sum()} rows have age outside [18, 70] — will be kept as-is.")

    if 'avg_training_score' in cleaned.columns:
        bad_score = (cleaned['avg_training_score'] < 0) | (cleaned['avg_training_score'] > 100)
        if bad_score.any():
            warnings_list.append(f"{bad_score.sum()} rows have avg_training_score outside [0, 100].")

    if 'KPIs_met >80%' in cleaned.columns:
        bad_kpi = ~cleaned['KPIs_met >80%'].isin([0, 1])
        if bad_kpi.any():
            warnings_list.append(f"{bad_kpi.sum()} rows have invalid KPIs_met >80% values — will be coerced.")
            cleaned['KPIs_met >80%'] = pd.to_numeric(cleaned['KPIs_met >80%'], errors='coerce').fillna(0).astype(int)

    if 'awards_won?' in cleaned.columns:
        bad_award = ~cleaned['awards_won?'].isin([0, 1])
        if bad_award.any():
            warnings_list.append(f"{bad_award.sum()} rows have invalid awards_won? values — will be coerced.")
            cleaned['awards_won?'] = pd.to_numeric(cleaned['awards_won?'], errors='coerce').fillna(0).astype(int)

    return {
        'valid': True,
        'errors': errors,
        'warnings': warnings_list,
        'cleaned_df': cleaned
    }
