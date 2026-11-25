from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.models import TrafficEntry
from datetime import datetime, timezone
import uuid


def test_project_target_scope_and_dashboard():
    with TestClient(app) as client:
        created = client.post("/api/projects", json={"name": "Authorized lab", "description": "Local test"})
        assert created.status_code == 201
        project = created.json()

        target = client.post(f"/api/projects/{project['id']}/targets", json={"origin": "https://lab.example.test/"})
        assert target.status_code == 201
        assert target.json()["origin"] == "https://lab.example.test"

        in_scope = client.get("/api/scope/check", params={"project_id": project["id"], "url": "https://lab.example.test/account?tab=profile"})
        out_of_scope = client.get("/api/scope/check", params={"project_id": project["id"], "url": "https://other.example.test/"})
        assert in_scope.json()["allowed"] is True
        assert out_of_scope.json()["allowed"] is False

        dashboard = client.get("/api/dashboard").json()
        assert dashboard["projects"] == 1
        assert dashboard["websites"] == 1
        assert dashboard["requests"] == 0
        assert dashboard["vulnerabilities"] == 0


def test_target_validation_and_scope_project_lookup():
    with TestClient(app) as client:
        assert client.post("/api/projects", json={"name": "   "}).status_code == 422
        created = client.post("/api/projects", json={"name": "Validation lab"})
        project_id = created.json()["id"]
        bad_targets = [
            "file:///C:/Windows",
            "https://user:secret@example.test",
            "https://example.test/path",
            "https://example.test:invalid",
        ]
        for origin in bad_targets:
            assert client.post(f"/api/projects/{project_id}/targets", json={"origin": origin}).status_code == 422

        missing = client.get("/api/scope/check", params={"project_id": 999999, "url": "https://lab.example.test"})
        assert missing.status_code == 404


def test_traffic_history_is_project_filtered_and_inspectable():
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name": "Traffic history lab"}).json()
        target = client.post(f"/api/projects/{project['id']}/targets", json={"origin": "http://127.0.0.1:8888"}).json()
        entry_id = str(uuid.uuid4())
        with SessionLocal() as db:
            db.add(TrafficEntry(id=entry_id, project_id=project["id"], target_id=target["id"],
                timestamp=datetime.now(timezone.utc), method="POST", url="http://127.0.0.1:8888/login",
                hostname="127.0.0.1", path="/login", query_params="{}", http_version="HTTP/1.1",
                status_code=200, request_headers='{"Authorization":"[REDACTED]"}', response_headers='{}',
                request_body='{"password":"[REDACTED]"}', response_body='{"ok":true}',
                request_size=21, response_size=11, content_type="application/json", duration_ms=4.5))
            db.commit()
        listing = client.get("/api/traffic", params={"project_id": project["id"], "method": "post"})
        assert listing.status_code == 200 and len(listing.json()) == 1
        assert "request_body" not in listing.json()[0]
        detail = client.get(f"/api/traffic/{entry_id}")
        assert detail.json()["request_body"] == '{"password":"[REDACTED]"}'
        assert detail.json()["target_id"] == target["id"]
        assert client.get("/api/traffic", params={"project_id": 999999}).json() == []
        assert client.delete("/api/traffic", params={"project_id": project["id"]}).json()["deleted"] == 1


def test_repeater_blocks_out_of_scope_destination():
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name": "Repeater scope lab"}).json()
        target = client.post(f"/api/projects/{project['id']}/targets", json={"origin": "http://127.0.0.1:8888"}).json()
        entry_id = str(uuid.uuid4())
        with SessionLocal() as db:
            db.add(TrafficEntry(id=entry_id, project_id=project["id"], target_id=target["id"], method="GET",
                url="http://127.0.0.1:8888/", hostname="127.0.0.1", path="/", request_headers="{}", response_headers="{}"))
            db.commit()
        blocked = client.post("/api/repeater/send", json={"project_id": project["id"], "parent_id": entry_id,
            "method": "GET", "url": "http://example.com/", "headers": {}, "body": ""})
        assert blocked.status_code == 403
        assert "outside" in blocked.json()["detail"]
