"""Tests for auth reset functions."""
import pytest
from lib.reset_tokens import generate_token, hash_token, is_expired
from datetime import datetime, timezone, timedelta

def test_token_generation():
    plaintext, hashed = generate_token()
    assert plaintext != hashed
    assert len(plaintext) == 64
    assert len(hashed) == 64

def test_token_hash_deterministic():
    plaintext = "this_is_a_test_token_123"
    hash1 = hash_token(plaintext)
    hash2 = hash_token(plaintext)
    assert hash1 == hash2

def test_is_expired_recent():
    now = datetime.now(timezone.utc).isoformat()
    assert not is_expired(now)

def test_is_expired_old():
    old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    assert is_expired(old)

def test_is_expired_malformed():
    assert is_expired("not a timestamp")
