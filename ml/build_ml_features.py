from pathlib import Path
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

LABELED_FILE = ROOT / "ml" / "labeled_training_dataset.csv"

RAW_DIR = (
    ROOT
    / "ml"
    / "data"
    / "historical_tle"
    / "raw"
)

OUTPUT_FILE = ROOT / "ml" / "ml_training_features.csv"


FEATURE_NAMES = [
    "prediction_horizon_hours",
    "inclination_deg",
    "eccentricity",
    "mean_motion_rev_day",
    "bstar",
    "mean_motion_derivative",
    "mean_motion_second_derivative",
]


def main():

    print("=" * 70)
    print("BUILDING ML FEATURE DATASET")
    print("=" * 70)

    # --------------------------------------------------------
    # Load labeled cases
    # --------------------------------------------------------

    labeled = pd.read_csv(LABELED_FILE)

    labeled["NORAD_CAT_ID"] = pd.to_numeric(
        labeled["NORAD_CAT_ID"],
        errors="coerce"
    )

    labeled["SOURCE_EPOCH"] = pd.to_datetime(
        labeled["SOURCE_EPOCH"],
        utc=True
    )

    print()
    print("Labeled cases:", len(labeled))

    # --------------------------------------------------------
    # Load raw historical records
    # --------------------------------------------------------

    raw_files = sorted(RAW_DIR.glob("*.csv"))

    print(
        "Raw historical files:",
        len(raw_files)
    )

    records = []

    for csv_file in raw_files:

        raw = pd.read_csv(csv_file)

        required = [
            "NORAD_CAT_ID",
            "EPOCH",
            "INCLINATION",
            "ECCENTRICITY",
            "MEAN_MOTION",
            "BSTAR",
            "MEAN_MOTION_DOT",
            "MEAN_MOTION_DDOT",
        ]

        missing = [
            column
            for column in required
            if column not in raw.columns
        ]

        if missing:
            print(
                f"Skipping {csv_file.name}: {missing}"
            )
            continue

        raw = raw[required].copy()

        raw["NORAD_CAT_ID"] = pd.to_numeric(
            raw["NORAD_CAT_ID"],
            errors="coerce"
        )

        raw["EPOCH"] = pd.to_datetime(
            raw["EPOCH"],
            utc=True
        )

        records.append(raw)

    if not records:
        raise RuntimeError(
            "No usable historical records found."
        )

    raw_all = pd.concat(
        records,
        ignore_index=True
    )

    print(
        "Raw source records loaded:",
        len(raw_all)
    )

    # --------------------------------------------------------
    # Convert orbital values to numeric
    # --------------------------------------------------------

    numeric_columns = [
        "INCLINATION",
        "ECCENTRICITY",
        "MEAN_MOTION",
        "BSTAR",
        "MEAN_MOTION_DOT",
        "MEAN_MOTION_DDOT",
    ]

    for column in numeric_columns:

        raw_all[column] = pd.to_numeric(
            raw_all[column],
            errors="coerce"
        )

    # --------------------------------------------------------
    # CRITICAL FIX
    #
    # There must be EXACTLY ONE raw record for every:
    #
    # NORAD_CAT_ID + EPOCH
    #
    # Your audit showed duplicated copies of the same record.
    # We keep only the first copy.
    # --------------------------------------------------------

    before = len(raw_all)

    raw_all = raw_all.drop_duplicates(
        subset=[
            "NORAD_CAT_ID",
            "EPOCH"
        ],
        keep="first"
    ).copy()

    removed = before - len(raw_all)

    print(
        "Duplicate source records removed:",
        removed
    )

    print(
        "Unique source records:",
        len(raw_all)
    )

    # --------------------------------------------------------
    # Rename epoch for merge
    # --------------------------------------------------------

    raw_all = raw_all.rename(
        columns={
            "EPOCH": "SOURCE_EPOCH"
        }
    )

    # --------------------------------------------------------
    # VERIFY uniqueness BEFORE merging
    # --------------------------------------------------------

    duplicate_keys = raw_all.duplicated(
        subset=[
            "NORAD_CAT_ID",
            "SOURCE_EPOCH"
        ]
    ).sum()

    if duplicate_keys != 0:

        raise RuntimeError(
            "Duplicate NORAD + SOURCE_EPOCH keys still exist."
        )

    print(
        "Duplicate merge keys remaining:",
        duplicate_keys
    )

    # --------------------------------------------------------
    # Merge
    # --------------------------------------------------------

    result = labeled.merge(
        raw_all,
        on=[
            "NORAD_CAT_ID",
            "SOURCE_EPOCH"
        ],
        how="left",
        validate="many_to_one"
    )

    # --------------------------------------------------------
    # Verify row count
    # --------------------------------------------------------

    print()
    print(
        "Rows after merge:",
        len(result)
    )

    if len(result) != len(labeled):

        raise RuntimeError(
            "MERGE CHANGED THE NUMBER OF TRAINING CASES. "
            "This must be investigated before training."
        )

    # --------------------------------------------------------
    # Verify matching
    # --------------------------------------------------------

    missing_features = result["INCLINATION"].isna().sum()

    print(
        "Cases NOT matched:",
        missing_features
    )

    if missing_features > 0:

        raise RuntimeError(
            f"{missing_features} cases have no source "
            "orbital features."
        )

    # --------------------------------------------------------
    # Build features
    # --------------------------------------------------------

    result["prediction_horizon_hours"] = pd.to_numeric(
        result["PREDICTION_HORIZON_HOURS"],
        errors="coerce"
    )

    result["inclination_deg"] = result["INCLINATION"]

    result["eccentricity"] = result["ECCENTRICITY"]

    result["mean_motion_rev_day"] = result["MEAN_MOTION"]

    result["bstar"] = result["BSTAR"]

    result["mean_motion_derivative"] = (
        result["MEAN_MOTION_DOT"]
    )

    result["mean_motion_second_derivative"] = (
        result["MEAN_MOTION_DDOT"]
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # PREDICTION_ERROR_KM is retained for analysis,
    # but is NOT included in FEATURE_NAMES.
    #
    # Therefore there is no target leakage.
    # --------------------------------------------------------

    output_columns = [
        "NORAD_CAT_ID",
        "SOURCE_EPOCH",
        "REFERENCE_EPOCH",
        "PREDICTION_ERROR_KM",
        "reliability_label",
        "reliability",
    ] + FEATURE_NAMES

    result = result[output_columns].copy()

    # --------------------------------------------------------
    # Remove invalid feature rows
    # --------------------------------------------------------

    result = result.replace(
        [np.inf, -np.inf],
        np.nan
    )

    before_clean = len(result)

    result = result.dropna(
        subset=FEATURE_NAMES + [
            "reliability_label"
        ]
    )

    rows_removed = (
        before_clean - len(result)
    )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    result = result.sort_values(
        [
            "NORAD_CAT_ID",
            "SOURCE_EPOCH"
        ]
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Final save
    # --------------------------------------------------------

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("ML FEATURE DATASET CREATED")
    print("=" * 70)

    print()
    print(
        "Final feature rows:",
        len(result)
    )

    print(
        "Rows removed:",
        rows_removed
    )

    print(
        "Unique objects:",
        result["NORAD_CAT_ID"].nunique()
    )

    print()
    print("FEATURES USED BY MODEL")
    print("-" * 70)

    for feature in FEATURE_NAMES:
        print(feature)

    print()
    print("CLASS DISTRIBUTION")
    print("-" * 70)

    print(
        result["reliability"]
        .value_counts()
        .to_string()
    )

    print()
    print("FEATURE PREVIEW")
    print("-" * 70)

    print(
        result[
            ["NORAD_CAT_ID"]
            + FEATURE_NAMES
            + ["reliability_label"]
        ]
        .head(10)
        .to_string(index=False)
    )

    print()
    print("Saved to:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()