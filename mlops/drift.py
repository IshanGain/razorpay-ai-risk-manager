"""
Drift Detection
PSI (Population Stability Index) and KL divergence
monitoring for feature and score drift
"""

import json
import numpy as np
from datetime import datetime, timezone, timedelta


def compute_psi(expected: np.ndarray,
                actual: np.ndarray,
                buckets: int = 10) -> float:
    """
    Compute Population Stability Index (PSI)

    PSI < 0.1  : No significant change
    PSI < 0.2  : Moderate change, monitor
    PSI >= 0.2 : Significant change, retrain

    Args:
        expected: Reference distribution (training scores)
        actual:   Current distribution (recent scores)
        buckets:  Number of buckets for binning

    Returns:
        PSI value
    """
    expected = np.array(expected)
    actual   = np.array(actual)

    # Create buckets from expected distribution
    breakpoints = np.linspace(0, 1, buckets + 1)

    expected_pct = np.histogram(expected, breakpoints)[0] / len(expected)
    actual_pct   = np.histogram(actual,   breakpoints)[0] / len(actual)

    # Avoid division by zero
    expected_pct = np.where(expected_pct == 0, 1e-6, expected_pct)
    actual_pct   = np.where(actual_pct   == 0, 1e-6, actual_pct)

    psi = np.sum(
        (actual_pct - expected_pct) * np.log(actual_pct / expected_pct)
    )

    return float(psi)


def compute_kl_divergence(p: np.ndarray,
                          q: np.ndarray,
                          buckets: int = 10) -> float:
    """
    Compute KL Divergence between two distributions

    Args:
        p: Reference distribution
        q: Current distribution
        buckets: Number of buckets

    Returns:
        KL divergence value
    """
    breakpoints = np.linspace(0, 1, buckets + 1)
    p_hist = np.histogram(p, breakpoints)[0] / len(p)
    q_hist = np.histogram(q, breakpoints)[0] / len(q)

    p_hist = np.where(p_hist == 0, 1e-6, p_hist)
    q_hist = np.where(q_hist == 0, 1e-6, q_hist)

    return float(np.sum(p_hist * np.log(p_hist / q_hist)))


def load_recent_scores(log_file: str = "audit/decisions.jsonl",
                       hours: int = 24) -> list:
    """
    Load recent fraud scores from audit log

    Args:
        log_file: Path to audit JSONL
        hours: Lookback window in hours

    Returns:
        List of p_fraud scores
    """
    scores = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    try:
        with open(log_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    ts = record.get("timestamp", "")
                    dt = datetime.fromisoformat(ts)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if dt > cutoff:
                        p = record.get("p_fraud")
                        if p is not None:
                            scores.append(float(p))
                except Exception:
                    continue
    except FileNotFoundError:
        pass

    return scores


def check_score_drift(reference_scores: list,
                      log_file: str = "audit/decisions.jsonl",
                      hours: int = 24,
                      psi_threshold: float = 0.2) -> dict:
    """
    Check if recent fraud scores have drifted from reference

    Args:
        reference_scores: Training/baseline fraud scores
        log_file: Audit log path
        hours: Lookback window
        psi_threshold: PSI threshold for drift alert

    Returns:
        Drift report dict
    """
    recent_scores = load_recent_scores(log_file, hours)

    if len(recent_scores) < 10:
        return {
            "status":        "INSUFFICIENT_DATA",
            "message":       f"Only {len(recent_scores)} recent scores (need 10+)",
            "recent_count":  len(recent_scores),
            "psi":           None,
            "kl_divergence": None,
            "drift_detected": False,
            "retrain_recommended": False,
        }

    psi = compute_psi(
        np.array(reference_scores),
        np.array(recent_scores)
    )
    kl  = compute_kl_divergence(
        np.array(reference_scores),
        np.array(recent_scores)
    )

    drift_detected     = psi >= psi_threshold
    retrain_recommended = psi >= psi_threshold

    if psi < 0.1:
        status = "STABLE"
    elif psi < 0.2:
        status = "MONITOR"
    else:
        status = "DRIFT_DETECTED"

    return {
        "status":              status,
        "psi":                 round(psi, 4),
        "kl_divergence":       round(kl, 4),
        "psi_threshold":       psi_threshold,
        "drift_detected":      drift_detected,
        "retrain_recommended": retrain_recommended,
        "recent_count":        len(recent_scores),
        "reference_count":     len(reference_scores),
        "recent_mean":         round(float(np.mean(recent_scores)), 4),
        "reference_mean":      round(float(np.mean(reference_scores)), 4),
        "checked_at":          datetime.now(timezone.utc).isoformat(),
        "message": (
            "Retraining recommended — score distribution has shifted"
            if retrain_recommended else
            "Model is stable — no retraining needed"
        ),
    }


def get_drift_summary(log_file: str = "audit/decisions.jsonl") -> dict:
    """
    Quick drift summary using last 24h vs last 7 days as reference

    Returns:
        Drift summary dict
    """
    # Use 7-day scores as reference
    reference = load_recent_scores(log_file, hours=168)
    # Use 24h scores as current
    recent    = load_recent_scores(log_file, hours=24)

    if len(reference) < 10 or len(recent) < 5:
        return {
            "status":  "INSUFFICIENT_DATA",
            "message": "Not enough data for drift analysis yet",
            "reference_count": len(reference),
            "recent_count":    len(recent),
        }

    return check_score_drift(reference, log_file)