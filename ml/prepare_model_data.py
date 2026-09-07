import pandas as pd
import numpy as np

INPUT_FILE = "ml_training_features.csv"
OUTPUT_FILE = "ml_model_data.csv"

FEATURES = [
    "prediction_horizon_hours",
    "inclination_deg",
    "eccentricity",
    "mean_motion_rev_day",
    "bstar",
    "mean_motion_derivative",
]

REQUIRED_COLUMNS = FEATURES + [
    "NORAD_CAT_ID",
    "reliability_label",
    "reliability",
]


print("=" * 70)
print("PREPARING FINAL MODEL DATA")
print("=" * 70)

# ---------------------------------------------------------
# Load
# ---------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

print(f"\nInput rows: {len(df)}")

# ---------------------------------------------------------
# Check required columns
# ---------------------------------------------------------

missing = [
    col for col in REQUIRED_COLUMNS
    if col not in df.columns
]

if missing:
    print("\n❌ Missing columns:")
    for col in missing:
        print(f"   {col}")

    raise SystemExit(1)

print("✅ All required columns present")

# ---------------------------------------------------------
# Keep only required columns
# ---------------------------------------------------------

model_df = df[
    FEATURES
    + [
        "NORAD_CAT_ID",
        "reliability_label",
        "reliability",
    ]
].copy()

# ---------------------------------------------------------
# Numeric validation
# ---------------------------------------------------------

for feature in FEATURES:

    model_df[feature] = pd.to_numeric(
        model_df[feature],
        errors="coerce"
    )

# ---------------------------------------------------------
# Check missing / infinite
# ---------------------------------------------------------

missing_count = model_df[FEATURES].isna().sum().sum()

infinite_count = np.isinf(
    model_df[FEATURES].to_numpy()
).sum()

print(f"\nMissing feature values: {missing_count}")
print(f"Infinite feature values: {infinite_count}")

if missing_count > 0 or infinite_count > 0:
    print("\n❌ Invalid feature values detected")
    raise SystemExit(1)

print("✅ Feature values are valid")

# ---------------------------------------------------------
# Check duplicate rows
# ---------------------------------------------------------

duplicate_count = model_df.duplicated().sum()

print(f"\nDuplicate rows: {duplicate_count}")

if duplicate_count > 0:
    print("⚠️ Duplicate rows found")

# ---------------------------------------------------------
# Check label distribution
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("CLASS DISTRIBUTION")
print("=" * 70)

print(
    model_df["reliability"]
    .value_counts()
)

# ---------------------------------------------------------
# Check objects
# ---------------------------------------------------------

unique_objects = model_df["NORAD_CAT_ID"].nunique()

print(f"\nUnique objects: {unique_objects}")

# ---------------------------------------------------------
# Check feature variation
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("FEATURE VARIATION")
print("=" * 70)

for feature in FEATURES:

    unique_count = model_df[feature].nunique()

    print(
        f"{feature:35s} "
        f"unique values = {unique_count}"
    )

# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

model_df.to_csv(
    OUTPUT_FILE,
    index=False
)

# ---------------------------------------------------------
# Final summary
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("FINAL MODEL DATA CREATED")
print("=" * 70)

print(f"Rows: {len(model_df)}")
print(f"Columns: {len(model_df.columns)}")
print(f"Objects: {unique_objects}")

print("\nFeatures used:")

for feature in FEATURES:
    print(f"  ✓ {feature}")

print("\nExcluded:")
print("  ✗ mean_motion_second_derivative")
print("    Reason: all 19,933 historical values are exactly zero")

print(f"\nSaved to:")
print(OUTPUT_FILE)

print("\n✅ READY FOR OBJECT-WISE SPLITTING")