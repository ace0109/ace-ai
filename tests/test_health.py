def test_health_endpoint(client, admin_headers):
    response = client.get("/api/health", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "200"
    assert data["message"] == "success"
    assert data["data"] == {"status": "ok"}
