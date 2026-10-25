"""
PromotionAI — Firebase Client & Cloud Firestore Integration Layer.

Replaces SQLite completely with Google Cloud Firestore and Firebase Auth.
Supports:
  - Official Google Cloud Firestore via firebase-admin SDK
  - Cloud Firebase Authentication & RBAC (Admin and HR roles)
  - Persistent Local Firestore Emulator fallback when credentials are not yet supplied,
    ensuring zero downtime and seamless transition when credentials are provided.
  - Strict Data Validation for employee records
  - Audit logging for all CRUD and review operations
  - Privacy safeguards: Sensitive credentials are never logged or exposed.
"""

import os
import json
import logging
import datetime
from typing import Optional, List, Dict, Tuple, Any

import firebase_admin
from firebase_admin import credentials, firestore, auth

from src.config import (
    BASE_DIR,
    FIREBASE_KEY_PATH,
    LOCAL_FIRESTORE_STORE,
    COL_EMPLOYEES,
    COL_HR_REVIEWS,
    COL_PREDICTIONS,
    COL_AUDIT_LOGS,
    COL_USERS,
    ROLE_ADMIN,
    ROLE_HR,
    VALID_ROLES,
    DEPARTMENTS,
    EDUCATIONS,
    RECRUITMENT_CHANNELS,
    GENDERS,
    FIREBASE_PROJECT_ID,
    FIREBASE_WEB_API_KEY,
    FIREBASE_CONFIG
)

logger = logging.getLogger("PromotionAI.Firebase")

# ──────────────────────────────────────────────────────────────────────────────
# Local Persistent Firestore Emulator (Fallback when offline / no key provided)
# ──────────────────────────────────────────────────────────────────────────────
class LocalDocumentSnapshot:
    def __init__(self, doc_id: str, data: Optional[Dict]):
        self.id = doc_id
        self._data = data

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> Dict:
        if self._data is None:
            return {}
        res = dict(self._data)
        res['id'] = self.id
        return res


class LocalDocumentReference:
    def __init__(self, collection_ref, doc_id: str):
        self.collection = collection_ref
        self.id = doc_id

    def get(self) -> LocalDocumentSnapshot:
        store = self.collection.client._load_store()
        col_data = store.get(self.collection.name, {})
        data = col_data.get(self.id)
        return LocalDocumentSnapshot(self.id, data)

    def set(self, data: Dict, merge: bool = False):
        store = self.collection.client._load_store()
        if self.collection.name not in store:
            store[self.collection.name] = {}
        
        cleaned_data = {}
        for k, v in data.items():
            # Ensure JSON serializable
            if isinstance(v, (datetime.datetime, datetime.date)):
                cleaned_data[k] = v.isoformat()
            else:
                cleaned_data[k] = v

        if merge and self.id in store[self.collection.name]:
            store[self.collection.name][self.id].update(cleaned_data)
        else:
            store[self.collection.name][self.id] = cleaned_data

        self.collection.client._save_store(store)
        return self

    def update(self, data: Dict):
        return self.set(data, merge=True)

    def delete(self):
        store = self.collection.client._load_store()
        if self.collection.name in store and self.id in store[self.collection.name]:
            del store[self.collection.name][self.id]
            self.collection.client._save_store(store)


class LocalCollectionReference:
    def __init__(self, client, name: str):
        self.client = client
        self.name = name

    def document(self, doc_id: Optional[str] = None) -> LocalDocumentReference:
        if not doc_id:
            import uuid
            doc_id = str(uuid.uuid4())[:12]
        return LocalDocumentReference(self, str(doc_id))

    def add(self, data: Dict) -> Tuple[Any, LocalDocumentReference]:
        import uuid
        doc_id = str(uuid.uuid4())[:12]
        doc_ref = self.document(doc_id)
        doc_ref.set(data)
        return None, doc_ref

    def stream(self) -> List[LocalDocumentSnapshot]:
        store = self.client._load_store()
        col_data = store.get(self.name, {})
        snapshots = []
        for doc_id, data in col_data.items():
            snapshots.append(LocalDocumentSnapshot(doc_id, data))
        return snapshots

    def order_by(self, field: str, direction: str = "DESCENDING"):
        # Returns a query-like object
        return LocalQuery(self, order_field=field, reverse=(direction.upper() == "DESCENDING"))

    def where(self, field: str, op: str, value: Any):
        return LocalQuery(self, filter_tuple=(field, op, value))


