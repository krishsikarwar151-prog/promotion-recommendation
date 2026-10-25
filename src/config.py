"""
Central configuration constants for the Employee Promotion Prediction System.
"""
import os

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_FILE = os.path.join(BASE_DIR, "employeePromotion.csv")
MODEL_PATH = os.path.join(BASE_DIR, "models", "model_rf.joblib")
MODEL_LEGACY_PATH = os.path.join(BASE_DIR, "model_rf.joblib")   # backwards compat

# Firebase and Persistence configuration
FIREBASE_KEY_PATH = os.path.join(BASE_DIR, "serviceAccountKey.json")
LOCAL_FIRESTORE_STORE = os.path.join(BASE_DIR, ".firestore_local_store.json")
LEGACY_SQLITE_PATH = os.path.join(BASE_DIR, "hr_reviews.db")  # for migration utility

# Live Firebase Project Credentials
FIREBASE_PROJECT_ID = "promotion-a1dc4"
FIREBASE_WEB_API_KEY = "AIzaSyC7nLuwlY-ECSrJDNo6eg70ahPdI4amThs"
FIREBASE_CONFIG = {
    "apiKey": FIREBASE_WEB_API_KEY,
    "authDomain": "promotion-a1dc4.firebaseapp.com",
    "projectId": FIREBASE_PROJECT_ID,
    "storageBucket": "promotion-a1dc4.firebasestorage.app",
    "messagingSenderId": "377100113275",
    "appId": "1:377100113275:web:08925b6d3a3f659825d9de",
    "measurementId": "G-V4TEJ8G0H7"
}

# Firestore Collections
COL_EMPLOYEES     = "employees"
COL_HR_REVIEWS    = "hr_reviews"
COL_PREDICTIONS   = "prediction_history"
COL_AUDIT_LOGS    = "audit_logs"
COL_USERS         = "users"

# RBAC Roles
ROLE_ADMIN = "Admin"
ROLE_HR    = "HR"
VALID_ROLES = [ROLE_ADMIN, ROLE_HR]

# ── Dataset Categorical Values (derived from actual dataset) ─────────────────
DEPARTMENTS = [
    'Analytics', 'Finance', 'HR', 'Legal', 'Operations',
    'Procurement', 'R&D', 'Sales & Marketing', 'Technology'
]
EDUCATIONS = ["Bachelor's", "Master's & above", "Below Secondary"]
RECRUITMENT_CHANNELS = ['sourcing', 'referred', 'other']
REGIONS = [f"region_{i}" for i in range(1, 35)]
GENDERS = ["m", "f"]
GENDER_LABELS = {"m": "Male", "f": "Female"}

# ── Feature schema used during training ─────────────────────────────────────
NUMERIC_FEATURES = [
    'no_of_trainings', 'age', 'previous_year_rating',
    'length_of_service', 'KPIs_met >80%', 'awards_won?', 'avg_training_score'
]

CAT_FEATURES = ['department', 'region', 'education', 'gender', 'recruitment_channel']

# ── Model defaults ───────────────────────────────────────────────────────────
DECISION_THRESHOLD = 0.50
RANDOM_STATE = 42
TEST_SIZE = 0.20

# ── UI Theme colors ──────────────────────────────────────────────────────────
COLOR_PRIMARY = "#2563EB"
COLOR_SUCCESS = "#16A34A"
COLOR_DANGER  = "#DC2626"
COLOR_WARNING = "#D97706"
COLOR_NEUTRAL = "#64748B"
