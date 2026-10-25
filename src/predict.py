"""
Prediction logic for the Employee Promotion Prediction System.
Wraps preprocessing + model inference in one clean interface.
"""
import pandas as pd
import numpy as np
from typing import Tuple, List

from src.preprocessing import preprocess_single, preprocess_batch, validate_batch_csv
from src.config import DECISION_THRESHOLD


def predict_single(
    input_dict: dict,
    model,
    feature_columns: List[str],
    threshold: float = DECISION_THRESHOLD
) -> Tuple[int, float]:
    """
    Predict promotion for a single employee.

    Args:
        input_dict: raw employee record using original column names.
        model: fitted sklearn-compatible classifier.
        feature_columns: ordered list of feature names the model expects.
        threshold: decision boundary (default 0.50).

    Returns:
        (prediction: int, probability: float)
        prediction = 1 means "recommended for promotion"
    """
    X = preprocess_single(input_dict, feature_columns)
    prob = float(model.predict_proba(X)[0][1])
    pred = int(prob >= threshold)
    return pred, prob


def predict_batch(
    df: pd.DataFrame,
    model,
    feature_columns: List[str],
    threshold: float = DECISION_THRESHOLD
) -> pd.DataFrame:
    """
    Predict promotions for a DataFrame of employees.

    Returns the input DataFrame with two new columns appended:
      - 'Promotion_Probability'  (float 0–1)
      - 'Promotion_Prediction'   (int 0/1)
      - 'Prediction_Label'       (human-readable string)
      - 'Risk_Tier'              ('High', 'Medium', 'Low' promotion likelihood)
    """
    validation = validate_batch_csv(df)
    if not validation['valid']:
        raise ValueError("Batch CSV validation failed: " + "; ".join(validation['errors']))

    cleaned = validation['cleaned_df']
    X = preprocess_batch(cleaned, feature_columns)
    probs = model.predict_proba(X)[:, 1]
    preds = (probs >= threshold).astype(int)

    result = df.copy()
    result['Promotion_Probability'] = probs
    result['Promotion_Prediction']  = preds
    result['Prediction_Label'] = ['✅ PROMOTED' if p == 1 else '❌ NOT PROMOTED' for p in preds]
    result['Risk_Tier'] = pd.cut(
        probs,
        bins=[0, 0.33, 0.66, 1.0],
        labels=['Low', 'Medium', 'High'],
        include_lowest=True
    )
    return result, validation['warnings']
