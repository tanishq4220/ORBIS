"""ORBIS ACI (Awareness and Confidence Index) pipeline.

Reads TLE orbital data, calculates four confidence factors:
1. Data Age Confidence (temporal decay)
2. SP3 Prediction Error (ground-truth reference comparison)
3. Trajectory Consistency (SGP4 orbital arc stability)
4. ML Model Confidence (calibrated Random Forest classifier)

Produces aci_output.csv with composite ACI score and operational decisions.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sgp4.api import Satrec, jday

# Paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(PROJECT_DIR) not in sys.path:
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
from sp3_integration import calculate_sp3_prediction_errors

INPUT_FILE = BASE_DIR / "satellite_debris_tle (2).xlsx"
OUTPUT_FILE = BASE_DIR / "aci_output.csv"

# Settings
NUM_STEPS = 6
STEP_MINUTES = 10
PREDICTION_HORIZON_HOURS = 24.0
ACI_THRESHOLD = 0.70

# Default anchor timestamp corresponding to the capture epoch of the static TLE dataset
# (ensures deterministic, reproducible ACI scores matching baseline verification benchmarks)
DEFAULT_CATALOG_ANCHOR_TIME = datetime(2026, 9, 7, 18, 26, 26, tzinfo=timezone.utc)


def get_sgp4_positions(
    tle1: str,
    tle2: str,
    start_time: datetime,
    num_steps: int = NUM_STEPS,
    step_minutes: int = STEP_MINUTES,
) -> Optional[list[list[float]]]:
    """Propagate a TLE at several timestamps and return SGP4 positions in km."""
    try:
        satellite = Satrec.twoline2rv(str(tle1).strip(), str(tle2).strip())
        positions = []
        for step in range(num_steps):
            step_time = start_time + timedelta(minutes=step * step_minutes)
            jd, fr = jday(
                step_time.year,
                step_time.month,
                step_time.day,
                step_time.hour,
                step_time.minute,
                step_time.second + step_time.microsecond / 1_000_000.0,
            )
            error_code, position, _ = satellite.sgp4(jd, fr)
            if error_code != 0:
                return None
            positions.append(list(position))
        return positions
    except Exception:  # noqa: BLE001
        return None


def run_pipeline(
    input_file: Path | str = INPUT_FILE,
    output_file: Path | str = OUTPUT_FILE,
    current_time: Optional[datetime] = None,
    horizon_hours: float = PREDICTION_HORIZON_HOURS,
    threshold: float = ACI_THRESHOLD,
) -> pd.DataFrame:
    """Execute the full ACI pipeline and return the resulting DataFrame."""
    input_path = Path(input_file)
    output_path = Path(output_file)

    print("=" * 70)
    print("ORBIS ACI PROCESSING")
    print("=" * 70)
    print(f"\nLoading orbital dataset from {input_path}...")

    df = pd.read_excel(input_path)
    print(f"Dataset loaded: {len(df)} objects")

    if current_time is None:
        anchor_env = os.environ.get("ORBIS_CATALOG_ANCHOR")
        if anchor_env:
            current_time = datetime.fromisoformat(anchor_env)
            if current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=timezone.utc)
        else:
            current_time = DEFAULT_CATALOG_ANCHOR_TIME

    print(f"Current UTC time: {current_time.isoformat()}")
    print(f"Prediction horizon: {horizon_hours:.1f} hours")

    # FACTOR 1: Data Age
    print("\nCalculating Data Age...")
    df["Data_Age_days"] = df["Epoch"].apply(lambda ep: calculate_data_age(ep, current_time))

    # FACTOR 3: Track / Trajectory Consistency
    print("Calculating SGP4 trajectory consistency...")
    trajectory_consistencies = []
    for _, row in df.iterrows():
        positions = get_sgp4_positions(row["TLE Line 1"], row["TLE Line 2"], current_time)
        if positions is None:
            trajectory_consistencies.append(np.nan)
        else:
            trajectory_consistencies.append(calculate_trajectory_consistency(positions))
    df["Trajectory_Consistency"] = trajectory_consistencies

    # FACTOR 2: Prediction Error (SP3 reference integration)
    print("\nPrediction Error (SP3):")
    df["Prediction_Error_km"] = calculate_sp3_prediction_errors(df)
    num_calculated = int(df["Prediction_Error_km"].notna().sum())
    num_nan = int(df["Prediction_Error_km"].isna().sum())
    print(f"Calculated prediction error for {num_calculated} objects.")
    print(f"Left {num_nan} objects as NaN (unmapped to GPS constellation).")

    # FACTOR 4: ML Model Confidence
    print("\nCalculating ML Model Confidence...")
    df["Prediction_Horizon_hours"] = horizon_hours
    df = add_model_confidence(df)
    print(f"ML Model Confidence calculated for {len(df)} objects.")

    # NORMALIZE FACTORS
    print("\nNormalizing ACI factors...")
    df["Data_Age_Confidence"] = df["Data_Age_days"].apply(normalize_data_age)
    df["Prediction_Confidence"] = df["Prediction_Error_km"].apply(normalize_prediction_error)
    df["Track_Confidence"] = df["Trajectory_Consistency"].apply(normalize_trajectory_consistency)
    df["Model_Confidence_Normalized"] = df["Model_Confidence"].apply(normalize_model_confidence)

    # CALCULATE COMPOSITE ACI
    print("Calculating ACI...")
    df["ACI"] = df.apply(
        lambda row: calculate_aci(
            data_age_confidence=row["Data_Age_Confidence"],
            prediction_confidence=row["Prediction_Confidence"],
            track_confidence=row["Track_Confidence"],
            model_confidence=row["Model_Confidence_Normalized"],
        ),
        axis=1,
    )

    # FAST / DEEP DECISION
    df["Decision"] = df["ACI"].apply(lambda x: make_decision(x, threshold=threshold))

    # SAVE OUTPUT
    df.to_csv(output_path, index=False)
    print(f"\nOutput saved to:\n{output_path}")

    # SUMMARY OUTPUT
    print("\n" + "=" * 70)
    print("ACI PROCESSING COMPLETE")
    print("=" * 70)

    display_columns = [
        "ID", "Name", "Type", "Epoch", "Data_Age_days", "Data_Age_Confidence",
        "Trajectory_Consistency", "Track_Confidence", "Prediction_Error_km",
        "Prediction_Confidence", "Prediction_Horizon_hours", "Model_Confidence",
        "ML_Prediction", "ACI", "Decision",
    ]
    print("\nFIRST 20 RESULTS")
    print(df[display_columns].head(20).to_string(index=False))

    print("\n" + "=" * 70)
    print("ACI SUMMARY")
    print("=" * 70)
    print(f"\nObjects processed: {len(df)}")
    print("\nML predictions:")
    print(df["ML_Prediction"].value_counts(dropna=False).to_string())
    print("\nDecision distribution:")
    print(df["Decision"].value_counts(dropna=False).to_string())
    print("\nACI statistics:")
    print(df["ACI"].describe().to_string())
    print("\nModel Confidence statistics:")
    print(df["Model_Confidence"].describe().to_string())
    print("\n[OK] ORBIS ACI PIPELINE COMPLETE")

    return df


def main() -> None:
    """CLI entrypoint."""
    run_pipeline()


if __name__ == "__main__":
    main()