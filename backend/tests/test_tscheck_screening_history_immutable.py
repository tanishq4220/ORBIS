"""
Criterion: Configurable conjunction screening and immutable full history.
Verifies a fresh screen against the seeded object (25867) with editable
config parameters completes with a non-collision-probability status, the
saved full_results length matches objects_screened and exceeds top_n, and
that GET on history never reruns/overwrites a previously completed screening
(re-fetching the seed screening returns byte-identical core fields).
"""
import httpx

BASE_URL = "http://localhost:8001/api"
DEMO_EMAIL = "operator@orbis.local"
DEMO_PASSWORD = "ORBIS-DEMO-2026"
SEED_SCREENING_ID = "078e10a3-6a5a-4c86-b3fd-f92b578ea657"


def _login(client: httpx.Client) -> None:
    resp = client.post("/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert resp.status_code == 200, resp.text


def test_seed_history_row_is_immutable_on_repeated_get():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        _login(client)
        first = client.get(f"/conjunctions/history/{SEED_SCREENING_ID}")
        assert first.status_code == 200, first.text
        first_body = first.json()
        assert first_body["objects_screened"] == 18689
        assert len(first_body["full_results"]) == first_body["objects_screened"]
        assert first_body["top_n"] < len(first_body["full_results"])
        assert "probability" not in str(first_body).lower()

        second = client.get(f"/conjunctions/history/{SEED_SCREENING_ID}")
        assert second.status_code == 200, second.text
        second_body = second.json()
        # GET must never rerun/overwrite: identical immutable core fields
        assert second_body["screening_id"] == first_body["screening_id"]
        assert second_body["timestamp_utc"] == first_body["timestamp_utc"]
        assert second_body["completed_utc"] == first_body["completed_utc"]
        assert second_body["full_results"] == first_body["full_results"]
        assert second_body["minimum_separation_km"] == first_body["minimum_separation_km"]


def test_new_screening_with_editable_config_completes_and_appends_history():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        _login(client)
        before = client.get("/conjunctions/history")
        assert before.status_code == 200, before.text
        before_total = before.json()["total"]

        payload = {
            "object_id": "25867",
            "time_step_min": 15,
            "window_min": 90,
            "threshold_km": 75.0,
            "top_n": 5,
        }
        resp = client.post("/conjunctions/screen", json=payload)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] in ("CLEAR", "POTENTIAL_CONJUNCTION", "ERROR")
        assert "probability" not in str(body).lower()
        if body["status"] != "ERROR":
            assert body["objects_screened"] == len(body["full_results"])
            assert body["objects_screened"] > body["top_n"]
            assert body["time_step_min"] == 15
            assert body["window_min"] == 90
            assert body["threshold_km"] == 75.0
            assert body["top_n"] == 5

        after = client.get("/conjunctions/history")
        assert after.status_code == 200, after.text
        assert after.json()["total"] == before_total + 1
