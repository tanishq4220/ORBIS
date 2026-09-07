"""Train the ORBIS Unit-4 model.

IMPORTANT: the current ORBIS package does not contain enough independent
historical/reference error labels to train a scientifically validated
supervised model. This script therefore creates a BOOTSTRAP prototype model
from physically motivated reliability labels. Replace the bootstrap labels
with real historical SGP4-vs-reference labels when those data are available.
"""
from pathlib import Path
import sys
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, classification_report

ROOT = Path(__file__).resolve().parents[1]
ACI = ROOT / "ACI"
sys.path.insert(0, str(ACI))
from engine import normalize_data_age
sys.path.insert(0, str(ROOT))
from ml.features import FEATURE_NAMES, build_feature_matrix

INPUT = ACI / "satellite_debris_tle (2).xlsx"
MODEL = Path(__file__).resolve().parent / "orbital_reliability_model.joblib"
META = Path(__file__).resolve().parent / "model_metadata.txt"


def make_bootstrap_label(frame):
    """Create a temporary reliability label for a runnable prototype.

    This is deliberately deterministic and documented; it is NOT claimed to
    be ground truth. The future production label should be based on measured
    SGP4/reference position error.
    """
    age_conf = np.clip(1.0 - frame["data_age_days"] / 7.0, 0, 1)
    track = frame["trajectory_consistency"].fillna(0.5).clip(0, 1)
    # Conservative bootstrap rule: a case is reliable when the combined
    # stability score is at least 0.65.
    score = 0.55 * age_conf + 0.45 * track
    return (score >= 0.65).astype(int)


def main():
    df = pd.read_excel(INPUT)
    features = pd.DataFrame(build_feature_matrix(df), columns=FEATURE_NAMES)
    features = features.replace([np.inf, -np.inf], np.nan)
    features = features.fillna(features.median(numeric_only=True)).fillna(0.0)
    y = make_bootstrap_label(features)

    if y.nunique() < 2:
        # Ensure a trainable prototype if a future dataset has nearly no
        # variation. Use the ranking of the bootstrap score for the split.
        score = 0.55 * np.clip(1 - features["data_age_days"] / 7, 0, 1) + 0.45 * features["trajectory_consistency"]
        cutoff = score.median()
        y = (score >= cutoff).astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        features, y, test_size=0.20, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, list(model.classes_).index(1)]
    accuracy = accuracy_score(y_test, pred)
    f1 = f1_score(y_test, pred, zero_division=0)
    auc = roc_auc_score(y_test, proba) if y_test.nunique() == 2 else float("nan")

    joblib.dump(model, MODEL)
    META.write_text(
        "ORBIS Unit 4 ML model\n"
        "Model: RandomForestClassifier\n"
        "Training labels: BOOTSTRAP PROTOTYPE, not independent ground truth.\n"
        "Production replacement: train against measured SGP4-vs-reference position error.\n"
        f"Rows: {len(df)}\nFeatures: {', '.join(FEATURE_NAMES)}\n"
        f"Accuracy: {accuracy:.4f}\nF1: {f1:.4f}\nROC-AUC: {auc:.4f}\n"
    )

    print("ML MODEL TRAINED")
    print("Rows:", len(df))
    print("Features:", FEATURE_NAMES)
    print(f"Accuracy: {accuracy:.4f}")
    print(f"F1: {f1:.4f}")
    print(f"ROC-AUC: {auc:.4f}")
    print("Saved:", MODEL)
    print("WARNING: bootstrap labels are a prototype; replace with historical reference-error labels for scientific validation.")

if __name__ == "__main__":
    main()
