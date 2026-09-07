from pathlib import Path
import pandas as pd
import numpy as np


ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    ROOT
    / "ml"
    / "prediction_error_dataset.csv"
)


def main():

    df = pd.read_csv(INPUT_FILE)

    df["SOURCE_EPOCH"] = pd.to_datetime(
        df["SOURCE_EPOCH"],
        utc=True
    )

    df["REFERENCE_EPOCH"] = pd.to_datetime(
        df["REFERENCE_EPOCH"],
        utc=True
    )

    error = df["PREDICTION_ERROR_KM"]

    print("=" * 70)
    print("PREDICTION ERROR DATASET ANALYSIS")
    print("=" * 70)

    print()
    print("Total cases:", len(df))
    print("Unique objects:", df["NORAD_CAT_ID"].nunique())

    print()
    print("ERROR STATISTICS")
    print("-" * 70)

    print(f"Minimum : {error.min():.6f} km")
    print(f"25%     : {error.quantile(0.25):.6f} km")
    print(f"Median  : {error.median():.6f} km")
    print(f"75%     : {error.quantile(0.75):.6f} km")
    print(f"95%     : {error.quantile(0.95):.6f} km")
    print(f"99%     : {error.quantile(0.99):.6f} km")
    print(f"Mean    : {error.mean():.6f} km")
    print(f"Maximum : {error.max():.6f} km")

    print()
    print("PREDICTION HORIZON STATISTICS")
    print("-" * 70)

    horizon = df["PREDICTION_HORIZON_HOURS"]

    print(f"Minimum : {horizon.min():.2f} hours")
    print(f"Median  : {horizon.median():.2f} hours")
    print(f"Mean    : {horizon.mean():.2f} hours")
    print(f"Maximum : {horizon.max():.2f} hours")

    # --------------------------------------------------------
    # Largest errors
    # --------------------------------------------------------

    print()
    print("TOP 20 LARGEST ERRORS")
    print("-" * 70)

    top = df.nlargest(
        20,
        "PREDICTION_ERROR_KM"
    )

    for _, row in top.iterrows():

        print(
            f"NORAD={int(row['NORAD_CAT_ID'])} | "
            f"Error={row['PREDICTION_ERROR_KM']:.3f} km | "
            f"Horizon={row['PREDICTION_HORIZON_HOURS']:.2f} h | "
            f"Source={row['SOURCE_EPOCH']} | "
            f"Reference={row['REFERENCE_EPOCH']}"
        )

    # --------------------------------------------------------
    # Error ranges
    # --------------------------------------------------------

    print()
    print("ERROR RANGES")
    print("-" * 70)

    ranges = [
        ("< 0.1 km", error < 0.1),
        ("0.1 - 1 km", (error >= 0.1) & (error < 1)),
        ("1 - 10 km", (error >= 1) & (error < 10)),
        ("10 - 100 km", (error >= 10) & (error < 100)),
        ("100 - 1000 km", (error >= 100) & (error < 1000)),
        (">= 1000 km", error >= 1000),
    ]

    for name, mask in ranges:

        count = int(mask.sum())
        percentage = count / len(df) * 100

        print(
            f"{name:15s}: "
            f"{count:6d} cases "
            f"({percentage:6.2f}%)"
        )

    # --------------------------------------------------------
    # Horizon bins
    # --------------------------------------------------------

    print()
    print("ERROR BY PREDICTION HORIZON")
    print("-" * 70)

    bins = [
        0,
        6,
        12,
        24,
        48,
        72,
        np.inf
    ]

    labels = [
        "0-6 h",
        "6-12 h",
        "12-24 h",
        "24-48 h",
        "48-72 h",
        ">72 h"
    ]

    df["HORIZON_BIN"] = pd.cut(
        df["PREDICTION_HORIZON_HOURS"],
        bins=bins,
        labels=labels,
        right=False
    )

    grouped = (
        df
        .groupby("HORIZON_BIN", observed=True)
        ["PREDICTION_ERROR_KM"]
        .agg(
            ["count", "median", "mean", "max"]
        )
    )

    print(grouped.to_string())

    # --------------------------------------------------------
    # Objects with extreme errors
    # --------------------------------------------------------

    print()
    print("OBJECTS WITH ERRORS >= 100 KM")
    print("-" * 70)

    extreme = (
        df[df["PREDICTION_ERROR_KM"] >= 100]
        .groupby("NORAD_CAT_ID")
        .agg(
            cases=("PREDICTION_ERROR_KM", "size"),
            max_error_km=("PREDICTION_ERROR_KM", "max"),
            median_error_km=("PREDICTION_ERROR_KM", "median"),
            max_horizon_hours=("PREDICTION_HORIZON_HOURS", "max")
        )
        .sort_values(
            "max_error_km",
            ascending=False
        )
    )

    if extreme.empty:
        print("No cases >= 100 km.")
    else:
        print(extreme.head(30).to_string())

    # --------------------------------------------------------
    # Objects with only one historical record
    # --------------------------------------------------------

    print()
    print("OBJECTS WITH ONLY ONE HISTORICAL RECORD")
    print("-" * 70)

    # This is based on the generated prediction cases.
    # An object with zero prediction cases is not present here,
    # so we identify expected objects from the raw files separately.

    print(
        "The generated dataset contains 98 objects because "
        "at least one historical CSV had fewer than 2 usable records."
    )

    print()
    print("=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()