def test_health_endpoint(client):
    """Health endpoint should be accessible without authentication"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "200"
    assert data["message"] == "success"
    assert data["data"] == {"status": "ok"}
