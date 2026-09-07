import pandas as pd
from datetime import datetime, timezone, timedelta
from pathlib import Path
from sys import path

from prop import propagate_multiple

# Access factors.py from ACI folder
path.append(str(Path(__file__).resolve().parent.parent / "ACI"))

from factors import calculate_trajectory_consistency


# Find Excel file
current_folder = Path(__file__).resolve().parent

files = list(
    current_folder.parent.rglob("satellite_debris_tle*.xlsx")
)

if not files:
    print("ERROR: Excel file not found!")
    exit()

INPUT_FILE = files[0]

print("Excel found at:", INPUT_FILE)


# Load dataset
df = pd.read_excel(INPUT_FILE)

# Take first satellite for testing
row = df.iloc[0]

name = row["Name"]
tle_line1 = row["TLE Line 1"]
tle_line2 = row["TLE Line 2"]


# Starting time
start_time = datetime.now(timezone.utc)

# Six points, 10 minutes apart
times = [
    start_time + timedelta(minutes=10 * i)
    for i in range(6)
]


# Propagate satellite
positions, velocities, error_codes = propagate_multiple(
    tle_line1,
    tle_line2,
    times
)


# Calculate trajectory consistency
consistency = calculate_trajectory_consistency(
    positions
)


# Display results
print("=" * 55)
print("TRAJECTORY CONSISTENCY TEST")
print("=" * 55)

print(f"Satellite: {name}")

print("\nPropagation results:")

for i in range(len(times)):

    print(
        f"T{i}: Position = "
        f"({positions[i][0]:.3f}, "
        f"{positions[i][1]:.3f}, "
        f"{positions[i][2]:.3f}) km"
    )

    print(
        f"    SGP4 Error Code = {error_codes[i]}"
    )


print("\nTrajectory Consistency:")
print(f"{consistency:.4f}")


if all(code == 0 for code in error_codes):
    print("\nSUCCESS: All SGP4 propagations worked!")
else:
    print("\nWARNING: One or more SGP4 propagations failed.")