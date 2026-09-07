from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    ROOT
    / "ml"
    / "prediction_error_dataset.csv"
)

OUTPUT_FILE = (
    ROOT
    / "ml"
    / "training_dataset.csv"
)


def main():

    df = pd.read_csv(INPUT_FILE)

    original_count = len(df)

    # Remove extremely small time gaps that can behave like
    # near-duplicate observations.
    df = df[
        df["PREDICTION_HORIZON_HOURS"] > 0.1
    ].copy()

    # Keep the initial operational modeling window to 72 hours.
    df = df[
        df["PREDICTION_HORIZON_HOURS"] <= 72
    ].copy()

    # Remove invalid numerical values.
    df = df[
        df["PREDICTION_ERROR_KM"].notna()
        & df["PREDICTION_HORIZON_HOURS"].notna()
    ].copy()

    # Make sure errors and horizons are physically meaningful.
    df = df[
        df["PREDICTION_ERROR_KM"] >= 0
    ].copy()

    # Sort for reproducibility.
    df = df.sort_values(
        ["NORAD_CAT_ID", "SOURCE_EPOCH"]
    ).reset_index(drop=True)

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("=" * 70)
    print("TRAINING DATASET PREPARED")
    print("=" * 70)

    print()
    print("Original prediction cases:", original_count)

    print(
        "Removed horizon <= 0.1 h:",
        original_count
        - len(
            pd.read_csv(INPUT_FILE)
            .query("PREDICTION_HORIZON_HOURS <= 0.1")
        )
    )

    print(
        "Final training cases:",
        len(df)
    )

    print(
        "Unique objects:",
        df["NORAD_CAT_ID"].nunique()
    )

    print(
        "Minimum horizon:",
        f"{df['PREDICTION_HORIZON_HOURS'].min():.3f} hours"
    )

    print(
        "Maximum horizon:",
        f"{df['PREDICTION_HORIZON_HOURS'].max():.3f} hours"
    )

    print(
        "Median error:",
        f"{df['PREDICTION_ERROR_KM'].median():.6f} km"
    )

    print(
        "Mean error:",
        f"{df['PREDICTION_ERROR_KM'].mean():.6f} km"
    )

    print()
    print("Saved to:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()