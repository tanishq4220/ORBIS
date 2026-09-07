"""Local operator authentication; scientific catalog remains independent."""
import hashlib
import os
import secrets
from datetime import datetime, timezone

import jwt
from fastapi import HTTPException, Request
from models.auth import AuthUser


def password_hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 240_000).hex()


def create_session(user: dict) -> str:
    return jwt.encode({"sub": user["id"], "email": user["email"], "name": user["name"],
                       "exp": datetime.now(timezone.utc).timestamp() + 86400 * 7},
                      os.environ["SESSION_SECRET"], algorithm="HS256")


def current_user(token: str | None) -> AuthUser:
    if not token:
        raise HTTPException(401, "Authentication required")
    try:
        value = jwt.decode(token, os.environ["SESSION_SECRET"], algorithms=["HS256"])
        return AuthUser(id=value["sub"], email=value["email"], name=value["name"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(401, "Session expired") from exc


def require_user(request: Request) -> AuthUser:
    return current_user(request.cookies.get("orbis_session"))


async def ensure_demo_user() -> None:
    from lib.db import db
    salt = secrets.token_hex(16)
    await db.operators.update_one({"email": "operator@orbis.local"}, {"$setOnInsert": {
        "id": "operator-demo", "email": "operator@orbis.local", "name": "ORBIS Operator",
        "salt": salt, "password_hash": password_hash("ORBIS-DEMO-2026", salt),
    }}, upsert=True)