import pandas as pd

TEST_FILE = "ml_test.csv"

print("=" * 70)
print("BASELINE MODEL EVALUATION")
print("=" * 70)

df = pd.read_csv(TEST_FILE)

y_true = df["reliability_label"]

# ---------------------------------------------------------
# Always predict Reliable
# ---------------------------------------------------------

baseline_prediction = 1

correct = (
    y_true == baseline_prediction
).sum()

total = len(y_true)

accuracy = correct / total

# ---------------------------------------------------------
# Confusion matrix manually
# ---------------------------------------------------------

true_positive = (
    (y_true == 1) &
    (y_true == baseline_prediction)
).sum()

true_negative = (
    (y_true == 0) &
    (y_true != baseline_prediction)
).sum()

false_positive = (
    (y_true == 0) &
    (y_true == baseline_prediction)
).sum()

false_negative = (
    (y_true == 1) &
    (y_true != baseline_prediction)
).sum()

print("\nTest cases:")
print(total)

print("\nActual classes:")
print(
    y_true.value_counts()
    .rename(index={
        0: "Not Reliable",
        1: "Reliable"
    })
)

print("\n" + "=" * 70)
print("ALWAYS-RELIABLE BASELINE")
print("=" * 70)

print(f"\nCorrect predictions: {correct}")
print(f"Total predictions:   {total}")
print(f"Accuracy:            {accuracy:.4f}")
print(f"Accuracy percentage:  {accuracy * 100:.2f}%")

print("\nConfusion matrix components:")
print(f"True Positive:  {true_positive}")
print(f"True Negative:  {true_negative}")
print(f"False Positive: {false_positive}")
print(f"False Negative: {false_negative}")

print("\nInterpretation:")
print(
    "This baseline predicts every case as Reliable."
)

print(
    "Any useful ML model should demonstrate meaningful "
    "improvement beyond this baseline, especially in "
    "detecting Not Reliable cases."
)

print("\n✅ BASELINE COMPLETE")