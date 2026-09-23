"""Conjunction screening using SGP4 geometric separations with TCA refinement."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import numpy as np
from sgp4.api import Satrec, jday

from propagate import make_satrec, _jd_fr

DEFAULT_STEP_MIN = 10
DEFAULT_WINDOW_MIN = 60
DEFAULT_THRESHOLD_KM = 50.0
DEFAULT_TOP_N = 10

# Golden ratio constant for 1D TCA interval search
_INV_PHI = (math.sqrt(5.0) - 1.0) / 2.0  # ~0.6180339887


def _separation_at_dt(sat1: Satrec, sat2: Satrec, dt: datetime) -> Optional[float]:
    """Calculate Euclidean distance in km between two satellites at a specific datetime."""
    jd, fr = _jd_fr(dt)
    err1, pos1, _ = sat1.sgp4(jd, fr)
    if err1 != 0 or pos1 is None:
        return None
    err2, pos2, _ = sat2.sgp4(jd, fr)
    if err2 != 0 or pos2 is None:
        return None
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    dz = pos1[2] - pos2[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _refine_tca_golden_section(
    sat1: Satrec,
    sat2: Satrec,
    coarse_tca: datetime,
    half_interval_min: float,
    tolerance_sec: float = 1.0,
    max_iter: int = 15,
) -> tuple[datetime, float]:
    """
    Refine Time of Closest Approach (TCA) and minimum separation distance.

    Uses golden-section search on the time interval [coarse_tca - delta, coarse_tca + delta].
    This provides sub-second TCA precision and exact local minimum separation
    without making assumptions about orbital derivatives.
    """
    a_sec = -half_interval_min * 60.0
    b_sec = half_interval_min * 60.0

    c_sec = b_sec - _INV_PHI * (b_sec - a_sec)
    d_sec = a_sec + _INV_PHI * (b_sec - a_sec)

    fc = _separation_at_dt(sat1, sat2, coarse_tca + timedelta(seconds=c_sec))
    fd = _separation_at_dt(sat1, sat2, coarse_tca + timedelta(seconds=d_sec))

    if fc is None or fd is None:
        coarse_sep = _separation_at_dt(sat1, sat2, coarse_tca)
        return coarse_tca, coarse_sep or float("inf")

    for _ in range(max_iter):
        if (b_sec - a_sec) < tolerance_sec:
            break
        if fc < fd:
            b_sec = d_sec
            d_sec = c_sec
            fd = fc
            c_sec = b_sec - _INV_PHI * (b_sec - a_sec)
            fc = _separation_at_dt(sat1, sat2, coarse_tca + timedelta(seconds=c_sec))
            if fc is None:
                break
        else:
            a_sec = c_sec
            c_sec = d_sec
            fc = fd
            d_sec = a_sec + _INV_PHI * (b_sec - a_sec)
            fd = _separation_at_dt(sat1, sat2, coarse_tca + timedelta(seconds=d_sec))
            if fd is None:
                break

    best_offset_sec = (a_sec + b_sec) / 2.0
    best_tca = coarse_tca + timedelta(seconds=best_offset_sec)
    best_dist = _separation_at_dt(sat1, sat2, best_tca)
    if best_dist is None:
        coarse_sep = _separation_at_dt(sat1, sat2, coarse_tca)
        return coarse_tca, coarse_sep or float("inf")
    return best_tca, best_dist


def screen_object(
    target_id: str,
    target_tle1: str,
    target_tle2: str,
    catalog_rows: list[dict[str, Any]],
    time_step_min: int = DEFAULT_STEP_MIN,
    window_min: int = DEFAULT_WINDOW_MIN,
    threshold_km: float = DEFAULT_THRESHOLD_KM,
    top_n: int = DEFAULT_TOP_N,
    start_utc: Optional[datetime] = None,
) -> dict[str, Any]:
    """
    Screen target against catalog using geometric separation with local TCA refinement.

    Scientific disclosure:
    - Method: geometric_prototype
    - Computes 3D Euclidean distance between SGP4 positions
    - Refines TCA using 1D golden-section search around the coarse minimum
    - This is NOT a validated Pc (collision likelihood) calculation
    - No covariance data is used
    """
    started = datetime.now(timezone.utc)
    if start_utc is None:
        start_utc = started

    try:
        target_sat = make_satrec(target_tle1, target_tle2)
    except Exception as exc:  # noqa: BLE001
        return {
            "screening_id": str(uuid.uuid4()),
            "status": "ERROR",
            "error": f"Target TLE invalid: {exc}",
            "target_id": target_id,
            "timestamp_utc": started.isoformat().replace("+00:00", "Z"),
            "time_step_min": time_step_min,
            "window_min": window_min,
            "threshold_km": threshold_km,
            "results": [],
            "method": "geometric_prototype",
            "method_description": (
                "Geometric SGP4 separation screening. "
                "Computes minimum 3D Euclidean distance between propagated object positions. "
                "This is NOT a validated Pc calculation. "
                "No covariance data is used. Results indicate geometric proximity only."
            ),
            "disclaimer": (
                "PROTOTYPE GEOMETRIC CONJUNCTION SCREENING. "
                "Computes minimum 3D Euclidean separation between SGP4-propagated positions. "
                "This is NOT a validated Pc calculation. "
                "Minimum separation in km IS NOT Pc. "
                "No covariance data is used. Results indicate geometric proximity only."
            ),
        }

    n_steps = (window_min // time_step_min) + 1
    times = [
        start_utc + timedelta(minutes=time_step_min * i) for i in range(n_steps)
    ]

    # Precompute (jd, fr) tuples for all coarse time steps
    times_jd_fr = [_jd_fr(dt) for dt in times]

    # Pre-propagate target positions (as raw float tuples) for all time steps
    target_pos_tuples: list[Optional[tuple[float, float, float]]] = []
    for jd, fr in times_jd_fr:
        err, pos, _ = target_sat.sgp4(jd, fr)
        if err != 0 or pos is None:
            return {
                "screening_id": str(uuid.uuid4()),
                "status": "ERROR",
                "error": "Target SGP4 propagation failed.",
                "target_id": target_id,
                "timestamp_utc": started.isoformat().replace("+00:00", "Z"),
                "time_step_min": time_step_min,
                "window_min": window_min,
                "threshold_km": threshold_km,
                "results": [],
                "method": "geometric_prototype",
                "method_description": (
                    "Geometric SGP4 separation screening. "
                    "Computes minimum 3D Euclidean distance between propagated object positions. "
                    "This is NOT a validated Pc calculation. "
                    "No covariance data is used. Results indicate geometric proximity only."
                ),
                "disclaimer": (
                    "PROTOTYPE GEOMETRIC CONJUNCTION SCREENING. "
                    "Computes minimum 3D Euclidean separation between SGP4-propagated positions. "
                    "This is NOT a validated Pc calculation. "
                    "Minimum separation in km IS NOT Pc. "
                    "No covariance data is used. Results indicate geometric proximity only."
                ),
            }
        target_pos_tuples.append((pos[0], pos[1], pos[2]))

    results: list[dict[str, Any]] = []
    target_id_str = str(target_id)
    half_step_min = time_step_min / 2.0

    for row in catalog_rows:
        oid = str(row.get("id", ""))
        if oid == target_id_str:
            continue
        tle1 = row.get("tle_line1")
        tle2 = row.get("tle_line2")
        if not tle1 or not tle2:
            continue
        try:
            sat = make_satrec(str(tle1), str(tle2))
        except Exception:  # noqa: BLE001
            continue

        # Fast coarse evaluation using pure float math (no numpy array heap allocations)
        min_dist = float("inf")
        min_idx = -1
        ok = True

        for i, (jd, fr) in enumerate(times_jd_fr):
            err, pos, _ = sat.sgp4(jd, fr)
            if err != 0 or pos is None:
                ok = False
                break
            tx, ty, tz = target_pos_tuples[i]
            px, py, pz = pos
            dx = tx - px
            dy = ty - py
            dz = tz - pz
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            if dist < min_dist:
                min_dist = dist
                min_idx = i

        if not ok or min_idx < 0:
            continue

        coarse_tca = times[min_idx]

        # Refine TCA locally around the closest approach if within 5x threshold or top candidate
        if min_dist <= threshold_km * 5.0 or min_dist < 500.0:
            refined_tca, refined_dist = _refine_tca_golden_section(
                target_sat, sat, coarse_tca, half_step_min
            )
            tca = refined_tca
            min_dist = min(min_dist, refined_dist)
        else:
            tca = coarse_tca

        status = (
            "POTENTIAL_CONJUNCTION"
            if min_dist <= threshold_km
            else "CLEAR"
        )
        results.append(
            {
                "object_id": oid,
                "object_name": row.get("name"),
                "object_type": row.get("type"),
                "minimum_separation_km": min_dist,
                "tca_utc": tca.isoformat().replace("+00:00", "Z"),
                "status": status,
            }
        )

    results.sort(key=lambda r: r["minimum_separation_km"])
    top = results[:top_n]
    potentials = [r for r in results if r["status"] == "POTENTIAL_CONJUNCTION"]

    overall = "ERROR" if not results else "POTENTIAL_CONJUNCTION" if potentials else "CLEAR"
    min_sep = top[0]["minimum_separation_km"] if top else None
    tca_overall = top[0]["tca_utc"] if top else None

    finished = datetime.now(timezone.utc)
    return {
        "screening_id": str(uuid.uuid4()),
        "status": overall,
        **({"error": "No secondary objects could be propagated; screening is inconclusive."} if not results else {}),
        "prototype": True,
        "method": "geometric_prototype",
        "method_description": (
            "Geometric SGP4 separation screening with golden-section TCA refinement. "
            "Computes minimum 3D Euclidean distance between propagated object positions. "
            "This is NOT a validated Pc calculation. "
            "No covariance data is used. Results indicate geometric proximity only."
        ),
        "tca_refinement": "golden_section_search",
        "disclaimer": (
            "PROTOTYPE GEOMETRIC CONJUNCTION SCREENING. "
            "Computes minimum 3D Euclidean separation between SGP4-propagated positions. "
            "This is NOT a validated Pc calculation. "
            "Minimum separation in km IS NOT Pc. "
            "No covariance data is used. Results indicate geometric proximity only."
        ),
        "target_id": target_id,
        "target_name": next(
            (r.get("name") for r in catalog_rows if str(r["id"]) == str(target_id)),
            None,
        ),
        "timestamp_utc": started.isoformat().replace("+00:00", "Z"),
        "completed_utc": finished.isoformat().replace("+00:00", "Z"),
        "start_utc": start_utc.isoformat().replace("+00:00", "Z"),
        "time_step_min": time_step_min,
        "window_min": window_min,
        "threshold_km": threshold_km,
        "top_n": top_n,
        "objects_screened": len(results),
        "potential_count": len(potentials),
        "minimum_separation_km": min_sep,
        "tca_utc": tca_overall,
        "results": top,
        "full_results": results,
    }