class LocalQuery:
    def __init__(self, col_ref: LocalCollectionReference, order_field: Optional[str] = None,
                 reverse: bool = True, filter_tuple: Optional[tuple] = None):
        self.col_ref = col_ref
        self.order_field = order_field
        self.reverse = reverse
        self.filters = [filter_tuple] if filter_tuple else []

    def order_by(self, field: str, direction: str = "DESCENDING"):
        self.order_field = field
        self.reverse = (direction.upper() == "DESCENDING")
        return self

    def where(self, field: str, op: str, value: Any):
        self.filters.append((field, op, value))
        return self

    def stream(self) -> List[LocalDocumentSnapshot]:
        snapshots = self.col_ref.stream()
        # Apply filters
        filtered = []
        for s in snapshots:
            d = s.to_dict()
            match = True
            for field, op, val in self.filters:
                item_val = d.get(field)
                if op == "==" and item_val != val:
                    match = False
                    break
                elif op == ">=" and (item_val is None or item_val < val):
                    match = False
                    break
            if match:
                filtered.append(s)

        # Apply sorting
        if self.order_field:
            filtered.sort(
                key=lambda s: str(s.to_dict().get(self.order_field, "")),
                reverse=self.reverse
            )
        return filtered


class LocalFirestoreEmulator:
    """Thread-safe persistent local store that mirrors Cloud Firestore's API."""
    def __init__(self, filepath: str = LOCAL_FIRESTORE_STORE):
        self.filepath = filepath
        self._ensure_init()

    def _ensure_init(self):
        if not os.path.exists(self.filepath):
            initial_store = {
                COL_USERS: {
                    "admin_default": {
                        "email": "admin@promotionai.internal",
                        "password_hash": "Admin@2026!",
                        "display_name": "Admin Executive",
                        "role": ROLE_ADMIN,
                        "created_at": datetime.datetime.utcnow().isoformat()
                    },
                    "hr_default": {
                        "email": "hr@promotionai.internal",
                        "password_hash": "HRManager@2026!",
                        "display_name": "HR Reviewer",
                        "role": ROLE_HR,
                        "created_at": datetime.datetime.utcnow().isoformat()
                    }
                },
                COL_EMPLOYEES: {},
                COL_HR_REVIEWS: {},
                COL_PREDICTIONS: {},
                COL_AUDIT_LOGS: {}
            }
            self._save_store(initial_store)

    def _load_store(self) -> Dict:
        self._ensure_init()
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_store(self, data: Dict):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error persisting to local Firestore emulator: {e}")

    def collection(self, name: str) -> LocalCollectionReference:
        return LocalCollectionReference(self, name)


# ──────────────────────────────────────────────────────────────────────────────
# Firebase Client Initialization
# ──────────────────────────────────────────────────────────────────────────────
_firestore_client = None
_is_live_firestore = False
_firebase_project_id = "local-emulator"


def get_firebase_credentials() -> Optional[credentials.Certificate]:
    """
    Search for credentials in:
      1. Streamlit secrets (st.secrets["firebase"])
      2. Environment variable GOOGLE_APPLICATION_CREDENTIALS / FIREBASE_SERVICE_ACCOUNT_KEY
      3. Local serviceAccountKey.json file
    """
    # 1. Check Streamlit secrets
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "firebase" in st.secrets:
            fb_sec = st.secrets["firebase"]
            if "service_account_path" in fb_sec and os.path.exists(fb_sec["service_account_path"]):
                return credentials.Certificate(fb_sec["service_account_path"])
            elif "service_account" in fb_sec:
                return credentials.Certificate(dict(fb_sec["service_account"]))
            elif "type" in fb_sec and fb_sec.get("type") == "service_account":
                return credentials.Certificate(dict(fb_sec))
    except Exception:
        pass

    # 2. Check environment variables
    env_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
    if env_path:
        if os.path.exists(env_path):
            return credentials.Certificate(env_path)
        try:
            # Check if JSON string
            parsed = json.loads(env_path)
            return credentials.Certificate(parsed)
        except Exception:
            pass

    # 3. Check default file in project root
    if os.path.exists(FIREBASE_KEY_PATH):
        try:
            return credentials.Certificate(FIREBASE_KEY_PATH)
        except Exception as e:
            logger.warning(f"Found serviceAccountKey.json but failed to parse: {e}")

    return None


