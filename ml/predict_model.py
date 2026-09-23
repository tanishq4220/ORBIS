from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd


# =========================================================
# PATHS
# =========================================================

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(ROOT)
)

from ml.features import (
    FEATURE_NAMES,
    build_feature_matrix
)


MODEL_PATH = (
    Path(__file__).resolve().parent
    / "random_forest_calibrated.joblib"
)


# =========================================================
# LOAD MODEL
# =========================================================

def load_model():

    if not MODEL_PATH.exists():

        raise FileNotFoundError(
            f"Calibrated ML model not found:\n"
            f"{MODEL_PATH}\n\n"
            f"Run ml/calibrate_model.py first."
        )

    model_package = joblib.load(
        MODEL_PATH
    )

    return model_package


# =========================================================
# PREDICT MODEL CONFIDENCE
# =========================================================

def add_model_confidence(df):

    model_package = load_model()

    model = model_package["model"]
    calibrator = model_package["calibrator"]

    trained_features = (
        model_package["features"]
    )

    # -----------------------------------------------------
    # Verify feature order
    # -----------------------------------------------------

    if trained_features != FEATURE_NAMES:

        raise ValueError(
            "Feature mismatch between the saved model "
            "and ml/features.py.\n\n"
            f"Model expects:\n{trained_features}\n\n"
            f"Code provides:\n{FEATURE_NAMES}"
        )

    # -----------------------------------------------------
    # Build features
    # -----------------------------------------------------

    feature_df = pd.DataFrame(
        build_feature_matrix(df),
        columns=FEATURE_NAMES
    )

    # -----------------------------------------------------
    # Handle invalid values
    # -----------------------------------------------------

    feature_df = feature_df.replace(
        [np.inf, -np.inf],
        np.nan
    )

    feature_df = feature_df.fillna(
        feature_df.median(
            numeric_only=True
        )
    )

    feature_df = feature_df.fillna(0.0)

    # -----------------------------------------------------
    # Raw Random Forest probability
    # -----------------------------------------------------

    probabilities = (
        model.predict_proba(
            feature_df
        )
    )

    classes = list(
        model.classes_
    )

    if 1 not in classes:

        raise ValueError(
            "Reliable class (1) is missing "
            "from the trained model."
        )

    reliable_index = (
        classes.index(1)
    )

    raw_probability = (
        probabilities[:, reliable_index]
    )

    # -----------------------------------------------------
    # Calibrate probability
    # -----------------------------------------------------

    calibrated_probability = (
        calibrator.predict_proba(
            raw_probability.reshape(-1, 1)
        )[:, 1]
    )

    calibrated_probability = np.clip(
        calibrated_probability,
        0.0,
        1.0
    )

    # -----------------------------------------------------
    # Classification
    # -----------------------------------------------------

    threshold = model_package.get(
        "classification_threshold",
        0.5
    )

    prediction = np.where(
        calibrated_probability >= threshold,
        "RELIABLE",
        "LOW_CONFIDENCE"
    )

    # -----------------------------------------------------
    # Return results
    # -----------------------------------------------------

    result = df.copy()

    result["Model_Confidence"] = (
        calibrated_probability
    )

    result["ML_Prediction"] = prediction

    return result