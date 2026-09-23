import secrets
import uuid
from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from pymongo.errors import DuplicateKeyError
from lib.auth import create_session, current_user, password_hash
from lib.db import db
from lib.session_cookies import set_session_cookie, clear_session_cookie
from models.auth import AuthUser, LoginRequest, RegisterRequest

router = APIRouter(prefix="/auth")


@router.post("/login", response_model=AuthUser)
async def login(body: LoginRequest, request: Request, response: Response) -> AuthUser:
    user = await db.operators.find_one({"email": body.email.strip().lower()})
    if not user or not secrets.compare_digest(user["password_hash"], password_hash(body.password, user["salt"])):
        raise HTTPException(401, "Invalid email or password")
    set_session_cookie(response, request, create_session(user))
    return AuthUser(**user)


@router.post("/register", response_model=AuthUser)
async def register(body: RegisterRequest, request: Request, response: Response) -> AuthUser:
    name, email = body.name.strip(), body.email.strip().lower()
    if len(name) < 2 or "@" not in email or len(email) > 254:
        raise HTTPException(422, "Enter a valid name and email")
    salt = secrets.token_hex(16)
    user = {"id": str(uuid.uuid4()), "email": email, "name": name, "salt": salt,
            "password_hash": password_hash(body.password, salt)}
    try:
        await db.operators.insert_one(user)
    except DuplicateKeyError as exc:
        raise HTTPException(409, "An account with this email already exists") from exc
    set_session_cookie(response, request, create_session(user))
    return AuthUser(**user)


@router.get("/me", response_model=AuthUser | None)
async def me(response: Response, orbis_session: str | None = Cookie(default=None)) -> AuthUser | None:
    response.headers["Cache-Control"] = "no-store"
    try:
        return current_user(orbis_session)
    except HTTPException:
        return None


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response) -> None:
    clear_session_cookie(response, request)