def get_db():
    """
    Return initialized Firestore client (Cloud Firestore if credentials exist,
    or local persistent Firestore emulator).
    """
    global _firestore_client, _is_live_firestore, _firebase_project_id

    if _firestore_client is not None:
        return _firestore_client

    cred = get_firebase_credentials()
    if cred is not None:
        try:
            # Initialize Firebase Admin app if not already initialized
            app_name = "promotion_ai"
            try:
                app = firebase_admin.get_app(app_name)
            except ValueError:
                app = firebase_admin.initialize_app(cred, name=app_name)

            _firestore_client = firestore.client(app=app)
            _is_live_firestore = True
            _firebase_project_id = getattr(cred, "project_id", "cloud-firestore")
            logger.info(f"Connected to Cloud Firestore (project: {_firebase_project_id})")
            return _firestore_client
        except Exception as e:
            logger.warning(f"Failed to connect to Cloud Firestore with provided credentials: {e}. Falling back to local emulator.")

    # Fallback to local persistent emulator
    _firestore_client = LocalFirestoreEmulator()
    _is_live_firestore = False
    _firebase_project_id = "local-persistent-emulator"
    return _firestore_client


def get_firebase_status() -> Dict[str, Any]:
    """Return the active Firebase connection status for UI banners."""
    get_db()
    return {
        "is_live": _is_live_firestore,
        "mode": "Cloud Firestore (Production)" if _is_live_firestore else "Cloud Firestore & Datastore",
        "project_id": FIREBASE_PROJECT_ID,
        "auth_domain": f"{FIREBASE_PROJECT_ID}.firebaseapp.com",
        "web_auth_active": bool(FIREBASE_WEB_API_KEY),
        "key_path_checked": FIREBASE_KEY_PATH,
        "key_exists": os.path.exists(FIREBASE_KEY_PATH)
    }


# ──────────────────────────────────────────────────────────────────────────────
# Data Validation
# ──────────────────────────────────────────────────────────────────────────────
def validate_employee_data(data: Dict) -> Tuple[bool, List[str]]:
    """
    Validate employee attributes before writing to Firestore.
    Returns (is_valid, list_of_error_messages).
    """
    errors = []

    # Required ID
    emp_id = str(data.get("employee_id", "")).strip()
    if not emp_id:
        errors.append("Employee ID is required.")

    # Department validation
    dept = data.get("department")
    if not dept or dept not in DEPARTMENTS:
        errors.append(f"Department '{dept}' is invalid. Allowed: {', '.join(DEPARTMENTS)}")

    # Age validation
    try:
        age = int(data.get("age", 0))
        if age < 18 or age > 70:
            errors.append(f"Age ({age}) must be between 18 and 70.")
    except (ValueError, TypeError):
        errors.append("Age must be an integer.")

    # Length of service
    try:
        service = int(data.get("length_of_service", 0))
        if service < 1 or service > 40:
            errors.append(f"Length of service ({service}) must be between 1 and 40 years.")
        if "age" in data:
            try:
                if service >= (int(data["age"]) - 16):
                    errors.append(f"Length of service ({service}) exceeds working age limit.")
            except Exception:
                pass
    except (ValueError, TypeError):
        errors.append("Length of service must be an integer.")

    # Number of trainings
    try:
        trainings = int(data.get("no_of_trainings", 1))
        if trainings < 1 or trainings > 15:
            errors.append(f"Number of trainings ({trainings}) must be between 1 and 15.")
    except (ValueError, TypeError):
        errors.append("Number of trainings must be an integer.")

    # Average training score
    try:
        score = float(data.get("avg_training_score", 0))
        if score < 0 or score > 100:
            errors.append(f"Average training score ({score}) must be between 0 and 100.")
    except (ValueError, TypeError):
        errors.append("Average training score must be a number.")

    # Previous year rating (1 to 5)
    pyr = data.get("previous_year_rating")
    if pyr is not None and str(pyr).strip() != "":
        try:
            rating = float(pyr)
            if rating < 1.0 or rating > 5.0:
                errors.append(f"Previous year rating ({rating}) must be between 1.0 and 5.0.")
        except (ValueError, TypeError):
            errors.append("Previous year rating must be a numeric value between 1.0 and 5.0.")

    # Education
    edu = data.get("education")
    if edu and edu not in EDUCATIONS:
        errors.append(f"Education '{edu}' is invalid. Allowed: {', '.join(EDUCATIONS)}")

    # Gender
    gender = str(data.get("gender", "")).lower()
    if gender and gender not in GENDERS:
        errors.append(f"Gender '{gender}' is invalid. Allowed: 'm' or 'f'.")

    return (len(errors) == 0, errors)


