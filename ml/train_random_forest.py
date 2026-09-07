import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    classification_report,
)


# =========================================================
# CONFIGURATION
# =========================================================

TRAIN_FILE = "ml_train.csv"
TEST_FILE = "ml_test.csv"

MODEL_FILE = "random_forest_reliability_model.joblib"

RANDOM_STATE = 42

FEATURES = [
    "prediction_horizon_hours",
    "inclination_deg",
    "eccentricity",
    "mean_motion_rev_day",
    "bstar",
    "mean_motion_derivative",
]

TARGET = "reliability_label"


# =========================================================
# LOAD DATA
# =========================================================

print("=" * 70)
print("RANDOM FOREST RELIABILITY MODEL")
print("=" * 70)

train_df = pd.read_csv(TRAIN_FILE)
test_df = pd.read_csv(TEST_FILE)

print("\nTraining data:")
print(f"Cases:   {len(train_df)}")
print(
    f"Objects: {train_df['NORAD_CAT_ID'].nunique()}"
)

print("\nTesting data:")
print(f"Cases:   {len(test_df)}")
print(
    f"Objects: {test_df['NORAD_CAT_ID'].nunique()}"
)


# =========================================================
# VERIFY OBJECT SEPARATION
# =========================================================

train_objects = set(
    train_df["NORAD_CAT_ID"].unique()
)

test_objects = set(
    test_df["NORAD_CAT_ID"].unique()
)

overlap = train_objects.intersection(
    test_objects
)

print("\n" + "=" * 70)
print("OBJECT LEAKAGE VERIFICATION")
print("=" * 70)

print(f"Training objects: {len(train_objects)}")
print(f"Testing objects:  {len(test_objects)}")
print(f"Overlap:          {len(overlap)}")

if len(overlap) != 0:

    print("\n❌ OBJECT LEAKAGE DETECTED")

    print(sorted(overlap))

    raise SystemExit(1)

print("\n✅ No object leakage")


# =========================================================
# PREPARE FEATURES AND TARGET
# =========================================================

X_train = train_df[FEATURES].copy()
y_train = train_df[TARGET].copy()

X_test = test_df[FEATURES].copy()
y_test = test_df[TARGET].copy()


# =========================================================
# CHECK DATA
# =========================================================

if X_train.isna().sum().sum() > 0:
    raise ValueError(
        "Missing values found in training features."
    )

if X_test.isna().sum().sum() > 0:
    raise ValueError(
        "Missing values found in testing features."
    )

if np.isinf(X_train.to_numpy()).sum() > 0:
    raise ValueError(
        "Infinite values found in training features."
    )

if np.isinf(X_test.to_numpy()).sum() > 0:
    raise ValueError(
        "Infinite values found in testing features."
    )


# =========================================================
# CLASS DISTRIBUTION
# =========================================================

print("\n" + "=" * 70)
print("TRAINING CLASS DISTRIBUTION")
print("=" * 70)

print(
    y_train.value_counts()
    .sort_index()
)

print("\nTesting class distribution:")

print(
    y_test.value_counts()
    .sort_index()
)


# =========================================================
# CREATE MODEL
# =========================================================

print("\n" + "=" * 70)
print("CREATING RANDOM FOREST")
print("=" * 70)

model = RandomForestClassifier(
    n_estimators=400,
    max_depth=None,
    min_samples_split=4,
    min_samples_leaf=2,
    class_weight="balanced",
    random_state=RANDOM_STATE,
    n_jobs=-1,
)

print("\nModel configuration:")
print(f"Trees:             {model.n_estimators}")
print(f"Class weighting:   {model.class_weight}")
print(f"Min samples split: {model.min_samples_split}")
print(f"Min samples leaf:  {model.min_samples_leaf}")


# =========================================================
# TRAIN
# =========================================================

print("\n" + "=" * 70)
print("TRAINING")
print("=" * 70)

model.fit(
    X_train,
    y_train
)

print("\n✅ Random Forest training completed")


# =========================================================
# PREDICTIONS
# =========================================================

