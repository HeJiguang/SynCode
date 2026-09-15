from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_reports_up():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}
