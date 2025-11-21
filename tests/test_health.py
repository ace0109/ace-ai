from fastapi.testclient import TestClient

from app.services.key_store import key_store
from app.main import app  # noqa: E402


client = TestClient(app)
TEST_API_KEY = key_store.create_key("admin", label="test-suite")["api_key"]


def test_health_endpoint():
    response = client.get("/api/health", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
