from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_ok():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app_env"] == "local"
    assert body["demo_mode"] is True