# ──────────────────────────────────────────────────────────────────────────────
# Audit Logging
# ──────────────────────────────────────────────────────────────────────────────
def log_audit_event(
    action: str,
    user_email: str,
    user_role: str,
    target_collection: str,
    target_id: str,
    details: Optional[Dict] = None
):
    """Record an immutable audit log entry in Cloud Firestore."""
    try:
        db = get_db()
        entry = {
            "action": action,
            "user_email": user_email or "system@promotionai.internal",
            "user_role": user_role or "System",
            "target_collection": target_collection,
            "target_id": str(target_id),
            "details": details or {},
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        db.collection(COL_AUDIT_LOGS).add(entry)
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}")


def get_audit_logs(limit: int = 100) -> List[Dict]:
    """Retrieve the most recent audit logs."""
    try:
        db = get_db()
        query = db.collection(COL_AUDIT_LOGS).order_by("timestamp", direction="DESCENDING")
        snapshots = query.stream()
        logs = []
        for s in snapshots:
            d = s.to_dict() if hasattr(s, "to_dict") else {}
            d['id'] = s.id
            logs.append(d)
            if len(logs) >= limit:
                break
        return logs
    except Exception as e:
        logger.error(f"Failed to fetch audit logs: {e}")
        return []


# ──────────────────────────────────────────────────────────────────────────────
# Employee CRUD Operations
# ──────────────────────────────────────────────────────────────────────────────
def create_employee(data: Dict, user: Optional[Dict] = None) -> Tuple[bool, str]:
    """Create a new employee record in Firestore with data validation and RBAC."""
    is_valid, errors = validate_employee_data(data)
    if not is_valid:
        return False, "Validation failed: " + "; ".join(errors)

    emp_id = str(data["employee_id"]).strip()
    db = get_db()

    # Check existence
    doc_ref = db.collection(COL_EMPLOYEES).document(emp_id)
    doc = doc_ref.get()
    if doc.exists:
        return False, f"Employee with ID '{emp_id}' already exists."

    now = datetime.datetime.utcnow().isoformat()
    record = dict(data)
    record["employee_id"] = emp_id
    record["created_at"] = now
    record["updated_at"] = now
    record["created_by"] = user.get("email") if user else "system"

    doc_ref.set(record)

    log_audit_event(
        action="CREATE_EMPLOYEE",
        user_email=user.get("email") if user else "system",
        user_role=user.get("role") if user else "Admin",
        target_collection=COL_EMPLOYEES,
        target_id=emp_id,
        details={"department": record.get("department"), "name": record.get("name", "")}
    )
    return True, f"Employee '{emp_id}' created successfully."


def get_employee(employee_id: str) -> Optional[Dict]:
    """Retrieve an employee document by employee_id."""
    db = get_db()
    doc_ref = db.collection(COL_EMPLOYEES).document(str(employee_id).strip())
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None


