import numpy as np


# ============================================================
# DATA AGE NORMALIZATION
# ============================================================

def normalize_data_age(
    age_days,
    max_age_days=7.0
):
    """
    Convert Data Age into confidence from 0 to 1.

    NOTE:
    This is currently a prototype mapping.
    It should later be calibrated using historical data.
    """

    if age_days is None or np.isnan(age_days):
        return np.nan

    confidence = 1.0 - (
        age_days / max_age_days
    )

    return float(
        np.clip(confidence, 0.0, 1.0)
    )


# ============================================================
# PREDICTION ERROR NORMALIZATION
# ============================================================

def normalize_prediction_error(
    error_km,
    max_error_km=10.0
):
    """
    Convert prediction error into confidence.

    Smaller error = higher confidence.

    Prototype mapping.
    """

    if error_km is None or np.isnan(error_km):
        return np.nan

    confidence = 1.0 - (
        error_km / max_error_km
    )

    return float(
        np.clip(confidence, 0.0, 1.0)
    )


# ============================================================
# PROPAGATION / TRAJECTORY CONSISTENCY
# ============================================================

def normalize_trajectory_consistency(
    consistency
):
    """
    Trajectory consistency is already a score
    between 0 and 1.

    Higher value = more consistent trajectory.
    """

    if consistency is None or np.isnan(consistency):
        return np.nan

    return float(
        np.clip(consistency, 0.0, 1.0)
    )


# ============================================================
# MODEL CONFIDENCE NORMALIZATION
# ============================================================

def normalize_model_confidence(
    model_confidence
):
    """
    Model confidence is already expected
    to be between 0 and 1.
    """

    if (
        model_confidence is None
        or np.isnan(model_confidence)
    ):
        return np.nan

    return float(
        np.clip(model_confidence, 0.0, 1.0)
    )


# ============================================================
# ACI CALCULATION
# ============================================================

def calculate_aci(
    data_age_confidence,
    prediction_confidence,
    track_confidence,
    model_confidence,
    weights=None
):
    """
    Calculate Adaptive Confidence Index.

    Available factors are automatically used.
    Missing factors are ignored and remaining
    weights are re-normalized.
    """

    if weights is None:
        weights = {
            "data_age": 0.25,
            "prediction": 0.25,
            "track": 0.25,
            "model": 0.25
        }

    factors = {
        "data_age": data_age_confidence,
        "prediction": prediction_confidence,
        "track": track_confidence,
        "model": model_confidence
    }

    available = {
        name: value
        for name, value in factors.items()
        if value is not None
        and not np.isnan(value)
    }

    if not available:
        return np.nan

    total_weight = sum(
        weights[name]
        for name in available
    )

    aci = sum(
        weights[name] * value
        for name, value in available.items()
    ) / total_weight

    return float(
        np.clip(aci, 0.0, 1.0)
    )


# ============================================================
# FAST / DEEP DECISION
# ============================================================

def make_decision(
    aci,
    threshold=0.70
):
    """
    Select Fast Path or Deep Path.
    """

    if aci is None or np.isnan(aci):
        return "INSUFFICIENT_DATA"

    if aci >= threshold:
        return "FAST"

    return "DEEP"