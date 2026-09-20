from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_run_rejects_missing_key():
    response = client.post("/run", json={"job": "booking"})
    assert response.status_code == 401


def test_run_rejects_unknown_job_with_key(monkeypatch):
    import app.config as config

    monkeypatch.setattr(config.settings, "WORKER_API_KEY", "test-key", raising=False)
    response = client.post("/run", json={"job": "nope"}, headers={"X-API-Key": "test-key"})
    assert response.status_code == 400