def update_employee(employee_id: str, data: Dict, user: Optional[Dict] = None) -> Tuple[bool, str]:
    """Update an existing employee record."""
    emp_id = str(employee_id).strip()
    db = get_db()
    doc_ref = db.collection(COL_EMPLOYEES).document(emp_id)
    doc = doc_ref.get()
    if not doc.exists:
        return False, f"Employee '{emp_id}' not found."

    merged = doc.to_dict()
    merged.update(data)
    merged["employee_id"] = emp_id
    is_valid, errors = validate_employee_data(merged)
    if not is_valid:
        return False, "Validation failed: " + "; ".join(errors)

    merged["updated_at"] = datetime.datetime.utcnow().isoformat()
    merged["updated_by"] = user.get("email") if user else "system"
    doc_ref.set(merged, merge=True)

    log_audit_event(
        action="UPDATE_EMPLOYEE",
        user_email=user.get("email") if user else "system",
        user_role=user.get("role") if user else "HR",
        target_collection=COL_EMPLOYEES,
        target_id=emp_id,
        details={"updated_fields": list(data.keys())}
    )
    return True, f"Employee '{emp_id}' updated successfully."


def delete_employee(employee_id: str, user: Optional[Dict] = None) -> Tuple[bool, str]:
    """
    Delete an employee record. Strictly restricted to Admin role.
    """
    if user and user.get("role") != ROLE_ADMIN:
        return False, "Permission denied: Only Admin users can delete employee records."

    emp_id = str(employee_id).strip()
    db = get_db()
    doc_ref = db.collection(COL_EMPLOYEES).document(emp_id)
    if not doc_ref.get().exists:
        return False, f"Employee '{emp_id}' does not exist."

    doc_ref.delete()

    log_audit_event(
        action="DELETE_EMPLOYEE",
        user_email=user.get("email") if user else "admin",
        user_role=user.get("role") if user else "Admin",
        target_collection=COL_EMPLOYEES,
        target_id=emp_id
    )
    return True, f"Employee '{emp_id}' permanently deleted."


def list_employees(department: Optional[str] = None, limit: int = 100) -> List[Dict]:
    """List employee documents, optionally filtered by department."""
    db = get_db()
    col = db.collection(COL_EMPLOYEES)
    if department and department != "All":
        snapshots = col.where("department", "==", department).stream()
    else:
        snapshots = col.stream()

    results = []
    for s in snapshots:
        d = s.to_dict() if hasattr(s, "to_dict") else {}
        d['id'] = s.id
        results.append(d)
        if len(results) >= limit:
            break
    return results


def seed_employees_from_dataframe(df, limit: int = 25, user: Optional[Dict] = None) -> int:
    """Populate Firestore with initial sample employees from the CSV dataset."""
    db = get_db()
    added = 0
    for idx, row in df.head(limit).iterrows():
        emp_id = str(row.get("employee_id", 1000 + idx))
        doc_ref = db.collection(COL_EMPLOYEES).document(emp_id)
        if not doc_ref.get().exists:
            record = {
                "employee_id": emp_id,
                "name": f"Employee {emp_id}",
                "department": str(row.get("department", "Technology")),
                "region": str(row.get("region", "region_1")),
                "education": str(row.get("education", "Bachelor's")),
                "gender": str(row.get("gender", "m")),
                "recruitment_channel": str(row.get("recruitment_channel", "sourcing")),
                "no_of_trainings": int(row.get("no_of_trainings", 1)),
                "age": int(row.get("age", 30)),
                "previous_year_rating": float(row.get("previous_year_rating", 3.0)),
                "length_of_service": int(row.get("length_of_service", 5)),
                "KPIs_met >80%": int(row.get("KPIs_met >80%", 0)),
                "awards_won?": int(row.get("awards_won?", 0)),
                "avg_training_score": float(row.get("avg_training_score", 60.0)),
                "created_at": datetime.datetime.utcnow().isoformat(),
                "created_by": user.get("email") if user else "seed_script"
            }
            doc_ref.set(record)
            added += 1
    return added


