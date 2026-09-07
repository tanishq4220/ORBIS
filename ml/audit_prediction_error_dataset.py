from pathlib import Path
import pandas as pd
import numpy as np


ROOT = Path(__file__).resolve().parents[1]

ERROR_FILE = (
    ROOT
    / "ml"
    / "prediction_error_dataset.csv"
)

OBJECT_FILE = (
    ROOT
    / "ml"
    / "data"
    / "historical_tle"
    / "training_objects.csv"
)


def main():

    df = pd.read_csv(ERROR_FILE)

    objects = pd.read_csv(OBJECT_FILE)

    print("=" * 70)
    print("PREDICTION ERROR DATA QUALITY AUDIT")
    print("=" * 70)

    # --------------------------------------------------------
    # Basic information
    # --------------------------------------------------------

    print()
    print("Prediction cases:", len(df))
    print(
        "Unique objects:",
        df["NORAD_CAT_ID"].nunique()
    )

    # --------------------------------------------------------
    # Add object type/name information
    # --------------------------------------------------------

    object_columns = [
        column
        for column in [
            "ID",
            "NORAD_CAT_ID",
            "Name",
            "OBJECT_NAME",
            "Type"
        ]
        if column in objects.columns
    ]

    print()
    print("Training object columns found:", object_columns)

    # Find the ID column
    id_column = None

    if "ID" in objects.columns:
        id_column = "ID"
    elif "NORAD_CAT_ID" in objects.columns:
        id_column = "NORAD_CAT_ID"

    if id_column is not None:

        objects[id_column] = pd.to_numeric(
            objects[id_column],
            errors="coerce"
        )

        df["NORAD_CAT_ID"] = pd.to_numeric(
            df["NORAD_CAT_ID"],
            errors="coerce"
        )

        merge_columns = [id_column]

        for column in ["Name", "OBJECT_NAME", "Type"]:
            if column in objects.columns:
                merge_columns.append(column)

        object_info = (
            objects[merge_columns]
            .drop_duplicates(subset=[id_column])
        )

        df = df.merge(
            object_info,
            left_on="NORAD_CAT_ID",
            right_on=id_column,
            how="left"
        )

    # --------------------------------------------------------
    # Horizon audit
    # --------------------------------------------------------

    horizon = df["PREDICTION_HORIZON_HOURS"]

    print()
    print("HORIZON AUDIT")
    print("-" * 70)

    print(
        "Cases < 1 hour:",
        int((horizon < 1).sum())
    )

    print(
        "Cases < 0.1 hour:",
        int((horizon < 0.1).sum())
    )

    print(
        "Cases > 72 hours:",
        int((horizon > 72).sum())
    )

    print(
        "Cases > 168 hours:",
        int((horizon > 168).sum())
    )

    print(
        "Cases > 30 days:",
        int((horizon > 24 * 30).sum())
    )

    print()
    print("LARGEST PREDICTION GAPS")
    print("-" * 70)

    largest_gaps = df.nlargest(
        20,
        "PREDICTION_HORIZON_HOURS"
    )

    for _, row in largest_gaps.iterrows():

        name = (
            row.get("Name")
            if pd.notna(row.get("Name"))
            else row.get("OBJECT_NAME", "")
        )

        object_type = row.get("Type", "")

        print(
            f"NORAD={int(row['NORAD_CAT_ID'])} | "
            f"Type={object_type} | "
            f"Name={name} | "
            f"Horizon={row['PREDICTION_HORIZON_HOURS']:.2f} h | "
            f"Error={row['PREDICTION_ERROR_KM']:.3f} km"
        )

    # --------------------------------------------------------
    # Extreme error audit
    # --------------------------------------------------------

    print()
    print("EXTREME ERROR CASES")
    print("-" * 70)

    extreme = df[
        df["PREDICTION_ERROR_KM"] >= 100
    ].sort_values(
        "PREDICTION_ERROR_KM",
        ascending=False
    )

    print(
        "Cases >= 100 km:",
        len(extreme)
    )

    print()

    for _, row in extreme.head(40).iterrows():

        name = (
            row.get("Name")
            if pd.notna(row.get("Name"))
            else row.get("OBJECT_NAME", "")
        )

        object_type = row.get("Type", "")

        print(
            f"NORAD={int(row['NORAD_CAT_ID'])} | "
            f"Type={object_type} | "
            f"Name={name} | "
            f"Error={row['PREDICTION_ERROR_KM']:.3f} km | "
            f"Horizon={row['PREDICTION_HORIZON_HOURS']:.2f} h"
        )

    # --------------------------------------------------------
    # Extreme short-horizon cases
    # --------------------------------------------------------

    print()
    print("LARGE ERRORS AT SHORT HORIZONS")
    print("-" * 70)

    short_large = df[
        (df["PREDICTION_HORIZON_HOURS"] <= 24)
        & (df["PREDICTION_ERROR_KM"] >= 100)
    ].sort_values(
        "PREDICTION_ERROR_KM",
        ascending=False
    )

    print(
        "Cases with horizon <= 24 h and error >= 100 km:",
        len(short_large)
    )

    print()

    for _, row in short_large.head(30).iterrows():

        name = (
            row.get("Name")
            if pd.notna(row.get("Name"))
            else row.get("OBJECT_NAME", "")
        )

        object_type = row.get("Type", "")

        print(
            f"NORAD={int(row['NORAD_CAT_ID'])} | "
            f"Type={object_type} | "
            f"Name={name} | "
            f"Error={row['PREDICTION_ERROR_KM']:.3f} km | "
            f"Horizon={row['PREDICTION_HORIZON_HOURS']:.2f} h"
        )

    # --------------------------------------------------------
    # Object-level extreme behavior
    # --------------------------------------------------------

    print()
    print("OBJECT-LEVEL ERROR SUMMARY")
    print("-" * 70)

    object_summary = (
        df.groupby("NORAD_CAT_ID")
        .agg(
            cases=(
                "PREDICTION_ERROR_KM",
                "size"
            ),
            median_error_km=(
                "PREDICTION_ERROR_KM",
                "median"
            ),
            mean_error_km=(
                "PREDICTION_ERROR_KM",
                "mean"
            ),
            maximum_error_km=(
                "PREDICTION_ERROR_KM",
                "max"
            ),
            median_horizon_hours=(
                "PREDICTION_HORIZON_HOURS",
                "median"
            )
        )
        .sort_values(
            "maximum_error_km",
            ascending=False
        )
    )

    print(
        object_summary.head(30).to_string()
    )

    print()
    print("=" * 70)
    print("AUDIT COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()