"""Unit tests for ORBIS 3D globe coordinate mapping.

Verifies the mathematical convention between geographic / ECEF coordinates
and Three.js unit sphere globe_xyz coordinates:
  - Latitude 0°, Longitude 0°: +X
  - Latitude 0°, Longitude +90° (East): -Z
  - Latitude 0°, Longitude -90° (West): +Z
  - Latitude +90° (North pole): +Y
  - Latitude -90° (South pole): -Y

Also verifies that physical ECEF values remain completely untouched.
"""

import math
import numpy as np
import pytest

from propagate import EARTH_RADIUS_KM, ecef_to_globe_xyz, state_payload, teme_to_ecef
from datetime import datetime, timezone


def test_lat0_lon0_maps_to_positive_x():
    # Greenwich meridian on equator: ECEF is (R, 0, 0)
    pos_ecef = np.array([EARTH_RADIUS_KM, 0.0, 0.0], dtype=float)
    x, y, z = ecef_to_globe_xyz(pos_ecef, radius=1.0)
    assert abs(x - 1.0) < 1e-6, f"Expected x=+1.0, got {x}"
    assert abs(y) < 1e-6, f"Expected y=0.0, got {y}"
    assert abs(z) < 1e-6, f"Expected z=0.0, got {z}"


def test_lat0_lon90e_maps_to_negative_z():
    # 90° East on equator: ECEF is (0, R, 0)
    pos_ecef = np.array([0.0, EARTH_RADIUS_KM, 0.0], dtype=float)
    x, y, z = ecef_to_globe_xyz(pos_ecef, radius=1.0)
    assert abs(x) < 1e-6, f"Expected x=0.0, got {x}"
    assert abs(y) < 1e-6, f"Expected y=0.0, got {y}"
    assert abs(z - (-1.0)) < 1e-6, f"Expected z=-1.0 (-Z), got {z}"


def test_lat0_lon90w_maps_to_positive_z():
    # 90° West (-90° lon) on equator: ECEF is (0, -R, 0)
    pos_ecef = np.array([0.0, -EARTH_RADIUS_KM, 0.0], dtype=float)
    x, y, z = ecef_to_globe_xyz(pos_ecef, radius=1.0)
    assert abs(x) < 1e-6, f"Expected x=0.0, got {x}"
    assert abs(y) < 1e-6, f"Expected y=0.0, got {y}"
    assert abs(z - 1.0) < 1e-6, f"Expected z=+1.0 (+Z), got {z}"


def test_lat90n_maps_to_positive_y():
    # North pole: ECEF is (0, 0, R)
    pos_ecef = np.array([0.0, 0.0, EARTH_RADIUS_KM], dtype=float)
    x, y, z = ecef_to_globe_xyz(pos_ecef, radius=1.0)
    assert abs(x) < 1e-6, f"Expected x=0.0, got {x}"
    assert abs(y - 1.0) < 1e-6, f"Expected y=+1.0 (+Y), got {y}"
    assert abs(z) < 1e-6, f"Expected z=0.0, got {z}"


def test_lat90s_maps_to_negative_y():
    # South pole: ECEF is (0, 0, -R)
    pos_ecef = np.array([0.0, 0.0, -EARTH_RADIUS_KM], dtype=float)
    x, y, z = ecef_to_globe_xyz(pos_ecef, radius=1.0)
    assert abs(x) < 1e-6, f"Expected x=0.0, got {x}"
    assert abs(y - (-1.0)) < 1e-6, f"Expected y=-1.0 (-Y), got {y}"
    assert abs(z) < 1e-6, f"Expected z=0.0, got {z}"


def test_altitude_scaling():
    # Object at 1000 km altitude at lat 0, lon 0
    alt_km = 1000.0
    pos_ecef = np.array([EARTH_RADIUS_KM + alt_km, 0.0, 0.0], dtype=float)
    x, y, z = ecef_to_globe_xyz(pos_ecef, radius=1.0)
    expected_scale = 1.0 + (alt_km / EARTH_RADIUS_KM)
    assert abs(x - expected_scale) < 1e-6
    assert abs(y) < 1e-6
    assert abs(z) < 1e-6


def test_state_payload_physical_ecef_preserved():
    # Verify that physical ECEF coordinates are untouched in state_payload
    dt = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    pos_teme = np.array([7000.0, 0.0, 0.0], dtype=float)
    vel_teme = np.array([0.0, 7.5, 0.0], dtype=float)

    payload = state_payload(pos_teme, vel_teme, dt, 0)
    assert payload["sgp4_status"] == "OK"

    # Physical ECEF must match TEME -> ECEF exactly
    expected_ecef = teme_to_ecef(pos_teme, dt)
    assert abs(payload["position_ecef_km"]["x"] - expected_ecef[0]) < 1e-9
    assert abs(payload["position_ecef_km"]["y"] - expected_ecef[1]) < 1e-9
    assert abs(payload["position_ecef_km"]["z"] - expected_ecef[2]) < 1e-9

    # globe_xyz is present and separate
    assert "globe_xyz" in payload
    g = payload["globe_xyz"]
    assert "x" in g and "y" in g and "z" in g
