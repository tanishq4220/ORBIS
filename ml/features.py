import numpy as np
from sgp4.api import Satrec


# =========================================================
# FEATURES USED BY THE TRAINED ML MODEL
# =========================================================

FEATURE_NAMES = [
    "prediction_horizon_hours",
    "inclination_deg",
    "eccentricity",
    "mean_motion_rev_day",
    "bstar",
    "mean_motion_derivative",
]


def _safe(value, default=0.0):
    """
    Convert a value to a finite float.
    """
    try:
        value = float(value)

        if np.isfinite(value):
            return value

        return default

    except (TypeError, ValueError):
        return default


def extract_tle_features(
    tle1,
    tle2,
    prediction_horizon_hours
):
    """
    Extract exactly the six features expected
    by the trained Random Forest model.
    """

    sat = Satrec.twoline2rv(
        str(tle1).strip(),
        str(tle2).strip()
    )

    return {
        "prediction_horizon_hours":
            _safe(prediction_horizon_hours),

        "inclination_deg":
            np.degrees(
                _safe(sat.inclo)
            ),

        "eccentricity":
            _safe(sat.ecco),

        "mean_motion_rev_day":
            _safe(sat.no_kozai)
            * 1440.0
            / (2.0 * np.pi),

        "bstar":
            _safe(sat.bstar),

        "mean_motion_derivative":
            _safe(sat.ndot),
    }


def build_feature_matrix(df):
    """
    Build a feature matrix matching the exact
    feature order used during model training.
    """

    rows = []

    for _, row in df.iterrows():

        try:

            # -------------------------------------------------
            # Determine prediction horizon
            # -------------------------------------------------

            if "Prediction_Horizon_hours" in row:
                horizon = row[
                    "Prediction_Horizon_hours"
                ]

            elif "prediction_horizon_hours" in row:
                horizon = row[
                    "prediction_horizon_hours"
                ]

            else:
                # If no horizon is supplied, use 0.
                # The caller should provide the actual
                # prediction horizon whenever possible.
                horizon = 0.0

            rows.append(
                extract_tle_features(
                    row["TLE Line 1"],
                    row["TLE Line 2"],
                    horizon
                )
            )

        except Exception:

            rows.append(
                {
                    name: np.nan
                    for name in FEATURE_NAMES
                }
            )

    return rows