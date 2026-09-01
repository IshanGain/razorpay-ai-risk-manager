"""
Razorpay AI Risk Manager - Ops Dashboard
Real-time fraud monitoring and transaction scoring
"""
import sys
import os

# Add the project root to the Python path so it can find the 'batch' module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from batch.scorer import score_batch_csv, validate_csv, generate_sample_csv
from mlops.drift import get_drift_summary, check_score_drift

import streamlit as st
import requests
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import time

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Razorpay AI Risk Manager",
    page_icon="https://razorpay.com/favicon.ico",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Razorpay brand colors: Deep midnight backgrounds, vibrant blue accents */
    [data-testid="stAppViewContainer"] {
        background-color: #0b1121; 
    }
    [data-testid="stSidebar"] {
        background-color: #121a2f; 
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #338cf0 !important; /* Razorpay primary blue */
        color: #ffffff !important;
        border: none;
        border-radius: 4px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #1d72d6 !important;
        box-shadow: 0 4px 12px rgba(51, 140, 240, 0.3);
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #ffffff;
        font-weight: 700;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
    }
    .stTabs [aria-selected="true"]::after {
        background-color: #338cf0 !important;
    }
    
    /* Download Buttons */
    .stDownloadButton > button {
        background-color: transparent !important;
        border: 1px solid #338cf0 !important;
        color: #338cf0 !important;
    }
    .stDownloadButton > button:hover {
        background-color: rgba(51, 140, 240, 0.1) !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Helper functions ──────────────────────────────────────────────────────────
def get_health():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=3)
        return r.json()
    except:
        return None

def get_audit_stats(hours=24):
    try:
        r = requests.get(f"{API_BASE}/audit/stats?hours={hours}", timeout=3)
        data = r.json()
        if isinstance(data, dict):
            return data
        return {}
    except:
        return {}

def get_audit_history(limit=20):
    try:
        r = requests.get(f"{API_BASE}/audit/history?limit={limit}", timeout=3)
        data = r.json()
        if isinstance(data, list):
            return data
        return []
    except:
        return []

def score_transaction(payload: dict):
    try:
        r = requests.post(f"{API_BASE}/score", json=payload, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def create_order(amount_inr: float, merchant_id: str):
    try:
        r = requests.post(
            f"{API_BASE}/razorpay/create-order",
            params={"amount_inr": amount_inr, "merchant_id": merchant_id},
            timeout=10
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://razorpay.com/favicon.ico", width=32)
    st.title("Risk Manager")
    st.caption("Track 02 — AI Buildathon 2026")
    st.divider()

    # API health
    health = get_health()
    if health:
        st.success("API Online")
        rzp_status = "Connected" if health.get("razorpay_connected") else "Disconnected"
        st.caption(f"Razorpay: {rzp_status}")
        st.caption(f"Model: {health.get('model_ver', 'unknown')}")
    else:
        st.error("API Offline — start uvicorn")

    st.divider()

    # Auto-refresh
    auto_refresh = st.toggle("Auto Refresh", value=False)
    refresh_interval = st.slider("Refresh interval (sec)", 5, 60, 10)

    st.divider()
    st.caption("Thresholds")
    if health:
        t = health.get("thresholds", {})
        st.caption(f"APPROVE  < {t.get('approve', 'N/A')}")
        st.caption(f"STEP_UP  < {t.get('stepup', 'N/A')}")
        st.caption(f"DECLINE >= {t.get('decline', 'N/A')}")

# ── Main header ───────────────────────────────────────────────────────────────
st.title("Razorpay AI Risk Manager")
st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')} | "
           f"Track 02 — AI Buildathon 2026")
st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Live Dashboard",
    "Score Transaction",
    "Audit History",
    "Model Info",
    "Batch Scorer",
    "Drift Monitor"
])

