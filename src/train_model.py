"""
Model training, loading, and multi-model comparison for the Promotion Prediction System.
Handles:
  - Loading the existing saved model artifact (fast path)
  - Training a fresh Random Forest with SMOTE if no artifact exists
  - Training and comparing Logistic Regression, Random Forest, GBM, XGBoost
  - Saving / loading model artifacts into models/
"""
import warnings
warnings.filterwarnings("ignore")

import os
import joblib
import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, average_precision_score,
    roc_curve, precision_recall_curve
)
from imblearn.over_sampling import SMOTE

from src.config import (
    CSV_FILE, MODEL_PATH, MODEL_LEGACY_PATH,
    RANDOM_STATE, TEST_SIZE
)
from src.preprocessing import fill_missing, encode_categoricals


# ──────────────────────────────────────────────────────────────────────────────
def _compute_metrics(model, X_test, y_test, feature_columns):
    """Compute a full set of evaluation metrics for a fitted model."""
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    fpr, tpr, _ = roc_curve(y_test, y_prob)
    prec_curve, rec_curve, _ = precision_recall_curve(y_test, y_prob)

    importances = None
    if hasattr(model, 'feature_importances_'):
        importances = pd.Series(model.feature_importances_, index=feature_columns).sort_values(ascending=False)
    elif hasattr(model, 'coef_'):
        importances = pd.Series(np.abs(model.coef_[0]), index=feature_columns).sort_values(ascending=False)

    return {
        'accuracy':         float(accuracy_score(y_test, y_pred)),
        'precision':        float(precision_score(y_test, y_pred, zero_division=0)),
        'recall':           float(recall_score(y_test, y_pred, zero_division=0)),
        'f1':               float(f1_score(y_test, y_pred, zero_division=0)),
        'roc_auc':          float(roc_auc_score(y_test, y_prob)),
        'pr_auc':           float(average_precision_score(y_test, y_prob)),
        'confusion_matrix': confusion_matrix(y_test, y_pred),
        'feature_importances': importances,
        'feature_columns':  feature_columns,
        'fpr': fpr,
        'tpr': tpr,
        'prec_curve': prec_curve,
        'rec_curve':  rec_curve,
    }


# ──────────────────────────────────────────────────────────────────────────────
def load_or_train_model(df: pd.DataFrame):
    """
    Fast path: load saved artifact.
    Fallback: train a new Random Forest with SMOTE.

    Returns (model, metrics, feature_columns, X_test, y_test)
    """
    # Try the new models/ path first, then legacy root path
    for path in [MODEL_PATH, MODEL_LEGACY_PATH]:
        if os.path.exists(path):
            try:
                saved = joblib.load(path)
                model = saved['model']
                metrics = saved['metrics']
                feature_columns = saved['feature_columns']
                # Reconstruct X_test / y_test for SHAP background (small sample)
                X_test, y_test = _build_test_split(df, feature_columns)
                return model, metrics, feature_columns, X_test, y_test
            except Exception:
                pass

    # ── Train fresh model ──────────────────────────────────────────────────
    return _train_rf(df, save=True)


def _build_test_split(df: pd.DataFrame, feature_columns):
    """Recreate the same test split used during training (for SHAP background)."""
    df_enc = fill_missing(df.copy())
    df_enc = encode_categoricals(df_enc)
    drop_cols = [c for c in ['is_promoted', 'employee_id'] if c in df_enc.columns]
    X = df_enc.drop(columns=drop_cols)
    y = df_enc['is_promoted']

    for col in feature_columns:
        if col not in X.columns:
            X[col] = 0
    X = X[feature_columns]

    _, X_test, _, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    return X_test.reset_index(drop=True), y_test.reset_index(drop=True)


def _train_rf(df: pd.DataFrame, save: bool = True):
    """Train a balanced Random Forest using SMOTE."""
    df_enc = fill_missing(df.copy())
    df_enc = encode_categoricals(df_enc)
    drop_cols = [c for c in ['is_promoted', 'employee_id'] if c in df_enc.columns]
    X = df_enc.drop(columns=drop_cols)
    y = df_enc['is_promoted']
    feature_columns = list(X.columns)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    smote = SMOTE(random_state=RANDOM_STATE, sampling_strategy=1.0)
    X_train_res, y_train_res = smote.fit_resample(X_train, y_train)

    model = RandomForestClassifier(
        n_estimators=100, max_depth=10,
        min_samples_leaf=2, random_state=RANDOM_STATE, n_jobs=-1
    )
    model.fit(X_train_res, y_train_res)

    metrics = _compute_metrics(model, X_test, y_test, feature_columns)

    if save:
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump({'model': model, 'metrics': metrics, 'feature_columns': feature_columns}, MODEL_PATH)

    return model, metrics, feature_columns, X_test.reset_index(drop=True), y_test.reset_index(drop=True)


# ──────────────────────────────────────────────────────────────────────────────
def train_all_models(df: pd.DataFrame) -> dict:
    """
    Train and evaluate Logistic Regression, Random Forest, GBM, XGBoost.
    Uses stratified train/test split; SMOTE applied inside training fold only.
    Returns a dict of {model_name: {'model', 'metrics', 'feature_columns'}}.
    """
    try:
        from xgboost import XGBClassifier
        has_xgb = True
    except ImportError:
        has_xgb = False

    df_enc = fill_missing(df.copy())
    df_enc = encode_categoricals(df_enc)
    drop_cols = [c for c in ['is_promoted', 'employee_id'] if c in df_enc.columns]
    X = df_enc.drop(columns=drop_cols)
    y = df_enc['is_promoted']
    feature_columns = list(X.columns)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    smote = SMOTE(random_state=RANDOM_STATE, sampling_strategy=1.0)
    X_tr_res, y_tr_res = smote.fit_resample(X_train, y_train)

    candidates = {
        "Logistic Regression": LogisticRegression(
            max_iter=1000, random_state=RANDOM_STATE, class_weight='balanced'
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=100, max_depth=10, min_samples_leaf=2,
            random_state=RANDOM_STATE, n_jobs=-1
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=100, max_depth=5, random_state=RANDOM_STATE
        ),
    }
    if has_xgb:
        scale_pos = int((y_tr_res == 0).sum() / (y_tr_res == 1).sum())
        candidates["XGBoost"] = XGBClassifier(
            n_estimators=100, max_depth=5,
            scale_pos_weight=scale_pos,
            random_state=RANDOM_STATE, eval_metric='logloss',
            use_label_encoder=False
        )

    results = {}
    for name, clf in candidates.items():
        clf.fit(X_tr_res, y_tr_res)
        m = _compute_metrics(clf, X_test, y_test, feature_columns)
        results[name] = {
            'model': clf,
            'metrics': m,
            'feature_columns': feature_columns
        }

    return results
