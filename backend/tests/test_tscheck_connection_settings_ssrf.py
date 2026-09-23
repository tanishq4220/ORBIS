"""
Criterion: Authenticated backend settings, live remote switching and offline recovery.
Verifies /api/connection/test against the real public ORBIS proxy origin round-trips
health/subsystems, private/reserved/nonstandard-port hosts are rejected (SSRF guard),
a non-ORBIS public host produces a truthful offline result (never fake cached data),
and settings are restored to local/hosted mode afterwards (finally-block discipline).
"""
import httpx

BASE_URL = "http://localhost:8001/api"
DEMO_EMAIL = "operator@orbis.local"
DEMO_PASSWORD = "ORBIS-DEMO-2026"
PUBLIC_ORBIS_URL = "https://orbis-tracker.preview.emergentagent.com"


def _login(client: httpx.Client) -> None:
    resp = client.post("/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert resp.status_code == 200, resp.text


def test_default_connection_is_local_hosted():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        _login(client)
        resp = client.get("/connection")
        assert resp.status_code == 200, resp.text
        assert resp.json()["mode"] == "local"


def test_remote_public_orbis_backend_roundtrips_health():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        _login(client)
        resp = client.post("/connection/test", json={"mode": "remote", "url": PUBLIC_ORBIS_URL})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["connected"] is True, body
        assert isinstance(body["subsystems"], dict) and body["subsystems"], body


def test_ssrf_guard_rejects_private_and_nonstandard_hosts():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        _login(client)
        for bad_url in (
            "http://127.0.0.1:8001",
            "http://169.254.169.254/latest/meta-data/",
            "http://localhost:3000",
            "https://orbis-tracker.preview.emergentagent.com:9999",
        ):
            resp = client.post("/connection/test", json={"mode": "remote", "url": bad_url})
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert body["connected"] is False, f"{bad_url} should have been rejected: {body}"

            save_resp = client.put("/connection", json={"mode": "remote", "url": bad_url})
            # save either rejects outright or normalizes but never persists an
            # unreachable/private target as a working remote origin.
            if save_resp.status_code == 200:
                assert "127.0.0.1" not in (save_resp.json().get("url") or "")
                assert "169.254" not in (save_resp.json().get("url") or "")
                assert "localhost" not in (save_resp.json().get("url") or "")


def test_non_orbis_public_host_reports_truthful_offline_state():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        _login(client)
        resp = client.post("/connection/test", json={"mode": "remote", "url": "https://example.com"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["connected"] is False
        assert body["subsystems"] == {}
        message = body["message"].lower()
        assert "unavailable" in message or "offline" in message or "invalid" in message


def test_settings_restored_to_local_after_remote_exercise():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        _login(client)
        put_remote = client.put("/connection", json={"mode": "remote", "url": PUBLIC_ORBIS_URL})
        assert put_remote.status_code == 200, put_remote.text
        assert put_remote.json()["mode"] == "remote"

        try:
            got = client.get("/connection")
            assert got.json()["mode"] == "remote"
        finally:
            reset = client.put("/connection", json={"mode": "local"})
            assert reset.status_code == 200, reset.text
            assert reset.json()["mode"] == "local"
            assert reset.json()["url"] is None

        confirm = client.get("/connection")
        assert confirm.status_code == 200
        assert confirm.json()["mode"] == "local"
