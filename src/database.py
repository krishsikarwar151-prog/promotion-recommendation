"""
PromotionAI — Database Interface Layer.

Migrated from SQLite to Google Cloud Firestore.
No SQL, SQLite, or relational database is used.

All methods are backed by Firebase Cloud Firestore through `src.firebase_client`:
  - Collections: employees, hr_reviews, prediction_history, audit_logs, users
  - Enforces Role-Based Access Control (Admin vs HR)
  - Data validation on all write operations
  - Full audit logging
"""

from src.firebase_client import (
    get_db,
    get_firebase_status,
    save_review,
    get_all_reviews,
    get_review,
    delete_review,
    get_review_stats,
    create_employee,
    get_employee,
    update_employee,
    delete_employee,
    list_employees,
    seed_employees_from_dataframe,
    validate_employee_data,
    log_audit_event,
    get_audit_logs,
    log_prediction_history,
    authenticate_user,
    register_user,
    ROLE_ADMIN,
    ROLE_HR,
    VALID_ROLES,
)


def init_db():
    """
    Initialise the Cloud Firestore connection.
    Called once at application startup.
    Replaces SQLite CREATE TABLE statements.
    """
    db = get_db()
    status = get_firebase_status()
    return status
