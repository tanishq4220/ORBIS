"""
Criterion: Paginated catalog and connected routes.
Verifies /api/objects page counts reconcile with /api/summary totals, type
filters (Satellite/Debris) return correctly-scoped pages capped well under
18693 rows per request, and backend search resolves the seeded object 25867
by catalog ID.
"""
import httpx

BASE_URL = "http://localhost:8001/api"
DEMO_EMAIL = "operator@orbis.local"
DEMO_PASSWORD = "ORBIS-DEMO-2026"


def _login(client: httpx.Client) -> None:
    resp = client.post("/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert resp.status_code == 200, resp.text


def test_objects_pagination_reconciles_with_summary_totals():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        _login(client)
        summary = client.get("/summary").json()
        page = client.get("/objects", params={"page": 1, "page_size": 40})
        assert page.status_code == 200, page.text
        body = page.json()
        assert body["total"] == summary["total_objects"] == 18693
        assert len(body["objects"]) <= 40

        sats = client.get("/objects", params={"page": 1, "page_size": 40, "type": "Satellite"})
        assert sats.status_code == 200, sats.text
        sat_body = sats.json()
        assert sat_body["total"] == summary["satellites"] == 16035
        assert all(o["type"] == "Satellite" for o in sat_body["objects"])
        assert len(sat_body["objects"]) <= 40

        debris = client.get("/objects", params={"page": 1, "page_size": 40, "type": "Debris"})
        assert debris.status_code == 200, debris.text
        debris_body = debris.json()
        assert debris_body["total"] == summary["debris"] == 2658
        assert all(o["type"] == "Debris" for o in debris_body["objects"])


def test_search_resolves_seeded_object_by_catalog_id():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        _login(client)
        resp = client.get("/search", params={"q": "25867"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] >= 1
        ids = [r["id"] for r in body["results"]]
        assert "25867" in ids
        target = next(r for r in body["results"] if r["id"] == "25867")
        assert target["name"] == "CXO"


def test_object_detail_state_and_trajectory_routes_connect():
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        _login(client)
        obj = client.get("/objects/25867")
        assert obj.status_code == 200, obj.text
        assert obj.json()["id"] == "25867"

        state = client.get("/objects/25867/state")
        assert state.status_code == 200, state.text

        trajectory = client.get("/objects/25867/trajectory")
        assert trajectory.status_code == 200, trajectory.text
        traj_body = trajectory.json()
        assert traj_body["status"] == "OK"
        assert traj_body["sample_count"] == len(traj_body["samples"])
        assert traj_body["sample_count"] > 0