# ════════════════════════════════════════════════════════════
# TAB 1 — LIVE DASHBOARD
# ════════════════════════════════════════════════════════════
with tab1:

    stats = get_audit_stats(hours=24)

    # ── Row 1: Key metrics ──────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)

    total     = stats.get("total_decisions", 0)
    approve   = stats.get("approve", 0)
    step_up   = stats.get("step_up", 0)
    decline   = stats.get("decline", 0)
    avg_score = stats.get("avg_fraud_score", 0)

    with col1:
        st.metric("Total Decisions", f"{total:,}", help="Last 24 hours")
    with col2:
        st.metric("Approved", f"{approve:,}",
                  delta=f"{approve/max(total,1):.1%}",
                  delta_color="normal")
    with col3:
        st.metric("Step-Up 2FA", f"{step_up:,}",
                  delta=f"{step_up/max(total,1):.1%}",
                  delta_color="off")
    with col4:
        st.metric("Declined", f"{decline:,}",
                  delta=f"{decline/max(total,1):.1%}",
                  delta_color="inverse")
    with col5:
        st.metric("Avg P(Fraud)", f"{avg_score:.4f}",
                  help="Average fraud probability")

    st.divider()

    # ── Row 2: Charts ───────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Decision Breakdown")
        if total > 0:
            fig = go.Figure(data=[go.Pie(
                labels=["Approve", "Step-Up 2FA", "Decline"],
                values=[approve, step_up, decline],
                hole=0.5,
                marker_colors=["#10b981", "#f59e0b", "#ef4444"],
            )])
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                showlegend=True,
                margin=dict(t=20, b=20, l=20, r=20),
                height=280,
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No decisions yet — score some transactions first")

    with col_right:
        st.subheader("Fraud Score Gauge")
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=avg_score,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Avg P(Fraud)", "font": {"color": "white"}},
            gauge={
                "axis": {"range": [0, 1], "tickcolor": "white"},
                "bar": {"color": "#ffffff", "thickness": 0.2},
                "steps": [
                    {"range": [0, 0.10], "color": "#10b981"},
                    {"range": [0.10, 0.35], "color": "#f59e0b"},
                    {"range": [0.35, 1.0], "color": "#ef4444"},
                ],
                "threshold": {
                    "line": {"color": "white", "width": 2},
                    "thickness": 0.75,
                    "value": avg_score,
                },
            },
            number={"font": {"color": "white"}},
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            height=320,
            margin=dict(t=60, b=20, l=40, r=40),
        )
        st.plotly_chart(fig, width="stretch")

    # ── Row 3: Recent decisions ─────────────────────────────
    st.subheader("Recent Decisions")
    history = get_audit_history(limit=10)

    if history:
        rows = []
        for r in history:
            decision = r.get("decision", "")
            rows.append({
                "Time": r.get("timestamp", "")[:19].replace("T", " "),
                "Decision": decision,
                "P(Fraud)": f"{r.get('p_fraud', 0):.4f}",
                "Amount": f"₹{r.get('amount', 0):,.0f}",
                "Reasons": ", ".join(r.get("reasons", [])[:2]),
                "Path": r.get("path", ""),
                "Latency": f"{r.get('latency_ms', 0):.1f}ms",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("No decisions logged yet")

    # Auto-refresh
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

# ════════════════════════════════════════════════════════════
# TAB 2 — SCORE TRANSACTION
# ════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Score a Transaction")

    col_form, col_result = st.columns([1, 1])

    with col_form:
        st.caption("Transaction Details")

        amount = st.number_input("Amount (INR)", min_value=1.0,
                                  max_value=100000.0, value=250.0)
        merchant_id = st.text_input("Merchant ID", value="merchant_123")
        card1 = st.number_input("Card ID (card1)", value=9500)
        hour = st.slider("Hour of Day", 0, 23, 14)
        day = st.selectbox("Day of Week",
                           ["Monday","Tuesday","Wednesday",
                            "Thursday","Friday","Saturday","Sunday"],
                           index=1)
        day_num = ["Monday","Tuesday","Wednesday",
                   "Thursday","Friday","Saturday","Sunday"].index(day)

        is_night   = 1 if hour >= 22 or hour <= 5 else 0
        is_weekend = 1 if day_num >= 5 else 0

        vel_1h  = st.number_input("Card velocity (1h)", value=3.0, step=1.0)
        vel_6h  = st.number_input("Card velocity (6h)", value=8.0, step=1.0)
        vel_24h = st.number_input("Card velocity (24h)", value=15.0, step=1.0)

        col_a, col_b = st.columns(2)
        with col_a:
            is_cold  = st.checkbox("Cold Start")
            risky_email = st.checkbox("Risky Email")
        with col_b:
            addr_mismatch = st.checkbox("Address Mismatch")

        create_rzp = st.checkbox("Create Razorpay order first", value=True)

        score_btn = st.button("Score Transaction", use_container_width=True)

    with col_result:
        st.caption("Result")

        if score_btn:
            order_id = None

            # Create Razorpay order
            if create_rzp:
                with st.spinner("Creating Razorpay order..."):
                    order = create_order(amount, merchant_id)
                    if "error" not in order:
                        order_id = order.get("order_id")
                        st.success(f"Order created: `{order_id}`")
                    else:
                        st.warning(f"Order creation failed: {order['error']}")

            # Score the transaction
            payload = {
                "TransactionAmt": amount,
                "card1": int(card1),
                "hour_of_day": hour,
                "day_of_week": day_num,
                "is_night": is_night,
                "is_weekend": is_weekend,
                "is_cold_start": int(is_cold),
                "risky_email_domain": int(risky_email),
                "addr_mismatch": int(addr_mismatch),
                "card1_vel_3600s": vel_1h,
                "card1_vel_21600s": vel_6h,
                "card1_vel_86400s": vel_24h,
                "merchant_id": merchant_id,
                "order_id": order_id,
            }

            with st.spinner("Scoring..."):
                result = score_transaction(payload)

            if "error" not in result:
                decision = result.get("decision", "")
                p_fraud  = result.get("p_fraud", 0)
                reasons  = result.get("reasons", [])
                latency  = result.get("latency_ms", 0)

                # Decision badge
                color = {"APPROVE": "#10b981",
                         "STEP_UP_2FA": "#f59e0b",
                         "DECLINE": "#ef4444"}.get(decision, "#338cf0")
                
                st.markdown(
                    f"<h2 style='color:{color}; font-weight: bold;'>{decision}</h2>",
                    unsafe_allow_html=True
                )

                # Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("P(Fraud)", f"{p_fraud:.4f}")
                m2.metric("Latency", f"{latency:.1f}ms")
                m3.metric("Path", result.get("path", ""))

                # Reason codes
                st.caption("Risk Factors")
                for r in reasons:
                    st.code(r)

                # Audit info
                with st.expander("Audit Trail"):
                    st.json(result.get("audit", {}))

            else:
                st.error(f"Error: {result['error']}")

# ════════════════════════════════════════════════════════════
# TAB 3 — AUDIT HISTORY
# ════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Audit History")

    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        txn_filter = st.text_input("Filter by Transaction ID", placeholder="optional")
    with col_f2:
        limit = st.selectbox("Show last", [10, 25, 50, 100], index=0)

    history = get_audit_history(limit=limit)

    if txn_filter:
        history = [h for h in history
                   if txn_filter in h.get("transaction_id", "")]

    if history:
        rows = []
        for r in history:
            decision = r.get("decision", "")
            rows.append({
                "Timestamp": r.get("timestamp", "")[:19].replace("T", " "),
                "Txn ID": r.get("transaction_id", "")[:12],
                "Decision": decision,
                "P(Fraud)": round(r.get("p_fraud", 0), 4),
                "Amount": f"₹{r.get('amount', 0):,.0f}",
                "Merchant": r.get("merchant_id", "N/A"),
                "Top Reason": (r.get("reasons", ["N/A"])[0] if r.get("reasons") else "N/A"),
                "Path": r.get("path", ""),
                "Latency": f"{r.get('latency_ms', 0):.1f}ms",
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, width="stretch", hide_index=True)

        # Download
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"audit_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No audit records found")

# ════════════════════════════════════════════════════════════
# TAB 4 — MODEL INFO
# ════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Model Information")

    if health:
        metrics = health.get("eval_metrics", {})
        thresholds = health.get("thresholds", {})

        col1, col2 = st.columns(2)

        with col1:
            st.caption("Eval Metrics — IEEE-CIS held-out val set")
            metric_data = {
                "AUC-ROC": metrics.get("auc_roc", "N/A"),
                "Precision (High)": metrics.get("precision_high", "N/A"),
                "Recall (High)": metrics.get("recall_high", "N/A"),
                "FPR (High)": metrics.get("fpr_high", "N/A"),
                "Precision (Balanced)": metrics.get("precision_balanced", "N/A"),
                "Recall (Balanced)": metrics.get("recall_balanced", "N/A"),
                "FPR (Balanced)": metrics.get("fpr_balanced", "N/A"),
            }
            for k, v in metric_data.items():
                st.metric(k, v)

        with col2:
            st.caption("Threshold Configuration")
            st.metric("APPROVE threshold", f"< {thresholds.get('approve', 'N/A')}")
            st.metric("STEP_UP threshold", f"< {thresholds.get('stepup', 'N/A')}")
            st.metric("DECLINE threshold", f">= {thresholds.get('decline', 'N/A')}")

            st.divider()
            st.caption("Architecture")
            st.markdown("""
            - **Model**: LightGBM (3129 trees)
            - **Calibration**: Isotonic Regression
            - **Features**: 451 (V, C, D, M, id cols + engineered)
            - **Cold-start**: Rule-based fallback
            - **Explainability**: TreeSHAP reason codes
            - **Dataset**: IEEE-CIS Fraud Detection
            - **Training size**: 472,432 transactions
            """)
    else:
        st.error("API offline — cannot load model info")

# ════════════════════════════════════════════════════════════
# TAB 5 — BATCH CSV SCORER
# ════════════════════════════════════════════════════════════
with tab5:
    st.subheader("Batch CSV Scorer")
    st.caption("Upload a CSV of transactions and get fraud scores + SHAP reasons per row")

    # Sample download
    col_dl, col_info = st.columns([1, 3])
    with col_dl:
        sample_csv = generate_sample_csv()
        st.download_button(
            label="Download Sample CSV",
            data=sample_csv,
            file_name="sample_transactions.csv",
            mime="text/csv",
            help="Download a sample CSV to see the expected format"
        )
    with col_info:
        st.info("Required column: `TransactionAmt`. "
                "All other columns are optional with sensible defaults.")

    st.divider()

    # File upload
    uploaded_file = st.file_uploader(
        "Upload transaction CSV",
        type=["csv"],
        help="CSV with transaction data. Download sample above for format."
    )

    if uploaded_file:
        df_input = pd.read_csv(uploaded_file)

        # Validate
        valid, msg = validate_csv(df_input)
        if not valid:
            st.error(f"Invalid CSV: {msg}")
        else:
            st.success(f"CSV loaded: {len(df_input)} transactions")

            # Preview
            with st.expander("Preview input data"):
                st.dataframe(df_input.head(5), width="stretch")

            # Score button
            if st.button("Score All Transactions", use_container_width=True):
                progress_bar = st.progress(0)
                status_text  = st.empty()

                def update_progress(pct):
                    progress_bar.progress(pct)
                    status_text.caption(
                        f"Scoring... {int(pct * len(df_input))}/{len(df_input)}")

                with st.spinner("Scoring transactions..."):
                    result_df = score_batch_csv(df_input, update_progress)

                progress_bar.progress(1.0)
                status_text.caption("Done!")

                # Summary metrics
                st.divider()
                total_b   = len(result_df)
                approve_b = (result_df["decision"] == "APPROVE").sum()
                stepup_b  = (result_df["decision"] == "STEP_UP_2FA").sum()
                decline_b = (result_df["decision"] == "DECLINE").sum()
                errors_b  = (result_df["decision"] == "ERROR").sum()
                avg_p     = result_df["p_fraud"].mean()

                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Total", total_b)
                c2.metric("Approved",    approve_b,
                          f"{approve_b/total_b:.1%}")
                c3.metric("Step-Up 2FA", stepup_b,
                          f"{stepup_b/total_b:.1%}")
                c4.metric("Declined",    decline_b,
                          f"{decline_b/total_b:.1%}")
                c5.metric("Avg P(Fraud)", f"{avg_p:.4f}")

                # Results table
                st.divider()
                st.subheader("Results")

                # Color-code decisions
                def color_decision(val):
                    color = {
                        "APPROVE":     "color: #10b981; font-weight: 600;",
                        "STEP_UP_2FA": "color: #f59e0b; font-weight: 600;",
                        "DECLINE":     "color: #ef4444; font-weight: 600;",
                        "ERROR":       "color: #94a3b8; font-weight: 600;",
                    }.get(val, "")
                    return color

                display_cols = (
                    ["TransactionAmt"] +
                    [c for c in ["merchant_id","card1","hour_of_day",
                                 "is_cold_start"] if c in result_df.columns] +
                    ["p_fraud","decision","reason_1","reason_2",
                     "reason_3","path","latency_ms"]
                )
                display_df = result_df[
                    [c for c in display_cols if c in result_df.columns]
                ]

                styled = display_df.style.map(
                    color_decision, subset=["decision"]
                )
                st.dataframe(styled, width="stretch", hide_index=True)

                # Download results
                st.divider()
                csv_out = result_df.to_csv(index=False)
                st.download_button(
                    label="Download Scored Results CSV",
                    data=csv_out,
                    file_name=f"scored_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

                # Fraud breakdown chart
                if total_b > 0:
                    st.divider()
                    st.subheader("Decision Distribution")
                    fig = go.Figure(data=[go.Bar(
                        x=["Approve", "Step-Up 2FA", "Decline"],
                        y=[approve_b, stepup_b, decline_b],
                        marker_color=["#10b981", "#f59e0b", "#ef4444"],
                    )])
                    fig.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_color="white",
                        height=300,
                        margin=dict(t=20, b=20, l=20, r=20),
                        yaxis=dict(gridcolor="#1e2430"),
                    )
                    st.plotly_chart(fig, width="stretch")

# ════════════════════════════════════════════════════════════
# TAB 6 — DRIFT MONITOR
# ════════════════════════════════════════════════════════════
with tab6:
    st.subheader("Model Drift Monitor")
    st.caption("PSI and KL divergence monitoring — auto-triggers retrain alert when PSI > 0.2")

    # ── Drift summary ─────────────────────────────────────────
    col_refresh, col_window = st.columns([1, 2])
    with col_refresh:
        run_drift = st.button(" Run Drift Check", use_container_width=True)
    with col_window:
        st.caption("Compares last 24h scores against last 7 days as reference baseline")

    st.divider()

    if run_drift:
        with st.spinner("Computing PSI and KL divergence..."):
            summary = get_drift_summary()

        # ── Status banner ──────────────────────────────────────
        status = summary.get("status", "UNKNOWN")

        if status == "STABLE":
            st.success(f" Model is STABLE — No retraining needed")
        elif status == "MONITOR":
            st.warning(f" Model is MONITOR — Moderate drift detected, keep watching")
        elif status == "DRIFT_DETECTED":
            st.error(f" Model is DRIFT DETECTED — Retraining recommended")
        else:
            st.info(f"ℹ️ {summary.get('message', 'Insufficient data for drift analysis')}")

        st.divider()

        if status not in ["INSUFFICIENT_DATA", "UNKNOWN"]:
            # ── Key metrics ────────────────────────────────────
            c1, c2, c3, c4 = st.columns(4)

            psi = summary.get("psi", 0)
            kl  = summary.get("kl_divergence", 0)

            with c1:
                psi_color = (
                    "normal" if psi < 0.1 else
                    "off"    if psi < 0.2 else
                    "inverse"
                )
                st.metric(
                    "PSI Score",
                    f"{psi:.4f}",
                    delta=(
                        "Stable" if psi < 0.1 else
                        "Monitor" if psi < 0.2 else
                        "Retrain!"
                    ),
                    delta_color=psi_color,
                    help="Population Stability Index. < 0.1 stable, 0.1-0.2 monitor, > 0.2 retrain"
                )
            with c2:
                st.metric(
                    "KL Divergence",
                    f"{kl:.4f}",
                    help="KL divergence between reference and current distributions"
                )
            with c3:
                st.metric(
                    "Recent Scores",
                    summary.get("recent_count", 0),
                    help="Number of scores in last 24h window"
                )
            with c4:
                st.metric(
                    "Reference Scores",
                    summary.get("reference_count", 0),
                    help="Number of scores in 7-day reference window"
                )

            st.divider()

            # ── Score distribution comparison ──────────────────
            col_l, col_r = st.columns(2)

            with col_l:
                st.subheader("PSI Interpretation")
                psi_data = {
                    "Range":        ["< 0.1", "0.1 – 0.2", "> 0.2"],
                    "Status":       [" Stable", " Monitor", " Retrain"],
                    "Action":       ["None", "Keep watching", "Trigger retraining"],
                    "Your PSI":     [
                        f"{psi:.4f}" if psi < 0.1 else "",
                        f"{psi:.4f}" if 0.1 <= psi < 0.2 else "",
                        f"{psi:.4f}" if psi >= 0.2 else "",
                    ]
                }
                st.dataframe(
                    pd.DataFrame(psi_data),
                    use_container_width=True,
                    hide_index=True
                )

            with col_r:
                st.subheader("Score Means")
                means_fig = go.Figure(data=[go.Bar(
                    x=["Reference (7d)", "Recent (24h)"],
                    y=[
                        summary.get("reference_mean", 0),
                        summary.get("recent_mean", 0)
                    ],
                    marker_color=["#3d7fff", "#ef4444"],
                    text=[
                        f"{summary.get('reference_mean', 0):.4f}",
                        f"{summary.get('recent_mean', 0):.4f}"
                    ],
                    textposition="auto",
                )])
                means_fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="white",
                    height=250,
                    margin=dict(t=20, b=20, l=20, r=20),
                    yaxis=dict(
                        gridcolor="#1e2430",
                        title="Avg P(Fraud)"
                    ),
                )
                st.plotly_chart(means_fig, use_container_width=True)

            st.divider()

            # ── Retrain button ─────────────────────────────────
            st.subheader("Retraining")

            if summary.get("retrain_recommended"):
                st.error(
                    " Retraining is recommended. "
                    "PSI has exceeded the 0.2 threshold."
                )
                if st.button(" Trigger Retraining",
                             type="primary",
                             use_container_width=True):
                    st.info(
                        "In production this would trigger the retraining "
                        "pipeline with the latest labeled data from ClickHouse. "
                        "For this demo, re-run the Kaggle training notebook "
                        "and replace the artifacts."
                    )
                    st.code(
                        "# Production retraining command\n"
                        "python models/trainer.py --retrain --data latest",
                        language="bash"
                    )
            else:
                st.success(
                    " No retraining needed. "
                    "Model is stable — PSI is within acceptable range."
                )

            # ── Last checked ───────────────────────────────────
            st.divider()
            st.caption(
                f"Last checked: {summary.get('checked_at', 'N/A')} | "
                f"PSI threshold: {summary.get('psi_threshold', 0.2)}"
            )

        else:
            # Not enough data
            st.info(
                f"Not enough data yet for drift analysis. "
                f"Need at least 10 recent scores. "
                f"Current: {summary.get('recent_count', 0)}"
            )
            st.caption(
                "Score more transactions via the Score Transaction tab "
                "or Batch Scorer to build up enough data."
            )

    else:
        # Not yet run
        st.info("Click 'Run Drift Check' to analyse model drift.")

        st.subheader("How Drift Detection Works")
        st.markdown("""
        **PSI (Population Stability Index)** measures how much the
        distribution of fraud scores has shifted between a reference
        period (last 7 days) and a recent window (last 24 hours).

        | PSI Range | Status | Action |
        |---|---|---|
        | < 0.1 | Stable | No action needed |
        | 0.1 – 0.2 | Monitor | Watch closely |
        | > 0.2 | Drift | Retrain model |

        **KL Divergence** measures information loss between the two
        distributions — a complementary signal to PSI.

        The system automatically flags when retraining is recommended
        and shows which direction the scores have drifted.
        """)