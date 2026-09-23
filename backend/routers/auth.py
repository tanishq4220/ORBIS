import secrets
import uuid
from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from pymongo.errors import DuplicateKeyError
from lib.auth import create_session, current_user, password_hash
from lib.db import db
from lib.session_cookies import set_session_cookie, clear_session_cookie
from models.auth import AuthUser, LoginRequest, RegisterRequest, ForgotPasswordRequest, ResetPasswordRequest
from lib.reset_tokens import generate_token, hash_token, is_expired, TOKEN_EXPIRY_SECONDS
from lib.email_delivery import send_reset_email
from datetime import datetime, timezone

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


@router.post("/forgot-password", status_code=200)
async def forgot_password(body: ForgotPasswordRequest) -> dict:
    """
    Request a password reset link.
    
    SECURITY: Always returns the same response regardless of whether
    the email exists, to prevent account enumeration.
    """
    email = body.email.strip().lower()
    
    generic_response = {"message": "If an account with that email exists, a reset link has been sent."}
    
    user = await db.operators.find_one({"email": email})
    if not user:
        return generic_response
        
    plaintext_token, token_hash = generate_token()
    
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.password_reset_tokens.update_one(
        {"email": email},
        {"$set": {
            "email": email,
            "token_hash": token_hash,
            "created_at": now_iso,
            "used": False,
        }},
        upsert=True,
    )
    
    try:
        send_reset_email(email, plaintext_token)
    except Exception:
        pass  # Delivery failure does not expose user existence
    
    return generic_response


@router.post("/reset-password", status_code=200)
async def reset_password(body: ResetPasswordRequest) -> dict:
    """
    Complete a password reset using a valid token.
    
    Does NOT auto-authenticate after success.
    """
    token_hash = hash_token(body.token.strip())
    
    record = await db.password_reset_tokens.find_one({"token_hash": token_hash})
    
    if not record:
        raise HTTPException(400, "Invalid or expired reset token.")
    
    if record.get("used"):
        raise HTTPException(400, "Reset token has already been used.")
    
    if is_expired(record.get("created_at", "")):
        raise HTTPException(400, "Reset token has expired. Request a new one.")
    
    if len(body.new_password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters.")
    
    email = record["email"]
    user = await db.operators.find_one({"email": email})
    if not user:
        raise HTTPException(400, "Invalid or expired reset token.")
        
    await db.password_reset_tokens.update_one(
        {"token_hash": token_hash},
        {"$set": {"used": True}},
    )
    
    import secrets as _secrets
    new_salt = _secrets.token_hex(16)
    new_hash = password_hash(body.new_password, new_salt)
    
    await db.operators.update_one(
        {"email": email},
        {"$set": {"salt": new_salt, "password_hash": new_hash}},
    )
    
    return {"message": "Password updated successfully. Please sign in with your new password."}