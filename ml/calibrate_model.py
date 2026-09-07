import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
)
from sklearn.linear_model import LogisticRegression


# =========================================================
# CONFIGURATION
# =========================================================

TRAIN_FILE = "ml_train.csv"
TEST_FILE = "ml_test.csv"

MODEL_FILE = "random_forest_calibrated.joblib"

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
print("MANUAL GROUPED PROBABILITY CALIBRATION")
print("=" * 70)

train_df = pd.read_csv(TRAIN_FILE)
test_df = pd.read_csv(TEST_FILE)

X_train = train_df[FEATURES].copy()
y_train = train_df[TARGET].copy()

X_test = test_df[FEATURES].copy()
y_test = test_df[TARGET].copy()

groups = train_df["NORAD_CAT_ID"].values


print("\nTraining cases:", len(train_df))
print("Training objects:", train_df["NORAD_CAT_ID"].nunique())

print("\nTesting cases:", len(test_df))
print("Testing objects:", test_df["NORAD_CAT_ID"].nunique())


# =========================================================
# VERIFY OBJECT SEPARATION
# =========================================================

train_objects = set(train_df["NORAD_CAT_ID"])
test_objects = set(test_df["NORAD_CAT_ID"])

overlap = train_objects.intersection(test_objects)

print("\n" + "=" * 70)
print("OBJECT LEAKAGE CHECK")
print("=" * 70)

print("Objects in both sets:", len(overlap))

if overlap:
    raise ValueError(
        "Object leakage detected."
    )

print("✅ No object leakage")


# =========================================================
# STEP 1
# GENERATE OUT-OF-FOLD PROBABILITIES
# =========================================================

print("\n" + "=" * 70)
print("GENERATING GROUPED OUT-OF-FOLD PROBABILITIES")
print("=" * 70)

cv = GroupKFold(n_splits=5)

oof_probability = np.zeros(
    len(X_train),
    dtype=float
)

fold_number = 0

for fold_train_idx, fold_valid_idx in cv.split(
    X_train,
    y_train,
    groups=groups
):

    fold_number += 1

    print(
        f"\nFold {fold_number}/5"
    )

    X_fold_train = X_train.iloc[
        fold_train_idx
    ]

    y_fold_train = y_train.iloc[
        fold_train_idx
    ]

    X_fold_valid = X_train.iloc[
        fold_valid_idx
    ]

    valid_groups = set(
        groups[fold_valid_idx]
    )

    train_groups = set(
        groups[fold_train_idx]
    )

    group_overlap = (
        train_groups.intersection(
            valid_groups
        )
    )

    if group_overlap:

        raise ValueError(
            f"Object leakage in calibration fold "
            f"{fold_number}"
        )

    print(
        f"Training objects: {len(train_groups)}"
    )

    print(
        f"Validation objects: {len(valid_groups)}"
    )

    model = RandomForestClassifier(
        n_estimators=400,
        max_depth=None,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    model.fit(
        X_fold_train,
        y_fold_train
    )

    class_index = list(
        model.classes_
    ).index(1)

    probabilities = model.predict_proba(
        X_fold_valid
    )[:, class_index]

    oof_probability[
        fold_valid_idx
    ] = probabilities

    print(
        f"Validation cases: "
        f"{len(fold_valid_idx)}"
    )


# =========================================================
# VERIFY OOF PROBABILITIES
# =========================================================

print("\n" + "=" * 70)
print("OUT-OF-FOLD PROBABILITY CHECK")
print("=" * 70)

print(
    "Minimum:",
    oof_probability.min()
)

print(
    "Maximum:",
    oof_probability.max()
)

if not np.all(
    np.isfinite(oof_probability)
):

    raise ValueError(
        "Invalid OOF probabilities detected."
    )

print(
    "Unassigned probabilities:",
    np.sum(oof_probability == 0)
)

print(
    "Note: zero can be a valid model probability, "
    "so this is only informational."
)

print(
    "\n✅ All training cases received an "
    "out-of-fold probability."
)


# =========================================================
# STEP 2
# FIT SIGMOID CALIBRATOR
# =========================================================

print("\n" + "=" * 70)
print("FITTING SIGMOID CALIBRATOR")
print("=" * 70)

# Logistic regression is used as a sigmoid calibrator.
# It receives ONLY out-of-fold probabilities.

calibrator = LogisticRegression(
    random_state=RANDOM_STATE
)

calibrator.fit(
    oof_probability.reshape(-1, 1),
    y_train
)

print(
    "✅ Sigmoid calibration fitted"
)


# =========================================================
# STEP 3
# TRAIN FINAL RANDOM FOREST
# =========================================================

print("\n" + "=" * 70)
print("TRAINING FINAL RANDOM FOREST")
print("=" * 70)

final_model = RandomForestClassifier(
    n_estimators=400,
    max_depth=None,
    min_samples_split=4,
    min_samples_leaf=2,
    class_weight="balanced",
    random_state=RANDOM_STATE,
    n_jobs=-1,
)

final_model.fit(
    X_train,
    y_train
)

print(
    "✅ Final Random Forest trained on "
    "all 76 training objects"
)


# =========================================================
# STEP 4
# RAW TEST PROBABILITIES
# =========================================================

print("\n" + "=" * 70)
print("GENERATING TEST PROBABILITIES")
print("=" * 70)

class_index = list(
    final_model.classes_
).index(1)

raw_test_probability = (
    final_model
    .predict_proba(X_test)[:, class_index]
)

print(
    "Raw probability range:"
)

print(
    f"Minimum: {raw_test_probability.min():.6f}"
)

print(
    f"Maximum: {raw_test_probability.max():.6f}"
)


# =========================================================
# STEP 5
# CALIBRATED TEST PROBABILITIES
# =========================================================

calibrated_probability = calibrator.predict_proba(
    raw_test_probability.reshape(-1, 1)
)[:, 1]

print(
    "\nCalibrated probability range:"
)

print(
    f"Minimum: {calibrated_probability.min():.6f}"
)

print(
    f"Maximum: {calibrated_probability.max():.6f}"
)


# =========================================================
# CLASSIFICATION
# =========================================================

y_pred = (
    calibrated_probability >= 0.5
).astype(int)


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
    calibrated_probability
)

