import json
import re
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from lib.auth import require_user
from lib.db import db
from lib.upstream import public_request, validate_origin
from models.auth import AuthUser
from models.workstation import ConnectionConfig, ConnectionTest

router = APIRouter()
SCIENCE_GET = re.compile(r"^(health|summary|analytics|positions|search|objects|objects/[\w.-]+(?:/(?:state|trajectory|telemetry))?|conjunctions/history(?:/[\w-]+)?)$")


@router.get("/connection", response_model=ConnectionConfig)
async def connection(user: AuthUser = Depends(require_user)) -> ConnectionConfig:
    saved = await db.connections.find_one({"_id": user.id})
    return ConnectionConfig(**saved) if saved else ConnectionConfig()


@router.put("/connection", response_model=ConnectionConfig)
async def save_connection(body: ConnectionConfig, user: AuthUser = Depends(require_user)) -> ConnectionConfig:
    if body.mode == "remote":
        if not body.url:
            raise HTTPException(422, "Enter a public ORBIS backend URL")
        origin, _ = await validate_origin(body.url)
        body.url = origin
    else:
        body.url = None
    await db.connections.update_one({"_id": user.id}, {"$set": body.model_dump()}, upsert=True)
    return body


async def local_request(request: Request, method: str, path: str, body: bytes = b"") -> tuple[int, bytes]:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=request.app), base_url="http://orbis.internal") as client:
        response = await client.request(method, "/api/" + path, params=request.query_params,
                                        content=body, headers={"Content-Type": "application/json"})
        return response.status_code, response.content


@router.post("/connection/test", response_model=ConnectionTest)
async def test_connection(body: ConnectionConfig, request: Request, user: AuthUser = Depends(require_user)) -> ConnectionTest:
    try:
        status, payload = await public_request(body.url or "", "GET", "health") if body.mode == "remote" else await local_request(request, "GET", "health")
        data = json.loads(payload)
        connected = status == 200 and isinstance(data, dict) and isinstance(data.get("subsystems"), dict)
        return ConnectionTest(connected=connected, message="ORBIS backend connected" if connected else "DATA UNAVAILABLE — incompatible ORBIS health response",
                              subsystems=data.get("subsystems", {}) if connected else {})
    except HTTPException as exc:
        return ConnectionTest(connected=False, message=str(exc.detail))


@router.api_route("/data/{path:path}", methods=["GET", "POST"])
async def scientific_gateway(path: str, request: Request, user: AuthUser = Depends(require_user)) -> Response:
    if not ((request.method == "GET" and SCIENCE_GET.fullmatch(path)) or (request.method == "POST" and path == "conjunctions/screen")):
        raise HTTPException(404, "Not an allowed scientific endpoint")
    config = await connection(user)
    body = await request.body()
    if config.mode == "remote":
        # Never forward the operator cookie, authorization, or arbitrary headers.
        status, payload = await public_request(config.url or "", request.method, path, request.url.query, body)
        if status == 200:
            value = json.loads(payload)
            required = {"health": ["subsystems", "utc"], "summary": ["total_objects", "satellites", "debris", "aci", "model_confidence"],
                        "positions": ["ids", "positions", "valid", "type_codes", "utc"], "analytics": ["summary", "aci_histogram"],
                        "objects": ["objects", "total", "total_pages"], "search": ["results"]}.get(path, [])
            if not isinstance(value, dict) or any(key not in value for key in required):
                raise HTTPException(502, "DATA UNAVAILABLE — remote backend response is not ORBIS-compatible")
    else:
        status, payload = await local_request(request, request.method, path, body)
    return Response(payload, status_code=status, media_type="application/json", headers={"Cache-Control": "no-store"})