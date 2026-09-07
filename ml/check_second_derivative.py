import pandas as pd
import glob
import os

RAW_DIR = "data/historical_tle/raw"

print("=" * 70)
print("CHECKING MEAN MOTION SECOND DERIVATIVE")
print("=" * 70)

files = glob.glob(os.path.join(RAW_DIR, "*.csv"))

print(f"\nHistorical files: {len(files)}")

all_values = []

for file in files:

    try:
        df = pd.read_csv(file)

        if "MEAN_MOTION_DDOT" not in df.columns:
            print(f"⚠️ Missing column: {file}")
            continue

        values = pd.to_numeric(
            df["MEAN_MOTION_DDOT"],
            errors="coerce"
        )

        all_values.append(values)

    except Exception as e:
        print(f"❌ Error reading {file}")
        print(e)

values = pd.concat(all_values, ignore_index=True)

print("\n" + "=" * 70)
print("RAW HISTORICAL DATA")
print("=" * 70)

print(f"Total values: {len(values)}")
print(f"Missing values: {values.isna().sum()}")
print(f"Non-zero values: {(values != 0).sum()}")
print(f"Zero values: {(values == 0).sum()}")

print("\nStatistics:")
print(values.describe())

print("\n" + "=" * 70)
print("UNIQUE VALUES")
print("=" * 70)

unique_values = values.dropna().unique()

print(f"Number of unique values: {len(unique_values)}")

print("\nFirst 30 unique values:")

for value in unique_values[:30]:
    print(repr(value))

print("\n" + "=" * 70)
print("EXTREME VALUES")
print("=" * 70)

non_zero = values[
    values.notna() &
    (values != 0)
]

if len(non_zero) > 0:

    print(f"Non-zero count: {len(non_zero)}")
    print(f"Minimum non-zero: {non_zero.min()}")
    print(f"Maximum non-zero: {non_zero.max()}")

else:

    print("⚠️ ALL RAW VALUES ARE ZERO")

print("\n" + "=" * 70)
print("CONCLUSION")
print("=" * 70)

if len(non_zero) == 0:

    print(
        "The historical CelesTrak data contains only zero "
        "MEAN_MOTION_DDOT values."
    )

    print(
        "Therefore this feature has no information and should "
        "not be used by the ML model."
    )

else:

    print(
        "The historical data contains non-zero "
        "MEAN_MOTION_DDOT values."
    )

    print(
        "The feature extraction pipeline should be investigated "
        "before training."
    )