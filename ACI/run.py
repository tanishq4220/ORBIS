import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd

from sgp4.api import Satrec, jday


# ============================================================
# IMPORT PROJECT MODULES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(PROJECT_DIR))

from factors import (
    calculate_data_age,
    calculate_trajectory_consistency,
)

from engine import (
    normalize_data_age,
    normalize_prediction_error,
    normalize_trajectory_consistency,
    normalize_model_confidence,
    calculate_aci,
    make_decision,
)

from ml.predict_model import add_model_confidence


# ============================================================
# PATHS
# ============================================================

INPUT_FILE = (
    BASE_DIR
    / "satellite_debris_tle (2).xlsx"
)

OUTPUT_FILE = (
    BASE_DIR
    / "aci_output.csv"
)


# ============================================================
# SETTINGS
# ============================================================

NUM_STEPS = 6
STEP_MINUTES = 10

# ------------------------------------------------------------
# Prototype prediction horizon used by the ML model.
#
# IMPORTANT:
# In the final application this should come from the
# actual prediction request made by the operator/frontend.
# ------------------------------------------------------------

PREDICTION_HORIZON_HOURS = 12.0

# ACI prototype decision threshold.
ACI_THRESHOLD = 0.70


# ============================================================
# LOAD DATASET
# ============================================================

print("=" * 70)
print("ORBIS ACI PROCESSING")
print("=" * 70)

print("\nLoading orbital dataset...")

df = pd.read_excel(INPUT_FILE)

print(
    f"Dataset loaded: {len(df)} objects"
)


# ============================================================
# CURRENT UTC TIME
# ============================================================

current_time = datetime.now(
    timezone.utc
)

print(
    f"Current UTC time: "
    f"{current_time.isoformat()}"
)

print(
    f"Prediction horizon: "
    f"{PREDICTION_HORIZON_HOURS:.1f} hours"
)


# ============================================================
# FUNCTION: GET SGP4 POSITIONS
# ============================================================

def get_sgp4_positions(
    tle1,
    tle2
):
    """
    Propagate a TLE at several timestamps and return
    the resulting SGP4 positions in km.
    """

    try:

        satellite = Satrec.twoline2rv(
            str(tle1).strip(),
            str(tle2).strip()
        )

        positions = []

        for step in range(NUM_STEPS):

            future_time = (
                current_time
                + timedelta(
                    minutes=STEP_MINUTES * step
                )
            )

            jd, fr = jday(
                future_time.year,
                future_time.month,
                future_time.day,
                future_time.hour,
                future_time.minute,
                future_time.second
            )

            error_code, position, velocity = (
                satellite.sgp4(
                    jd,
                    fr
                )
            )

            if error_code != 0:
                return None

            positions.append(
                position
            )

        return positions

    except Exception:

        return None


# ============================================================
# FACTOR 1 — DATA AGE
# ============================================================

print("\nCalculating Data Age...")

df["Data_Age_days"] = (
    df["Epoch"]
    .apply(calculate_data_age)
)


# ============================================================
# FACTOR 3 — TRACK / TRAJECTORY CONSISTENCY
# ============================================================

print(
    "Calculating SGP4 trajectory consistency..."
)

trajectory_consistencies = []

for _, row in df.iterrows():

    positions = get_sgp4_positions(
        row["TLE Line 1"],
        row["TLE Line 2"]
    )

    if positions is None:

        trajectory_consistencies.append(
            np.nan
        )

    else:

        consistency = (
            calculate_trajectory_consistency(
                positions
            )
        )

        trajectory_consistencies.append(
            consistency
        )


df["Trajectory_Consistency"] = (
    trajectory_consistencies
)


# ============================================================
# FACTOR 2 — PREDICTION ERROR
# ============================================================

print(
    "\nPrediction Error:"
)

print(
    "Unavailable for live ACI evaluation."
)

print(
    "No valid future reference orbit is supplied "
    "for the current TLE dataset."
)

print(
    "Therefore Prediction Error will remain NaN "
    "and ACI will renormalize the available factors."
)

