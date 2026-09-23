"""
Criterion: Canonical scientific data, model confidence and analytic integrity.
Verifies /api/summary totals reconcile with the briefing's seeded catalog
(18693 total / 16035 satellites / 2658 debris), /api/analytics distributions
sum consistently with those totals, and the authenticated /api/data/* gateway
dispatches the EXISTING /api/summary handler rather than a second implementation.
"""
import httpx

BASE_URL = "http://localhost:8001/api"
DEMO_EMAIL = "operator@orbis.local"
DEMO_PASSWORD = "ORBIS-DEMO-2026"


def _login(client: httpx.Client) -> None:
    resp = client.post("/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert resp.status_code == 200, resp.text


def test_summary_matches_seeded_catalog_totals():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        _login(client)
        resp = client.get("/summary")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total_objects"] == 18693
        assert body["satellites"] == 16035
        assert body["debris"] == 2658
        # model confidence must be populated (non-null) per criterion
        assert body["model_confidence"]["mean"] is not None
        assert 0.0 <= body["model_confidence"]["mean"] <= 1.0
        assert body["aci"]["mean"] is not None


def test_analytics_distributions_reconcile_with_summary():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        _login(client)
        summary = client.get("/summary").json()
        analytics = client.get("/analytics")
        assert analytics.status_code == 200, analytics.text
        body = analytics.json()
        # four distributions expected
        for key in ("type_distribution", "decision_distribution", "ml_distribution", "aci_histogram"):
            assert key in body, f"missing distribution {key}"
        type_total = sum(row["count"] for row in body["type_distribution"])
        decision_total = sum(row["count"] for row in body["decision_distribution"])
        assert type_total == summary["total_objects"] == 18693
        assert decision_total == summary["total_objects"]
        sat_row = next(r for r in body["type_distribution"] if r["label"] == "Satellite")
        deb_row = next(r for r in body["type_distribution"] if r["label"] == "Debris")
        assert sat_row["count"] == 16035
        assert deb_row["count"] == 2658


def test_authenticated_data_gateway_dispatches_existing_summary_handler():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        _login(client)
        direct = client.get("/summary").json()
        via_gateway = client.get("/data/summary")
        assert via_gateway.status_code == 200, via_gateway.text
        gw_body = via_gateway.json()
        assert gw_body["total_objects"] == direct["total_objects"] == 18693
        assert gw_body["satellites"] == direct["satellites"]
        assert gw_body["debris"] == direct["debris"]

        # gateway rejects paths that are not on the scientific allow-list
        blocked = client.get("/data/auth/me")
        assert blocked.status_code == 404, blocked.text


def test_data_gateway_requires_authentication():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as anon:
        resp = anon.get("/data/summary")
        assert resp.status_code in (401, 403), resp.text
