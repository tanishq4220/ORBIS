import pandas as pd
import numpy as np
from sklearn.model_selection import GroupShuffleSplit

INPUT_FILE = "ml_model_data.csv"

TRAIN_FILE = "ml_train.csv"
TEST_FILE = "ml_test.csv"

RANDOM_STATE = 42
TEST_SIZE = 0.20

FEATURES = [
    "prediction_horizon_hours",
    "inclination_deg",
    "eccentricity",
    "mean_motion_rev_day",
    "bstar",
    "mean_motion_derivative",
]

print("=" * 70)
print("CREATING OBJECT-WISE TRAIN / TEST SPLIT")
print("=" * 70)

# ---------------------------------------------------------
# Load dataset
# ---------------------------------------------------------

df = pd.read_csv(INPUT_FILE)

print(f"\nTotal cases: {len(df)}")
print(f"Total objects: {df['NORAD_CAT_ID'].nunique()}")

# ---------------------------------------------------------
# Basic checks
# ---------------------------------------------------------

if df["NORAD_CAT_ID"].isna().any():
    raise ValueError("NORAD_CAT_ID contains missing values.")

if df["reliability_label"].isna().any():
    raise ValueError("reliability_label contains missing values.")

# ---------------------------------------------------------
# Grouped split
# ---------------------------------------------------------

groups = df["NORAD_CAT_ID"]

splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
)

train_idx, test_idx = next(
    splitter.split(
        df,
        df["reliability_label"],
        groups=groups
    )
)

train_df = df.iloc[train_idx].copy()
test_df = df.iloc[test_idx].copy()

# ---------------------------------------------------------
# Object sets
# ---------------------------------------------------------

train_objects = set(
    train_df["NORAD_CAT_ID"].unique()
)

test_objects = set(
    test_df["NORAD_CAT_ID"].unique()
)

overlap = train_objects.intersection(test_objects)

# ---------------------------------------------------------
# Verify no object leakage
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("OBJECT LEAKAGE CHECK")
print("=" * 70)

print(f"Training objects: {len(train_objects)}")
print(f"Testing objects:  {len(test_objects)}")
print(f"Objects in both:  {len(overlap)}")

if len(overlap) > 0:
    print("\n❌ OBJECT LEAKAGE DETECTED")

    print("Overlapping objects:")
    print(sorted(overlap))

    raise SystemExit(1)

print("\n✅ No object appears in both training and testing")

# ---------------------------------------------------------
# Case counts
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("CASE DISTRIBUTION")
print("=" * 70)

print(f"Training cases: {len(train_df)}")
print(f"Testing cases:  {len(test_df)}")

print(
    f"Training percentage: "
    f"{len(train_df) / len(df) * 100:.2f}%"
)

print(
    f"Testing percentage: "
    f"{len(test_df) / len(df) * 100:.2f}%"
)

# ---------------------------------------------------------
# Class distribution
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("TRAINING CLASS DISTRIBUTION")
print("=" * 70)

print(
    train_df["reliability"]
    .value_counts()
)

print("\nTraining percentages:")

print(
    train_df["reliability"]
    .value_counts(normalize=True)
    .mul(100)
)

print("\n" + "=" * 70)
print("TESTING CLASS DISTRIBUTION")
print("=" * 70)

print(
    test_df["reliability"]
    .value_counts()
)

print("\nTesting percentages:")

print(
    test_df["reliability"]
    .value_counts(normalize=True)
    .mul(100)
)

# ---------------------------------------------------------
# Label availability
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("LABEL AVAILABILITY")
print("=" * 70)

train_classes = sorted(
    train_df["reliability_label"].unique()
)

test_classes = sorted(
    test_df["reliability_label"].unique()
)

print(f"Training labels: {train_classes}")
print(f"Testing labels:  {test_classes}")

if len(train_classes) < 2:
    print(
        "\n⚠️ WARNING: Training set contains only one class."
    )

if len(test_classes) < 2:
    print(
        "\n⚠️ WARNING: Testing set contains only one class."
    )

# ---------------------------------------------------------
# Object-level summary
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("OBJECT DISTRIBUTION")
print("=" * 70)

train_cases_per_object = (
    train_df
    .groupby("NORAD_CAT_ID")
    .size()
)

test_cases_per_object = (
    test_df
    .groupby("NORAD_CAT_ID")
    .size()
)

print("Training cases per object:")
print(
    train_cases_per_object.describe()
    .to_string()
)

print("\nTesting cases per object:")
print(
    test_cases_per_object.describe()
    .to_string()
)

# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

train_df.to_csv(
    TRAIN_FILE,
    index=False
)

test_df.to_csv(
    TEST_FILE,
    index=False
)

# ---------------------------------------------------------
# Final summary
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("OBJECT-WISE SPLIT CREATED")
print("=" * 70)

print(f"\nSaved training data:")
print(TRAIN_FILE)

print(f"\nSaved testing data:")
print(TEST_FILE)

print("\nFeatures available for training:")

for feature in FEATURES:
    print(f"  ✓ {feature}")

print("\n✅ READY FOR MODEL BASELINE")