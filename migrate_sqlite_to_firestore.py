#!/usr/bin/env python3
"""
PromotionAI — SQLite to Cloud Firestore Migration Tool.

Migrates legacy HR review records and review histories from SQLite (hr_reviews.db)
into Cloud Firestore collections ('hr_reviews' and 'audit_logs').

Usage:
    python3 migrate_sqlite_to_firestore.py [--db-path hr_reviews.db] [--dry-run]
"""

import os
import sys
import argparse
import sqlite3
import datetime

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.config import LEGACY_SQLITE_PATH, COL_HR_REVIEWS, COL_AUDIT_LOGS
from src.firebase_client import get_db, get_firebase_status, log_audit_event


def migrate_database(sqlite_path: str, dry_run: bool = False):
    print("=" * 70)
    print("🚀 PromotionAI: SQLite -> Cloud Firestore Migration Utility")
    print("=" * 70)

    if not os.path.exists(sqlite_path):
        print(f"❌ Error: SQLite database not found at '{sqlite_path}'. Nothing to migrate.")
        return False

    status = get_firebase_status()
    print(f"Target Database Mode : {status['mode']}")
    print(f"Project ID           : {status['project_id']}")
    print(f"SQLite Source        : {sqlite_path}")
    print(f"Dry Run Mode         : {dry_run}")
    print("-" * 70)

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Fetch reviews
    try:
        cur.execute("SELECT * FROM hr_reviews")
        review_rows = cur.fetchall()
    except sqlite3.OperationalError as e:
        print(f"⚠️ hr_reviews table missing or unreadable: {e}")
        review_rows = []

    # 2. Fetch history
    try:
        cur.execute("SELECT * FROM review_history")
        history_rows = cur.fetchall()
    except sqlite3.OperationalError:
        history_rows = []

    print(f"Found {len(review_rows)} HR review records in SQLite.")
    print(f"Found {len(history_rows)} audit history records in SQLite.")

    if not review_rows and not history_rows:
        print("ℹ️ No records found to migrate.")
        conn.close()
        return True

    db = get_db()
    reviews_migrated = 0
    history_migrated = 0

    # Migrate HR reviews
    print("\n📦 Migrating HR Reviews to Firestore...")
    for row in review_rows:
        r = dict(row)
        emp_id = str(r.get("employee_id", "")).strip()
        if not emp_id:
            continue

        doc_data = {
            "employee_id":         emp_id,
            "employee_name":       r.get("employee_name", ""),
            "department":          r.get("department", ""),
            "prediction":          int(r.get("prediction", 0)),
            "probability":         float(r.get("probability", 0.0)),
            "hr_decision":         r.get("hr_decision", "Pending"),
            "decision_reason":     r.get("decision_reason", ""),
            "development_actions": r.get("development_actions", ""),
            "reviewer_name":       r.get("reviewer_name", "Legacy Reviewer"),
            "reviewer_email":      "legacy_import@promotionai.internal",
            "reviewer_role":       "HR",
            "review_date":         r.get("review_date") or datetime.datetime.utcnow().isoformat(),
            "status":              r.get("status", "Reviewed"),
            "created_at":          r.get("created_at") or datetime.datetime.utcnow().isoformat(),
            "updated_at":          r.get("updated_at") or datetime.datetime.utcnow().isoformat(),
            "_migrated_from_sqlite": True
        }

        if not dry_run:
            db.collection(COL_HR_REVIEWS).document(emp_id).set(doc_data, merge=True)
        reviews_migrated += 1
        print(f"  ✓ [{reviews_migrated}/{len(review_rows)}] Migrated review for Employee ID: {emp_id}")

    # Migrate Review History -> Audit Logs
    print("\n📜 Migrating Review History to Audit Logs...")
    for h in history_rows:
        h_dict = dict(h)
        audit_entry = {
            "action":            "MIGRATED_SQLITE_AUDIT",
            "user_email":        h_dict.get("changed_by", "system"),
            "user_role":         "System",
            "target_collection": COL_HR_REVIEWS,
            "target_id":         str(h_dict.get("review_id", "")),
            "details": {
                "field_changed": h_dict.get("field_changed"),
                "old_value":     h_dict.get("old_value"),
                "new_value":     h_dict.get("new_value")
            },
            "timestamp": h_dict.get("changed_at") or datetime.datetime.utcnow().isoformat()
        }
        if not dry_run:
            db.collection(COL_AUDIT_LOGS).add(audit_entry)
        history_migrated += 1

    conn.close()

    if not dry_run:
        log_audit_event(
            action="MIGRATE_SQLITE_DATA",
            user_email="migration_script@promotionai.internal",
            user_role="Admin",
            target_collection="system",
            target_id="sqlite_import",
            details={
                "reviews_migrated": reviews_migrated,
                "history_migrated": history_migrated,
                "source_file": sqlite_path
            }
        )

    print("\n" + "=" * 70)
    print(f"✅ Migration Complete!")
    print(f"   • HR Reviews Migrated : {reviews_migrated}")
    print(f"   • Audit Logs Migrated : {history_migrated}")
    print("=" * 70)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate SQLite data to Cloud Firestore.")
    parser.add_argument(
        "--db-path",
        default=LEGACY_SQLITE_PATH,
        help="Path to the legacy SQLite database file (default: hr_reviews.db)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without writing to Firestore."
    )
    args = parser.parse_args()
    migrate_database(args.db_path, args.dry_run)