df["Prediction_Error_km"] = np.nan


# ============================================================
# FACTOR 4 — ML MODEL CONFIDENCE
# ============================================================

print(
    "\nCalculating ML Model Confidence..."
)

try:

    # The ML model expects the prediction horizon.
    df["Prediction_Horizon_hours"] = (
        PREDICTION_HORIZON_HOURS
    )

    df = add_model_confidence(
        df
    )

    print(
        "ML Model Confidence calculated for "
        f"{len(df)} objects."
    )

except Exception as e:

    print(
        "\n❌ ML model calculation failed:"
    )

    print(e)

    raise


# ============================================================
# NORMALIZE FACTORS
# ============================================================

print(
    "\nNormalizing ACI factors..."
)


# ------------------------------------------------------------
# Data Age
# ------------------------------------------------------------

df["Data_Age_Confidence"] = (
    df["Data_Age_days"]
    .apply(
        normalize_data_age
    )
)


# ------------------------------------------------------------
# Prediction Error
# ------------------------------------------------------------

df["Prediction_Confidence"] = (
    df["Prediction_Error_km"]
    .apply(
        normalize_prediction_error
    )
)


# ------------------------------------------------------------
# Track
# ------------------------------------------------------------

df["Track_Confidence"] = (
    df["Trajectory_Consistency"]
    .apply(
        normalize_trajectory_consistency
    )
)


# ------------------------------------------------------------
# Model Confidence
# ------------------------------------------------------------

df["Model_Confidence_Normalized"] = (
    df["Model_Confidence"]
    .apply(
        normalize_model_confidence
    )
)


# ============================================================
# CALCULATE ACI
# ============================================================

print(
    "Calculating ACI..."
)

df["ACI"] = df.apply(
    lambda row: calculate_aci(

        data_age_confidence=
            row["Data_Age_Confidence"],

        prediction_confidence=
            row["Prediction_Confidence"],

        track_confidence=
            row["Track_Confidence"],

        model_confidence=
            row["Model_Confidence_Normalized"]

    ),
    axis=1
)


# ============================================================
# FAST / DEEP DECISION
# ============================================================

df["Decision"] = (
    df["ACI"]
    .apply(
        lambda x:
            make_decision(
                x,
                threshold=ACI_THRESHOLD
            )
    )
)


# ============================================================
# SAVE OUTPUT
# ============================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# DISPLAY RESULTS
# ============================================================

print(
    "\n" + "=" * 70
)

print(
    "ACI PROCESSING COMPLETE"
)

print(
    "=" * 70
)


display_columns = [
    "ID",
    "Name",
    "Type",
    "Epoch",
    "Data_Age_days",
    "Data_Age_Confidence",
    "Trajectory_Consistency",
    "Track_Confidence",
    "Prediction_Error_km",
    "Prediction_Confidence",
    "Prediction_Horizon_hours",
    "Model_Confidence",
    "ML_Prediction",
    "ACI",
    "Decision",
]


print(
    "\nFIRST 20 RESULTS"
)

print(
    df[display_columns]
    .head(20)
    .to_string(index=False)
)


# ============================================================
# SUMMARY
# ============================================================

print(
    "\n" + "=" * 70
)

print(
    "ACI SUMMARY"
)

print(
    "=" * 70
)

print(
    "\nObjects processed:",
    len(df)
)

print(
    "\nML predictions:"
)

print(
    df["ML_Prediction"]
    .value_counts(dropna=False)
    .to_string()
)

print(
    "\nDecision distribution:"
)

print(
    df["Decision"]
    .value_counts(dropna=False)
    .to_string()
)

print(
    "\nACI statistics:"
)

print(
    df["ACI"]
    .describe()
    .to_string()
)

print(
    "\nModel Confidence statistics:"
)

print(
    df["Model_Confidence"]
    .describe()
    .to_string()
)

print(
    "\nOutput saved to:"
)

print(
    OUTPUT_FILE
)

print(
    "\n✅ ORBIS ACI PIPELINE COMPLETE"
)