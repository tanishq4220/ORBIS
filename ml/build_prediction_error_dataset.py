from pathlib import Path
import numpy as np
import pandas as pd
from sgp4 import omm
from sgp4.api import Satrec, jday


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = (
    ROOT
    / "ml"
    / "data"
    / "historical_tle"
    / "raw"
)

OUTPUT_FILE = (
    ROOT
    / "ml"
    / "prediction_error_dataset.csv"
)


# ============================================================
# CREATE SGP4 SATELLITE FROM ONE HISTORICAL OMM RECORD
# ============================================================

def make_satellite(row):
    fields = {
        key: value
        for key, value in row.items()
        if pd.notna(value)
    }

    # sgp4.omm.initialize() expects EPOCH as a string
    fields["EPOCH"] = pd.Timestamp(row["EPOCH"]).strftime(
        "%Y-%m-%dT%H:%M:%S.%f"
    )

    sat = Satrec()
    omm.initialize(sat, fields)

    return sat


# ============================================================
# PROPAGATE SGP4 TO A SPECIFIC UTC TIME
# ============================================================

def propagate_at_epoch(sat, epoch):
    epoch = pd.Timestamp(epoch).to_pydatetime()

    jd, fr = jday(
        epoch.year,
        epoch.month,
        epoch.day,
        epoch.hour,
        epoch.minute,
        epoch.second + epoch.microsecond * 1e-6
    )

    error, position, velocity = sat.sgp4(jd, fr)

    if error != 0:
        raise RuntimeError(
            f"SGP4 propagation failed with error code {error}"
        )

    return np.asarray(position, dtype=float)


# ============================================================
# PROCESS ONE OBJECT
# ============================================================

def process_file(csv_file):
    df = pd.read_csv(csv_file)

    if len(df) < 2:
        return []

    df["EPOCH"] = pd.to_datetime(
        df["EPOCH"],
        utc=True
    )

    df = (
        df
        .sort_values("EPOCH")
        .drop_duplicates(subset=["EPOCH"])
        .reset_index(drop=True)
    )

    results = []

    # --------------------------------------------------------
    # Use consecutive historical records:
    #
    # record i       = source orbital data
    # record i + 1   = later reference orbital data
    # --------------------------------------------------------

    for i in range(len(df) - 1):

        source = df.iloc[i]
        reference = df.iloc[i + 1]

        source_epoch = source["EPOCH"]
        reference_epoch = reference["EPOCH"]

        horizon_hours = (
            reference_epoch - source_epoch
        ).total_seconds() / 3600.0

        # Ignore invalid/non-positive intervals
        if horizon_hours <= 0:
            continue

        try:
            # Build SGP4 from the SOURCE record
            source_sat = make_satellite(source)

            # Predict where the source orbit says the object
            # should be at the later reference epoch.
            predicted_position = propagate_at_epoch(
                source_sat,
                reference_epoch
            )

            # Build SGP4 from the LATER reference record
            reference_sat = make_satellite(reference)

            # Calculate the reference position at its own epoch.
            reference_position = propagate_at_epoch(
                reference_sat,
                reference_epoch
            )

            # 3D Euclidean position error in km
            prediction_error_km = float(
                np.linalg.norm(
                    predicted_position - reference_position
                )
            )

            results.append({
                "NORAD_CAT_ID": int(source["NORAD_CAT_ID"]),
                "OBJECT_NAME": source["OBJECT_NAME"],
                "SOURCE_EPOCH": source_epoch,
                "REFERENCE_EPOCH": reference_epoch,
                "PREDICTION_HORIZON_HOURS": horizon_hours,
                "PREDICTION_ERROR_KM": prediction_error_km,
            })

        except Exception as exc:
            print(
                f"Skipped pair in {csv_file.name}, "
                f"row {i}: {exc}"
            )

    return results


# ============================================================
# MAIN
# ============================================================

def main():

    csv_files = sorted(
        RAW_DIR.glob("*.csv")
    )

    print("Historical CSV files found:", len(csv_files))
    print()

    all_results = []

    for index, csv_file in enumerate(csv_files, start=1):

        results = process_file(csv_file)

        all_results.extend(results)

        print(
            f"[{index:02d}/{len(csv_files)}] "
            f"{csv_file.name}: "
            f"{len(results)} prediction cases"
        )

    # --------------------------------------------------------
    # Create final dataframe
    # --------------------------------------------------------

    result_df = pd.DataFrame(all_results)

    if result_df.empty:
        raise RuntimeError(
            "No prediction-error records were generated."
        )

    # Sort for reproducibility
    result_df = result_df.sort_values(
        ["NORAD_CAT_ID", "SOURCE_EPOCH"]
    ).reset_index(drop=True)

    # Save
    result_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("PREDICTION ERROR DATASET CREATED")
    print("=" * 60)

    print("Objects processed:", result_df["NORAD_CAT_ID"].nunique())
    print("Prediction cases:", len(result_df))

    print(
        "Minimum error:",
        f"{result_df['PREDICTION_ERROR_KM'].min():.6f} km"
    )

    print(
        "Maximum error:",
        f"{result_df['PREDICTION_ERROR_KM'].max():.6f} km"
    )

    print(
        "Mean error:",
        f"{result_df['PREDICTION_ERROR_KM'].mean():.6f} km"
    )

    print(
        "Median error:",
        f"{result_df['PREDICTION_ERROR_KM'].median():.6f} km"
    )

    print(
        "Mean prediction horizon:",
        f"{result_df['PREDICTION_HORIZON_HOURS'].mean():.2f} hours"
    )

    print()
    print("Saved to:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()