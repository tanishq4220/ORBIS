"""
Criterion: Scientific dashboard remains authoritative and accessible after
login - /api/summary reflects the real catalog (18693 objects), not
placeholders, and is reachable using the authenticated session.
"""
import httpx

BASE_URL = "http://localhost:8001/api"
DEMO_EMAIL = "operator@orbis.local"
DEMO_PASSWORD = "ORBIS-DEMO-2026"


def test_summary_reflects_real_catalog_after_login():
    with httpx.Client(base_url=BASE_URL) as client:
        login_resp = client.post(
            "/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
        )
        assert login_resp.status_code == 200, login_resp.text

        summary_resp = client.get("/summary")
        assert summary_resp.status_code == 200, summary_resp.text
        body = summary_resp.json()
        assert body["total_objects"] == 18693
        assert body["subsystems"]["backend"] == "OPERATIONAL"
        assert body["subsystems"]["dataset"] == "OPERATIONAL"
