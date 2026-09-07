from pathlib import Path
import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

LABELED_FILE = (
    ROOT
    / "ml"
    / "labeled_training_dataset.csv"
)

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
    / "ml_training_features.csv"
)


# ============================================================
# FEATURES USED BY THE ML MODEL
# ============================================================

FEATURE_NAMES = [
    "prediction_horizon_hours",
    "inclination_deg",
    "eccentricity",
    "mean_motion_rev_day",
    "bstar",
    "mean_motion_derivative",
    "mean_motion_second_derivative",
]


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("BUILDING ML FEATURE DATASET")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. Load labeled prediction cases
    # --------------------------------------------------------

    labeled = pd.read_csv(
        LABELED_FILE
    )

    print()
    print(
        "Labeled cases:",
        len(labeled)
    )

    labeled["SOURCE_EPOCH"] = pd.to_datetime(
        labeled["SOURCE_EPOCH"],
        utc=True
    )

    labeled["NORAD_CAT_ID"] = pd.to_numeric(
        labeled["NORAD_CAT_ID"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # 2. Load all raw historical CelesTrak records
    # --------------------------------------------------------

    raw_files = sorted(
        RAW_DIR.glob("*.csv")
    )

    print(
        "Raw historical files:",
        len(raw_files)
    )

    source_records = []

    for csv_file in raw_files:

        try:

            raw = pd.read_csv(
                csv_file
            )

            required_columns = [
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
                for column in required_columns
                if column not in raw.columns
            ]

            if missing:

                print(
                    f"Skipping {csv_file.name}: "
                    f"missing columns {missing}"
                )

                continue

            raw["NORAD_CAT_ID"] = pd.to_numeric(
                raw["NORAD_CAT_ID"],
                errors="coerce"
            )

            raw["EPOCH"] = pd.to_datetime(
                raw["EPOCH"],
                utc=True
            )

            source_records.append(
                raw[required_columns].copy()
            )

        except Exception as exc:

            print(
                f"Could not read {csv_file.name}: {exc}"
            )

    if not source_records:

        raise RuntimeError(
            "No usable raw historical records found."
        )

    raw_all = pd.concat(
        source_records,
        ignore_index=True
    )

    print(
        "Raw source records loaded:",
        len(raw_all)
    )

    # --------------------------------------------------------
    # 3. Convert orbital parameters to numeric
    # --------------------------------------------------------

    orbital_columns = [
        "INCLINATION",
        "ECCENTRICITY",
        "MEAN_MOTION",
        "BSTAR",
        "MEAN_MOTION_DOT",
        "MEAN_MOTION_DDOT",
    ]

    for column in orbital_columns:

        raw_all[column] = pd.to_numeric(
            raw_all[column],
            errors="coerce"
        )

    # --------------------------------------------------------
    # 4. Remove duplicate raw orbital records
    #
    # Your audit showed that the raw files contain duplicate
    # copies of identical NORAD + epoch records.
    #
    # These duplicates must not multiply our training cases
    # during the merge.
    # --------------------------------------------------------

    before_dedup = len(raw_all)

    raw_all = raw_all.drop_duplicates(
        subset=[
            "NORAD_CAT_ID",
            "EPOCH",
            "INCLINATION",
            "ECCENTRICITY",
            "MEAN_MOTION",
            "BSTAR",
            "MEAN_MOTION_DOT",
            "MEAN_MOTION_DDOT",
        ]
    ).copy()

    duplicates_removed = (
        before_dedup - len(raw_all)
    )

    print(
        "Duplicate raw records removed:",
        duplicates_removed
    )

    print(
        "Unique raw source records:",
        len(raw_all)
    )

    # --------------------------------------------------------
    # 5. Rename EPOCH so it matches SOURCE_EPOCH
    # --------------------------------------------------------

    raw_all = raw_all.rename(
        columns={
            "EPOCH": "SOURCE_EPOCH"
        }
    )

    # --------------------------------------------------------
    # 6. Merge each labeled prediction case with the exact
    #    historical orbital record that produced the prediction.
    #
    #    Matching:
    #       NORAD_CAT_ID
    #       SOURCE_EPOCH
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
    # 7. Verify matching
    # --------------------------------------------------------

    matched = (
        result["INCLINATION"].notna().sum()
    )

    not_matched = (
        len(result) - matched
    )

    print()
    print(
        "Cases matched to source orbital records:",
        matched
    )

    print(
        "Cases NOT matched:",
        not_matched
    )

    if not_matched > 0:

        raise RuntimeError(
            f"{not_matched} prediction cases could not "
            "be matched to their source orbital records."
        )

    # --------------------------------------------------------
    # 8. Create ML features
    # --------------------------------------------------------

    result["prediction_horizon_hours"] = pd.to_numeric(
        result["PREDICTION_HORIZON_HOURS"],
        errors="coerce"
    )

    result["inclination_deg"] = (
        result["INCLINATION"]
    )

    result["eccentricity"] = (
        result["ECCENTRICITY"]
    )

    result["mean_motion_rev_day"] = (
        result["MEAN_MOTION"]
    )

    result["bstar"] = (
        result["BSTAR"]
    )

    result["mean_motion_derivative"] = (
        result["MEAN_MOTION_DOT"]
    )

    result["mean_motion_second_derivative"] = (
        result["MEAN_MOTION_DDOT"]
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # PREDICTION_ERROR_KM is NOT an ML feature.
    #
    # It was used to create reliability_label.
    # Giving it to the model would be target leakage.
    # --------------------------------------------------------

    # --------------------------------------------------------
    # 9. Select final columns
    # --------------------------------------------------------

    output_columns = [
        "NORAD_CAT_ID",
        "SOURCE_EPOCH",
        "REFERENCE_EPOCH",
        "PREDICTION_ERROR_KM",
        "reliability_label",
        "reliability",
    ] + FEATURE_NAMES

    result = result[
        output_columns
    ].copy()

    # --------------------------------------------------------
    # 10. Handle invalid feature values
    # --------------------------------------------------------

    result = result.replace(
        [np.inf, -np.inf],
        np.nan
    )

    before_cleaning = len(result)

    result = result.dropna(
        subset=FEATURE_NAMES + [
            "reliability_label"
        ]
    )

    rows_removed = (
        before_cleaning - len(result)
    )

    # --------------------------------------------------------
    # 11. Sort for reproducibility
    # --------------------------------------------------------

    result = result.sort_values(
        [
            "NORAD_CAT_ID",
            "SOURCE_EPOCH"
        ]
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # 12. Save final feature dataset
    # --------------------------------------------------------

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # 13. Final verification
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
            [
                "NORAD_CAT_ID"
            ]
            + FEATURE_NAMES
            + [
                "reliability_label"
            ]
        ]
        .head(10)
        .to_string(
            index=False
        )
    )

    print()
    print("Saved to:")
    print(OUTPUT_FILE)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()