# 👔 PromotionAI — Employee Promotion Recommendation System

> Enterprise-grade machine learning system for fair, data-driven, and explainable employee promotion decisions, powered by **Firebase Authentication** and **Cloud Firestore**.

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-red)](https://streamlit.io)
[![Firebase](https://img.shields.io/badge/Firebase-Admin%20SDK-orange)](https://firebase.google.com)
[![Firestore](https://img.shields.io/badge/Database-Cloud%20Firestore-yellow)](https://cloud.google.com/firestore)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3%2B-orange)](https://scikit-learn.org)
[![SHAP](https://img.shields.io/badge/SHAP-0.43%2B-purple)](https://shap.readthedocs.io)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 🚀 Quick Start & Run Commands

```bash
# 1. Clone or navigate to the repository
cd "/Users/prathvisikarwar098/Desktop/mini project/Employee-Promotion-Prediction"

# 2. Install all dependencies (including firebase-admin)
python3 -m pip install -r requirements.txt

# 3. (Optional) Run automated test suite
python3 -m pytest tests/test_system.py -v

# 4. Launch the application
python3 -m streamlit run app.py
```

The application will be live at **http://localhost:8501**.

---

## 🔐 Firebase Authentication & Cloud Firestore Architecture

The system has completely replaced SQLite/relational databases with **Firebase Authentication** and **Google Cloud Firestore**.

### Firestore Collections & Data Model

| Collection | Document ID | Purpose | Security & RBAC |
| :--- | :--- | :--- | :--- |
| `employees` | `employee_id` | Master employee records, demographics, performance attributes, tenure | **HR:** Read, Create, Update (validated)<br>**Admin:** Full CRUD (Delete restricted to Admin) |
| `hr_reviews` | `employee_id` | Official HR decisions (`Approve`, `Reject`, `Hold`), reasons, reviewer name & email | **HR & Admin:** Read and Submit<br>**Admin:** Permanent deletion |
| `prediction_history` | Auto UUID | Audit trail of all ML inference calls, feature snapshots, probabilities | **HR & Admin:** Read and Create |
| `audit_logs` | Auto UUID | Immutable append-only log of all database mutations and auth events | **Admin:** Read-only access<br>**System:** Append-only (immutable) |
| `users` | UID / User ID | User identity profiles, email, role assignment (`Admin` or `HR`) | **Admin:** Role management<br>**User:** Read own profile |

---

## 🔑 Role-Based Access Control (RBAC)

PromotionAI enforces strict role separation between **Administrator** and **HR Specialist**:

- **👑 Administrator (`Admin` Role)**:
  - Full access to all ML prediction, SHAP, and analytics dashboards.
  - Full CRUD operations over `employees` in Cloud Firestore (including record deletion).
  - Authority to permanently delete or purge HR review records.
  - Access to immutable Firestore **Audit Trail** and system activity logs.
- **👔 HR Specialist (`HR` Role)**:
  - Access to all prediction pipelines, batch scoring, XAI explanations, and HR dashboards.
  - Permission to create and update employee profiles with data validation.
  - Authority to submit independent HR promotion reviews and development action plans.
  - Cannot delete employee records or purge review histories.

### Demo Accounts (Pre-configured for Instant Evaluation)

When running the application, click **Quick Demo Logins** on the login portal:
1. **👑 Administrator**: `admin@promotionai.internal` / Password: `Admin@2026!`
2. **👔 HR Specialist**: `hr@promotionai.internal` / Password: `HRManager@2026!`

Alternatively, you can register new accounts using the **Create Account** tab.

---

## ⚙️ Firebase Setup & Configuration

PromotionAI supports both **Production Cloud Firestore** and an **Integrated Persistent Emulator**:
- If Firebase credentials are provided, it automatically connects to live Google Cloud Firestore.
- If credentials are not yet supplied, it runs in a thread-safe, persistent local Firestore emulator (`.firestore_local_store.json`), allowing offline evaluation and automated testing without breaking.

### Option 1: Using `serviceAccountKey.json` (Recommended for Local Dev)
1. In your Firebase Console, navigate to **Project Settings** > **Service accounts**.
2. Click **Generate new private key** and download the JSON file.
3. Place the file in the project root as `serviceAccountKey.json` (this file is `.gitignore`d).

### Option 2: Using Streamlit Secrets (`.streamlit/secrets.toml`)
Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`:
```toml
[firebase]
service_account_path = "serviceAccountKey.json"

# OR direct service account keys (recommended for Streamlit Cloud):
# [firebase.service_account]
# project_id = "your-project-id"
# private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
# client_email = "firebase-adminsdk-xxx@your-project-id.iam.gserviceaccount.com"

[firebase.auth]
web_api_key = "AIzaSy..."  # Firebase Web API key from Project Settings > General
```

### Option 3: Environment Variables
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/serviceAccountKey.json"
export FIREBASE_WEB_API_KEY="AIzaSy..."
```

---

## 🛡️ Cloud Firestore Security Rules

Production-grade rules are provided in [`firestore.rules`](file:///Users/prathvisikarwar098/Desktop/mini%20project/Employee-Promotion-Prediction/firestore.rules). Deploy them to Firebase with:

```bash
firebase deploy --only firestore:rules
```

Key security mechanisms enforced:
- Validation that employee age is between 18 and 70.
- Mandatory department validation against allowed organizational units.
- Strict deletion restrictions limiting `employees` and `hr_reviews` deletion to `isAdmin()`.
- Append-only immutability for `audit_logs` (`allow update, delete: if false;`).

---

## 🔄 Migrating Legacy SQLite Data to Firestore

If you have existing reviews in a legacy SQLite database (`hr_reviews.db`), run the included migration script:

```bash
# Preview records to migrate (dry-run):
python3 migrate_sqlite_to_firestore.py --dry-run

# Execute migration to Cloud Firestore:
python3 migrate_sqlite_to_firestore.py --db-path hr_reviews.db
```

The script will:
1. Extract all rows from `hr_reviews` and `review_history`.
2. Map and validate fields to Cloud Firestore schema.
3. Write documents to `hr_reviews` and append migration events to `audit_logs`.

---

## 📁 Project Architecture

```
Employee-Promotion-Prediction/
│
├── app.py                          # Streamlit entrypoint, auth gate, routing & session state
│
├── pages/                          # Application pages
│   ├── home.py                     # Overview dashboard with KPI cards & charts
│   ├── employee_management.py      # Firestore Employee CRUD, validation & audit logs
│   ├── prediction.py               # Individual prediction + SHAP explanation
│   ├── bulk_prediction.py          # Batch CSV upload, schema validation & scoring
│   ├── explainability.py           # Global feature importance + SHAP waterfall explorer
│   ├── skill_gap.py                # Skill gap analysis & 30-60-90 day roadmap
│   ├── hr_analytics.py             # 8 interactive Plotly analytical breakdown charts
│   ├── model_performance.py        # ROC/PR curves, confusion matrices, multi-model benchmark
│   ├── fairness_audit.py           # Disparate impact & Four-Fifths rule bias audit
│   ├── hr_review.py                # HR decision recording (separate from model)
│   └── review_history.py           # Searchable history, CSV export & role-gated deletion
│
├── src/                            # Core Modules
│   ├── config.py                   # Central paths, Firestore collections, RBAC constants
│   ├── firebase_client.py          # Cloud Firestore client, auth & local persistence emulator
│   ├── database.py                 # Abstract database interface routing to Firestore
│   ├── auth_ui.py                  # Firebase login portal, demo credentials & user badge
│   ├── preprocessing.py            # Missing value imputation & 53-feature schema encoder
│   ├── train_model.py              # SMOTE pipeline, Random Forest & multi-model trainer
│   ├── predict.py                  # predict_single & predict_batch wrappers
│   ├── explainability.py           # SHAP TreeExplainer & waterfall charts
│   ├── recommendations.py          # Skill gap analysis & 90-day timeline generator
│   ├── analytics.py                # KPI calculations & fairness metric computations
│   ├── reports.py                  # ReportLab PDF generation & CSV export
│   └── ui_components.py            # Global modern CSS theme, cards, alerts
│
├── firestore.rules                 # Cloud Firestore security & authorization rules
├── migrate_sqlite_to_firestore.py  # SQLite to Cloud Firestore migration utility
├── .gitignore                      # Strictly blocks serviceAccountKey.json, secrets, DBs
├── .env.example                    # Environment variable configuration template
├── .streamlit/
│   ├── config.toml                 # Streamlit UI theme configuration
│   └── secrets.toml.example        # Firebase secrets template
│
├── models/
│   └── model_rf.joblib             # Trained Random Forest model artifact
│
├── tests/
│   └── test_system.py              # Pytest test suite (13 passing tests)
│
├── employeePromotion.csv           # Historical training dataset (54,808 records)
├── requirements.txt                # Updated dependencies (firebase-admin, etc.)
└── README.md
```

---

## 🧪 Automated Testing

Run the full automated test suite covering ML pipelines, SHAP, Cloud Firestore operations, CRUD validation, RBAC, and Authentication:

```bash
python3 -m pytest tests/test_system.py -v
```

All 13 unit and integration tests pass cleanly.

---

## 🔒 Security Best Practices

1. **Zero Secret Leaks**: `serviceAccountKey.json`, `.env`, and `.streamlit/secrets.toml` are excluded in `.gitignore`.
2. **Input Validation**: `validate_employee_data` rejects invalid ages, departments, and out-of-range ratings before any write to Firestore.
3. **Audit Trail**: Every record creation, update, deletion, and login is stamped with the user's email, role, and UTC timestamp in `audit_logs`.
4. **Separation of Concerns**: Model predictions and human HR decisions are stored in distinct attributes to ensure compliance and accountability.
