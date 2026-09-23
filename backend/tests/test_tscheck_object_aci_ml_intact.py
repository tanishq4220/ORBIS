"""Criterion: Object click/search and backend ACI/ML remain intact.

Verifies the backend ACI/ML values for ISS (25544) that the Reliability
panel renders are the authoritative backend-computed values (no frontend
recomputation). Values come from ACI/aci_output.csv after ML feature-unit
fix (TLE n-dot as rev/day^2) and 24 h operational horizon.
"""
import httpx

BASE = "http://localhost:8001/api"
CREDS = {"email": "operator@orbis.local", "password": "ORBIS-DEMO-2026"}


def _authed_client() -> httpx.Client:
    client = httpx.Client(base_url=BASE, timeout=30)
    resp = client.post("/auth/login", json=CREDS)
    assert resp.status_code == 200, f"login failed: {resp.status_code} {resp.text[:200]}"
    return client


def test_iss_aci_ml_values_match_backend():
    client = _authed_client()
    try:
        resp = client.get("/objects/25544")
        assert resp.status_code == 200, f"GET /objects/25544 -> {resp.status_code} {resp.text[:200]}"
        body = resp.json()
        assert body["id"] == "25544"
        assert abs(body["aci"] - 0.672143) < 1e-3, f"aci {body['aci']} drifted from expected ~0.672143"
        assert abs(body["model_confidence"] - 0.463801) < 1e-3, (
            f"model_confidence {body['model_confidence']} drifted from expected ~0.463801"
        )
        assert body["decision"] == "DEEP"
        assert body["ml_prediction"] == "LOW_CONFIDENCE"
    finally:
        client.close()


def test_invalid_object_returns_404():
    client = _authed_client()
    try:
        resp = client.get("/objects/tscheck-nonexistent-object-id")
        assert resp.status_code == 404, f"expected 404 for invalid object id, got {resp.status_code}"
    finally:
        client.close()
