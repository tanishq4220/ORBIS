"""
Conjunction screening history persistence for ORBIS.

Architecture:
- PRIMARY: MongoDB collection ``screening_history`` when the DB is available.
- FALLBACK: File-based JSON history when ORBIS_OFFLINE_AUTH=1 or MongoDB is unreachable.

Both backends implement the same interface:
  save_screening(result)  → summary dict
  list_history(limit)     → list[summary]
  get_screening(sid)      → full result or None

Retention: 200 most-recent screenings are kept (same as the original file backend).

MongoDB backend advantages over file storage:
- Correct behaviour under multiple uvicorn workers (atomic updates via $setOnInsert)
- Queryable and inspectable via MongoDB Atlas / compass
- No file-system state to lose or corrupt

The file-based backend is preserved for offline/dev mode and as a migration path.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

HISTORY_DIR = Path(__file__).resolve().parent / "screening_history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
INDEX_FILE = HISTORY_DIR / "index.json"
_file_lock = threading.RLock()

MAX_HISTORY = 200

# ─────────────────────────────────────────────────────────────────────────────
# Utility: build a summary dict from a full screening result
# ─────────────────────────────────────────────────────────────────────────────

def _build_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "screening_id": result["screening_id"],
        "timestamp_utc": result.get("timestamp_utc"),
        "target_id": result.get("target_id"),
        "target_name": result.get("target_name"),
        "time_step_min": result.get("time_step_min"),
        "window_min": result.get("window_min"),
        "threshold_km": result.get("threshold_km"),
        "top_n": result.get("top_n"),
        "result_count": len(result.get("full_results") or result.get("results") or []),
        "minimum_separation_km": result.get("minimum_separation_km"),
        "tca_utc": result.get("tca_utc"),
        "status": result.get("status"),
        "potential_count": result.get("potential_count"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# File-based backend (offline/dev mode)
# ─────────────────────────────────────────────────────────────────────────────

def _file_load_index() -> list[dict[str, Any]]:
    if not INDEX_FILE.exists():
        return []
    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []


def _file_save_index(items: list[dict[str, Any]]) -> None:
    temporary = INDEX_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(items, indent=2), encoding="utf-8")
    temporary.replace(INDEX_FILE)


def _file_save_screening(result: dict[str, Any]) -> dict[str, Any]:
    with _file_lock:
        sid = result["screening_id"]
        uuid.UUID(sid)  # validate format
        path = HISTORY_DIR / f"{sid}.json"
        if path.exists():
            return next(
                (row for row in _file_load_index() if row.get("screening_id") == sid),
                {"screening_id": sid},
            )
        with path.open("x", encoding="utf-8") as f:
            json.dump(result, f, separators=(",", ":"))
        summary = _build_summary(result)
        index = _file_load_index()
        index = [i for i in index if i.get("screening_id") != sid]
        index.insert(0, summary)
        _file_save_index(index[:MAX_HISTORY])
        return summary


def _file_list_history(limit: int = 50) -> list[dict[str, Any]]:
    return _file_load_index()[:limit]


def _file_get_screening(screening_id: str) -> Optional[dict[str, Any]]:
    try:
        uuid.UUID(screening_id)
    except ValueError:
        return None
    path = HISTORY_DIR / f"{screening_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


# ─────────────────────────────────────────────────────────────────────────────
# MongoDB backend (production mode)
# ─────────────────────────────────────────────────────────────────────────────

_USE_LOCAL = os.environ.get("ORBIS_OFFLINE_AUTH", "").strip().lower() in {"1", "true", "yes"}


async def _mongo_save_screening(result: dict[str, Any]) -> dict[str, Any]:
    """
    Upsert a screening result into MongoDB.

    Uses $setOnInsert so concurrent workers don't overwrite an already-saved record.
    After insert, enforces retention by removing documents beyond MAX_HISTORY.
    Returns the summary dict.
    """
    from lib.db import db

    sid = result["screening_id"]
    uuid.UUID(sid)  # validate format

    summary = _build_summary(result)

    # Full document for lookup/replay
    full_doc = {"_id": sid, **result}
    await db.screening_history_full.update_one(
        {"_id": sid},
        {"$setOnInsert": full_doc},
        upsert=True,
    )

    # Summary index document
    summary_doc = {"_id": sid, **summary}
    await db.screening_history.update_one(
        {"_id": sid},
        {"$setOnInsert": summary_doc},
        upsert=True,
    )

    # Enforce retention: keep only the MAX_HISTORY most recent
    # Find the MAX_HISTORY-th newest timestamp
    try:
        count = await db.screening_history.count_documents({})
        if count > MAX_HISTORY:
            # Get the ID of the oldest record beyond the retention limit
            cutoff_cursor = db.screening_history.find(
                {}, {"_id": 1}
            ).sort("timestamp_utc", -1).skip(MAX_HISTORY).limit(1)
            cutoff_docs = await cutoff_cursor.to_list(length=1)
            if cutoff_docs:
                cutoff_id = cutoff_docs[0]["_id"]
                # Delete all records older than (or at) the cutoff
                await db.screening_history.delete_many(
                    {"timestamp_utc": {"$lte": cutoff_id}}
                )
    except Exception as exc:  # noqa: BLE001
        logger.warning("screening_history retention cleanup failed: %s", exc)

    return summary


async def _mongo_list_history(limit: int = 50) -> list[dict[str, Any]]:
    from lib.db import db
    cursor = db.screening_history.find({}, {"_id": 0}).sort("timestamp_utc", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def _mongo_get_screening(screening_id: str) -> Optional[dict[str, Any]]:
    from lib.db import db
    try:
        uuid.UUID(screening_id)
    except ValueError:
        return None
    doc = await db.screening_history_full.find_one({"_id": screening_id})
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc


# ─────────────────────────────────────────────────────────────────────────────
# Public interface — async (callers are FastAPI route handlers)
# ─────────────────────────────────────────────────────────────────────────────

async def save_screening(result: dict[str, Any]) -> dict[str, Any]:
    """Persist a completed screening result; returns the summary."""
    if _USE_LOCAL:
        return _file_save_screening(result)
    try:
        return await _mongo_save_screening(result)
    except Exception as exc:  # noqa: BLE001
        logger.error("MongoDB history save failed (%s) — falling back to file backend", exc)
        return _file_save_screening(result)


async def list_history(limit: int = 50) -> list[dict[str, Any]]:
    """Return the most-recent screening summaries."""
    if _USE_LOCAL:
        return _file_list_history(limit)
    try:
        return await _mongo_list_history(limit)
    except Exception as exc:  # noqa: BLE001
        logger.error("MongoDB history list failed (%s) — falling back to file backend", exc)
        return _file_list_history(limit)


async def get_screening(screening_id: str) -> Optional[dict[str, Any]]:
    """Return a full screening result by ID for replay."""
    if _USE_LOCAL:
        return _file_get_screening(screening_id)
    try:
        result = await _mongo_get_screening(screening_id)
        if result is not None:
            return result
        # Fall through to file backend in case it was saved there before migration
        return _file_get_screening(screening_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("MongoDB history get failed (%s) — falling back to file backend", exc)
        return _file_get_screening(screening_id)