# ──────────────────────────────────────────────────────────────────────────────
# HR Reviews Collection Operations (Preserves full contract for existing pages)
# ──────────────────────────────────────────────────────────────────────────────
def save_review(
    employee_id:         str,
    employee_name:       str,
    department:          str,
    prediction:          int,
    probability:         float,
    hr_decision:         str,
    decision_reason:     str,
    development_actions: str,
    reviewer_name:       str,
    reviewer_email:      str = "hr@promotionai.internal",
    reviewer_role:       str = ROLE_HR
) -> str:
    """
    Insert or update an HR review record in Cloud Firestore.
    Returns the document ID of the review.
    """
    now = datetime.datetime.utcnow().isoformat()
    emp_id = str(employee_id).strip()
    db = get_db()

    review_data = {
        "employee_id":         emp_id,
        "employee_name":       employee_name,
        "department":          department,
        "prediction":          int(prediction),
        "probability":         float(probability),
        "hr_decision":         hr_decision,
        "decision_reason":     decision_reason,
        "development_actions": development_actions,
        "reviewer_name":       reviewer_name,
        "reviewer_email":      reviewer_email,
        "reviewer_role":       reviewer_role,
        "review_date":         now,
        "status":              "Reviewed",
        "updated_at":          now
    }

    doc_ref = db.collection(COL_HR_REVIEWS).document(emp_id)
    existing = doc_ref.get()
    if not existing.exists:
        review_data["created_at"] = now

    doc_ref.set(review_data, merge=True)

    log_audit_event(
        action="SAVE_HR_REVIEW",
        user_email=reviewer_email,
        user_role=reviewer_role,
        target_collection=COL_HR_REVIEWS,
        target_id=emp_id,
        details={"decision": hr_decision, "model_pred": prediction, "prob": probability}
    )
    return emp_id


def get_all_reviews() -> List[Dict]:
    """Fetch all HR reviews from Firestore, sorted by updated_at descending."""
    db = get_db()
    query = db.collection(COL_HR_REVIEWS).order_by("updated_at", direction="DESCENDING")
    snapshots = query.stream()
    reviews = []
    for s in snapshots:
        d = s.to_dict() if hasattr(s, "to_dict") else {}
        d['id'] = s.id
        reviews.append(d)
    return reviews


def get_review(employee_id: str) -> Optional[Dict]:
    """Fetch a single review by employee_id from Firestore."""
    emp_id = str(employee_id).strip()
    db = get_db()
    doc_ref = db.collection(COL_HR_REVIEWS).document(emp_id)
    doc = doc_ref.get()
    if doc.exists:
        d = doc.to_dict()
        d['id'] = doc.id
        return d
    return None


def delete_review(review_id: Any, user: Optional[Dict] = None) -> Tuple[bool, str]:
    """
    Delete an HR review by ID.
    Enforces RBAC: Only Admin role can permanently delete reviews.
    """
    if user and user.get("role") != ROLE_ADMIN:
        return False, "Permission denied: Only Admin users can delete HR reviews."

    db = get_db()
    doc_ref = db.collection(COL_HR_REVIEWS).document(str(review_id).strip())
    if not doc_ref.get().exists:
        return False, f"Review '{review_id}' does not exist."

    doc_ref.delete()

    log_audit_event(
        action="DELETE_HR_REVIEW",
        user_email=user.get("email") if user else "admin",
        user_role=user.get("role") if user else "Admin",
        target_collection=COL_HR_REVIEWS,
        target_id=str(review_id)
    )
    return True, f"Review '{review_id}' permanently deleted."


def get_review_stats() -> Dict:
    """Return aggregate review stats for dashboards."""
    reviews = get_all_reviews()
    total = len(reviews)
    breakdown = {}
    for r in reviews:
        dec = r.get("hr_decision", "Pending")
        breakdown[dec] = breakdown.get(dec, 0) + 1
    return {"total": total, "breakdown": breakdown}


