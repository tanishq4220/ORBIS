import pandas as pd
import numpy as np
from sgp4.api import Satrec, jday
from astropy.time import Time
from astropy import units as u
from astropy.coordinates import TEME, ITRS, CartesianRepresentation


# --------------------------------------------------
# 1. Load SP3 reference data
# --------------------------------------------------

sp3 = pd.read_csv("sp3_reference.csv")

# Use G01 for our first prototype test
reference = sp3[sp3["PRN"] == "PG01"].iloc[0]

timestamp = reference["Timestamp"]

reference_position = np.array([
    reference["X_km"],
    reference["Y_km"],
    reference["Z_km"]
], dtype=float)

print("SP3 Reference")
print("-------------------------")
print("PRN:", reference["PRN"])
print("Timestamp:", timestamp)
print("X:", reference_position[0], "km")
print("Y:", reference_position[1], "km")
print("Z:", reference_position[2], "km")


# --------------------------------------------------
# 2. Load NORAD 62339 TLE from ORBIS Excel
# --------------------------------------------------

excel_file = r"ACI\satellite_debris_tle (2).xlsx"

df = pd.read_excel(excel_file)

satellite_row = df[
    df["ID"].astype(str).str.strip() == "62339"
].iloc[0]

tle1 = str(satellite_row["TLE Line 1"])
tle2 = str(satellite_row["TLE Line 2"])

print("\nSatellite")
print("-------------------------")
print("NORAD:", satellite_row["ID"])
print("Name:", satellite_row["Name"])
print("TLE Epoch:", satellite_row["Epoch"])


# --------------------------------------------------
# 3. Create SGP4 satellite
# --------------------------------------------------

satellite = Satrec.twoline2rv(tle1, tle2)


# --------------------------------------------------
# 4. Convert SP3 timestamp to Julian Date
# --------------------------------------------------

time = Time(timestamp, format="iso", scale="utc")

jd = time.jd1
fr = time.jd2


# --------------------------------------------------
# 5. Propagate using SGP4
# --------------------------------------------------

error, position_teme, velocity = satellite.sgp4(jd, fr)

if error != 0:
    raise RuntimeError(f"SGP4 failed with error code {error}")


print("\nSGP4 TEME Position")
print("-------------------------")
print("X:", position_teme[0], "km")
print("Y:", position_teme[1], "km")
print("Z:", position_teme[2], "km")


# --------------------------------------------------
# 6. Convert SGP4 TEME → ITRS
# --------------------------------------------------

teme = TEME(
    CartesianRepresentation(
        position_teme[0] * u.km,
        position_teme[1] * u.km,
        position_teme[2] * u.km
    ),
    obstime=time
)

itrs = teme.transform_to(ITRS(obstime=time))

predicted_position = itrs.cartesian.xyz.to_value(u.km)


print("\nSGP4 ITRS Position")
print("-------------------------")
print("X:", predicted_position[0], "km")
print("Y:", predicted_position[1], "km")
print("Z:", predicted_position[2], "km")


# --------------------------------------------------
# 7. Calculate Prediction Error
# --------------------------------------------------

difference = predicted_position - reference_position

prediction_error = np.linalg.norm(difference)


print("\nPrediction Error")
print("-------------------------")
print("Error:", prediction_error, "km")


# --------------------------------------------------
# 8. Calculate prototype Prediction Confidence
# --------------------------------------------------

MAX_ERROR_KM = 10.0

prediction_confidence = np.clip(
    1.0 - (prediction_error / MAX_ERROR_KM),
    0.0,
    1.0
)


print("Prediction Confidence:", prediction_confidence)