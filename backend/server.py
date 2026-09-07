"""ORBIS API bootstrap: scientific modules remain the authoritative source."""

from __future__ import annotations

import hashlib
import os
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Cookie, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import jwt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from catalog import row_to_object, store, subsystem_status  # noqa: E402
from history import get_screening, list_history, save_screening  # noqa: E402
from models.auth import AuthUser, LoginRequest, RegisterRequest  # noqa: E402
from models.orbis import ScreenRequest  # noqa: E402
from propagate import (  # noqa: E402
    build_satrec_cache,
    parse_utc,
    propagate_all_globe,
    state_payload,
    trajectory_samples,
    propagate_tle,
)
from screening import screen_object  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _satrec_cache, _ids, _types, _startup_error
    try:
        store.load()
        frame = store.require()
        _ids = frame["ID"].astype(str).tolist()
        _types = frame["Type"].astype(str).tolist()
        _satrec_cache = build_satrec_cache(frame)
        _startup_error = None
        print(f"ORBIS catalog loaded: {len(frame)} objects, {len(_satrec_cache)} TLE slots")
    except Exception as exc:  # noqa: BLE001
        _startup_error = str(exc)
        print(f"ORBIS startup warning: {_startup_error}")
    yield


app = FastAPI(title="ORBIS API", version="2.1.0", lifespan=lifespan)
api_router = APIRouter(prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_satrec_cache: list = []
_ids: list[str] = []
_types: list[str] = []
_startup_error: Optional[str] = None
_users: dict[str, dict[str, str]] = {}
SESSION_SECRET = os.environ["SESSION_SECRET"]


def _password_hash(password: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), b"orbis-local", 120_000).hex()


def _user_payload(user: dict[str, str]) -> AuthUser:
    return AuthUser(id=user["id"], email=user["email"], name=user["name"])


def _seed_demo_user() -> None:
    _users["operator@orbis.local"] = {
        "id": "operator-demo",
        "email": "operator@orbis.local",
        "name": "ORBIS Operator",
        "password_hash": _password_hash("ORBIS-DEMO-2026"),
    }


_seed_demo_user()


def _create_session(user: dict[str, str]) -> str:
    return jwt.encode(
        {
            "sub": user["id"],
            "email": user["email"],
            "name": user["name"],
            "exp": datetime.now(timezone.utc).timestamp() + 86400 * 7,
        },
        SESSION_SECRET,
        algorithm="HS256",
    )


def _current_user(session: Optional[str]) -> AuthUser:
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(session, SESSION_SECRET, algorithms=["HS256"])
        return AuthUser(id=str(payload["sub"]), email=str(payload["email"]), name=str(payload["name"]))
    except (jwt.InvalidTokenError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Session expired") from exc


@api_router.get("/health")
async def health() -> dict[str, Any]:
    statuses = subsystem_status()
    if _startup_error:
        statuses["backend"] = "DEGRADED"
        statuses["dataset"] = "OFFLINE"
    return {
        "status": "ok" if store.loaded else "degraded",
        "service": "ORBIS API",
        "utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "aci_output_available": store.loaded,
        "object_count": int(len(store.df)) if store.df is not None else 0,
        "sgp4_cache_size": len(_satrec_cache),
        "startup_error": _startup_error,
        "subsystems": statuses,
    }


@api_router.post("/auth/login", response_model=AuthUser)
async def login(body: LoginRequest, response: Response) -> AuthUser:
    user = _users.get(body.email.strip().lower())
    if not user or not secrets.compare_digest(user["password_hash"], _password_hash(body.password)):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = _create_session(user)
    response.set_cookie("orbis_session", token, httponly=True, samesite="lax", max_age=86400 * 7)
    return _user_payload(user)


@api_router.post("/auth/register", response_model=AuthUser)
async def register(body: RegisterRequest, response: Response) -> AuthUser:
    email = body.email.strip().lower()
    if email in _users:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": body.name.strip(),
        "password_hash": _password_hash(body.password),
    }
    _users[email] = user
    token = _create_session(user)
    response.set_cookie("orbis_session", token, httponly=True, samesite="lax", max_age=86400 * 7)
    return _user_payload(user)


@api_router.get("/auth/me", response_model=Optional[AuthUser])
async def me(orbis_session: Optional[str] = Cookie(default=None)) -> Optional[AuthUser]:
    if not orbis_session:
        return None
    try:
        return _current_user(orbis_session)
    except HTTPException:
        return None


@api_router.post("/auth/logout", status_code=204)
async def logout(response: Response, orbis_session: Optional[str] = Cookie(default=None)) -> None:
    response.delete_cookie("orbis_session")


