"""Secure password-reset token management for ORBIS."""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timezone

TOKEN_BYTES = 32        # 256 bits of entropy
TOKEN_EXPIRY_SECONDS = 3600  # 1 hour

def generate_token() -> tuple[str, str]:
    """Generate a reset token.
    
    Returns:
        (plaintext_token, token_hash) — store only the hash.
    """
    plaintext = secrets.token_hex(TOKEN_BYTES)
    token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    return plaintext, token_hash

def hash_token(plaintext: str) -> str:
    """Hash a received token for safe database lookup."""
    return hashlib.sha256(plaintext.encode()).hexdigest()

def is_expired(created_at_iso: str) -> bool:
    """Check whether a token's creation timestamp has expired."""
    try:
        created = datetime.fromisoformat(created_at_iso)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - created).total_seconds()
        return elapsed > TOKEN_EXPIRY_SECONDS
    except (ValueError, TypeError):
        return True  # Treat unparseable timestamp as expired
