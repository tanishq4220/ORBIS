"""Persist completed conjunction screening history for replay."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

HISTORY_DIR = Path(__file__).resolve().parent / "screening_history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
INDEX_FILE = HISTORY_DIR / "index.json"


def _load_index() -> list[dict[str, Any]]:
    if not INDEX_FILE.exists():
        return []
    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []


def _save_index(items: list[dict[str, Any]]) -> None:
    INDEX_FILE.write_text(
        json.dumps(items, indent=2),
        encoding="utf-8",
    )


def save_screening(result: dict[str, Any]) -> dict[str, Any]:
    sid = result["screening_id"]
    path = HISTORY_DIR / f"{sid}.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    summary = {
        "screening_id": sid,
        "timestamp_utc": result.get("timestamp_utc"),
        "target_id": result.get("target_id"),
        "target_name": result.get("target_name"),
        "time_step_min": result.get("time_step_min"),
        "window_min": result.get("window_min"),
        "threshold_km": result.get("threshold_km"),
        "result_count": len(result.get("full_results") or result.get("results") or []),
        "minimum_separation_km": result.get("minimum_separation_km"),
        "tca_utc": result.get("tca_utc"),
        "status": result.get("status"),
        "potential_count": result.get("potential_count"),
    }

    index = _load_index()
    index = [i for i in index if i.get("screening_id") != sid]
    index.insert(0, summary)
    _save_index(index[:200])
    return summary


def list_history(limit: int = 50) -> list[dict[str, Any]]:
    return _load_index()[:limit]


def get_screening(screening_id: str) -> Optional[dict[str, Any]]:
    path = HISTORY_DIR / f"{screening_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
