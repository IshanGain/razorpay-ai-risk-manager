<div align="center">

<img src="https://razorpay.com/favicon.ico" width="48" />

# Razorpay AI Risk Manager

**Real-time fraud detection with explainable decisions, cold-start handling, and full Razorpay test-mode integration.**

Track 02 — AI Risk Manager | AI Buildathon 2026

---

![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI_0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit_1.35-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![AUC-ROC](https://img.shields.io/badge/AUC--ROC%3A%200.9187-2B6BE6?style=for-the-badge)
![Tests](https://img.shields.io/badge/51%20Tests%20Passing-22863a?style=for-the-badge&logo=checkmarx&logoColor=white)

</div>

---

## Overview

Razorpay AI Risk Manager is a production-grade fraud detection system that scores transactions in real time, generates explainable decisions with SHAP reason codes, and integrates directly with Razorpay's test-mode API. Every decision is logged to an immutable audit trail and can be exported as a chargeback evidence pack.

The system handles the full fraud detection lifecycle — from transaction ingestion and feature engineering, through ML inference and threshold routing, to merchant webhook delivery and drift monitoring.

---

## Evaluation Metrics

Evaluated on the IEEE-CIS Fraud Detection dataset (118,108 validation transactions)

| Metric | HIGH_PRECISION | BALANCED |
|---|---|---|
| AUC-ROC | 0.9187 | 0.9187 |
| Precision | 0.8854 | 0.7047 |
| Recall | 0.2756 | 0.4011 |
| False Positive Rate | 0.0013 | 0.0060 |
| F1 Score | 0.4198 | 0.5117 |

**Combined fraud coverage:** 66.6% of all fraud addressed (40.1% hard declined + 26.5% routed to 2FA)

**False positives in HIGH_PRECISION mode:** 145 transactions wrongly declined out of 114,044 (0.13%)

**Model:** LightGBM 3129 trees, 451 features, isotonic calibration

**Training data:** 472,432 transactions | **Validation data:** 118,108 transactions

---

## Project Structure

```
razorpay-ai-risk-manager/
├── api/
│   └── main.py                  FastAPI inference server
├── artifacts/
│   ├── lgbm_risk_model.txt      LightGBM model (3129 trees)
│   ├── isotonic_calibrator.pkl  Calibration model
│   └── model_metadata.json      Model metadata and thresholds
├── audit/
│   ├── __init__.py
│   ├── logger.py                Append-only JSONL audit trail
│   ├── evidence.py              Chargeback evidence packs
│   ├── decisions.jsonl          Immutable decision log
│   └── evidence_packs/          Generated evidence packs
├── batch/
│   ├── __init__.py
│   └── scorer.py                Batch CSV scoring with SHAP
├── coldstart/
│   ├── __init__.py
│   └── fallback.py              Rule-based fallback for new entities
├── dashboard/
│   ├── __init__.py
│   └── app.py                   Streamlit ops dashboard
├── docker/
│   ├── Dockerfile               API container
│   ├── Dockerfile.dashboard     Dashboard container
│   └── docker-compose.yml       Multi-container orchestration
├── docs/
│   └── architecture.md          System architecture documentation
├── mlops/
│   ├── __init__.py
│   └── drift.py                 Drift detection (PSI, KL divergence)
├── notebooks/
│   └── ai-risk-manager.ipynb    Model training pipeline
├── outputs/                     Training outputs and visualizations
├── rzp/
│   ├── __init__.py
│   ├── client.py                Razorpay API client
│   └── orders.py                Order management
├── tests/
│   ├── __init__.py
│   ├── test_api.py              26 API endpoint tests
│   ├── test_audit.py            10 audit logger tests
│   └── test_threshold.py        15 threshold logic tests
├── webhooks/
│   ├── __init__.py
│   └── merchant.py              Merchant webhook delivery
├── .env.example                 Environment template
├── requirements.txt             Python dependencies
└── README.md                    This file
```

---

## Quick Start

**Prerequisites:** Python 3.12, pip, Razorpay test account

```bash
# Clone repository
git clone https://github.com/IshanGain/razorpay-ai-risk-manager
cd razorpay-ai-risk-manager

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate         # Windows
# source venv/bin/activate   # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env with rzp_test_* keys from dashboard.razorpay.com/app/keys

# Terminal 1: Run API server
uvicorn api.main:app --reload --port 8000

# Terminal 2: Run dashboard
streamlit run dashboard/app.py

# Terminal 3: Run tests
pytest tests/ -v
```

Access points:
- API documentation: http://localhost:8000/docs
- Dashboard: http://localhost:8501
- API health: http://localhost:8000/health

---

## API Reference

### Score a Transaction

```bash
POST /score
```

Request:
```json
{
  "TransactionAmt": 250.0,
  "card1": 9500,
  "hour_of_day": 14,
  "day_of_week": 2,
  "is_cold_start": 0,
  "card1_vel_3600s": 3.0,
  "card1_vel_21600s": 8.0,
  "card1_vel_86400s": 15.0,
  "merchant_id": "merchant_123",
  "order_id": "order_TTwcmGyJ2hWTFv"
}
```

Response:
```json
{
  "transaction_id": "35535090-344",
  "p_fraud": 0.3443,
  "decision": "STEP_UP_2FA",
  "reasons": ["HIGH_C14", "LOW_CARD1_MEAN_AMT", "HIGH_C13"],
  "path": "ML_MODEL",
  "model_ver": "lgbm-v1.0",
  "latency_ms": 27.51,
  "audit": {
    "order_id": "order_TTwcmGyJ2hWTFv",
    "merchant_id": "merchant_123",
    "amount": 250.0,
    "decision": "STEP_UP_2FA",
    "thresholds": {
      "approve": 0.1,
      "stepup": 0.35,
      "decline": 0.35
    }
  }
}
```

### Create Razorpay Test Order

```bash
POST /razorpay/create-order?amount_inr=250&merchant_id=merchant_123
```

### Batch Score from CSV

```bash
POST /batch
Content-Type: application/json

[
  { "TransactionAmt": 250.0, "card1": 9500 },
  { "TransactionAmt": 1500.0, "card1": 1234 }
]
```

### Audit History

```bash
GET /audit/history?limit=50
GET /audit/stats?hours=24
```

### Health Check

```bash
GET /health
```

Response:
```json
{
  "status": "ok",
  "model_ver": "lgbm-v1.0",
  "razorpay_connected": true,
  "thresholds": { "approve": 0.1, "stepup": 0.35, "decline": 0.35 }
}
```

---

## Dashboard

The Streamlit ops panel provides 6 tabs:

| Tab | Purpose |
|---|---|
| Live Dashboard | Real-time fraud rate, decision breakdown, fraud score gauge, recent decisions |
| Score Transaction | Interactive scoring form with Razorpay order creation and SHAP reasons |
| Audit History | Filterable decision log with CSV download |
| Model Info | Evaluation metrics, threshold configuration, architecture summary |
| Batch Scorer | CSV upload — scored transactions with SHAP reasons and distribution charts |
| Drift Monitor | PSI and KL divergence monitoring with retrain alerts |

---

## Features

### Core Features

- **Real-time inference:** Sub-50ms fraud scoring via LightGBM with isotonic calibration
- **Cold-start handling:** Rule-based fallback for entities with <10 transaction history
- **Explainability:** TreeSHAP reason codes for every decision
- **Razorpay integration:** Direct test-mode order creation and webhook delivery
- **Immutable audit trail:** Append-only JSONL log of all decisions
- **Drift monitoring:** PSI and KL divergence detection between reference and current windows

### Feature Engineering

Engineered features (17 new + 434 raw = 451 total):

- **Velocity:** card1_vel_3600s, card1_vel_21600s, card1_vel_86400s
- **Amount:** log_amount, amount_rounded, amount_gt_500, amount_gt_1000, amt_vs_card_mean
- **Time:** hour_of_day, day_of_week, is_night, is_weekend
- **Entity:** card1_freq, card2_freq, addr1_freq, email_match, addr_mismatch
- **Risk signals:** risky_email_domain, is_cold_start

---

## Test Suite

51 tests, 0 failures

**tests/test_api.py (26 tests)**
- Health endpoint (4): status, model version, thresholds, Razorpay connection
- Scoring (9): schema validation, p_fraud range, latency, error handling
- Cold-start (3): path routing, rule triggering
- Threshold routing (2): decision consistency with fraud probability
- Audit logging (5): stats, history, record creation
- Batch scoring (3): response format, result counts

**tests/test_threshold.py (15 tests)**
- Threshold logic (8): boundary conditions, decision routing
- Cold-start rules (7): risk adjustments, caps, reason codes

**tests/test_audit.py (10 tests)**
- Audit logger (10): append-only writes, filtering, statistics

Run tests:
```bash
pytest tests/ -v
```

---

## Docker Deployment

```bash
# Build and run API container
docker build -t razorpay-risk-api .
docker run -p 8000:8000 --env-file .env razorpay-risk-api

# Run full stack (API + Dashboard)
docker-compose -f docker/docker-compose.yml up
```

Base image: Python 3.11-slim

---

## Cold-Start Handling

New entities with fewer than 10 historical transactions are scored by a conservative rule engine:

| Condition | Risk Adjustment |
|---|---|
| Default prior | P(Fraud) = 0.45 |
| Amount exceeds INR 500 | P(Fraud) = max(current, 0.78) |
| Night-time transaction (22:00-05:00) | P(Fraud) += 0.10; amount limit = INR 350 |
| Risky email domain | P(Fraud) = max(current, 0.85) |
| Ceiling | P(Fraud) capped at 0.95 |

After 10 transactions, the entity graduates to the ML model path.

---

## Drift Detection

The `mlops/drift.py` module computes PSI (Population Stability Index) between a 7-day reference window and a 24-hour recent window.

Thresholds:
- PSI < 0.1: Stable, no action needed
- PSI 0.1-0.2: Monitor, watch closely
- PSI > 0.2: Drift detected, retrain recommended

Formulas:
```
PSI = sum((actual_pct - expected_pct) * ln(actual_pct / expected_pct))
KL_divergence = sum(p * ln(p / q))
```

---

## Model Training

Training pipeline uses the IEEE-CIS Fraud Detection dataset:

| Property | Value |
|---|---|
| Total transactions | 590,540 |
| Fraud rate | 3.50% (20,663 frauds) |
| Features | 434 raw + 17 engineered = 451 total |
| Training set | 472,432 transactions (80%) |
| Validation set | 118,108 transactions (20%) |
| Split method | Time-based (no shuffle) |
| Cold-start transactions | 28,052 (4.8%) |

Training configuration:
- Objective: binary classification
- Learning rate: 0.01
- Num leaves: 31
- Max depth: 6
- Min child samples: 100
- Feature fraction: 0.7
- Bagging fraction: 0.7
- Scale pos weight: 27.5
- Best iteration: 3129 (early stopping)

---

## Tech Stack

| Component | Technology |
|---|---|
| API Server | FastAPI 0.111, Uvicorn, Pydantic 2.7 |
| ML Model | LightGBM 4.3.0 (3129 trees) |
| Explainability | SHAP 0.45 (TreeSHAP) |
| Calibration | Isotonic regression (scikit-learn 1.4) |
| Dashboard | Streamlit 1.35, Plotly 5.22 |
| Payments API | Razorpay Python SDK 1.3 |
| Audit | Append-only JSONL |
| Drift Detection | PSI, KL divergence (NumPy 1.26) |
| Testing | pytest 9.1, pandas 2.1 |
| Containerization | Docker, docker-compose |
| Language | Python 3.12 (development), Python 3.11 (production container) |

---

## Environment Variables

Copy `.env.example` to `.env` and configure credentials:

```bash
cp .env.example .env
```

| Variable | Description | Source |
|---|---|---|
| RAZORPAY_KEY_ID | Test-mode API key ID | dashboard.razorpay.com/app/keys |
| RAZORPAY_KEY_SECRET | Test-mode API key secret | dashboard.razorpay.com/app/keys |

Never commit `.env` to version control. It is listed in `.gitignore`.

---

## Implementation Status

| Component | Status | Notes |
|---|---|---|
| LightGBM training pipeline | Complete | IEEE-CIS, 451 features, isotonic calibration |
| Cold-start rule engine | Complete | Conservative fallback for <10 txn entities |
| Dynamic threshold routing | Complete | APPROVE, STEP_UP_2FA, DECLINE decisions |
| FastAPI inference server | Complete | /score, /batch, /health, /audit endpoints |
| Razorpay test-mode integration | Complete | Real orders via rzp_test_ keys |
| Merchant webhooks | Complete | Fires on STEP_UP and DECLINE |
| Immutable audit logger | Complete | Append-only JSONL |
| Chargeback evidence packs | Complete | Auto-generated text reports |
| Streamlit dashboard | Complete | 6 tabs including drift monitor |
| Batch CSV scorer | Complete | SHAP reasons per row |
| PSI drift detection | Complete | 7-day vs 24-hour comparison |
| Unit tests | Complete | 51 tests, 0 failures |
| Docker containerization | Complete | API + dashboard |
| GraphSAGE graph model | Planned | Syndicate and mule ring detection |
| Redis live feature store | Planned | Real-time velocity computation |
| ClickHouse event log | Planned | Long-term storage for retraining |
| Automated retraining | Planned | Triggered when PSI exceeds 0.2 |

---

## Author

Ishan Gain

AI Buildathon 2026 — Track 02: AI Risk Manager

GitHub: [IshanGain](https://github.com/IshanGain)

---

Built for Razorpay AI Buildathon 2026
