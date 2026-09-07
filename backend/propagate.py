"""SGP4 propagation and coordinate transforms for ORBIS."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import numpy as np
from sgp4.api import Satrec, jday

EARTH_RADIUS_KM = 6371.0


def parse_utc(value: Optional[str] = None) -> datetime:
    if value is None or value == "" or value.lower() == "now":
        return datetime.now(timezone.utc)
    text = value.strip().replace("Z", "+00:00")
    if text.endswith(" UTC"):
        text = text[:-4] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _jd_fr(dt: datetime) -> tuple[float, float]:
    return jday(
        dt.year,
        dt.month,
        dt.day,
        dt.hour,
        dt.minute,
        dt.second + dt.microsecond / 1_000_000.0,
    )


def make_satrec(tle1: str, tle2: str) -> Satrec:
    return Satrec.twoline2rv(str(tle1).strip(), str(tle2).strip())


def propagate_sat(
    sat: Satrec, dt: datetime
) -> tuple[Optional[np.ndarray], Optional[np.ndarray], int]:
    jd, fr = _jd_fr(dt)
    err, pos, vel = sat.sgp4(jd, fr)
    if err != 0:
        return None, None, int(err)
    return np.array(pos, dtype=float), np.array(vel, dtype=float), 0


def propagate_tle(
    tle1: str, tle2: str, dt: Optional[datetime] = None
) -> tuple[Optional[np.ndarray], Optional[np.ndarray], int]:
    if dt is None:
        dt = datetime.now(timezone.utc)
    try:
        sat = make_satrec(tle1, tle2)
    except Exception:  # noqa: BLE001
        return None, None, -1
    return propagate_sat(sat, dt)


def gmst_rad(dt: datetime) -> float:
    """Greenwich Mean Sidereal Time (radians) — TEME/PEF rotation."""
    jd, fr = _jd_fr(dt)
    jd_full = jd + fr
    t = (jd_full - 2451545.0) / 36525.0
    gmst_deg = (
        280.46061837
        + 360.98564736629 * (jd_full - 2451545.0)
        + 0.000387933 * t * t
        - (t * t * t) / 38710000.0
    )
    return np.deg2rad(gmst_deg % 360.0)


def teme_to_ecef(pos_teme: np.ndarray, dt: datetime) -> np.ndarray:
    theta = gmst_rad(dt)
    c, s = np.cos(theta), np.sin(theta)
    x, y, z = pos_teme
    return np.array([c * x + s * y, -s * x + c * y, z], dtype=float)


def ecef_to_geodetic(pos_ecef: np.ndarray) -> tuple[float, float, float]:
    x, y, z = pos_ecef
    r = float(np.linalg.norm(pos_ecef))
    lat = float(np.degrees(np.arcsin(np.clip(z / r, -1.0, 1.0))))
    lon = float(np.degrees(np.arctan2(y, x)))
    alt = r - EARTH_RADIUS_KM
    return lat, lon, alt


def ecef_to_globe_xyz(
    pos_ecef: np.ndarray, radius: float = 1.0
) -> tuple[float, float, float]:
    """Map ECEF km to Three.js unit sphere (Y-up, +X lon0-ish)."""
    lat, lon, alt = ecef_to_geodetic(pos_ecef)
    scale = radius * (1.0 + max(alt, 0.0) / EARTH_RADIUS_KM)
    lat_r = np.deg2rad(lat)
    lon_r = np.deg2rad(lon)
    x = scale * np.cos(lat_r) * np.cos(lon_r)
    z = scale * np.cos(lat_r) * np.sin(lon_r)
    y = scale * np.sin(lat_r)
    return float(x), float(y), float(z)


def state_payload(
    pos_teme: Optional[np.ndarray],
    vel_teme: Optional[np.ndarray],
    dt: datetime,
    error_code: int,
) -> dict[str, Any]:
    if pos_teme is None or vel_teme is None or error_code != 0:
        return {
            "utc": dt.isoformat().replace("+00:00", "Z"),
            "sgp4_status": "ERROR" if error_code else "UNAVAILABLE",
            "sgp4_error_code": error_code,
            "position_teme_km": None,
            "velocity_teme_km_s": None,
            "position_ecef_km": None,
            "latitude_deg": None,
            "longitude_deg": None,
            "altitude_km": None,
            "speed_km_s": None,
            "globe_xyz": None,
        }

    ecef = teme_to_ecef(pos_teme, dt)
    lat, lon, alt = ecef_to_geodetic(ecef)
    gx, gy, gz = ecef_to_globe_xyz(ecef)
    return {
        "utc": dt.isoformat().replace("+00:00", "Z"),
        "sgp4_status": "OK",
        "sgp4_error_code": 0,
        "position_teme_km": {
            "x": float(pos_teme[0]),
            "y": float(pos_teme[1]),
            "z": float(pos_teme[2]),
        },
        "velocity_teme_km_s": {
            "vx": float(vel_teme[0]),
            "vy": float(vel_teme[1]),
            "vz": float(vel_teme[2]),
        },
        "position_ecef_km": {
            "x": float(ecef[0]),
            "y": float(ecef[1]),
            "z": float(ecef[2]),
        },
        "latitude_deg": lat,
        "longitude_deg": lon,
        "altitude_km": alt,
        "speed_km_s": float(np.linalg.norm(vel_teme)),
        "globe_xyz": {"x": gx, "y": gy, "z": gz},
    }


def build_satrec_cache(df) -> list[Optional[Satrec]]:
    cache: list[Optional[Satrec]] = []
    for _, row in df.iterrows():
        tle1 = row.get("TLE Line 1")
        tle2 = row.get("TLE Line 2")
        try:
            if tle1 is None or tle2 is None or (isinstance(tle1, float) and np.isnan(tle1)):
                cache.append(None)
                continue
            cache.append(make_satrec(str(tle1), str(tle2)))
        except Exception:  # noqa: BLE001
            cache.append(None)
    return cache


def propagate_all_globe(
    satrecs: list[Optional[Satrec]],
    types: list[str],
    ids: list[str],
    dt: datetime,
) -> dict[str, Any]:
    n = len(satrecs)
    positions = np.zeros((n, 3), dtype=np.float32)
    valid = np.zeros(n, dtype=np.uint8)
    type_codes = np.zeros(n, dtype=np.uint8)  # 0 sat, 1 debris, 2 other

    for i, sat in enumerate(satrecs):
        t = (types[i] or "").lower()
        if "debris" in t:
            type_codes[i] = 1
        elif "sat" in t:
            type_codes[i] = 0
        else:
            type_codes[i] = 2

        if sat is None:
            continue
        pos, _, err = propagate_sat(sat, dt)
        if pos is None or err != 0:
            continue
        ecef = teme_to_ecef(pos, dt)
        gx, gy, gz = ecef_to_globe_xyz(ecef)
        positions[i] = (gx, gy, gz)
        valid[i] = 1

    return {
        "utc": dt.isoformat().replace("+00:00", "Z"),
        "count": n,
        "ids": ids,
        "positions": positions.reshape(-1).tolist(),
        "valid": valid.tolist(),
        "type_codes": type_codes.tolist(),
    }


def trajectory_samples(
    tle1: str,
    tle2: str,
    start: datetime,
    hours: float = 1.5,
    step_minutes: float = 2.0,
) -> dict[str, Any]:
    try:
        sat = make_satrec(tle1, tle2)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "NOT_CALCULATED",
            "error": str(exc),
            "samples": [],
        }

    steps = max(2, int((hours * 60.0) / step_minutes) + 1)
    samples = []
    for i in range(steps):
        dt = start + timedelta(minutes=step_minutes * i)
        pos, vel, err = propagate_sat(sat, dt)
        payload = state_payload(pos, vel, dt, err)
        if payload["sgp4_status"] == "OK":
            samples.append(payload)

    if not samples:
        return {"status": "NOT_CALCULATED", "samples": []}

    return {
        "status": "OK",
        "start_utc": start.isoformat().replace("+00:00", "Z"),
        "hours": hours,
        "step_minutes": step_minutes,
        "sample_count": len(samples),
        "samples": samples,
    }
