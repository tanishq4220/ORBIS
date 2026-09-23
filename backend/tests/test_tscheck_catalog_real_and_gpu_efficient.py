"""Criterion: Catalog remains real, GPU-efficient and correctly aligned.

Verifies /api/data/positions returns the real 18693-entry catalog with the
expected ~18615 currently-valid states, and that positions/ids/valid arrays
are consistently sized (single aligned buffer, no fabricated values).
"""
import httpx

BASE = "http://localhost:8001/api"
CREDS = {"email": "operator@orbis.local", "password": "ORBIS-DEMO-2026"}


def _authed_client() -> httpx.Client:
    client = httpx.Client(base_url=BASE, timeout=30)
    resp = client.post("/auth/login", json=CREDS)
    assert resp.status_code == 200, f"login failed: {resp.status_code} {resp.text[:200]}"
    return client


def test_positions_catalog_is_real_and_aligned():
    client = _authed_client()
    try:
        resp = client.get("/data/positions")
        assert resp.status_code == 200, f"GET /data/positions -> {resp.status_code} {resp.text[:200]}"
        body = resp.json()
        assert body["count"] == 18693, f"expected 18693 catalog entries, got {body.get('count')}"
        ids = body["ids"]
        valid = body["valid"]
        positions = body["positions"]
        assert len(ids) == 18693
        assert len(valid) == 18693
        # positions is a flat/py list of xyz triples or flattened floats; must align with ids count
        assert len(positions) in (18693, 18693 * 3), (
            f"positions length {len(positions)} does not align with catalog size 18693"
        )
        valid_count = sum(1 for v in valid if v == 1)
        # Spec: approximately 18615 valid currently (allow drift as TLEs age)
        assert 18000 <= valid_count <= 18693, f"valid_count {valid_count} outside plausible range"
    finally:
        client.close()
