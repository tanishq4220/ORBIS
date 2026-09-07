from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    ROOT
    / "ml"
    / "training_dataset.csv"
)

OUTPUT_FILE = (
    ROOT
    / "ml"
    / "labeled_training_dataset.csv"
)


# Prototype operational threshold.
# This is NOT a universal orbital-accuracy limit.
RELIABILITY_THRESHOLD_KM = 5.0


def main():

    df = pd.read_csv(INPUT_FILE)

    # --------------------------------------------------------
    # Create reliability label
    #
    # 1 = Reliable
    # 0 = Not Reliable
    #
    # based on measured historical prediction error.
    # --------------------------------------------------------

    df["reliability_label"] = (
        df["PREDICTION_ERROR_KM"]
        <= RELIABILITY_THRESHOLD_KM
    ).astype(int)

    # Human-readable result
    df["reliability"] = df["reliability_label"].map({
        1: "Reliable",
        0: "Not Reliable"
    })

    # Save
    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    reliable = (
        df["reliability_label"] == 1
    ).sum()

    not_reliable = (
        df["reliability_label"] == 0
    ).sum()

    total = len(df)

    print("=" * 70)
    print("RELIABILITY LABEL DATASET CREATED")
    print("=" * 70)

    print()
    print(
        "Reliability threshold:",
        f"{RELIABILITY_THRESHOLD_KM:.1f} km"
    )

    print(
        "Total cases:",
        total
    )

    print(
        "Reliable:",
        reliable,
        f"({reliable / total * 100:.2f}%)"
    )

    print(
        "Not Reliable:",
        not_reliable,
        f"({not_reliable / total * 100:.2f}%)"
    )

    print()
    print("Label meaning:")
    print("1 = Reliable")
    print("0 = Not Reliable")

    print()
    print("Important:")
    print(
        "The 5 km threshold is a prototype operational "
        "assumption and is not a universal orbital limit."
    )

    print()
    print("Saved to:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()