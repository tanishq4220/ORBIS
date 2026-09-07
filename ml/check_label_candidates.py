from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    ROOT
    / "ml"
    / "training_dataset.csv"
)


def main():

    df = pd.read_csv(INPUT_FILE)

    error = df["PREDICTION_ERROR_KM"]

    print("=" * 70)
    print("RELIABILITY LABEL CANDIDATE ANALYSIS")
    print("=" * 70)

    print()
    print("Total cases:", len(df))
    print()

    # Candidate thresholds in km
    thresholds = [
        0.1,
        0.25,
        0.5,
        1.0,
        2.0,
        5.0,
        10.0,
        25.0,
        50.0,
        100.0
    ]

    print(
        f"{'Threshold (km)':<18}"
        f"{'Reliable':<12}"
        f"{'Not Reliable':<15}"
        f"{'Reliable %':<12}"
    )

    print("-" * 70)

    for threshold in thresholds:

        reliable = (error <= threshold).sum()
        not_reliable = (error > threshold).sum()

        reliable_percent = (
            reliable / len(df) * 100
        )

        print(
            f"{threshold:<18.2f}"
            f"{reliable:<12}"
            f"{not_reliable:<15}"
            f"{reliable_percent:<12.2f}"
        )

    print()
    print("ERROR PERCENTILES")
    print("-" * 70)

    percentiles = [
        50,
        60,
        70,
        75,
        80,
        85,
        90,
        95,
        97,
        98,
        99
    ]

    for percentile in percentiles:

        value = error.quantile(
            percentile / 100
        )

        print(
            f"{percentile:>2}th percentile: "
            f"{value:.6f} km"
        )

    print()
    print("=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()