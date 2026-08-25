"""
Razorpay AI Risk Manager - Ops Dashboard
Real-time fraud monitoring and transaction scoring
"""

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
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE = "http://127.0.0.1:8000"

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0a0c10; }
    .metric-card {
        background: #111318;
        border: 1px solid #1e2430;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .approve  { border-left: 4px solid #22c55e; }
    .stepup   { border-left: 4px solid #eab308; }
    .decline  { border-left: 4px solid #ef4444; }
    .stButton > button {
        background: #3d7fff;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 20px;
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
        return r.json()
    except:
        return {}

def get_audit_history(limit=20):
    try:
        r = requests.get(f"{API_BASE}/audit/history?limit={limit}", timeout=3)
        return r.json()
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
        rzp_status = "✅ Connected" if health.get("razorpay_connected") else "⚠️ Disconnected"
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
st.title("🛡️ Razorpay AI Risk Manager")
st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')} | "
           f"Track 02 — AI Buildathon 2026")
st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Live Dashboard",
    "🔍 Score Transaction",
    "📋 Audit History",
    "ℹ️ Model Info"
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
                marker_colors=["#22c55e", "#eab308", "#ef4444"],
            )])
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                showlegend=True,
                margin=dict(t=20, b=20, l=20, r=20),
                height=280,
            )
            st.plotly_chart(fig, use_container_width=True)
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
                "bar": {"color": "#3d7fff"},
                "steps": [
                    {"range": [0, 0.10], "color": "#22c55e"},
                    {"range": [0.10, 0.35], "color": "#eab308"},
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
            height=280,
            margin=dict(t=20, b=20, l=40, r=40),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 3: Recent decisions ─────────────────────────────
    st.subheader("Recent Decisions")
    history = get_audit_history(limit=10)

    if history:
        rows = []
        for r in history:
            decision = r.get("decision", "")
            emoji = {"APPROVE": "✅", "STEP_UP_2FA": "⚡", "DECLINE": "❌"}.get(decision, "")
            rows.append({
                "Time": r.get("timestamp", "")[:19].replace("T", " "),
                "Decision": f"{emoji} {decision}",
                "P(Fraud)": f"{r.get('p_fraud', 0):.4f}",
                "Amount": f"₹{r.get('amount', 0):,.0f}",
                "Reasons": ", ".join(r.get("reasons", [])[:2]),
                "Path": r.get("path", ""),
                "Latency": f"{r.get('latency_ms', 0):.1f}ms",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
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

        score_btn = st.button("🔍 Score Transaction", use_container_width=True)

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
                color = {"APPROVE": "green",
                         "STEP_UP_2FA": "orange",
                         "DECLINE": "red"}.get(decision, "blue")
                emoji = {"APPROVE": "✅",
                         "STEP_UP_2FA": "⚡",
                         "DECLINE": "❌"}.get(decision, "")
                st.markdown(
                    f"<h2 style='color:{color}'>{emoji} {decision}</h2>",
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
            emoji = {"APPROVE": "✅",
                     "STEP_UP_2FA": "⚡",
                     "DECLINE": "❌"}.get(decision, "")
            rows.append({
                "Timestamp": r.get("timestamp", "")[:19].replace("T", " "),
                "Txn ID": r.get("transaction_id", "")[:12],
                "Decision": f"{emoji} {decision}",
                "P(Fraud)": round(r.get("p_fraud", 0), 4),
                "Amount": f"₹{r.get('amount', 0):,.0f}",
                "Merchant": r.get("merchant_id", "N/A"),
                "Top Reason": (r.get("reasons", ["N/A"])[0] if r.get("reasons") else "N/A"),
                "Path": r.get("path", ""),
                "Latency": f"{r.get('latency_ms', 0):.1f}ms",
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Download
        csv = df.to_csv(index=False)
        st.download_button(
            label="⬇️ Download CSV",
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