@api_router.get("/summary")
async def get_summary() -> dict[str, Any]:
    try:
        frame = store.require()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    type_l = frame["Type"].astype(str).str.lower()
    decision_u = frame["Decision"].astype(str).str.upper()
    ml_u = frame["ML_Prediction"].astype(str).str.upper()
    aci, mc, age = frame["ACI"].dropna(), frame["Model_Confidence"].dropna(), frame["Data_Age_days"].dropna()
    return {
        "total_objects": int(len(frame)),
        "satellites": int((type_l == "satellite").sum()),
        "debris": int((type_l == "debris").sum()),
        "fast": int((decision_u == "FAST").sum()),
        "deep": int((decision_u == "DEEP").sum()),
        "insufficient_data": int((decision_u == "INSUFFICIENT_DATA").sum()),
        "reliable": int((ml_u == "RELIABLE").sum()),
        "low_confidence": int((ml_u == "LOW_CONFIDENCE").sum()),
        "aci": {"mean": float(aci.mean()) if len(aci) else None, "minimum": float(aci.min()) if len(aci) else None, "maximum": float(aci.max()) if len(aci) else None},
        "model_confidence": {"mean": float(mc.mean()) if len(mc) else None, "minimum": float(mc.min()) if len(mc) else None, "maximum": float(mc.max()) if len(mc) else None},
        "data_age_days": {"mean": float(age.mean()) if len(age) else None, "minimum": float(age.min()) if len(age) else None, "maximum": float(age.max()) if len(age) else None},
        "subsystems": subsystem_status(),
    }


@api_router.get("/analytics")
async def get_analytics() -> dict[str, Any]:
    import pandas as pd
    try:
        frame = store.require()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    def hist(series: pd.Series, bins: int = 10) -> list[dict[str, Any]]:
        values = pd.to_numeric(series, errors="coerce").dropna()
        if values.empty:
            return []
        counts, edges = pd.cut(values, bins=bins, retbins=True)
        result = []
        for interval, count in counts.value_counts().sort_index().items():
            result.append({"bin_start": float(interval.left), "bin_end": float(interval.right), "count": int(count)})
        return result

    def counts(column: str, upper: bool = False) -> list[dict[str, Any]]:
        values = frame[column].astype(str)
        if upper:
            values = values.str.upper()
        return values.value_counts().rename_axis("label").reset_index(name="count").to_dict(orient="records")

    return {"type_distribution": counts("Type"), "decision_distribution": counts("Decision", True), "ml_distribution": counts("ML_Prediction", True), "aci_histogram": hist(frame["ACI"]), "model_confidence_histogram": hist(frame["Model_Confidence"]), "data_age_histogram": hist(frame["Data_Age_days"]), "trajectory_consistency_histogram": hist(frame["Trajectory_Consistency"]), "summary": await get_summary()}