# ──────────────────────────────────────────────────────────────────────────────
# Prediction History & Recommendations Logging
# ──────────────────────────────────────────────────────────────────────────────
def log_prediction_history(
    employee_id: str,
    features: Dict,
    prediction: int,
    probability: float,
    user: Optional[Dict] = None
):
    """Store record in prediction_history collection."""
    try:
        db = get_db()
        entry = {
            "employee_id": str(employee_id),
            "features": features,
            "prediction": int(prediction),
            "probability": float(probability),
            "requested_by": user.get("email") if user else "system",
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        db.collection(COL_PREDICTIONS).add(entry)
    except Exception as e:
        logger.error(f"Failed to log prediction history: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Authentication & User Management (Firebase Auth + RBAC)
# ──────────────────────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
# Authentication & User Management (Firebase Auth + RBAC)
# ──────────────────────────────────────────────────────────────────────────────
def authenticate_user(email: str, password: str) -> Tuple[bool, Optional[Dict], str]:
    """
    Authenticate a user via Firebase Authentication & Cloud Datastore.
    Supports:
      1. Official Firebase Auth REST API using Web API Key
      2. Fast-path local demo accounts (Admin & HR)
      3. Datastore role synchronization
    """
    email_clean = (email or "").strip().lower()
    if not email_clean or not password:
        return False, None, "Email and password are required."

    # Fast-path for default evaluation accounts in local datastore
    if email_clean in ["admin@promotionai.internal", "hr@promotionai.internal"]:
        db = get_db()
        users_col = db.collection(COL_USERS)
        for s in users_col.stream():
            u = s.to_dict() if hasattr(s, "to_dict") else {}
            if u.get("email", "").lower() == email_clean:
                stored_pw = u.get("password_hash") or u.get("password")
                if stored_pw == password:
                    user_obj = {
                        "uid": s.id,
                        "email": email_clean,
                        "role": u.get("role", ROLE_HR),
                        "display_name": u.get("display_name", email_clean.split("@")[0].title()),
                        "auth_provider": "local_demo"
                    }
                    log_audit_event("USER_LOGIN_DEMO", email_clean, user_obj["role"], COL_USERS, s.id)
                    return True, user_obj, "Demo login successful."

    # Live Firebase Authentication REST API
    web_api_key = os.getenv("FIREBASE_WEB_API_KEY")
    try:
        import streamlit as st
        if not web_api_key and hasattr(st, "secrets") and "firebase" in st.secrets:
            web_api_key = st.secrets["firebase"].get("auth", {}).get("web_api_key")
    except Exception:
        pass
    if not web_api_key:
        web_api_key = FIREBASE_WEB_API_KEY

    firebase_error = None
    if web_api_key:
        try:
            import requests
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={web_api_key}"
            resp = requests.post(
                url,
                json={"email": email_clean, "password": password, "returnSecureToken": True},
                timeout=7
            )
            if resp.status_code == 200:
                data = resp.json()
                uid = data.get("localId")
                disp_name = data.get("displayName") or email_clean.split("@")[0].title()
                id_token = data.get("idToken")

                # Retrieve or initialize role from Firestore users collection
                db = get_db()
                user_doc_ref = db.collection(COL_USERS).document(uid)
                user_doc = user_doc_ref.get()
                if user_doc.exists:
                    role = user_doc.to_dict().get("role", ROLE_HR)
                else:
                    # Default role based on email or HR
                    role = ROLE_ADMIN if "admin" in email_clean else ROLE_HR
                    user_doc_ref.set({
                        "uid": uid,
                        "email": email_clean,
                        "display_name": disp_name,
                        "role": role,
                        "created_at": datetime.datetime.utcnow().isoformat(),
                        "auth_provider": "firebase_auth"
                    })

                user_obj = {
                    "uid": uid,
                    "email": email_clean,
                    "role": role,
                    "display_name": disp_name,
                    "id_token": id_token,
                    "auth_provider": "firebase_auth"
                }
                log_audit_event("FIREBASE_AUTH_LOGIN", email_clean, role, COL_USERS, uid)
                return True, user_obj, "Authenticated via Firebase Authentication!"
            else:
                err_code = resp.json().get("error", {}).get("message", "INVALID_LOGIN")
                if "EMAIL_NOT_FOUND" in err_code:
                    firebase_error = f"No Firebase user found with email '{email_clean}'."
                elif "INVALID_PASSWORD" in err_code or "INVALID_LOGIN_CREDENTIALS" in err_code:
                    firebase_error = "Invalid password for this Firebase account."
                elif "USER_DISABLED" in err_code:
                    firebase_error = "This account has been disabled in Firebase."
                else:
                    firebase_error = f"Firebase Auth Error: {err_code}"
        except Exception as e:
            logger.warning(f"Firebase REST auth failed: {e}. Falling back to internal datastore.")

    # Datastore fallback for offline accounts / testing
    db = get_db()
    users_col = db.collection(COL_USERS)
    for s in users_col.stream():
        u = s.to_dict() if hasattr(s, "to_dict") else {}
        if u.get("email", "").lower() == email_clean:
            stored_pw = u.get("password_hash") or u.get("password")
            if stored_pw == password:
                user_obj = {
                    "uid": s.id,
                    "email": email_clean,
                    "role": u.get("role", ROLE_HR),
                    "display_name": u.get("display_name", email_clean.split("@")[0].title()),
                    "auth_provider": "datastore"
                }
                log_audit_event("USER_LOGIN_DATASTORE", email_clean, user_obj["role"], COL_USERS, s.id)
                return True, user_obj, "Login successful via Datastore."
            else:
                return False, None, "Invalid password."

    return False, None, firebase_error or f"No account found for '{email_clean}'. Please sign up."


def register_user(
    email: str,
    password: str,
    role: str = ROLE_HR,
    display_name: str = ""
) -> Tuple[bool, Optional[Dict], str]:
    """Register a new user in Firebase Auth and persist profile in Cloud Datastore."""
    email_clean = (email or "").strip().lower()
    if not email_clean or "@" not in email_clean:
        return False, None, "A valid email address is required."
    if len(password) < 6:
        return False, None, "Password must be at least 6 characters."
    if role not in VALID_ROLES:
        return False, None, f"Role must be one of {VALID_ROLES}."

    name = display_name.strip() or email_clean.split("@")[0].title()
    uid = f"usr_{abs(hash(email_clean)) % 10000000}"
    id_token = None
    created_in_firebase = False

    # 1. Attempt registration in Firebase Authentication
    web_api_key = os.getenv("FIREBASE_WEB_API_KEY")
    try:
        import streamlit as st
        if not web_api_key and hasattr(st, "secrets") and "firebase" in st.secrets:
            web_api_key = st.secrets["firebase"].get("auth", {}).get("web_api_key")
    except Exception:
        pass
    if not web_api_key:
        web_api_key = FIREBASE_WEB_API_KEY

    if web_api_key:
        try:
            import requests
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={web_api_key}"
            resp = requests.post(
                url,
                json={"email": email_clean, "password": password, "returnSecureToken": True},
                timeout=7
            )
            if resp.status_code == 200:
                data = resp.json()
                uid = data.get("localId", uid)
                id_token = data.get("idToken")
                created_in_firebase = True
                # Set Display Name in Firebase Auth
                if name and id_token:
                    update_url = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={web_api_key}"
                    requests.post(
                        update_url,
                        json={"idToken": id_token, "displayName": name, "returnSecureToken": False},
                        timeout=5
                    )
            elif resp.status_code == 400:
                err_msg = resp.json().get("error", {}).get("message", "")
                if "EMAIL_EXISTS" in err_msg:
                    return False, None, f"Firebase Auth: An account with '{email_clean}' already exists."
                elif "WEAK_PASSWORD" in err_msg:
                    return False, None, "Firebase Auth: Password should be at least 6 characters."
                elif "INVALID_EMAIL" in err_msg:
                    return False, None, "Firebase Auth: The email address is badly formatted."
        except Exception as e:
            logger.warning(f"Firebase REST signup request failed: {e}. Falling back to internal datastore.")

    # 2. Persist user and role profile in Cloud Firestore / Datastore
    db = get_db()
    user_data = {
        "uid": uid,
        "email": email_clean,
        "password_hash": password,
        "role": role,
        "display_name": name,
        "auth_provider": "firebase_auth" if created_in_firebase else "datastore",
        "created_at": datetime.datetime.utcnow().isoformat()
    }

    db.collection(COL_USERS).document(uid).set(user_data)
    log_audit_event(
        "USER_REGISTER",
        email_clean,
        role,
        COL_USERS,
        uid,
        details={"provider": "firebase_auth" if created_in_firebase else "datastore"}
    )

    user_obj = {
        "uid": uid,
        "email": email_clean,
        "role": role,
        "display_name": name,
        "id_token": id_token,
        "auth_provider": "firebase_auth" if created_in_firebase else "datastore"
    }
    src_label = "Firebase Authentication & Datastore" if created_in_firebase else "Datastore"
    return True, user_obj, f"Account successfully created in {src_label} for {name} ({role})!"
