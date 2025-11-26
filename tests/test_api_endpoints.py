def test_create_and_list_api_keys(client, admin_headers):
    payload = {"role": "user", "label": "pytest-key"}
    create_resp = client.post("/api/keys", json=payload, headers=admin_headers)
    assert create_resp.status_code == 200
    created = create_resp.json()["data"]
    assert created["role"] == "user"
    assert created["label"] == "pytest-key"
    assert created["api_key"]

    list_resp = client.get("/api/keys", headers=admin_headers)
    assert list_resp.status_code == 200
    listed = list_resp.json()["data"]
    assert "items" in listed
    assert any(item["label"] == "pytest-key" and item["role"] == "user" for item in listed["items"])


def test_ingest_and_retrieve_documents(client, super_admin_headers):
    # reset 需要 super_admin 权限
    reset_resp = client.post("/api/reset", headers=super_admin_headers)
    assert reset_resp.status_code == 200

    ingest_resp = client.post("/api/ingest", json={"text": "Test document content"}, headers=super_admin_headers)
    assert ingest_resp.status_code == 200
    assert ingest_resp.json()["data"]["status"] == "success"

    list_resp = client.get("/api/documents", headers=super_admin_headers)
    assert list_resp.status_code == 200
    data = list_resp.json()["data"]
    assert data["total"] == 1
    doc_id = data["documents"][0]["id"]
    assert data["documents"][0]["content"] == "Test document content"

    detail_resp = client.get(f"/api/documents/{doc_id}", headers=super_admin_headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["data"]["content"] == "Test document content"


def test_delete_document(client, admin_headers):
    client.post("/api/ingest", json={"text": "Delete me"}, headers=admin_headers)
    doc_id = client.get("/api/documents", headers=admin_headers).json()["data"]["documents"][0]["id"]

    delete_resp = client.delete(f"/api/documents/{doc_id}", headers=admin_headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json()["data"]["status"] == "success"

    missing_resp = client.get(f"/api/documents/{doc_id}", headers=admin_headers)
    assert missing_resp.status_code == 404


def test_upload_and_delete_by_source(client, super_admin_headers, fake_rag_service):
    # 批量删除需要 super_admin 权限
    file_name = "sample.txt"
    upload_resp = client.post(
        "/api/documents/upload",
        files={"file": (file_name, b"hello world from upload", "text/plain")},
        headers=super_admin_headers,
    )
    assert upload_resp.status_code == 200
    body = upload_resp.json()["data"]
    assert body["filename"] == file_name
    assert body["chunks_created"] == len(fake_rag_service.docs)

    delete_resp = client.delete(
        "/api/documents/batch/by-source",
        params={"source": file_name},
        headers=super_admin_headers,
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["data"]["deleted_count"] == body["chunks_created"]

    list_resp = client.get("/api/documents", headers=super_admin_headers)
    assert list_resp.json()["data"]["total"] == 0


def test_chat_streaming(client, user_headers):
    client.post("/api/ingest", json={"text": "Context content"}, headers=user_headers)

    with client.stream("POST", "/api/chat", json={"message": "Hello"}, headers=user_headers) as response:
        assert response.status_code == 200
        lines = [
            line.decode() if isinstance(line, bytes) else line
            for line in response.iter_lines()
            if line
        ]
    assert any("stream chunk" in line for line in lines)


def test_reset_clears_documents(client, super_admin_headers):
    # reset 需要 super_admin 权限
    client.post("/api/ingest", json={"text": "Will be cleared"}, headers=super_admin_headers)
    before_reset = client.get("/api/documents", headers=super_admin_headers).json()["data"]
    assert before_reset["total"] == 1

    reset_resp = client.post("/api/reset", headers=super_admin_headers)
    assert reset_resp.status_code == 200
    assert reset_resp.json()["data"]["message"] == "Knowledge base reset successfully"

    after_reset = client.get("/api/documents", headers=super_admin_headers).json()["data"]
    assert after_reset["total"] == 0


def test_reset_requires_super_admin(client, admin_headers):
    """测试普通管理员无法重置知识库"""
    reset_resp = client.post("/api/reset", headers=admin_headers)
    assert reset_resp.status_code == 403
    assert "Super admin privileges required" in reset_resp.json()["detail"]


def test_batch_delete_requires_super_admin(client, admin_headers):
    """测试普通管理员无法批量删除"""
    delete_resp = client.delete(
        "/api/documents/batch/by-source",
        params={"source": "test.txt"},
        headers=admin_headers,
    )
    assert delete_resp.status_code == 403
    assert "Super admin privileges required" in delete_resp.json()["detail"]
