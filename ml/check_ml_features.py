import pandas as pd
import numpy as np

FILE = "ml_training_features.csv"

print("=" * 70)
print("FINAL ML FEATURE QUALITY CHECK")
print("=" * 70)

df = pd.read_csv(FILE)

print(f"\nRows: {len(df)}")
print(f"Columns: {len(df.columns)}")
print(f"Unique objects: {df['NORAD_CAT_ID'].nunique()}")

# ---------------------------------------------------------
# 1. Required columns
# ---------------------------------------------------------

required_features = [
    "prediction_horizon_hours",
    "inclination_deg",
    "eccentricity",
    "mean_motion_rev_day",
    "bstar",
    "mean_motion_derivative",
    "mean_motion_second_derivative",
]

required_columns = required_features + [
    "NORAD_CAT_ID",
    "reliability_label",
    "reliability",
]

print("\n" + "=" * 70)
print("REQUIRED COLUMNS")
print("=" * 70)

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    print("❌ Missing columns:")
    for col in missing_columns:
        print(f"   {col}")
    raise SystemExit(1)

print("✅ All required columns present")

# ---------------------------------------------------------
# 2. Missing values
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("MISSING VALUES")
print("=" * 70)

missing = df[required_features].isna().sum()

print(missing)

if missing.sum() == 0:
    print("\n✅ No missing feature values")
else:
    print("\n⚠️ Missing feature values detected")

# ---------------------------------------------------------
# 3. Infinite values
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("INFINITE VALUES")
print("=" * 70)

numeric_features = df[required_features].apply(
    pd.to_numeric,
    errors="coerce"
)

infinite_count = np.isinf(numeric_features).sum()

print(infinite_count)

if infinite_count.sum() == 0:
    print("\n✅ No infinite values")
else:
    print("\n❌ Infinite values detected")

# ---------------------------------------------------------
# 4. Duplicate feature rows
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("DUPLICATE ROW CHECK")
print("=" * 70)

duplicates = df.duplicated().sum()

print(f"Duplicate rows: {duplicates}")

if duplicates == 0:
    print("✅ No duplicate rows")
else:
    print("⚠️ Duplicate rows detected")

# ---------------------------------------------------------
# 5. Feature statistics
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("FEATURE STATISTICS")
print("=" * 70)

print(
    df[required_features]
    .describe()
    .T
    .to_string()
)

# ---------------------------------------------------------
# 6. Class distribution
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("CLASS DISTRIBUTION")
print("=" * 70)

class_counts = df["reliability"].value_counts()

print(class_counts)

class_percent = (
    df["reliability"]
    .value_counts(normalize=True)
    .mul(100)
)

print("\nPercentages:")
print(class_percent)

# ---------------------------------------------------------
# 7. Label consistency
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("LABEL CONSISTENCY")
print("=" * 70)

expected_reliable = (
    df["reliability_label"] == 1
).sum()

expected_not_reliable = (
    df["reliability_label"] == 0
).sum()

actual_reliable = (
    df["reliability"] == "Reliable"
).sum()

actual_not_reliable = (
    df["reliability"] == "Not Reliable"
).sum()

print(
    f"Label 1: {expected_reliable}"
)
print(
    f"Reliable: {actual_reliable}"
)

print(
    f"Label 0: {expected_not_reliable}"
)
print(
    f"Not Reliable: {actual_not_reliable}"
)

if (
    expected_reliable == actual_reliable
    and
    expected_not_reliable == actual_not_reliable
):
    print("\n✅ Labels are consistent")
else:
    print("\n❌ Label inconsistency detected")

# ---------------------------------------------------------
# 8. Object-level class distribution
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("OBJECT-LEVEL CHECK")
print("=" * 70)

object_summary = (
    df.groupby("NORAD_CAT_ID")
    .agg(
        cases=("NORAD_CAT_ID", "size"),
        reliable=("reliability_label", "sum"),
        not_reliable=(
            "reliability_label",
            lambda x: (x == 0).sum()
        )
    )
)

print(
    f"Objects: {len(object_summary)}"
)

print("\nCases per object:")
print(
    object_summary["cases"]
    .describe()
    .to_string()
)

objects_with_both = (
    (
        (object_summary["reliable"] > 0)
        &
        (object_summary["not_reliable"] > 0)
    )
    .sum()
)

print(
    f"\nObjects containing both classes: "
    f"{objects_with_both}"
)

print(
    f"Objects containing only Reliable: "
    f"{(object_summary['not_reliable'] == 0).sum()}"
)

print(
    f"Objects containing only Not Reliable: "
    f"{(object_summary['reliable'] == 0).sum()}"
)

# ---------------------------------------------------------
# FINAL STATUS
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("FINAL STATUS")
print("=" * 70)

if (
    len(df) == 14826
    and
    missing.sum() == 0
    and
    infinite_count.sum() == 0
    and
    missing_columns == []
):
    print("✅ DATASET IS READY FOR MODEL TRAINING")
else:
    print("⚠️ DATASET NEEDS ATTENTION BEFORE TRAINING")