pr_auc = average_precision_score(
    y_test,
    calibrated_probability
)

brier = brier_score_loss(
    y_test,
    calibrated_probability
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
print("CALIBRATED MODEL RESULTS")
print("=" * 70)

print(
    f"\nAccuracy:            {accuracy:.4f}"
)

print(
    f"Balanced Accuracy:   {balanced_accuracy:.4f}"
)

print(
    f"Precision:            {precision:.4f}"
)

print(
    f"Recall:               {recall:.4f}"
)

print(
    f"F1 Score:             {f1:.4f}"
)

print(
    f"ROC-AUC:              {roc_auc:.4f}"
)

print(
    f"PR-AUC:               {pr_auc:.4f}"
)

print(
    f"Brier Score:          {brier:.4f}"
)


# =========================================================
# CONFUSION MATRIX
# =========================================================

print("\n" + "=" * 70)
print("CONFUSION MATRIX")
print("=" * 70)

print(
    "\n                 Actual"
)

print(
    "              Not Rel   Reliable"
)

print(
    f"Pred Not Rel  {tn:7d}   {fp:7d}"
)

print(
    f"Pred Reliable {fn:7d}   {tp:7d}"
)

print("\nRaw matrix:")
print(cm)


# =========================================================
# PROBABILITY SUMMARY
# =========================================================

print("\n" + "=" * 70)
print("MODEL CONFIDENCE SUMMARY")
print("=" * 70)

probability_series = pd.Series(
    calibrated_probability
)

print(
    probability_series.describe()
    .to_string()
)

print(
    "\nFirst 20 calibrated Model Confidence values:"
)

for probability in calibrated_probability[:20]:

    print(
        f"  {probability:.6f}"
    )


# =========================================================
# SAVE MODEL PACKAGE
# =========================================================

model_package = {
    "model": final_model,
    "calibrator": calibrator,
    "features": FEATURES,
    "reliable_class": 1,
    "classification_threshold": 0.5,
    "calibration_method": "sigmoid",
    "random_state": RANDOM_STATE,
}

joblib.dump(
    model_package,
    MODEL_FILE
)


# =========================================================
# FINAL
# =========================================================

print("\n" + "=" * 70)
print("CALIBRATED MODEL SAVED")
print("=" * 70)

print(
    f"\nSaved to:\n{MODEL_FILE}"
)

print(
    "\nFinal ML output:"
)

print(
    "prediction = Reliable / Not Reliable"
)

print(
    "model_confidence = calibrated P(Reliable)"
)

print(
    "\nThe calibrated probability is the value "
    "intended for the ORBIS ACI Model Confidence factor."
)

print(
    "\n✅ CALIBRATED RANDOM FOREST COMPLETE"
)