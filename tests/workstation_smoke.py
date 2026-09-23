"""Public-ingress curl acceptance smoke. Run only at the verification gate."""
import json
import subprocess
import tempfile

BASE = "https://orbis-tracker.preview.emergentagent.com"


def main():
    with tempfile.TemporaryDirectory() as directory:
        jar, headers, bodyfile = [directory + "/" + name for name in ["cookies", "headers", "body"]]

        def call(path, method="GET", body=None, expected=200):
            args = ["curl", "-sS", "--max-time", "120", "-b", jar, "-c", jar, "-D", headers, "-o", bodyfile,
                    "-w", "%{http_code}", "-X", method]
            if body is not None:
                args += ["-H", "Content-Type: application/json", "-d", json.dumps(body)]
            status = int(subprocess.check_output(args + [BASE + "/api" + path], text=True))
            raw = open(bodyfile).read()
            result = json.loads(raw) if raw else None
            assert status == expected, (path, status, str(result)[:500])
            return result

        login = call("/auth/login", "POST", {"email": "operator@orbis.local", "password": "ORBIS-DEMO-2026"})
        assert login["id"] == "operator-demo"
        assert call("/auth/me")["email"] == login["email"]
        call("/connection", "PUT", {"mode": "local", "url": None})
        assert call("/connection/test", "POST", {"mode": "local"})["connected"]
        summary = call("/data/summary")
        assert summary["total_objects"] == summary["satellites"] + summary["debris"] > 0
        assert summary == call("/summary")
        print("PASS canonical public summary:", summary["total_objects"], summary["satellites"], summary["debris"])
        assert call("/data/health")["subsystems"]["backend"] == "OPERATIONAL"
        objects = call("/data/objects?limit=4&sort=data_age&order=asc")
        assert len(objects["objects"]) == 4 and objects["total"] == summary["total_objects"]
        obj = objects["objects"][0]
        oid = obj["id"]
        assert obj["model_confidence"] is not None
        assert call("/data/search?q=" + oid)["results"]
        state = call(f"/data/objects/{oid}/state")
        assert state["state"]["globe_xyz"] is not None
        trajectory = call(f"/data/objects/{oid}/trajectory")
        telemetry = call(f"/data/objects/{oid}/telemetry")
        assert trajectory["samples"] and telemetry["points"] and telemetry["points"][0]["velocity_teme_km_s"]
        positions = call("/data/positions")
        assert positions["count"] == summary["total_objects"] and len(positions["positions"]) == positions["count"] * 3
        assert call("/data/analytics")["summary"]["total_objects"] == summary["total_objects"]
        for level in ["countries", "regions", "cities"]:
            assert call("/geography/" + level)["labels"]
        assert len(call("/environment")["sun_direction"]) == 3
        assert call("/visuals/20580?name=HST")["kind"] == "photograph"
        assert call("/visuals/unknown?name=Unknown")["kind"] == "representative"
        print("PASS catalog, state, bulk SGP4, real trajectory/telemetry, analytics, cartography, image provenance")
        screen = call("/data/conjunctions/screen", "POST", {"object_id": oid, "time_step_min": 10, "window_min": 60, "threshold_km": 50, "top_n": 10})
        assert screen["status"] in ["CLEAR", "POTENTIAL_CONJUNCTION"], screen
        assert len(screen["full_results"]) == screen["objects_screened"] > len(screen["results"])
        sid = screen["screening_id"]
        saved = call("/data/conjunctions/history/" + sid)
        assert saved == screen and call("/data/conjunctions/history/" + sid) == saved
        assert any(row["screening_id"] == sid for row in call("/data/conjunctions/history")["items"])
        print("PASS immutable complete screening:", sid, len(saved["full_results"]), "rows")
        bad = call("/connection/test", "POST", {"mode": "remote", "url": "http://127.0.0.1"})
        assert not bad["connected"]
        bad = call("/data/objects?limit=0", expected=422)
        assert "detail" in bad
        assert call("/data/positions?utc=not-a-date", expected=422)["detail"]
        assert call("/auth/login", "POST", {"email": login["email"], "password": "wrong"}, expected=401)["detail"]
        print("PASS negative cases: SSRF, pagination, UTC validation, invalid credentials")
        assert call("/auth/logout", "POST", expected=204) is None
        assert call("/auth/me") is None
        print("ALL PUBLIC CURL CHECKS PASSED")


if __name__ == "__main__":
    main()