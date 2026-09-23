"""Prototype conjunction screening using SGP4 separations."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import numpy as np
from sgp4.api import Satrec

from propagate import make_satrec, propagate_sat


DEFAULT_STEP_MIN = 10
DEFAULT_WINDOW_MIN = 60
DEFAULT_THRESHOLD_KM = 50.0
DEFAULT_TOP_N = 10


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
    Screen target against catalog using prototype ORBIS conjunction logic.
    Does NOT compute collision probability.
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
        }

    n_steps = (window_min // time_step_min) + 1
    times = [
        start_utc + timedelta(minutes=time_step_min * i) for i in range(n_steps)
    ]

    target_positions: list[Optional[np.ndarray]] = []
    for dt in times:
        pos, _, err = propagate_sat(target_sat, dt)
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
            }
        target_positions.append(pos)

    results: list[dict[str, Any]] = []

    for row in catalog_rows:
        oid = str(row["id"])
        if oid == str(target_id):
            continue
        tle1 = row.get("tle_line1")
        tle2 = row.get("tle_line2")
        if not tle1 or not tle2:
            continue
        try:
            sat = make_satrec(str(tle1), str(tle2))
        except Exception:  # noqa: BLE001
            continue

        distances: list[float] = []
        ok = True
        for i, dt in enumerate(times):
            pos, _, err = propagate_sat(sat, dt)
            if err != 0 or pos is None:
                ok = False
                break
            dist = float(np.linalg.norm(target_positions[i] - pos))
            distances.append(dist)
        if not ok or not distances:
            continue

        min_idx = int(np.argmin(distances))
        min_dist = float(distances[min_idx])
        tca = times[min_idx]
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
        "disclaimer": (
            "PROTOTYPE CONJUNCTION SCREENING — geometric separation only. "
            "Not a validated collision probability."
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
        # Preserve the complete screened matrix for exact history replay. The UI
        # may display only `results` (top-N), but history must not lose rows.
        "full_results": results,
    }
