from pathlib import Path
import numpy as np
import pandas as pd
from sgp4 import omm
from sgp4.api import Satrec, jday


ROOT = Path(__file__).resolve().parents[1]

CSV_FILE = (
    ROOT
    / "ml"
    / "data"
    / "historical_tle"
    / "raw"
    / "sat000027168.csv"
)


def make_satellite(row):
    fields = {
        key: value
        for key, value in row.items()
        if pd.notna(value)
    }

    # OMM requires EPOCH as a string
    fields["EPOCH"] = pd.Timestamp(row["EPOCH"]).strftime(
        "%Y-%m-%dT%H:%M:%S.%f"
    )

    sat = Satrec()
    omm.initialize(sat, fields)

    return sat


def propagate_at_epoch(sat, epoch):
    epoch = pd.Timestamp(epoch).to_pydatetime()

    jd, fr = jday(
        epoch.year,
        epoch.month,
        epoch.day,
        epoch.hour,
        epoch.minute,
        epoch.second + epoch.microsecond * 1e-6
    )

    error, position, velocity = sat.sgp4(jd, fr)

    if error != 0:
        raise RuntimeError(
            f"SGP4 propagation failed with error code {error}"
        )

    return np.asarray(position, dtype=float)


def main():
    # Load historical data
    df = pd.read_csv(CSV_FILE)

    # Convert epoch column to datetime
    df["EPOCH"] = pd.to_datetime(df["EPOCH"], utc=True)

    # Sort chronologically
    df = df.sort_values("EPOCH").reset_index(drop=True)

    print("Object:", df["NORAD_CAT_ID"].iloc[0])
    print("Records:", len(df))
    print("First epoch:", df["EPOCH"].iloc[0])
    print("Last epoch:", df["EPOCH"].iloc[-1])
    print()

    # Use first record as prediction source
    source = df.iloc[0]

    # Use second record as later reference
    reference = df.iloc[1]

    source_epoch = source["EPOCH"]
    reference_epoch = reference["EPOCH"]

    horizon_hours = (
        reference_epoch - source_epoch
    ).total_seconds() / 3600.0

    print("Source epoch:", source_epoch)
    print("Reference epoch:", reference_epoch)
    print(f"Prediction horizon: {horizon_hours:.2f} hours")
    print()

    # Build SGP4 model from source record
    source_sat = make_satellite(source)

    # Predict source orbit at the later reference time
    predicted_position = propagate_at_epoch(
        source_sat,
        reference_epoch
    )

    # Build SGP4 model from later reference record
    reference_sat = make_satellite(reference)

    # Calculate reference position at its own epoch
    reference_position = propagate_at_epoch(
        reference_sat,
        reference_epoch
    )

    # Calculate 3D Euclidean position error
    error_km = float(
        np.linalg.norm(
            predicted_position - reference_position
        )
    )

    print("Predicted position [km]:")
    print(predicted_position)

    print()

    print("Reference position [km]:")
    print(reference_position)

    print()

    print(
        f"Historical SGP4 prediction error: "
        f"{error_km:.6f} km"
    )


if __name__ == "__main__":
    main()