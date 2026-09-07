import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from pathlib import Path

from prop import propagate_multiple


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

TIME_STEP_MINUTES = 10
TIME_WINDOW_MINUTES = 60

# Objects within this distance are flagged
SCREENING_THRESHOLD_KM = 50.0

# Show closest objects even if they are above threshold
TOP_RESULTS = 10


# --------------------------------------------------
# FIND DATASET
# --------------------------------------------------

current_folder = Path(__file__).resolve().parent

files = list(
    current_folder.parent.rglob("satellite_debris_tle*.xlsx")
)

if not files:
    print("ERROR: Excel file not found!")
    exit()

INPUT_FILE = files[0]

print("Excel found at:", INPUT_FILE)


# --------------------------------------------------
# LOAD DATASET
# --------------------------------------------------

df = pd.read_excel(INPUT_FILE)

print(f"Total objects loaded: {len(df)}")


# --------------------------------------------------
# SELECT TARGET OBJECT
# --------------------------------------------------

target_name = input(
    "\nEnter satellite/object name to screen: "
).strip()

matches = df[
    df["Name"].astype(str).str.contains(
        target_name,
        case=False,
        na=False
    )
]

if matches.empty:
    print("ERROR: Object not found.")
    exit()

target = matches.iloc[0]

print(f"\nSelected object: {target['Name']}")


target_tle1 = target["TLE Line 1"]
target_tle2 = target["TLE Line 2"]


# --------------------------------------------------
# CREATE PROPAGATION TIMES
# --------------------------------------------------

start_time = datetime.now(timezone.utc)

times = [
    start_time + timedelta(
        minutes=TIME_STEP_MINUTES * i
    )
    for i in range(
        (TIME_WINDOW_MINUTES // TIME_STEP_MINUTES) + 1
    )
]


# --------------------------------------------------
# PROPAGATE TARGET
# --------------------------------------------------

target_positions, _, target_errors = propagate_multiple(
    target_tle1,
    target_tle2,
    times
)

if not all(error == 0 for error in target_errors):
    print("ERROR: Target SGP4 propagation failed.")
    exit()


# --------------------------------------------------
# SCREEN ALL OTHER OBJECTS
# --------------------------------------------------

results = []

print("\nRunning conjunction screening...")
print("Please wait...")


for index, row in df.iterrows():

    # Skip selected object
    if index == target.name:
        continue

    name = row["Name"]

    tle1 = row["TLE Line 1"]
    tle2 = row["TLE Line 2"]

    try:

        positions, _, error_codes = propagate_multiple(
            tle1,
            tle2,
            times
        )

        # Skip failed propagations
        if not all(error == 0 for error in error_codes):
            continue


        # Calculate separation at every time
        distances = []

        for i in range(len(times)):

            target_position = np.array(
                target_positions[i]
            )

            object_position = np.array(
                positions[i]
            )

            distance = np.linalg.norm(
                target_position - object_position
            )

            distances.append(distance)


        # Minimum separation
        min_distance = min(distances)

        # Time of closest approach
        min_index = distances.index(min_distance)

        tca = times[min_index]


        results.append({
            "Object": name,
            "Min Distance (km)": min_distance,
            "TCA (UTC)": tca
        })


    except Exception:
        continue


# --------------------------------------------------
# SORT BY DISTANCE
# --------------------------------------------------

results.sort(
    key=lambda x: x["Min Distance (km)"]
)


# --------------------------------------------------
# DISPLAY RESULTS
# --------------------------------------------------

print("\n" + "=" * 70)
print("ORBIS CONJUNCTION SCREENING")
print("=" * 70)

print(f"Target Object: {target['Name']}")

print(
    f"Time Window: {TIME_WINDOW_MINUTES} minutes"
)

print(
    f"Time Step: {TIME_STEP_MINUTES} minutes"
)

print(
    f"Screening Threshold: "
    f"{SCREENING_THRESHOLD_KM} km"
)

print(
    f"Objects Successfully Screened: "
    f"{len(results)}"
)


# --------------------------------------------------
# CLOSEST OBJECTS
# --------------------------------------------------

print("\nCLOSEST APPROACHES:")
print("-" * 70)

for i, result in enumerate(
    results[:TOP_RESULTS],
    start=1
):

    distance = result["Min Distance (km)"]

    tca = result["TCA (UTC)"].strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    if distance <= SCREENING_THRESHOLD_KM:
        status = "POTENTIAL CONJUNCTION"
    else:
        status = "CLEAR"

    print(
        f"{i}. {result['Object']}"
    )

    print(
        f"   Minimum Distance : "
        f"{distance:.3f} km"
    )

    print(
        f"   TCA              : "
        f"{tca} UTC"
    )

    print(
        f"   Status           : "
        f"{status}"
    )

    print()


# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

potential = [
    r for r in results
    if r["Min Distance (km)"]
    <= SCREENING_THRESHOLD_KM
]

print("=" * 70)

print(
    f"Potential conjunctions: "
    f"{len(potential)}"
)

if potential:
    print(
        "WARNING: Objects crossed the "
        "prototype screening threshold."
    )
else:
    print(
        "No objects crossed the prototype "
        "screening threshold."
    )

print("=" * 70)