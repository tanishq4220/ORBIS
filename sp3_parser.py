import csv
from pathlib import Path

SP3_FILE = next(Path(".").glob("*.sp3"))
OUTPUT_FILE = "sp3_reference.csv"

records = []
current_timestamp = None

with open(SP3_FILE, "r", encoding="utf-8", errors="ignore") as file:
    for line in file:

        # Epoch line
        if line.startswith("*"):
            parts = line.split()

            # Example:
            # *  2026  9  6  0  0  0.00000000
            if len(parts) >= 7:
                current_timestamp = (
                    f"{parts[1]}-{parts[2].zfill(2)}-{parts[3].zfill(2)} "
                    f"{parts[4].zfill(2)}:{parts[5].zfill(2)}:{parts[6]}"
                )

        # Position line
        elif line.startswith("PG") and current_timestamp is not None:
            parts = line.split()

            if len(parts) >= 5:
                prn = parts[0]

                x = float(parts[1])
                y = float(parts[2])
                z = float(parts[3])

                records.append([
                    prn,
                    current_timestamp,
                    x,
                    y,
                    z
                ])

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)

    writer.writerow([
        "PRN",
        "Timestamp",
        "X_km",
        "Y_km",
        "Z_km"
    ])

    writer.writerows(records)

print(f"SP3 file: {SP3_FILE.name}")
print(f"Records extracted: {len(records)}")
print(f"Output created: {OUTPUT_FILE}")

print("\nFirst 10 records:")
for record in records[:10]:
    print(record)