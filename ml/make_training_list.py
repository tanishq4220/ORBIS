from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "ACI" / "satellite_debris_tle (2).xlsx"
OUTPUT = ROOT / "ml" / "data" / "historical_tle" / "training_objects.csv"


def main():

    df = pd.read_excel(INPUT)

    # Select 50 satellites
    satellites = (
        df[df["Type"].str.strip().str.lower() == "satellite"]
        .sample(n=50, random_state=42)
    )

    # Select 50 debris objects
    debris = (
        df[df["Type"].str.strip().str.lower() == "debris"]
        .sample(n=50, random_state=42)
    )

    selected = pd.concat(
        [satellites, debris],
        ignore_index=True
    )

    # Keep the information needed for historical-data matching
    selected = selected[
        [
            "ID",
            "Name",
            "Type",
            "TLE Line 1",
            "TLE Line 2",
            "Epoch",
        ]
    ]

    selected.to_csv(OUTPUT, index=False)

    print("TRAINING OBJECT LIST CREATED")
    print("Total objects:", len(selected))
    print()
    print(selected["Type"].value_counts())
    print()
    print("Saved to:")
    print(OUTPUT)


if __name__ == "__main__":
    main()