@api_router.get("/objects")
async def get_objects(page: int = 1, limit: int = 50, search: Optional[str] = None, object_type: Optional[str] = None, decision: Optional[str] = None, ml_prediction: Optional[str] = None, sort: Optional[str] = None, order: str = "desc") -> dict[str, Any]:
    import pandas as pd
    try:
        frame = store.require().copy()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if search:
        q = search.strip().lower()
        frame = frame[(frame["ID"].astype(str).str.lower().str.contains(q, na=False)) | (frame["Name"].astype(str).str.lower().str.contains(q, na=False)) | (frame["Type"].astype(str).str.lower().str.contains(q, na=False))]
    if object_type:
        frame = frame[frame["Type"].astype(str).str.lower() == object_type.strip().lower()]
    if decision:
        frame = frame[frame["Decision"].astype(str).str.upper() == decision.strip().upper()]
    if ml_prediction:
        frame = frame[frame["ML_Prediction"].astype(str).str.upper() == ml_prediction.strip().upper()]
    sort_map = {"name": "Name", "id": "ID", "type": "Type", "aci": "ACI", "decision": "Decision", "data_age": "Data_Age_days", "model_confidence": "Model_Confidence", "ml_prediction": "ML_Prediction"}
    if sort and sort.lower() in sort_map:
        frame = frame.sort_values(by=sort_map[sort.lower()], ascending=order.lower() != "desc", na_position="last")
    total = int(len(frame)); start = (page - 1) * limit
    page_frame = frame.iloc[start:start + limit]
    return {"page": page, "limit": limit, "total": total, "total_pages": (total + limit - 1) // limit if total else 0, "objects": [row_to_object(row) for _, row in page_frame.iterrows()]}


@api_router.get("/objects/{object_id}")
async def get_object(object_id: str) -> dict[str, Any]:
    row = store.get_row(object_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Object {object_id} not found.")
    return row_to_object(row)


@api_router.get("/objects/{object_id}/state")
async def get_object_state(object_id: str, utc: Optional[str] = None) -> dict[str, Any]:
    row = store.get_row(object_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Object {object_id} not found.")
    obj = row_to_object(row); dt = parse_utc(utc)
    if not obj.get("tle_line1") or not obj.get("tle_line2"):
        return {**obj, "state": state_payload(None, None, dt, -1)}
    pos, vel, err = propagate_tle(obj["tle_line1"], obj["tle_line2"], dt)
    return {**obj, "state": state_payload(pos, vel, dt, err)}


@api_router.get("/objects/{object_id}/trajectory")
async def get_object_trajectory(object_id: str, hours: float = 1.5, step_minutes: float = 2.0, start_utc: Optional[str] = None) -> dict[str, Any]:
    row = store.get_row(object_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Object {object_id} not found.")
    obj = row_to_object(row)
    if not obj.get("tle_line1") or not obj.get("tle_line2"):
        return {"object_id": object_id, "status": "NOT_CALCULATED", "samples": []}
    return {"object_id": object_id, "name": obj.get("name"), **trajectory_samples(obj["tle_line1"], obj["tle_line2"], parse_utc(start_utc), hours=hours, step_minutes=step_minutes)}


@api_router.get("/objects/{object_id}/telemetry")
async def get_object_telemetry(object_id: str, hours: float = 1.0, step_minutes: float = 1.0, start_utc: Optional[str] = None) -> dict[str, Any]:
    traj = await get_object_trajectory(object_id, hours, step_minutes, start_utc)
    return {"object_id": object_id, "status": traj.get("status", "NOT_CALCULATED"), "points": [{"utc": s["utc"], "altitude_km": s.get("altitude_km"), "speed_km_s": s.get("speed_km_s"), "latitude_deg": s.get("latitude_deg"), "longitude_deg": s.get("longitude_deg"), "position_teme_km": s.get("position_teme_km"), "velocity_teme_km_s": s.get("velocity_teme_km_s"), "globe_xyz": s.get("globe_xyz")} for s in traj.get("samples", [])]}


@api_router.get("/positions")
async def get_positions(utc: Optional[str] = None) -> dict[str, Any]:
    if not store.loaded or not _satrec_cache:
        raise HTTPException(status_code=503, detail="DATASET UNAVAILABLE")
    return propagate_all_globe(_satrec_cache, _types, _ids, parse_utc(utc))


@api_router.post("/conjunctions/screen")
async def run_screening(body: ScreenRequest) -> dict[str, Any]:
    row = store.get_row(body.object_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Object {body.object_id} not found.")
    target = row_to_object(row)
    if not target.get("tle_line1") or not target.get("tle_line2"):
        raise HTTPException(status_code=400, detail="Target has no TLE.")
    frame = store.require()
    result = screen_object(target_id=str(target["id"]), target_tle1=str(target["tle_line1"]), target_tle2=str(target["tle_line2"]), catalog_rows=[row_to_object(r) for _, r in frame.iterrows()], time_step_min=body.time_step_min, window_min=body.window_min, threshold_km=body.threshold_km, top_n=body.top_n, start_utc=parse_utc(body.start_utc) if body.start_utc else datetime.now(timezone.utc))
    if result.get("status") != "ERROR":
        save_screening(result)
    return result


@api_router.get("/conjunctions/history")
async def conjunction_history(limit: int = 50) -> dict[str, Any]:
    items = list_history(limit=limit)
    return {"total": len(items), "items": items}


@api_router.get("/conjunctions/history/{screening_id}")
async def conjunction_replay(screening_id: str) -> dict[str, Any]:
    data = get_screening(screening_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Screening not found.")
    return data


@api_router.get("/search")
async def global_search(q: str, limit: int = 20) -> dict[str, Any]:
    import pandas as pd
    try:
        frame = store.require()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    text = q.strip().lower()
    mask = (frame["ID"].astype(str).str.lower().str.contains(text, na=False)) | (frame["Name"].astype(str).str.lower().str.contains(text, na=False)) | (frame["Type"].astype(str).str.lower().str.contains(text, na=False))
    hits = frame[mask].head(limit)
    return {"query": q, "total": int(mask.sum()), "results": [row_to_object(row, include_tle=False) for _, row in hits.iterrows()]}


app.include_router(api_router)