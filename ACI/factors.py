import numpy as np
from datetime import datetime, timezone


# ============================================================
# FACTOR 1 — DATA AGE
# ============================================================

def calculate_data_age(epoch):
    """
    Calculate age of orbital data in days.

    Epoch is interpreted as UTC.
    """

    if epoch is None:
        return np.nan

    epoch = str(epoch).strip()
    epoch = epoch.replace(" UTC", "")

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]

    parsed_epoch = None

    for fmt in formats:
        try:
            parsed_epoch = datetime.strptime(
                epoch,
                fmt
            ).replace(
                tzinfo=timezone.utc
            )
            break

        except ValueError:
            continue

    if parsed_epoch is None:
        return np.nan

    current_time = datetime.now(
        timezone.utc
    )

    age_seconds = (
        current_time - parsed_epoch
    ).total_seconds()

    return max(
        age_seconds / 86400.0,
        0.0
    )


# ============================================================
# FACTOR 2 — PREDICTION ERROR
# ============================================================

def calculate_prediction_error(
    predicted_position,
    reference_position
):
    """
    Calculate 3D position error in km.

    Smaller error = better prediction reliability.
    """

    if (
        predicted_position is None
        or reference_position is None
    ):
        return np.nan

    try:

        predicted = np.asarray(
            predicted_position,
            dtype=float
        )

        reference = np.asarray(
            reference_position,
            dtype=float
        )

        if (
            predicted.shape != reference.shape
            or predicted.size == 0
        ):
            return np.nan

        return float(
            np.linalg.norm(
                predicted - reference
            )
        )

    except (TypeError, ValueError):

        return np.nan


# ============================================================
# FACTOR 3 — TRACK / TRAJECTORY CHANGE
# ============================================================

def calculate_track_change(positions):
    """
    Calculate average change in trajectory direction.

    positions:
        Multiple SGP4 positions.
        Each position should be [x, y, z] in km.

    Returns:
        Average direction change in degrees.

    Smaller direction changes generally indicate
    a smoother propagated trajectory.
    """

    if positions is None:
        return np.nan

    try:
        positions = np.asarray(
            positions,
            dtype=float
        )

    except (TypeError, ValueError):

        return np.nan

    if len(positions) < 3:
        return np.nan

    changes = []

    for i in range(
        1,
        len(positions) - 1
    ):

        vector_1 = (
            positions[i]
            - positions[i - 1]
        )

        vector_2 = (
            positions[i + 1]
            - positions[i]
        )

        norm_1 = np.linalg.norm(
            vector_1
        )

        norm_2 = np.linalg.norm(
            vector_2
        )

        if (
            norm_1 == 0
            or norm_2 == 0
        ):
            continue

        cosine_angle = (
            np.dot(
                vector_1,
                vector_2
            )
            /
            (norm_1 * norm_2)
        )

        cosine_angle = np.clip(
            cosine_angle,
            -1.0,
            1.0
        )

        angle = np.degrees(
            np.arccos(
                cosine_angle
            )
        )

        changes.append(
            angle
        )

    if not changes:
        return np.nan

    return float(
        np.mean(changes)
    )


def calculate_trajectory_consistency(
    positions
):
    """
    Convert trajectory direction changes
    into a 0–1 consistency score.

    Higher = more consistent.
    """

    if positions is None:
        return np.nan

    try:
        positions = np.asarray(
            positions,
            dtype=float
        )

    except (TypeError, ValueError):

        return np.nan

    if len(positions) < 3:
        return np.nan

    movement_vectors = np.diff(
        positions,
        axis=0
    )

    angles = []

    for i in range(
        len(movement_vectors) - 1
    ):

        v1 = movement_vectors[i]
        v2 = movement_vectors[i + 1]

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if (
            norm1 == 0
            or norm2 == 0
        ):
            continue

        cosine_angle = (
            np.dot(v1, v2)
            /
            (norm1 * norm2)
        )

        cosine_angle = np.clip(
            cosine_angle,
            -1.0,
            1.0
        )

        angle = np.degrees(
            np.arccos(
                cosine_angle
            )
        )

        angles.append(angle)

    if not angles:
        return np.nan

    average_turn_angle = np.mean(
        angles
    )

    consistency = (
        1.0
        - average_turn_angle / 180.0
    )

    return float(
        np.clip(
            consistency,
            0.0,
            1.0
        )
    )


# ============================================================
# FACTOR 4 — MODEL CONFIDENCE
# ============================================================

def get_model_confidence(
    model_package,
    features
):
    """
    Get calibrated P(Reliable) from the ORBIS
    Random Forest model package.

    Returns:
        Probability between 0 and 1.
    """

    if (
        model_package is None
        or features is None
    ):
        return np.nan

    try:

        model = model_package[
            "model"
        ]

        calibrator = model_package[
            "calibrator"
        ]

        probabilities = (
            model.predict_proba(
                features
            )
        )

        classes = list(
            model.classes_
        )

        if 1 not in classes:
            return np.nan

        reliable_index = (
            classes.index(1)
        )

        raw_probability = (
            probabilities[
                :,
                reliable_index
            ]
        )

        calibrated_probability = (
            calibrator.predict_proba(
                raw_probability.reshape(
                    -1,
                    1
                )
            )[:, 1]
        )

        return float(
            np.clip(
                calibrated_probability[0],
                0.0,
                1.0
            )
        )

    except (
        KeyError,
        AttributeError,
        TypeError,
        ValueError,
        IndexError
    ):

        return np.nan