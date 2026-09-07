import pandas as pd
from datetime import datetime, timezone

# Load debris dataset
df = pd.read_excel("satellite_debris_tle (1).xlsx")

# Convert Epoch to datetime
df["Epoch"] = pd.to_datetime(df["Epoch"], utc=True)

# Current UTC time
current_time = datetime.now(timezone.utc)

# Calculate Data Age in days
df["Data_Age_days"] = (
    current_time - df["Epoch"]
).dt.total_seconds() / 86400

# Show the results
print(df[["ID", "Name", "Epoch", "Data_Age_days"]])

# Save the updated dataset
df.to_csv("debris_with_data_age.csv", index=False)

print("\nDone!")
print("Saved as: debris_with_data_age.csv")