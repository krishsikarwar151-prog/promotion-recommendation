"""
Tests for the Employee Promotion Prediction System.
Covers: preprocessing, prediction, batch validation, database, and reports.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pandas as pd
import numpy as np


# ──────────────────────────────────────────────────────────────────────────────
# Preprocessing tests
# ──────────────────────────────────────────────────────────────────────────────

def test_fill_missing_education():
    from src.preprocessing import fill_missing
    df = pd.DataFrame({'education': [None, 'Bachelor\'s'], 'previous_year_rating': [None, 4.0]})
    result = fill_missing(df)
    assert result['education'].isna().sum() == 0
    assert result['previous_year_rating'].isna().sum() == 0
    assert result['education'].iloc[0] == "Bachelor's"
    assert result['previous_year_rating'].iloc[0] == 3.0


def test_encode_categoricals_creates_dummies():
    from src.preprocessing import encode_categoricals
    df = pd.DataFrame({
        'department': ['Technology', 'HR'],
        'gender': ['m', 'f'],
        'region': ['region_1', 'region_2'],
        'education': ["Bachelor's", "Master's & above"],
        'recruitment_channel': ['sourcing', 'other'],
        'age': [30, 28]
    })
    result = encode_categoricals(df)
    assert 'department' not in result.columns
    assert 'gender' not in result.columns
    assert 'age' in result.columns


def test_align_to_schema_fills_missing_columns():
    from src.preprocessing import align_to_schema
    df = pd.DataFrame({'col_a': [1], 'col_b': [2]})
    schema = ['col_a', 'col_b', 'col_c', 'col_d']
    result = align_to_schema(df, schema)
    assert list(result.columns) == schema
    assert result['col_c'].iloc[0] == 0
    assert result['col_d'].iloc[0] == 0


def test_validate_batch_csv_missing_columns():
    from src.preprocessing import validate_batch_csv
    df = pd.DataFrame({'age': [30], 'department': ['HR']})  # missing many required cols
    result = validate_batch_csv(df)
    assert result['valid'] is False
    assert len(result['errors']) > 0


def test_validate_batch_csv_valid():
    from src.preprocessing import validate_batch_csv
    df = pd.DataFrame([{
        'no_of_trainings': 2,
        'age': 30,
        'previous_year_rating': 4.0,
        'length_of_service': 5,
        'KPIs_met >80%': 1,
        'awards_won?': 0,
        'avg_training_score': 75,
        'department': 'Technology',
        'region': 'region_7',
        'education': "Bachelor's",
        'gender': 'm',
        'recruitment_channel': 'sourcing',
    }])
    result = validate_batch_csv(df)
    assert result['valid'] is True


# ──────────────────────────────────────────────────────────────────────────────
# Recommendation tests
# ──────────────────────────────────────────────────────────────────────────────

def test_analyse_skill_gaps_all_gaps():
    from src.recommendations import analyse_skill_gaps
    employee = {
        'avg_training_score': 50,
        'previous_year_rating': 2.0,
        'KPIs_met >80%': 0,
        'awards_won?': 0,
        'length_of_service': 1,
        'no_of_trainings': 1,
    }
    gaps = analyse_skill_gaps(employee)
    assert len(gaps) >= 3
    priorities = [g['priority'] for g in gaps]
    assert 'High' in priorities


def test_analyse_skill_gaps_no_gaps():
    from src.recommendations import analyse_skill_gaps
    employee = {
        'avg_training_score': 90,
        'previous_year_rating': 5.0,
        'KPIs_met >80%': 1,
        'awards_won?': 1,
        'length_of_service': 10,
        'no_of_trainings': 5,
    }
    gaps = analyse_skill_gaps(employee)
    high_gaps = [g for g in gaps if g['priority'] == 'High']
    assert len(high_gaps) == 0


def test_build_development_plan_with_gaps():
    from src.recommendations import analyse_skill_gaps, build_development_plan
    employee = {'avg_training_score': 50, 'previous_year_rating': 2.0,
                'KPIs_met >80%': 0, 'awards_won?': 0,
                'length_of_service': 1, 'no_of_trainings': 1}
    gaps = analyse_skill_gaps(employee)
    plan = build_development_plan(employee, gaps)
    assert 'summary' in plan
    assert 'timeline' in plan
    assert len(plan['timeline']) > 0


# ──────────────────────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
# Firebase & Cloud Firestore Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_firestore_review_save_and_retrieve():
    """Test saving and retrieving HR review records from Cloud Firestore."""
    from src.database import save_review, get_review, get_all_reviews, get_review_stats

    review_id = save_review(
        employee_id='TEST-EMP-999',
        employee_name='Taylor Swift',
        department='Technology',
        prediction=1,
        probability=0.88,
        hr_decision='Approve Promotion',
        decision_reason='Exceptional domain leadership and consistent KPI overachievement',
        development_actions='Executive mentorship track',
        reviewer_name='Chief HR Officer',
        reviewer_email='chro@company.internal',
        reviewer_role='Admin'
    )
    assert review_id == 'TEST-EMP-999'

    review = get_review('TEST-EMP-999')
    assert review is not None
    assert review['employee_name'] == 'Taylor Swift'
    assert abs(review['probability'] - 0.88) < 0.01
    assert review['status'] == 'Reviewed'

    stats = get_review_stats()
    assert stats['total'] >= 1
    assert 'Approve Promotion' in stats['breakdown']


def test_firestore_employee_crud_and_validation():
    """Test Employee CRUD operations, data validation, and RBAC in Cloud Firestore."""
    from src.database import (
        create_employee,
        get_employee,
        update_employee,
        delete_employee,
        validate_employee_data
    )

    admin_user = {"email": "admin@company.com", "role": "Admin"}
    hr_user = {"email": "hr@company.com", "role": "HR"}

    # 1. Validation failure test
    invalid_record = {
        "employee_id": "INVALID-1",
        "department": "NonExistentDept",
        "age": 12, # Under 18
    }
    is_valid, errors = validate_employee_data(invalid_record)
    assert not is_valid
    assert len(errors) >= 2

    # 2. Valid creation test
    valid_record = {
        "employee_id": "EMP-CRUDS-01",
        "name": "Jordan Bell",
        "department": "Analytics",
        "education": "Master's & above",
        "gender": "m",
        "region": "region_2",
        "recruitment_channel": "sourcing",
        "age": 32,
        "length_of_service": 6,
        "no_of_trainings": 2,
        "previous_year_rating": 4.5,
        "avg_training_score": 82.0,
        "KPIs_met >80%": 1,
        "awards_won?": 0
    }
    ok, msg = create_employee(valid_record, user=hr_user)
    assert ok, msg

    # 3. Read test
    fetched = get_employee("EMP-CRUDS-01")
    assert fetched is not None
    assert fetched["name"] == "Jordan Bell"
    assert fetched["department"] == "Analytics"

    # 4. Update test
    ok_up, msg_up = update_employee("EMP-CRUDS-01", {"avg_training_score": 90.0}, user=hr_user)
    assert ok_up, msg_up
    assert get_employee("EMP-CRUDS-01")["avg_training_score"] == 90.0

    # 5. RBAC Delete test: HR user should be forbidden
    ok_del_hr, msg_del_hr = delete_employee("EMP-CRUDS-01", user=hr_user)
    assert not ok_del_hr
    assert "Permission denied" in msg_del_hr

    # 6. Admin Delete test: Admin user succeeds
    ok_del_admin, msg_del_admin = delete_employee("EMP-CRUDS-01", user=admin_user)
    assert ok_del_admin, msg_del_admin
    assert get_employee("EMP-CRUDS-01") is None


def test_firebase_authentication():
    """Test user authentication and registration in Firebase."""
    from src.database import authenticate_user, register_user

    # Default seeded accounts
    ok_admin, user_admin, _ = authenticate_user("admin@promotionai.internal", "Admin@2026!")
    assert ok_admin
    assert user_admin["role"] == "Admin"

    ok_hr, user_hr, _ = authenticate_user("hr@promotionai.internal", "HRManager@2026!")
    assert ok_hr
    assert user_hr["role"] == "HR"

    # Invalid login
    ok_fail, _, err = authenticate_user("admin@promotionai.internal", "WrongPassword!")
    assert not ok_fail

    # User registration (idempotent across repeated test runs)
    import uuid
    test_email = f"recruiter_{uuid.uuid4().hex[:6]}@company.com"
    ok_reg, new_user, _ = register_user(
        email=test_email,
        password="SecurePass2026!",
        role="HR",
        display_name="New Recruiter"
    )
    assert ok_reg
    assert new_user["email"] == test_email


def test_firestore_audit_logging():
    """Test recording and reading immutable audit events."""
    from src.database import log_audit_event, get_audit_logs

    log_audit_event(
        action="TEST_ACTION",
        user_email="auditor@company.com",
        user_role="Admin",
        target_collection="employees",
        target_id="TEST-001",
        details={"note": "Automated security test"}
    )

    logs = get_audit_logs(limit=20)
    assert len(logs) > 0
    actions = [l.get("action") for l in logs]
    assert "TEST_ACTION" in actions


# ──────────────────────────────────────────────────────────────────────────────
# Analytics tests
# ──────────────────────────────────────────────────────────────────────────────

def test_compute_kpis():
    from src.analytics import compute_kpis
    df = pd.DataFrame({
        'is_promoted': [1, 0, 0, 1, 0],
        'avg_training_score': [80, 60, 70, 90, 55],
        'previous_year_rating': [4.0, 3.0, 3.5, 5.0, 2.0],
        'KPIs_met >80%': [1, 0, 1, 1, 0],
        'awards_won?': [0, 0, 1, 1, 0],
    })
    kpis = compute_kpis(df)
    assert kpis['total_employees'] == 5
    assert kpis['promoted'] == 2
    assert abs(kpis['promotion_rate'] - 0.4) < 0.01
    assert kpis['avg_training'] == pytest.approx(71.0, abs=0.1)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
