def test_health_endpoint(client, admin_headers):
    response = client.get("/api/health", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
