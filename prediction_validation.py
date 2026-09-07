import pandas as pd

SP3_FILE = "sp3_reference.csv"

df = pd.read_csv(SP3_FILE)

# Use only one satellite for the prototype
g01 = df[df["PRN"] == "PG01"].copy()

print("G01 reference records:")
print(g01.head(10).to_string(index=False))

print("\nNumber of G01 records:", len(g01))