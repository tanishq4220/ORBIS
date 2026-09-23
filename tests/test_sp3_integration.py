import sys
from pathlib import Path
import math
import numpy as np
import pandas as pd
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
ACI_DIR = BASE_DIR / "ACI"
sys.path.insert(0, str(ACI_DIR))

from sp3_integration import (
    load_sp3_reference,
    GPS_PRN_TO_NORAD,
    NORAD_TO_GPS_PRN,
    gmst_rad,
    calculate_sp3_prediction_errors
)

def test_load_sp3_reference():
    df = load_sp3_reference()
    assert not df.empty, "sp3_reference.csv should return a non-empty DataFrame"
    assert "PRN" in df.columns

def test_gps_prn_format():
    for prn, norad in GPS_PRN_TO_NORAD.items():
        assert prn.startswith("PG")
        assert NORAD_TO_GPS_PRN[norad] == prn

def test_gmst_calculation():
    dt = datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
    gmst = gmst_rad(dt)
    assert 0 <= gmst <= 2 * math.pi, "GMST should be in [0, 2π]"

def test_ecef_calculation():
    dt = datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
    gmst = gmst_rad(dt)
    
    x, y, z = 1000.0, 0.0, 500.0
    
    ecef_x = math.cos(gmst) * x + math.sin(gmst) * y
    ecef_y = -math.sin(gmst) * x + math.cos(gmst) * y
    ecef_z = z
    
    assert math.isclose(ecef_z, 500.0)
    r_teme = math.sqrt(x**2 + y**2 + z**2)
    r_ecef = math.sqrt(ecef_x**2 + ecef_y**2 + ecef_z**2)
    assert math.isclose(r_teme, r_ecef, rel_tol=1e-9)

def test_object_with_known_gps_norad_produces_numeric_error():
    tle1 = "1 62339U 24001A   26091.00000000  .00000000  00000-0  00000-0 0  9997"
    tle2 = "2 62339  55.0000 120.0000 0050000 250.0000 110.0000  2.00000000    13"
    
    df = pd.DataFrame([
        {
            "ID": "62339",
            "TLE Line 1": tle1,
            "TLE Line 2": tle2
        }
    ])
    
    errors = calculate_sp3_prediction_errors(df)
    assert not np.isnan(errors.iloc[0]), "Known GPS ID should not produce NaN prediction error"

def test_object_with_non_gps_norad_produces_nan():
    df = pd.DataFrame([
        {
            "ID": "99999",
            "TLE Line 1": "1 99999U 24001A   26091.00000000  .00000000  00000-0  00000-0 0  9997",
            "TLE Line 2": "2 99999  55.0000 120.0000 0050000 250.0000 110.0000 15.00000000    13"
        }
    ])
    
    errors = calculate_sp3_prediction_errors(df)
    assert np.isnan(errors.iloc[0]), "Non-GPS ID should produce NaN"

def test_fails_if_all_nan():
    excel_file = BASE_DIR / "ACI" / "satellite_debris_tle (2).xlsx"
    df = pd.read_excel(excel_file)
    errors = calculate_sp3_prediction_errors(df)
    
    assert not errors.isna().all(), "calculate_sp3_prediction_errors returned all NaN for the dataset."
