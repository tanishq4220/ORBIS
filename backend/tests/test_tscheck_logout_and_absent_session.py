"""
Criterion: Logout removes browser authentication and stale session state;
invalid/absent sessions do not authenticate.
"""
import httpx

BASE_URL = "http://localhost:8001/api"
DEMO_EMAIL = "operator@orbis.local"
DEMO_PASSWORD = "ORBIS-DEMO-2026"


def test_logout_clears_session():
    with httpx.Client(base_url=BASE_URL) as client:
        login_resp = client.post(
            "/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
        )
        assert login_resp.status_code == 200, login_resp.text

        me_resp = client.get("/auth/me")
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == DEMO_EMAIL

        logout_resp = client.post("/auth/logout")
        assert logout_resp.status_code == 204, logout_resp.text

        after_logout = client.get("/auth/me")
        assert after_logout.status_code == 200
        assert after_logout.json() is None


def test_auth_me_without_cookie_returns_null():
    with httpx.Client(base_url=BASE_URL) as client:
        resp = client.get("/auth/me")
        assert resp.status_code == 200, resp.text
        assert resp.json() is None

        resp2 = client.get("/auth/me", cookies={"orbis_session": "garbage-invalid-token"})
        assert resp2.status_code == 200, resp2.text
        assert resp2.json() is None