print("\n" + "=" * 70)
print("GENERATING TEST PREDICTIONS")
print("=" * 70)

y_pred = model.predict(X_test)

# Find probability column corresponding to Reliable = 1
class_index = list(
    model.classes_
).index(1)

y_probability = model.predict_proba(
    X_test
)[:, class_index]

print("✅ Predictions generated")


# =========================================================
# METRICS
# =========================================================

accuracy = accuracy_score(
    y_test,
    y_pred
)

balanced_accuracy = balanced_accuracy_score(
    y_test,
    y_pred
)

precision = precision_score(
    y_test,
    y_pred,
    zero_division=0
)

recall = recall_score(
    y_test,
    y_pred,
    zero_division=0
)

f1 = f1_score(
    y_test,
    y_pred,
    zero_division=0
)

roc_auc = roc_auc_score(
    y_test,
    y_probability
)

pr_auc = average_precision_score(
    y_test,
    y_probability
)


# =========================================================
# CONFUSION MATRIX
# =========================================================

cm = confusion_matrix(
    y_test,
    y_pred,
    labels=[0, 1]
)

tn, fp, fn, tp = cm.ravel()


# =========================================================
# RESULTS
# =========================================================

print("\n" + "=" * 70)
print("RANDOM FOREST TEST RESULTS")
print("=" * 70)

print(f"\nAccuracy:           {accuracy:.4f}")
print(f"Balanced Accuracy:  {balanced_accuracy:.4f}")
print(f"Precision:          {precision:.4f}")
print(f"Recall:             {recall:.4f}")
print(f"F1 Score:           {f1:.4f}")
print(f"ROC-AUC:            {roc_auc:.4f}")
print(f"PR-AUC:             {pr_auc:.4f}")

print("\n" + "=" * 70)
print("CONFUSION MATRIX")
print("=" * 70)

print("\n                 Actual")
print("              Not Rel   Reliable")
print(
    f"Pred Not Rel  {tn:7d}   {fn:7d}"
)
print(
    f"Pred Reliable {fp:7d}   {tp:7d}"
)

print("\nRaw matrix:")
print(cm)


# =========================================================
# CLASSIFICATION REPORT
# =========================================================

print("\n" + "=" * 70)
print("CLASSIFICATION REPORT")
print("=" * 70)

print(
    classification_report(
        y_test,
        y_pred,
        target_names=[
            "Not Reliable",
            "Reliable"
        ],
        zero_division=0
    )
)


# =========================================================
# BASELINE COMPARISON
# =========================================================

baseline_accuracy = (
    y_test == 1
).mean()

improvement = (
    accuracy - baseline_accuracy
)

print("\n" + "=" * 70)
print("BASELINE COMPARISON")
print("=" * 70)

print(
    f"\nAlways-Reliable baseline: "
    f"{baseline_accuracy:.4f}"
)

print(
    f"Random Forest accuracy:    "
    f"{accuracy:.4f}"
)

print(
    f"Improvement:               "
    f"{improvement:+.4f}"
)

print(
    f"Improvement percentage:     "
    f"{improvement * 100:+.2f} percentage points"
)


# =========================================================
# FEATURE IMPORTANCE
# =========================================================

print("\n" + "=" * 70)
print("FEATURE IMPORTANCE")
print("=" * 70)

importance = pd.Series(
    model.feature_importances_,
    index=FEATURES
).sort_values(
    ascending=False
)

for feature, value in importance.items():

    print(
        f"{feature:35s} "
        f"{value:.6f}"
    )


# =========================================================
# SAVE MODEL
# =========================================================

joblib.dump(
    model,
    MODEL_FILE
)

print("\n" + "=" * 70)
print("MODEL SAVED")
print("=" * 70)

print(f"\nSaved to:")
print(MODEL_FILE)

print("\nImportant:")
print(
    "The probability produced by this model is NOT yet "
    "calibrated for ACI Model Confidence."
)

print(
    "Calibration will be performed only after we compare "
    "the model against other candidates."
)

print("\n✅ RANDOM FOREST BASELINE MODEL COMPLETE")