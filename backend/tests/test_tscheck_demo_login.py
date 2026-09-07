"""
Criterion: Demo login through the public ORBIS URL.
Verifies operator@orbis.local / ORBIS-DEMO-2026 signs in against the real
running backend, returns the expected user, sets a session cookie, and
/api/auth/me reflects the authenticated user.
"""
import httpx

BASE_URL = "http://localhost:8001/api"
DEMO_EMAIL = "operator@orbis.local"
DEMO_PASSWORD = "ORBIS-DEMO-2026"


def test_demo_login_happy_path():
    with httpx.Client(base_url=BASE_URL) as client:
        resp = client.post(
            "/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["email"] == DEMO_EMAIL
        assert body["name"] == "ORBIS Operator"

        cookie = resp.cookies.get("orbis_session")
        assert cookie, "expected orbis_session cookie to be set on login"

        me_resp = client.get("/auth/me")
        assert me_resp.status_code == 200, me_resp.text
        me_body = me_resp.json()
        assert me_body["email"] == DEMO_EMAIL
        assert me_body["name"] == "ORBIS Operator"


def test_demo_login_wrong_password_rejected():
    with httpx.Client(base_url=BASE_URL) as client:
        resp = client.post(
            "/auth/login",
            json={"email": DEMO_EMAIL, "password": "not-the-right-password"},
        )
        assert resp.status_code == 401, resp.text
        assert "Invalid email or password" in resp.text

        # no session should have been created
        me_resp = client.get("/auth/me")
        assert me_resp.status_code == 200
        assert me_resp.json() is None

        # a subsequent correct login must still succeed
        good_resp = client.post(
            "/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
        )
        assert good_resp.status_code == 200, good_resp.text
